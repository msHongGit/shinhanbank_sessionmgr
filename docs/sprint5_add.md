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
   ├─ Session Manager: Redis에 `jti:{jti}` -> `global_session_key` 매핑 저장 (TTL: 30분)
   ├─ Session Manager: JWT 토큰 발급 (Access Token + Refresh Token, jti 포함)
   ├─ Session Manager → AGW: global_session_key, Access Token, Refresh Token, jti 반환
   ├─ AGW → Client: 쿠키로 JWT 토큰 전달 (httpOnly, Secure)
   └─ Session Manager → Relay(SSE) Server: jti 전달 (소켓 매핑용)

2. SSE 연결 설정 (AGW → Relay Server)
   └─ AGW: SSE 서버에 SoL WAS로 사용자 정보 요청 API / Client로 세션키와 SSE url 전달

3. 사용자 인증 (Client → SoL WAS)
   └─ client가 sol was로 대신 요청 → sol was <-> sse gw 확인 → 사용자 정보 쿠키 전달

4. 사용자 정보 저장 (AGW → Session Manager)
   ├─ `POST /api/v1/sessions/{global_session_key}/realtime-personal-context` API 호출
   └─ 이 시점부터 "사용자 인증 완료" 상태

5. Invoke 시작 (사용자 인증 완료 후)
   ├─ 사용자 인증 완료 전까지는 invoke 불가
   └─ 사용자 인증 완료 후부터 access token 사용하여 invoke 가능
```

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
- **TTL**: Access Token 만료 시간과 동일 (30분)

#### 토큰 구조

**Access Token:**
- 용도: 서비스 인증 + 세션 TTL 연장용
- 유효기간: 30분
- Payload: `{jti, sub, role, exp, iat, type: "access"}`

**Refresh Token:**
- 용도: Access Token 갱신용
- 유효기간: 7일
- Payload: `{jti, sub, role, exp, iat, type: "refresh"}`

**공통 필드:**
- `jti`: JWT ID (UUID)
- `sub`: Subject (user_id 또는 service_id)
- `role`: 서비스 구분 (user, agw, ma, portal 등)
- `exp`: 만료 시각
- `iat`: 발급 시각
- `type`: 토큰 타입 (access 또는 refresh)

#### TTL 연장 로직

Refresh Token으로 새 Access Token 발급 시:
1. Refresh Token의 jti 추출
2. Redis에서 `jti:{jti}` -> `global_session_key` 조회
3. 해당 세션의 TTL 연장 (`session:{global_session_key}` TTL 갱신)
4. 새 Access Token 발급 (동일 jti 사용)
5. Redis에 `jti:{jti}` 매핑 TTL 갱신 (30분)

### 1.4 부연 설명

#### Relay Server 연동
- Session Manager → Relay(SSE) Server: jti 전달 (세션 생성 시 즉시)
- Relay 서버는 jti를 Key로 하여 클라이언트의 접속 소켓을 매핑
- relay는 jti 값을 보면 전달 client 식별

#### 클라이언트 요청
- Client → AGW: `Authorization: Bearer <JWT>`
- Client → SSE 연결 요청: 쿠키 또는 쿼리 파라미터 사용 (쿠키 사용)

#### 토큰 만료와 재연결
- Client는 SSE 에러 발생 시, 만료 에러라면 `/refresh`를 통해 토큰을 갱신

### 1.5 참고 사항
- 쿠키에는 AccessToken, RefreshToken 저장
- 쿠키 생성 시 옵션: httpOnly (필수), Secure
- Access Token(JWT): Session Manager가 발급하고, Relay Server도 이 JWT를 검증할 수 있어야 함 (Secret Key 공유 필요)
- 모든 API 인증을 JWT로 통일 (기존 X-API-Key 헤더 방식 제거)

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

## 5. 실시간 API 조회 로그

### 5.1 현재 상태
- **API 엔드포인트**: `POST /api/v1/sessions/{global_session_key}/api-results`
- **상태**: 구현 완료
- **추가 작업**: 서비스팀에 API 스펙 다시 공유 필요

### 5.2 API 구조

#### Turn 메타데이터 Key
- **Key 패턴**: `turns:{global_session_key}` (세션 단위로 관리)
- **데이터 타입**: List (JSON 문자열 배열)
- **TTL**: 300초 (세션과 동일)