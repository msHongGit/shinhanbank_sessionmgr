# Sprint 5 업데이트 사항

## 1. JWT 인증 토큰 기반 세션 관리 변경

### 1.1 개요
- **기존 방식**: API Key 기반 인증, 세션 조회 시 TTL 연장 (ping API)
- **변경 사항**: JWT 토큰 기반 인증으로 통일, Refresh Token으로 TTL 연장

### 1.2 세션 생성 및 인증 플로우

**전체 플로우:**
```
1. 세션 생성 (Client → AGW → Session Manager)
   ├─ Session Manager: global_session_key 생성 및 Redis 저장
   ├─ Session Manager: jti(UUID) 생성
   ├─ Session Manager: Redis에 `jti:{jti}` -> `global_session_key` 매핑 저장 (TTL: 5분)
   ├─ Session Manager: JWT 토큰 발급 (Access Token + Refresh Token, jti 포함)
   ├─ Session Manager → AGW: global_session_key, Access Token, Refresh Token, jti 반환
   └─ AGW → Client: 쿠키로 JWT 토큰만 전달 (httpOnly, Secure)
      ⚠️ global_session_key는 Client에 전달하지 않음

2. SSE 연결 설정 (Client → Relay Server)
   ├─ Client: 헤더에 AccessToken 포함하여 SSE 연결 요청 (`Authorization: Bearer <access_token>`)
   └─ Relay(SSE) Server: 헤더에서 AccessToken 추출 및 검증 (Secret Key로만 검증)

3. 사용자 인증 (Client → SoL WAS)
   └─ Client가 SoL WAS로 대신 요청(우회 방법) → SoL WAS <-> SSE GW 확인 → 사용자 정보 전달
   └─ 이 시점이 사용자 인증 완료 상태

4. 사용자 정보 저장 (SSE GW → AGW → Session Manager)
   └─ AGW → Session Manager: `POST /api/v1/sessions/{global_session_key}/realtime-personal-context`

5. Invoke 시작 (사용자 인증 완료 후)
   ├─ 사용자 인증 완료 전까지는 invoke 불가
   └─ 사용자 인증 완료 후부터 Client → AGW는 access token 사용하여 invoke 가능
   └─ AGW 처리 플로우:
      ├─ AGW → Session Manager: `GET /api/v1/sessions/verify` 호출
      │  └─ 요청: Access Token (쿠키 또는 헤더)
      │  └─ 응답: {global_session_key, user_id, session_state, is_alive, expires_at}
      ├─ AGW → Master Agent: invoke(global_session_key, user_message)
      └─ Master Agent → Session Manager: 내부 서비스 API 호출 (global_session_key 사용)
         ├─ 세션 조회: `GET /api/v1/sessions/{global_session_key}`
         ├─ 세션 상태 업데이트: `PATCH /api/v1/sessions/{global_session_key}/state`

6. 기타 API 호출
   ├─ 세션 검증: Client → AGW → Session Manager: `GET /api/v1/sessions/verify` (토큰으로 요청, global_session_key 응답)
   ├─ Ping (세션 상태 확인): Client → AGW → Session Manager: `GET /api/v1/sessions/ping` (토큰으로 요청, 단순 세션 상태 확인)
   ├─ 세션 종료: Client → AGW → Session Manager: `DELETE /api/v1/sessions` (토큰으로 요청)
   ├─ 토큰 갱신: Client → AGW → Session Manager: `POST /api/v1/sessions/refresh` (Refresh Token 기반)
   └─ 세션 전체 정보 조회: Master Agent → Session Manager: `GET /api/v1/sessions/{global_session_key}/full`
```


**JWT 검증 시점:**

**Client → AGW → Session Manager API (토큰 기반, Client는 global_session_key를 알지 못함):**
- **세션 생성**: `POST /api/v1/sessions` (JWT 없이 호출 가능, 세션 생성 전이므로)
- **토큰 검증 및 세션 정보 조회**: `GET /api/v1/sessions/verify` (새 API, 구현 예정)
  - 요청: Access Token (쿠키 또는 헤더)
  - 응답: `{global_session_key, user_id, session_state, is_alive, expires_at}`
  - 목적: AGW가 invoke 전에 토큰 검증 및 global_session_key 획득
- **Ping (세션 상태 확인)**: `GET /api/v1/sessions/ping` (경로에서 global_session_key 제거, TTL 연장 제거)
  - 요청: Access Token (쿠키 또는 헤더)
  - 응답: `{is_alive, expires_at}` (TTL 연장 안 함)
- **세션 종료**: `DELETE /api/v1/sessions` (경로에서 global_session_key 제거)
  - 요청: Access Token (쿠키 또는 헤더)
  - 처리: 토큰에서 jti 추출 → global_session_key 조회 → 세션 종료
- **토큰 갱신**: `POST /api/v1/sessions/refresh`
  - 요청: Refresh Token (쿠키 또는 헤더)
  - 응답: 새 Access Token, Refresh Token, global_session_key (AGW에만 전달)
  - 호출 주체: AGW (Client는 AGW를 통해서만 호출)

**Master Agent API → Session Manager(내부 서비스, global_session_key 사용):**
- **세션 조회**: `GET /api/v1/sessions/{global_session_key}`
- **세션 상태 업데이트**: `PATCH /api/v1/sessions/{global_session_key}/state`
- **사용자 정보 저장**: `POST /api/v1/sessions/{global_session_key}/realtime-personal-context`
- **실시간 API 결과 저장**: `POST /api/v1/sessions/{global_session_key}/api-results`
- **세션 전체 정보 조회**: `GET /api/v1/sessions/{global_session_key}/full`

**JWT 검증 프로세스 (각 API 호출 시):**
1. Access Token 추출 (우선순위):
   - 헤더에서 추출: `Authorization: Bearer <access_token>`
   - 헤더에 없으면 쿠키에서 추출: Cookie의 `access_token` 값 사용
2. JWT 서명 검증: Secret Key로 서명 검증
3. 만료 시간 확인: `exp` 필드 확인
4. 토큰 타입 확인: `type: "access"` 확인
5. jti 추출 및 Redis 조회: `jti:{jti}` -> `global_session_key` 매핑 조회
6. 세션 존재 여부 확인: Redis에서 세션 조회
7. API 로직 실행: 검증 통과 시에만 API 로직 실행

**참고:**
- Relay Server(SSE GW)는 쿠키에서 AccessToken 추출 후 Secret Key로 서명 검증만 수행 (Redis 조회 없음)

### 1.3 JWT 토큰 설계

#### 기본 사항
- **용도**: 서비스 간 인증 + 세션 만료시간 연장 (통합)
- **API 인증**: JWT로 통일 (기존 API Key 방식 제거)
- **JWT 발급/검증**: Session Manager가 담당
- **JTI 생성**: 세션 생성 시 별도 UUID로 생성 (global_session_key와 분리)

#### JTI 매핑 저장
- **시점**: 세션 생성 시 JWT 발급과 함께 Redis에 저장
- **Key**: `jti:{jti}` (예: `jti:550e8400-e29b-41d4-a716-446655440000`)
- **Value**: `global_session_key` (예: `gsess_20260108123456_abcd12`)
- **TTL**: Access Token 만료 시간과 동일 (5분)

#### 토큰 구조

**Access Token:**
- 용도: 서비스 인증 + 세션 TTL 연장용
- 유효기간: 5분
- Payload: `{jti, sub, exp, iat, type: "access"}`

**Refresh Token:**
- 용도: Access Token 갱신용
- 유효기간: 1시간
- Payload: `{jti, sub, exp, iat, type: "refresh"}`

**공통 필드:**
- `jti`: JWT ID (UUID)
- `sub`: Subject (user_id)
- `exp`: 만료 시각
- `iat`: 발급 시각
- `type`: 토큰 타입 (access 또는 refresh)

#### TTL 연장 로직

**Session Manager 내부 처리** (`POST /api/v1/sessions/refresh` API 호출 시):

Refresh Token으로 새 Access Token 발급 시 Session Manager가 수행하는 내부 로직:
1. Refresh Token의 jti 추출
2. Redis에서 `jti:{jti}` -> `global_session_key` 조회
3. 해당 세션의 TTL 연장 (`session:{global_session_key}` TTL 갱신)
4. 새 Access Token 발급 (동일 jti 사용)
5. 새 Refresh Token 발급 (Refresh Token Rotation)
   - 기존 Refresh Token이 만료되면 새 Refresh Token 발급
   - 보안 강화를 위해 Refresh Token도 주기적으로 갱신
6. Redis에 `jti:{jti}` 매핑 TTL 갱신 (5분)

### 1.4 부연 설명

#### 새로운 API: 토큰 검증 및 세션 정보 조회

**엔드포인트:** `GET /api/v1/sessions/verify` (구현 예정)

**목적:** AGW가 invoke 전에 토큰 검증 및 global_session_key 획득

**요청:**
- 헤더: `Authorization: Bearer <access_token>` 또는 쿠키의 `access_token`

**응답:**
```json
{
  "global_session_key": "gsess_20260108123456_abcd12",
  "user_id": "0616001905",
  "session_state": "talk",
  "is_alive": true,
  "expires_at": "2024-01-01T12:05:00Z"
}
```

**처리 로직:**
1. Access Token 추출 및 검증
2. jti 추출
3. Redis에서 `jti:{jti}` → `global_session_key` 조회
4. 세션 존재 여부 확인
5. global_session_key 및 기본 정보 반환

#### Ping API 변경

**엔드포인트:** `GET /api/v1/sessions/ping` (경로에서 global_session_key 제거)

**변경 사항:**
- 경로에서 `global_session_key` 제거 (토큰에서 추출)
- TTL 연장 기능 제거 (Refresh Token 발급 시 TTL 연장)
- 세션 생존 여부만 확인

**요청:**
- 헤더: `Authorization: Bearer <access_token>` 또는 쿠키의 `access_token`

**응답:**
```json
{
  "is_alive": true,
  "expires_at": "2024-01-01T12:05:00Z"  // 현재 만료 시각 (연장 안 함)
}
```

**처리 로직:**
1. Access Token 추출 및 검증
2. jti 추출 → global_session_key 조회
3. 세션 존재 여부 확인
4. 현재 만료 시각 반환 (TTL 연장 안 함)

#### 세션 종료 API 변경

**엔드포인트:** `DELETE /api/v1/sessions` (경로에서 global_session_key 제거)

**변경 사항:**
- 경로에서 `global_session_key` 제거 (토큰에서 추출)

**요청:**
- 헤더: `Authorization: Bearer <access_token>` 또는 쿠키의 `access_token`
- 쿼리 파라미터: `close_reason` (선택)

**처리 로직:**
1. Access Token 추출 및 검증
2. jti 추출 → global_session_key 조회
3. 세션 종료 처리

#### Relay Server 검증
- Client → Relay(SSE) Server: 헤더에 AccessToken 포함하여 SSE 연결 요청 (`Authorization: Bearer <access_token>`)
- Relay 서버 검증 프로세스:
  1. 헤더에서 AccessToken 추출 (`Authorization: Bearer <access_token>`)
  2. JWT 서명 검증: Secret Key로 서명 검증
  3. 만료 시간 확인: `exp` 필드 확인
  4. 토큰 타입 확인: `type: "access"` 확인
- ⚠️ Redis 조회는 수행하지 않음 (Secret Key 검증만으로 충분)ㄴ

#### 클라이언트 요청
- Client → AGW: `Authorization: Bearer <JWT>` 또는 쿠키의 AccessToken 사용
- Client → SSE 연결 요청: 헤더에 AccessToken 포함 (`Authorization: Bearer <access_token>`)
- ⚠️ Client는 global_session_key를 알지 못함 (토큰만 사용)

#### 토큰 만료와 재연결

**토큰 만료 감지:**
- Client: API 호출 시 401 응답 수신 또는 SSE 연결 에러 발생 시 토큰 만료로 판단
- AGW: Session Manager API 호출 시 401 응답 수신 시 토큰 만료로 판단

**토큰 갱신 플로우** (Client는 AGW를 통해서만 연동):
1. Client → AGW: 토큰 갱신 요청 (Refresh Token은 쿠키에 자동 포함)
2. AGW → Session Manager: `POST /api/v1/sessions/refresh` 호출
   - 요청: Refresh Token (쿠키에서 추출 또는 헤더로 전달)
3. Session Manager 내부 처리 (위의 "TTL 연장 로직" 참조):
   - Refresh Token 검증 및 jti 추출
   - Redis에서 세션 조회 및 TTL 연장
   - 새 Access Token + Refresh Token 발급
4. Session Manager → AGW: 새 Access Token, Refresh Token, global_session_key 반환
   - ⚠️ global_session_key도 함께 반환 (AGW가 필요 시 사용)
5. AGW → Client: 새 토큰을 쿠키로 업데이트 (httpOnly, Secure)
   - ⚠️ global_session_key는 Client에 전달하지 않음
6. Client: 원래 요청 재시도 또는 SSE 재연결

**AGW의 토큰 검증 및 global_session_key 획득:**
- **방식**: 매번 토큰 검증 API 호출
- **사용 시점**:
  - Invoke 전: `GET /api/v1/sessions/verify` 호출하여 global_session_key 획득
  - 사용자 정보 저장 전: `GET /api/v1/sessions/verify` 호출하여 global_session_key 획득

**AGW의 토큰 갱신 로직:**
- API 호출 시 401 응답 수신 시 자동으로 토큰 갱신 시도
- 토큰 갱신 성공 시 원래 요청 자동 재시도
- 토큰 갱신 실패 시 Client에 세션 만료 안내

### 1.5 참고 사항
- 쿠키에는 AccessToken, RefreshToken 저장
- 쿠키 생성 시 옵션: httpOnly (필수), Secure
- Access Token(JWT): Session Manager가 발급하고, Relay Server(SSE GW)도 이 JWT를 검증할 수 있어야 함
  - **Secret Key 공유**: `JWT_SECRET_KEY` 환경변수만 공유하면 검증 가능 (Redis 공유 불필요)
  - Relay Server는 Secret Key로 서명 검증만 수행하며, Redis 조회는 하지 않음
- 모든 API 인증을 JWT로 통일 (기존 X-API-Key 헤더 방식 제거)

### 1.6 구현 라이브러리

#### JWT 라이브러리
- **사용 라이브러리**: `PyJWT[cryptography]>=2.8.0`
- **설치**: `pip install PyJWT[cryptography]` 또는 `uv add PyJWT[cryptography]`
- **알고리즘**: HS256 (HMAC-SHA256)
- **Secret Key**: 환경변수로 관리 (`JWT_SECRET_KEY`)

#### 보안 고려사항
- **JWT는 암호화가 아닌 서명(Signing) 사용**: Payload는 Base64 인코딩되어 디코딩 가능하지만, 서명으로 무결성 보장
- **HTTPS 필수**: 전송 중 암호화는 HTTPS로 처리 (쿠키 `Secure` 옵션 사용)
- **민감 정보 포함 금지**: Payload에 민감한 사용자 정보 포함하지 않음 (`user_id`만 포함)
- **Secret Key 관리**: 환경변수로 관리하며, 절대 코드에 하드코딩 금지

#### 구현 예시

**토큰 생성:**
```python
import jwt
from datetime import datetime, timedelta, UTC
from uuid import uuid4

# Access Token 생성
def create_access_token(jti: str, user_id: str, role: str, secret_key: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=5)
    payload = {
        "jti": jti,
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access"
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

# Refresh Token 생성
def create_refresh_token(jti: str, user_id: str, role: str, secret_key: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    payload = {
        "jti": jti,
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh"
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")
```

**토큰 검증:**
```python
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

def verify_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except DecodeError:
        raise ValueError("Invalid token format")
    except InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")

def get_jti_from_token(token: str, secret_key: str) -> str | None:
    try:
        payload = verify_token(token, secret_key)
        return payload.get("jti")
    except ValueError:
        return None
```

**환경변수 설정:**
```env
# JWT 설정
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=5
JWT_REFRESH_TOKEN_EXPIRE_HOURS=1
```

**Refresh Token Rotation:**
- Refresh Token이 만료되면 새 Refresh Token도 함께 발급
- 보안 강화를 위해 Refresh Token도 주기적으로 갱신
- 기존 Refresh Token은 무효화되고 새 Refresh Token 사용

---

## 2. 개인화 프로파일 적재

### 2.1 배치 프로파일
- **현재 상태**: Mock 데이터로 구현됨
- **구현 필요**: 실제 MariaDB에서 월/일 기준 2개 테이블 조회
- **저장 방식**: Long-term 컨텍스트로 관리
- **저장 시점**: 세션 생성 시
- **조회 시**: 실시간 프로파일과 통합하여 Master Agent에 제공

### 2.2 실시간 프로파일

#### API 설계
- **API 엔드포인트**: `POST /api/v1/sessions/{global_session_key}/realtime-personal-context`
- **API 이름**: `realTimePersonalContextUpdate`
- **호출 시점**: SOL 인증 완료 후 (세션 생성 이후, 사용자 인증 완료 단계)
- **호출 주체**: AGW (내부 서비스)
- **호출 플로우**:
  1. SSE GW → AGW: 사용자 정보 저장 요청 (access_token 포함)
  2. AGW → Session Manager: `GET /api/v1/sessions/verify` 호출하여 global_session_key 획득
  3. AGW → Session Manager: `POST /api/v1/sessions/{global_session_key}/realtime-personal-context` 호출
- **구현 필요**

#### 기능
- Redis에 `profile:realtime:{user_id}` 저장
- 세션의 `customer_profile` 스냅샷 업데이트
- 배치 프로파일과 통합하여 Master Agent에 제공

---

## 3. 대화이력 Context 적재
- **현재 상태**: `conversation_history`로 구현되어 있음
- **추가 작업**: 없음

---

## 4. Task Queue Context 적재
- **현재 상태**: 구현되어 있음
- **추가 작업**: 없음

---

## 5. 실시간 API log 저장

### 5.1 현재 상태
- **API 엔드포인트**: `POST /api/v1/sessions/{global_session_key}/api-results`
- **상태**: 구현 완료
- **추가 작업**: 서비스팀에 API 스펙 다시 공유 필요

### 5.2 API 구조

#### Turn 메타데이터 Key
- **Key 패턴**: `turns:{global_session_key}` (세션 단위로 관리)
- **데이터 타입**: List (JSON 문자열 배열)
- **TTL**: 300초 (세션과 동일)