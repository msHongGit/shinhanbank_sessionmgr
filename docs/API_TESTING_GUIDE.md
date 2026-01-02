# Dev 환경 API 테스트 가이드

> Azure AKS에 배포된 Session Manager API 테스트 방법

---

## 🔍 1. 배포 상태 확인

### AKS 클러스터 연결

```bash
# Azure 로그인
az login

# AKS credentials 가져오기
az aks get-credentials --resource-group shinhan-dev-rg --name shinhan-dev-aks

# Pod 상태 확인
kubectl get pods -n shinhan-dev | grep session-manager

# 예상 출력:
# session-manager-7d8f9c5b6-xxxxx   1/1     Running   0          5m
```

### Service 엔드포인트 확인

```bash
# Service 정보 조회
kubectl get svc session-manager -n shinhan-dev

# External IP 확인 (LoadBalancer 타입인 경우)
kubectl get svc session-manager -n shinhan-dev -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Ingress 확인
kubectl get ingress -n shinhan-dev
```

---

## 🌐 2. API 엔드포인트 접근 방법

### 옵션 A: Ingress를 통한 외부 접근 (권장)

```bash
# Ingress URL 확인
kubectl get ingress session-manager -n shinhan-dev -o jsonpath='{.spec.rules[0].host}'

# 예상 URL:
# https://session-manager-dev.shinhan.azure.com
```

**API 테스트:**
```bash
# Health Check
curl https://session-manager-dev.shinhan.azure.com/health

# Readiness Check
curl https://session-manager-dev.shinhan.azure.com/ready
```

### 옵션 B: LoadBalancer IP 직접 접근

```bash
# External IP 가져오기
EXTERNAL_IP=$(kubectl get svc session-manager -n shinhan-dev -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# API 테스트
curl http://$EXTERNAL_IP:8000/health
```

### 옵션 C: Port Forward (로컬 개발용)

```bash
# Port forwarding 시작
kubectl port-forward -n shinhan-dev svc/session-manager 8000:8000

# 새 터미널에서 테스트
curl http://localhost:8000/health
```

---

## 🧪 3. API 테스트 스크립트

### Health Check

```bash
#!/bin/bash

API_URL="https://session-manager-dev.shinhan.azure.com"

echo "=== Health Check ==="
curl -s $API_URL/health | jq

echo -e "\n=== Readiness Check ==="
curl -s $API_URL/ready | jq
```

### AGW API 테스트

```bash
#!/bin/bash

API_URL="https://session-manager-dev.shinhan.azure.com"
AGW_API_KEY="dev-agw-api-key"  # Secret에서 가져온 실제 키

echo "=== 1. 세션 생성 (AGW) ==="

CREATE_RESPONSE=$(curl -X POST "$API_URL/api/v1/agw/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGW_API_KEY" \
  -d "{
    \"user_id\": \"user_vip_001\",
    \"channel\": \"web\",
    \"customer_profile\": {
      \"user_id\": \"user_vip_001\",
      \"attributes\": {
        \"tier\": \"VIP\",
        \"preferred_language\": \"ko\"
      }
    }
  }" | jq)

echo $CREATE_RESPONSE
GLOBAL_SESSION_KEY=$(echo $CREATE_RESPONSE | jq -r '.global_session_key')
echo "생성된 Global Session Key: $GLOBAL_SESSION_KEY"

echo -e "\n=== 2. 세션 조회 ==="
curl -X GET "$API_URL/api/v1/portal/sessions" \
  -H "X-API-Key: test-portal-key" | jq
```

### MA API 테스트

```bash
#!/bin/bash

API_URL="https://session-manager-dev.shinhan.azure.com"
MA_API_KEY="dev-ma-api-key"
GLOBAL_SESSION_KEY="gsess_20260101_uuid_001"

echo "=== 1. 세션 조회 (Resolve) ==="
curl -X GET "$API_URL/api/v1/ma/sessions/resolve?global_session_key=$GLOBAL_SESSION_KEY&channel=web" \
  -H "X-API-Key: $MA_API_KEY" | jq

echo -e "\n=== 2. 대화 턴 저장 ==="
curl -X POST "$API_URL/api/v1/ma/context/turn" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MA_API_KEY" \
  -d "{
    \"global_session_key\": \"$GLOBAL_SESSION_KEY\",
    \"role\": \"user\",
    \"content\": \"환율 확인하고 싶어요\"
  }" | jq

echo -e "\n=== 3. 고객 프로필 조회 ==="
curl -X GET "$API_URL/api/v1/ma/profiles/CUST001" \
  -H "X-API-Key: $MA_API_KEY" | jq
```

---

## 🔐 4. API Key 관리

### Dev 환경 Secret 확인

```bash
# Secret 조회
kubectl get secret session-manager-secrets -n shinhan-dev -o yaml

# API Key 디코딩
kubectl get secret session-manager-secrets -n shinhan-dev \
  -o jsonpath='{.data.AGW_API_KEY}' | base64 -d

kubectl get secret session-manager-secrets -n shinhan-dev \
  -o jsonpath='{.data.MA_API_KEY}' | base64 -d
```

### 환경 변수 설정 (로컬 테스트용)

```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
export DEV_API_URL="https://session-manager-dev.shinhan.azure.com"
export DEV_AGW_API_KEY="your-dev-agw-key"
export DEV_MA_API_KEY="your-dev-ma-key"
export DEV_PORTAL_API_KEY="your-dev-portal-key"

# 적용
source ~/.zshrc
```

---

## 📊 5. 통합 테스트 (Demo Scenario)

### 전체 시나리오 스크립트

```bash
#!/bin/bash
set -e

API_URL="${DEV_API_URL:-https://session-manager-dev.shinhan.azure.com}"
AGW_KEY="${DEV_AGW_API_KEY}"
MA_KEY="${DEV_MA_API_KEY}"

echo "🚀 Session Manager Dev API 통합 테스트"
echo "API URL: $API_URL"
echo "======================================"

# 1. Health Check
echo -e "\n[1/6] Health Check..."
curl -sf $API_URL/health > /dev/null && echo "✅ OK" || echo "❌ FAILED"

# 2. 세션 생성 (AGW)
echo -e "\n[2/6] 세션 생성 (AGW)..."
CREATE_RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/agw/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGW_KEY" \
  -d "{
    \"user_id\": \"user_vip_001\",
    \"channel\": \"web\",
    \"customer_profile\": {
      \"user_id\": \"user_vip_001\",
      \"attributes\": {
        \"tier\": \"VIP\",
        \"preferred_language\": \"ko\"
      }
    }
  }")
echo $CREATE_RESPONSE | jq
GLOBAL_SESSION_KEY=$(echo $CREATE_RESPONSE | jq -r '.global_session_key')
echo "✅ Global Session Key: $GLOBAL_SESSION_KEY"

# 3. 세션 조회 (MA)
echo -e "\n[3/6] 세션 조회 (MA)..."
RESOLVE_RESPONSE=$(curl -sf -X GET "$API_URL/api/v1/ma/sessions/resolve?global_session_key=$GLOBAL_SESSION_KEY&channel=web" \
  -H "X-API-Key: $MA_KEY")
echo $RESOLVE_RESPONSE | jq
USER_ID=$(echo $RESOLVE_RESPONSE | jq -r '.session.user_id')
echo "✅ User ID: $USER_ID"

# 4. 대화 턴 저장
echo -e "\n[4/6] 대화 턴 저장..."
curl -sf -X POST "$API_URL/api/v1/ma/context/turn" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MA_KEY" \
  -d "{
    \"global_session_key\": \"$GLOBAL_SESSION_KEY\",
    \"role\": \"user\",
    \"content\": \"통합 테스트 메시지입니다\"
  }" | jq
echo "✅ Turn saved"

# 5. 프로필 조회
echo -e "\n[5/6] 고객 프로필 조회..."
curl -sf -X GET "$API_URL/api/v1/ma/profiles/$USER_ID" \
  -H "X-API-Key: $MA_KEY" | jq
echo "✅ Profile retrieved"

# 6. 전체 세션 목록
echo -e "\n[6/6] 전체 세션 목록 조회..."
curl -sf -X GET "$API_URL/api/v1/portal/sessions" \
  -H "X-API-Key: ${DEV_PORTAL_API_KEY}" | jq '.sessions | length'
echo "✅ Sessions listed"

echo -e "\n======================================"
echo "✅ 통합 테스트 완료!"
```

### 스크립트 실행

```bash
# 실행 권한 부여
chmod +x test-dev-api.sh

# 실행
./test-dev-api.sh
```

---

## 🐛 6. 로그 및 디버깅

### Pod 로그 확인

```bash
# 최근 로그 확인
kubectl logs -n shinhan-dev deployment/session-manager --tail=100

# 실시간 로그 스트리밍
kubectl logs -n shinhan-dev deployment/session-manager -f

# 특정 Pod 로그
POD_NAME=$(kubectl get pods -n shinhan-dev -l app=session-manager -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n shinhan-dev $POD_NAME -f
```

### Pod 내부 접근

```bash
# Pod에 Shell 접근
kubectl exec -it -n shinhan-dev deployment/session-manager -- /bin/bash

# Pod 내부에서 Health Check
curl localhost:8000/health
```

### 네트워크 디버깅

```bash
# Service Endpoints 확인
kubectl get endpoints session-manager -n shinhan-dev

# Pod IP 확인
kubectl get pods -n shinhan-dev -o wide

# Service → Pod 연결 확인
kubectl describe svc session-manager -n shinhan-dev
```

---

## 📈 7. 성능 테스트

### 간단한 부하 테스트

```bash
# Apache Bench 사용
ab -n 1000 -c 10 https://session-manager-dev.shinhan.azure.com/health

# wrk 사용
wrk -t4 -c100 -d30s https://session-manager-dev.shinhan.azure.com/health
```

### API 응답 시간 측정

```bash
#!/bin/bash

API_URL="https://session-manager-dev.shinhan.azure.com"

for i in {1..10}; do
  echo "Request $i:"
  time curl -sf $API_URL/health > /dev/null
done
```

---

## 🔄 8. CI/CD 파이프라인과 통합

### GitHub Actions에서 Smoke Test

```yaml
# .github/workflows/docker-smoke.yml 예시
- name: Smoke Test
  run: |
    # API 응답 대기
    for i in {1..30}; do
      if curl -sf $API_URL/health; then
        echo "✅ API is ready"
        break
      fi
      echo "⏳ Waiting for API... ($i/30)"
      sleep 10
    done
    
    # Health Check
    curl -f $API_URL/health || exit 1
    
    # Readiness Check
    curl -f $API_URL/ready || exit 1
```

---

## ⚠️ 9. 주의사항

### API Key 보안

- ❌ **절대 코드에 하드코딩하지 마세요**
- ✅ 환경 변수 사용: `export DEV_AGW_API_KEY="..."`
- ✅ Secret 관리: Kubernetes Secret, GitHub Secret
- ✅ 로컬 테스트: `.env` 파일 (`.gitignore`에 추가)

### Rate Limiting

```bash
# Dev 환경 제한 (예시):
# - 분당 100 요청
# - 동시 연결 20개

# 429 Too Many Requests 발생 시:
# - 요청 간격 조정
# - 재시도 로직 추가
```

### Dev vs Prod

| 항목 | Dev | Prod |
|------|-----|------|
| API URL | `session-manager-dev.*` | `session-manager.*` |
| API Key | `dev-*-key` | Production Key (Vault) |
| Rate Limit | 느슨함 (100/min) | 엄격함 (1000/min) |
| 로그 레벨 | DEBUG | INFO/WARNING |
| Mock DB | ✅ 사용 | ❌ 실제 PostgreSQL/Redis |

---

## 📚 추가 리소스

- [DEPLOYMENT.md](./DEPLOYMENT.md) - 배포 가이드
- [DEMO_SCENARIO_V2.md](./DEMO_SCENARIO_V2.md) - API 시나리오
- [Session_Manager_API.md](./Session_Manager_API.md) - API 스펙

---

## 🆘 문제 해결

### 1. API 접근 불가

```bash
# 1. Pod 상태 확인
kubectl get pods -n shinhan-dev

# 2. Service 확인
kubectl get svc session-manager -n shinhan-dev

# 3. Ingress 확인
kubectl get ingress -n shinhan-dev

# 4. 로그 확인
kubectl logs -n shinhan-dev deployment/session-manager
```

### 2. 401 Unauthorized

- API Key 확인: `kubectl get secret session-manager-secrets -n shinhan-dev`
- Header 확인: `X-API-Key` 대소문자 정확히
- 올바른 환경 Key 사용 (dev vs prod)

### 3. 503 Service Unavailable

```bash
# Service Endpoints 확인
kubectl get endpoints session-manager -n shinhan-dev

# Pod Readiness 확인
kubectl describe pod <pod-name> -n shinhan-dev
```

---

**마지막 업데이트**: 2026년 1월 2일  
**작성자**: Session Manager Team
