# Session Manager 배포 가이드

> **Sprint 2 기준** - Azure AKS + ArgoCD + GitHub Actions

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
3. [자동 배포 (GitHub Actions)](#자동-배포-github-actions)
4. [수동 배포](#수동-배포)
5. [배포 확인](#배포-확인)
6. [롤백](#롤백)
7. [트러블슈팅](#트러블슈팅)

---

## 🔧 사전 요구사항

### 필수 도구

```bash
# Python 3.13+
python --version

# UV (Python 패키지 관리자)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Docker
docker --version

# Azure CLI
az --version

# kubectl
kubectl version --client

# Helm (Optional - 수동 배포 시)
helm version
```

### Azure 리소스

- **ACR (Container Registry)**: `shbsoldemoacr.azurecr.io`
- **AKS (Kubernetes Service)**: Kubernetes 클러스터
- **ArgoCD**: GitOps 배포 도구 (클러스터 내 설치됨)

### GitHub Repository Secret 설정

**Settings → Secrets and variables → Actions**에서 다음 설정:

| Secret Name | Description | 예시 |
|------------|-------------|------|
| `ACR_LOGIN_SERVER` | Azure Container Registry 주소 | `shbsoldemoacr.azurecr.io` |
| `ACR_USERNAME` | ACR 사용자 이름 | Service Principal ID |
| `ACR_PASSWORD` | ACR 비밀번호 | Service Principal Secret |
| `CHART_REPO` | Helm Chart Git 저장소 URL | `https://github.com/org/helm-charts.git` |
| `CHART_TOKEN` | GitHub Personal Access Token | `ghp_xxxxx` |
| `CHART_PATH` | Helm Chart 경로 | `session-manager` |

---

## 💻 로컬 개발 환경 설정

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/shinhanbacnk-sol-session-manager.git
cd shinhanbacnk-sol-session-manager
```

### 2. Python 환경 설정

```bash
# UV로 의존성 설치
uv sync

# 가상 환경 활성화 (자동)
source .venv/bin/activate
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 수정
vim .env
```

**.env 예시**:
```bash
APP_ENV=dev
DEBUG=true
USE_MOCK_DB=true

# API Keys (개발 환경)
AGW_API_KEY=agw-api-key
MA_API_KEY=ma-api-key
PORTAL_API_KEY=portal-api-key
VDB_API_KEY=vdb-api-key

# Redis (로컬)
REDIS_URL=redis://localhost:6379/0

# PostgreSQL (로컬)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/session_manager
```

### 4. 로컬 서버 실행

```bash
# 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8080

# 또는
uv run python -m uvicorn app.main:app --reload --port 8080
```

**API 문서 확인**: http://localhost:8080/docs

### 5. 테스트 실행

```bash
# 전체 테스트
uv run pytest

# 데모 시나리오만
uv run pytest tests/test_demo_scenario.py -v

# 커버리지 포함
uv run pytest --cov=app --cov-report=html
```

### 6. 코드 품질 검사

```bash
# Ruff 린팅
uv run ruff check .

# 자동 수정
uv run ruff check . --fix

# 포맷팅
uv run ruff format .
```

---

## 🚀 자동 배포 (GitHub Actions)

### 배포 흐름

```
코드 푸시 (dev 브랜치)
    ↓
GitHub Actions 트리거
    ↓
1. Lint & Test (lint-and-tests.yml)
    ↓
2. Docker 빌드 & ACR 푸시 (deploy-dev.yml)
    ↓
3. Helm Chart values.yaml 업데이트
    ↓
ArgoCD 자동 감지 (3분 이내)
    ↓
AKS에 배포
```

### 배포 방법

**Step 1: dev 브랜치에 코드 푸시**

```bash
# 변경사항 확인
git status

# 로컬 테스트
uv run pytest
uv run ruff check .

# 커밋 & 푸시
git checkout dev
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin dev
```

**Step 2: GitHub Actions 확인**

1. GitHub 저장소 → **Actions** 탭
2. 워크플로우 실행 확인:
   - ✅ **Lint and Tests** (lint-and-tests.yml)
   - ✅ **Deploy to Dev** (deploy-dev.yml)
3. 각 단계별 로그 확인

**Step 3: ArgoCD 배포 확인**

```bash
# ArgoCD UI 접속
# https://argocd.your-domain.com

# 또는 CLI로 확인
kubectl get applications -n argocd
```

### GitHub Actions 워크플로우

#### 1. Lint and Tests (`lint-and-tests.yml`)

**트리거**: Pull Request, dev/main 브랜치 푸시

```yaml
# .github/workflows/lint-and-tests.yml
name: Lint and Tests

on:
  push:
    branches: [dev, main]
  pull_request:
    branches: [dev, main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v2
      
      - name: Set up Python
        run: uv python install
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run Ruff
        run: uv run ruff check .
      
      - name: Run tests
        run: uv run pytest --cov=app --cov-report=xml
```

#### 2. Deploy to Dev (`deploy-dev.yml`)

**트리거**: dev 브랜치 푸시

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy to Dev

on:
  push:
    branches: [dev]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Docker 빌드 & ACR 푸시
      - name: Login to ACR
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.ACR_LOGIN_SERVER }}/session-manager:${{ github.sha }}
            ${{ secrets.ACR_LOGIN_SERVER }}/session-manager:latest
      
      # Helm Chart 업데이트
      - name: Update Helm Chart
        run: |
          git clone https://${{ secrets.CHART_TOKEN }}@${{ secrets.CHART_REPO }} charts
          cd charts/${{ secrets.CHART_PATH }}
          
          # values-dev.yaml 업데이트
          sed -i "s|tag:.*|tag: ${{ github.sha }}|g" values-dev.yaml
          
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add values-dev.yaml
          git commit -m "chore: update session-manager to ${{ github.sha }}"
          git push
```

---

## 🔧 수동 배포

### 방법 1: Docker 이미지 직접 배포

**Step 1: ACR 로그인**

```bash
# Azure 로그인
az login

# ACR 로그인
az acr login --name shbsoldemoacr
```

**Step 2: Docker 이미지 빌드 & 푸시**

```bash
# 이미지 빌드
docker build -t shbsoldemoacr.azurecr.io/session-manager:manual-v1.0 .

# 이미지 푸시
docker push shbsoldemoacr.azurecr.io/session-manager:manual-v1.0

# 이미지 확인
az acr repository show-tags --name shbsoldemoacr --repository session-manager
```

**Step 3: Helm Chart 업데이트**

```bash
# Helm Chart 저장소 클론
git clone https://github.com/your-org/helm-charts.git
cd helm-charts/session-manager

# values-dev.yaml 수정
vim values-dev.yaml
```

```yaml
image:
  repository: shbsoldemoacr.azurecr.io/session-manager
  tag: manual-v1.0  # 여기를 변경
  pullPolicy: IfNotPresent
```

```bash
# 변경사항 커밋 & 푸시
git add values-dev.yaml
git commit -m "chore: manual deploy v1.0"
git push
```

**Step 4: ArgoCD 동기화**

```bash
# ArgoCD UI에서 Sync 버튼 클릭
# 또는 CLI로 동기화
kubectl patch application session-manager -n argocd \
  -p '{"operation": {"initiatedBy": {"username": "admin"}, "sync": {}}}' --type merge

# 자동 감지 대기 (3분 이내)
kubectl get application session-manager -n argocd -w
```

### 방법 2: kubectl로 직접 배포 (비권장)

```bash
# AKS 클러스터 연결
az aks get-credentials --resource-group <RG_NAME> --name <AKS_NAME>

# Deployment 이미지 업데이트
kubectl set image deployment/session-manager \
  session-manager=shbsoldemoacr.azurecr.io/session-manager:manual-v1.0 \
  -n <NAMESPACE>

# 배포 확인
kubectl rollout status deployment/session-manager -n <NAMESPACE>
```

---

## ✅ 배포 확인

### 1. Pod 상태 확인

```bash
# Pod 목록
kubectl get pods -n <namespace> | grep session-manager

# Pod 상세 정보
kubectl describe pod <pod-name> -n <namespace>

# Pod 로그
kubectl logs -f deployment/session-manager -n <namespace>

# 최근 100줄 로그
kubectl logs --tail=100 deployment/session-manager -n <namespace>
```

### 2. Service 확인

```bash
# Service 목록
kubectl get svc -n <namespace>

# Ingress 확인
kubectl get ingress -n <namespace>
```

### 3. Health Check

```bash
# Health 엔드포인트
curl https://session-manager-dev.azure.com/health

# 응답 예시
{
  "status": "healthy",
  "version": "3.0.0",
  "environment": "dev",
  "timestamp": "2026-01-02T10:00:00Z"
}
```

### 4. API 문서 확인

```bash
# Swagger UI
open https://session-manager-dev.azure.com/docs

# ReDoc
open https://session-manager-dev.azure.com/redoc
```

### 5. 테스트 API 호출

```bash
# Health Check
curl -X GET https://session-manager-dev.azure.com/health

# 세션 생성 (AGW)
curl -X POST https://session-manager-dev.azure.com/api/v1/agw/sessions \
  -H "X-API-Key: agw-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "global_session_key": "gsess_test_001",
    "user_id": "user_vip_001",
    "channel": "web"
  }'
```

### 6. ArgoCD 상태 확인

```bash
# Application 상태
kubectl get application session-manager -n argocd

# 상세 정보
kubectl describe application session-manager -n argocd

# ArgoCD UI에서 확인
# https://argocd.your-domain.com
# → Applications → session-manager
```

---

## 🔄 롤백

### 방법 1: ArgoCD를 통한 롤백

**ArgoCD UI**:
1. Application 선택
2. **History and Rollback** 탭
3. 이전 버전 선택 → **Rollback** 버튼

**ArgoCD CLI**:
```bash
# 이전 버전으로 롤백
argocd app rollback session-manager <REVISION_ID>

# 롤백 상태 확인
argocd app get session-manager
```

### 방법 2: Helm Chart 되돌리기

```bash
# Helm Chart 저장소에서 이전 커밋으로 revert
cd helm-charts/session-manager
git revert HEAD
git push

# ArgoCD가 자동으로 감지하여 롤백
```

### 방법 3: kubectl로 직접 롤백

```bash
# 롤아웃 히스토리 확인
kubectl rollout history deployment/session-manager -n <namespace>

# 이전 버전으로 롤백
kubectl rollout undo deployment/session-manager -n <namespace>

# 특정 리비전으로 롤백
kubectl rollout undo deployment/session-manager --to-revision=2 -n <namespace>

# 롤백 상태 확인
kubectl rollout status deployment/session-manager -n <namespace>
```

---

## 🔍 트러블슈팅

### 1. Pod가 CrashLoopBackOff

**원인**: 애플리케이션 시작 실패

```bash
# 로그 확인
kubectl logs <pod-name> -n <namespace>

# 이전 컨테이너 로그 확인
kubectl logs <pod-name> -n <namespace> --previous

# 일반적인 원인:
# - 환경 변수 누락 (ConfigMap/Secret 확인)
# - 의존성 서비스 미연결 (Redis, PostgreSQL)
# - 포트 충돌
```

**해결**:
```bash
# ConfigMap 확인
kubectl get configmap session-manager-config -n <namespace> -o yaml

# Secret 확인
kubectl get secret session-manager-secrets -n <namespace> -o yaml

# 환경 변수 확인
kubectl exec -it <pod-name> -n <namespace> -- env | grep APP_
```

### 2. ImagePullBackOff

**원인**: Docker 이미지를 가져올 수 없음

```bash
# 이벤트 확인
kubectl describe pod <pod-name> -n <namespace>

# 일반적인 원인:
# - ACR 인증 실패
# - 이미지 태그 오류
# - 네트워크 문제
```

**해결**:
```bash
# ACR 로그인 확인
kubectl get secret acr-secret -n <namespace> -o yaml

# 이미지 존재 확인
az acr repository show-tags --name shbsoldemoacr --repository session-manager

# Secret 재생성
kubectl create secret docker-registry acr-secret \
  --docker-server=shbsoldemoacr.azurecr.io \
  --docker-username=<USERNAME> \
  --docker-password=<PASSWORD> \
  -n <namespace>
```

### 3. ArgoCD 동기화 실패

**원인**: Helm Chart 문법 오류 또는 리소스 충돌

```bash
# ArgoCD 로그 확인
kubectl logs -n argocd deployment/argocd-application-controller

# Application 상태 확인
kubectl get application session-manager -n argocd -o yaml

# 일반적인 원인:
# - values.yaml 문법 오류
# - 리소스 이름 충돌
# - RBAC 권한 부족
```

**해결**:
```bash
# Dry-run으로 확인
helm template session-manager ./helm-charts/session-manager -f values-dev.yaml

# 강제 동기화
argocd app sync session-manager --force

# Helm Chart validation
helm lint ./helm-charts/session-manager
```

### 4. 503 Service Unavailable

**원인**: Service/Ingress 설정 오류

```bash
# Service 확인
kubectl get svc session-manager -n <namespace>

# Endpoint 확인
kubectl get endpoints session-manager -n <namespace>

# Ingress 확인
kubectl describe ingress session-manager-ingress -n <namespace>
```

**해결**:
```bash
# Pod의 Ready 상태 확인
kubectl get pods -n <namespace> | grep session-manager

# Health check 엔드포인트 테스트
kubectl exec -it <pod-name> -n <namespace> -- curl localhost:8080/health

# Service 포트 포워딩 테스트
kubectl port-forward svc/session-manager 8080:80 -n <namespace>
curl http://localhost:8080/health
```

### 5. GitHub Actions 실패

**원인**: Secret 누락 또는 권한 문제

```bash
# GitHub Actions 로그 확인
# https://github.com/<org>/<repo>/actions

# 일반적인 원인:
# - ACR_PASSWORD 만료
# - CHART_TOKEN 권한 부족
# - Docker 빌드 실패
```

**해결**:
```bash
# GitHub Secret 업데이트
# Settings → Secrets and variables → Actions → Update secret

# Service Principal 갱신 (ACR)
az ad sp create-for-rbac --name session-manager-sp --role acrpush \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG_NAME>/providers/Microsoft.ContainerRegistry/registries/shbsoldemoacr

# GitHub Personal Access Token 재생성
# https://github.com/settings/tokens
# 필요 권한: repo (Full control)
```

### 6. Mock DB 데이터 초기화

```bash
# Pod 재시작 (메모리 데이터 초기화)
kubectl rollout restart deployment/session-manager -n <namespace>

# 또는 특정 Pod 삭제
kubectl delete pod <pod-name> -n <namespace>
```

---

## 📝 체크리스트

### 배포 전

- [ ] 로컬에서 모든 테스트 통과 (`uv run pytest`)
- [ ] Ruff 린팅 통과 (`uv run ruff check .`)
- [ ] 환경 변수 확인 (`.env` 파일)
- [ ] API 문서 업데이트 (Swagger)
- [ ] CHANGELOG 업데이트
- [ ] GitHub Secret 유효성 확인

### 배포 후

- [ ] Pod 정상 실행 확인
- [ ] Health check 정상 응답
- [ ] API 문서 접근 가능
- [ ] 데모 시나리오 테스트
- [ ] 로그 모니터링 (에러 없음)
- [ ] ArgoCD 동기화 완료

---

## 🔐 보안 주의사항

### ⚠️ 절대 커밋 금지

```bash
# .gitignore에 포함 확인
.env
*.env.local
*.env.*.local
secrets/
*.pem
*.key
```

### 환경 변수 관리

**개발 환경**: `.env` 파일 (로컬만)
**운영 환경**: Kubernetes Secret

```bash
# Kubernetes Secret 생성
kubectl create secret generic session-manager-secrets \
  --from-literal=agw-api-key=<AGW_KEY> \
  --from-literal=ma-api-key=<MA_KEY> \
  --from-literal=portal-api-key=<PORTAL_KEY> \
  --from-literal=vdb-api-key=<VDB_KEY> \
  -n <namespace>
```

### API Key 관리

- **절대 하드코딩 금지**
- **환경 변수로만 관리**
- **정기적으로 로테이션**
- **최소 권한 원칙 적용**

---

## 📚 참고 문서

- [Session Manager API 명세](./Session_Manager_API_Sprint2.md)
- [데모 시나리오](./DEMO_SCENARIO_V2.md)
- [Azure AKS CI/CD](./azure_aks_cicd.md)
- [코드 컨벤션](./.github/copilot-instructions.md)

---

**문의**: Session Manager 개발팀
**최종 업데이트**: 2026-01-02
