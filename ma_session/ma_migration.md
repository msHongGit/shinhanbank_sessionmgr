온프레미스 에어갭 환경 마이그레이션 가이드
개요
본 가이드는 현재의 GitHub 기반 CI/CD 환경을 폐쇄된 온프레미스 환경으로 마이그레이션하는 포괄적인 단계를 제공합니다:

Nexus Repository: PyPI 프록시 및 Docker 레지스트리

Kubernetes Cluster: 온프레미스 K8s 컨테이너 오케스트레이션

GitLab CI/CD: GitHub Actions 대체

에어갭 환경: 외부 인터넷 접속 없음, USB 기반 아티팩트 전송

1. 의존성 목록
1.1 Docker 베이스 이미지
필수 이미지:



python:3.12-slim
ghcr.io/astral-sh/uv:latest
필요한 이유:

python:3.12-slim: 빌더 및 런타임 단계의 베이스 이미지

ghcr.io/astral-sh/uv: 빠른 Python 패키지 매니저 (pip 대체)

추출 명령:



# 이미지 풀 및 저장
docker pull python:3.12-slim
docker pull ghcr.io/astral-sh/uv:latest
# tar 파일로 저장
docker save python:3.12-slim -o python-3.12-slim.tar
docker save ghcr.io/astral-sh/uv:latest -o uv-latest.tar
# USB 저장을 위해 압축
gzip python-3.12-slim.tar
gzip uv-latest.tar
예상 크기: ~150-200 MB (압축)

1.2 Python 패키지
소스 파일:

pyproject.toml: 24개 의존성 (18개 프로덕션 + 6개 개발)

uv.lock: 2,495줄 (고정된 버전의 완전한 의존성 트리)

주요 의존성:



프로덕션:
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- langgraph>=0.2.0
- langchain>=0.3.0
- langchain-core>=0.3.0
- httpx>=0.25.0
- pydantic>=2.5.0
- redis>=5.0.0
- langfuse>=3.11.2
- streamlit>=1.28.0
개발:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- ruff>=0.1.0
- mypy>=1.7.0
추출 명령 (수정됨):



cd /Users/june/01.Workspace/00.Main/shinhanbank-sol-master-agent
# 방법 A: requirements.txt 생성 후 다운로드
uv export --no-hashes --frozen > requirements.txt
# 모든 wheel을 로컬 디렉토리에 다운로드
mkdir -p ./pypi-mirror
pip download -r requirements.txt -d ./pypi-mirror
# 방법 B: UV 캐시 디렉토리 직접 사용
# uv sync --frozen  # 캐시를 채웁니다
# cp -r ~/.cache/uv ./uv-cache-backup
# 주의: 'uv pip download' 명령은 작동하지 않습니다
# 대신 'pip download' 또는 UV 캐시 디렉토리를 사용하세요
예상 크기: ~500-800 MB (모든 wheel)

1.3 UV 바이너리 (Docker 이미지 대안)
독립 실행형 UV 바이너리를 선호하는 경우:



# Linux용 UV 바이너리 다운로드
curl -LsSf https://astral.sh/uv/install.sh | sh
cp ~/.cargo/bin/uv ./uv-binary-linux-x86_64
# macOS의 경우 (macOS에서 빌드하는 경우)
cp $(which uv) ./uv-binary-darwin-arm64
예상 크기: ~15-20 MB

1.4 CI/CD 아티팩트
변환할 GitHub Actions 워크플로:



.github/workflows/
├── lint-and-tests.yml      → .gitlab-ci.yml (test 스테이지)
├── docker-smoke.yml         → .gitlab-ci.yml (build 스테이지)
├── deploy-dev.yml           → .gitlab-ci.yml (deploy 스테이지)
└── security-scan.yml        → .gitlab-ci.yml (security 스테이지)
2. USB 저장소 구조
권장 디렉토리 레이아웃:



usb-migration-artifacts/
├── docker-images/
│   ├── python-3.12-slim.tar.gz
│   ├── uv-latest.tar.gz
│   └── checksums.txt
│
├── python-packages/
│   ├── requirements.txt
│   ├── wheels/
│   │   ├── fastapi-0.104.0-py3-none-any.whl
│   │   ├── uvicorn-0.24.0-py3-none-any.whl
│   │   └── ... (모든 wheel 파일)
│   └── checksums.txt
│
├── binaries/
│   ├── uv-binary-linux-x86_64
│   └── checksums.txt
│
├── source-code/
│   └── shinhanbank-sol-master-agent.tar.gz
│
├── configs/
│   ├── nexus-pypi-proxy-config.md
│   ├── nexus-docker-registry-config.md
│   ├── gitlab-ci.yml
│   └── on-prem-migration-guide-ko.md (이 파일)
│
└── scripts/
    ├── 01-load-docker-images.sh
    ├── 02-upload-to-nexus.sh
    ├── 03-verify-setup.sh
    └── README.md
3. 추출 스크립트
스크립트 생성: scripts/prepare-migration-artifacts.sh



#!/bin/bash
set -euo pipefail
ARTIFACT_DIR="usb-migration-artifacts"
WORK_DIR=$(pwd)
echo "🚀 온프레미스 마이그레이션을 위한 아티팩트 준비 시작..."
# 디렉토리 구조 생성
mkdir -p "$ARTIFACT_DIR"/{docker-images,python-packages/wheels,binaries,source-code,configs,scripts}
# 1. Docker 이미지
echo "📦 Docker 이미지 풀 및 저장..."
docker pull python:3.12-slim
docker pull ghcr.io/astral-sh/uv:latest
docker save python:3.12-slim | gzip > "$ARTIFACT_DIR/docker-images/python-3.12-slim.tar.gz"
docker save ghcr.io/astral-sh/uv:latest | gzip > "$ARTIFACT_DIR/docker-images/uv-latest.tar.gz"
# 2. Python 패키지 (수정됨)
echo "📚 Python 의존성 내보내기..."
uv export --no-hashes --frozen > "$ARTIFACT_DIR/python-packages/requirements.txt"
# pip download 사용 (uv pip download는 작동하지 않음)
pip download -r "$ARTIFACT_DIR/python-packages/requirements.txt" -d "$ARTIFACT_DIR/python-packages/wheels"
# 3. UV 바이너리
echo "🔧 UV 바이너리 복사..."
cp $(which uv) "$ARTIFACT_DIR/binaries/uv-binary-$(uname -s)-$(uname -m)"
# 4. 소스 코드
echo "📝 소스 코드 아카이빙..."
git archive --format=tar.gz --prefix=shinhanbank-sol-master-agent/ HEAD > "$ARTIFACT_DIR/source-code/shinhanbank-sol-master-agent.tar.gz"
# 5. 체크섬 생성
echo "🔐 체크섬 생성..."
find "$ARTIFACT_DIR" -type f -name "*.tar.gz" -o -name "*.whl" | while read file; do
    sha256sum "$file" >> "$ARTIFACT_DIR/checksums.txt"
done
# 6. 문서 복사
echo "📋 문서 복사..."
cp docs/on-prem-migration-guide.md "$ARTIFACT_DIR/configs/"
cp docs/on-prem-migration-guide-ko.md "$ARTIFACT_DIR/configs/" 2>/dev/null || true
echo "✅ 아티팩트 준비 완료!"
echo "📊 요약:"
du -sh "$ARTIFACT_DIR"
tree -L 2 "$ARTIFACT_DIR" || ls -lR "$ARTIFACT_DIR"
실행:



chmod +x scripts/prepare-migration-artifacts.sh
./scripts/prepare-migration-artifacts.sh
4. 온프레미스 설정 가이드
4.1 Nexus Repository 구성
PyPI 프록시 설정:



1. Nexus 로그인: http://nexus.your-company.com
2. PyPI (proxy) 리포지토리 생성:
   - Name: pypi-proxy
   - Remote Storage: https://pypi.org/simple (에어갭 환경인 경우 비활성화)
   - Blob Store: default
3. PyPI (hosted) 리포지토리 생성:
   - Name: pypi-internal
   - Blob Store: default
4. PyPI (group) 리포지토리 생성:
   - Name: pypi-all
   - Members: pypi-internal, pypi-proxy
Docker 레지스트리 설정:



1. Docker (hosted) 리포지토리 생성:
   - Name: docker-local
   - HTTP Port: 8082
   - Enable Docker V1 API: ✓
   - Blob Store: default
2. Docker (proxy) 리포지토리 생성:
   - Name: docker-proxy
   - Remote URL: https://registry-1.docker.io
   - HTTP Port: 8083
3. Docker (group) 리포지토리 생성:
   - Name: docker-all
   - HTTP Port: 8081
   - Members: docker-local, docker-proxy
Nexus에 아티팩트 업로드:



#!/bin/bash
# scripts/02-upload-to-nexus.sh
NEXUS_URL="http://nexus.your-company.com"
NEXUS_USER="admin"
NEXUS_PASSWORD="admin123"
# 1. Docker 이미지를 로컬 레지스트리에 로드
docker load < docker-images/python-3.12-slim.tar.gz
docker load < docker-images/uv-latest.tar.gz
# 2. Nexus Docker 레지스트리에 태그 및 푸시
docker tag python:3.12-slim nexus.your-company.com:8082/python:3.12-slim
docker tag ghcr.io/astral-sh/uv:latest nexus.your-company.com:8082/uv:latest
docker push nexus.your-company.com:8082/python:3.12-slim
docker push nexus.your-company.com:8082/uv:latest
# 3. Python wheel 업로드
cd python-packages/wheels
for wheel in *.whl; do
    curl -u "$NEXUS_USER:$NEXUS_PASSWORD" \
         --upload-file "$wheel" \
         "$NEXUS_URL/repository/pypi-internal/"
done
4.2 온프레미스용 수정된 Dockerfile
Dockerfile.onprem 생성:



# Nexus 호스팅 베이스 이미지 사용
ARG NEXUS_REGISTRY=nexus.your-company.com:8082
FROM ${NEXUS_REGISTRY}/python:3.12-slim AS builder
# Nexus 호스팅 이미지에서 UV 바이너리 복사
COPY --from=${NEXUS_REGISTRY}/uv:latest /uv /uvx /bin/
# 작업 디렉토리 설정
WORKDIR /app
# 의존성 파일 복사
COPY pyproject.toml uv.lock ./
# Nexus PyPI 미러 사용하도록 UV 구성
ENV UV_INDEX_URL=http://nexus.your-company.com:8081/repository/pypi-all/simple
ENV UV_TRUSTED_HOST=nexus.your-company.com
# 의존성 설치 (반복 빌드를 위한 캐시 마운트)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
# 시크릿을 위한 빌드 인자 (GitLab CI에서 주입)
ARG LLM_API_KEY
ARG LANGFUSE_SECRET_KEY
ARG LANGFUSE_PUBLIC_KEY
ARG SESSION_MANAGER_API_KEY
ARG SKILLSET_AGENT_API_KEY
ARG REDIS_PASSWORD
ARG REDIS_HOST
ARG REDIS_PORT
ARG REDIS_DB
ARG SESSION_MANAGER_URL
ARG SKILLSET_AGENT_URL
# 환경 변수
ENV LLM_API_KEY=$LLM_API_KEY \
    LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY \
    LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY \
    SESSION_MANAGER_API_KEY=$SESSION_MANAGER_API_KEY \
    SKILLSET_AGENT_API_KEY=$SKILLSET_AGENT_API_KEY \
    REDIS_PASSWORD=$REDIS_PASSWORD \
    REDIS_HOST=$REDIS_HOST \
    REDIS_PORT=$REDIS_PORT \
    REDIS_DB=$REDIS_DB \
    SESSION_MANAGER_URL=$SESSION_MANAGER_URL \
    SKILLSET_AGENT_URL=$SKILLSET_AGENT_URL
# 런타임 스테이지
FROM ${NEXUS_REGISTRY}/python:3.12-slim
WORKDIR /app
# non-root 사용자 생성
RUN useradd -m -u 1000 appuser
# 빌더에서 가상 환경 복사
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .
# PATH에 venv 추가
ENV PATH="/app/.venv/bin:$PATH"
# non-root 사용자로 전환
USER appuser
# 포트 구성
ENV PORT=5000
EXPOSE 5000
# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT','5000'); urllib.request.urlopen(f'http://localhost:{port}/health')"
# 애플리케이션 실행
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}"]
4.3 GitLab CI/CD 구성
.gitlab-ci.yml 생성:



stages:
  - lint
  - test
  - build
  - deploy
variables:
  DOCKER_REGISTRY: nexus.your-company.com:8082
  IMAGE_NAME: master-agent
  NEXUS_REGISTRY: nexus.your-company.com:8082
# Lint 스테이지 (lint-and-tests.yml과 동일)
lint:
  stage: lint
  image: ${NEXUS_REGISTRY}/python:3.12-slim
  before_script:
    - apt-get update && apt-get install -y curl
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv sync
  script:
    - uv run ruff check . --fix
    - uv run ruff check .
    - uv run mypy . || true  # 비차단
  only:
    - merge_requests
    - branches
  except:
    - main
    - dev
# Test 스테이지
test:
  stage: test
  image: ${NEXUS_REGISTRY}/python:3.12-slim
  before_script:
    - apt-get update && apt-get install -y curl
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv sync
  script:
    - uv run pytest tests/ -m "function or scenario or service" --cov=app --cov-report=term
  coverage: '/TOTAL.*\s+(\d+%)$/'
  variables:
    LLM_API_KEY: $LLM_API_KEY
    LANGFUSE_SECRET_KEY: $LANGFUSE_SECRET_KEY
    LANGFUSE_PUBLIC_KEY: $LANGFUSE_PUBLIC_KEY
    SESSION_MANAGER_API_KEY: $SESSION_MANAGER_API_KEY
  only:
    - merge_requests
    - branches
  except:
    - main
    - dev
# Docker Build 스테이지 (docker-smoke.yml과 동일)
build:
  stage: build
  image: docker:24-dind
  services:
    - docker:24-dind
  before_script:
    - docker login -u $NEXUS_USER -p $NEXUS_PASSWORD $DOCKER_REGISTRY
  script:
    - docker build 
        --build-arg NEXUS_REGISTRY=$NEXUS_REGISTRY
        --build-arg LLM_API_KEY="$LLM_API_KEY"
        --build-arg LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY"
        --build-arg LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY"
        --build-arg SESSION_MANAGER_API_KEY="$SESSION_MANAGER_API_KEY"
        --build-arg SKILLSET_AGENT_API_KEY="$SKILLSET_AGENT_API_KEY"
        --build-arg REDIS_PASSWORD="$REDIS_PASSWORD"
        -f Dockerfile.onprem
        -t $DOCKER_REGISTRY/$IMAGE_NAME:$CI_COMMIT_SHA
        -t $DOCKER_REGISTRY/$IMAGE_NAME:latest
        .
    - docker push $DOCKER_REGISTRY/$IMAGE_NAME:$CI_COMMIT_SHA
    - docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest
  only:
    - main
    - dev
# Deploy 스테이지 (deploy-dev.yml과 동일)
deploy:dev:
  stage: deploy
  image: ${NEXUS_REGISTRY}/alpine/helm:latest
  before_script:
    - apk add --no-cache curl
    - curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    - chmod +x kubectl && mv kubectl /usr/local/bin/
  script:
    # 새 이미지 태그로 Helm 차트 값 업데이트
    - helm upgrade --install master-agent ./helm-chart
        --namespace master-agent-dev
        --create-namespace
        --set image.repository=$DOCKER_REGISTRY/$IMAGE_NAME
        --set image.tag=$CI_COMMIT_SHA
        --set secrets.llmApiKey="$LLM_API_KEY"
        --set secrets.langfuseSecretKey="$LANGFUSE_SECRET_KEY"
        --set secrets.langfusePublicKey="$LANGFUSE_PUBLIC_KEY"
        --wait
  only:
    - dev
  environment:
    name: development
    url: http://master-agent-dev.k8s.your-company.com
# Security Scan 스테이지 (security-scan.yml과 동일)
security:
  stage: test
  image: ${NEXUS_REGISTRY}/python:3.12-slim
  script:
    - pip install bandit safety
    - bandit -r app/ -ll
    - safety check --json || true
  allow_failure: true
  only:
    - merge_requests
5. 추가 고려사항
5.1 TLS/SSL 인증서
내부 CA 인증서:



# Nexus가 자체 서명 인증서를 사용하는 경우
# CA 인증서를 USB에 복사
cp /etc/ssl/certs/internal-ca.crt usb-migration-artifacts/configs/
# Dockerfile.onprem에 추가:
COPY configs/internal-ca.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
5.2 DNS/네트워크 구성
온프레미스 K8s가 해석할 수 있어야 함:



nexus.your-company.com → 내부 IP
gitlab.your-company.com → 내부 IP
master-agent-dev.k8s.your-company.com → Ingress IP
/etc/hosts 또는 내부 DNS 업데이트:



10.0.1.10  nexus.your-company.com
10.0.1.20  gitlab.your-company.com
5.3 GitLab Runner 설정
K8s에 GitLab Runner 설치:



helm repo add gitlab https://charts.gitlab.io
helm install gitlab-runner gitlab/gitlab-runner \
  --namespace gitlab \
  --set gitlabUrl=https://gitlab.your-company.com \
  --set runnerRegistrationToken=$RUNNER_TOKEN \
  --set runners.image=nexus.your-company.com:8082/alpine:latest
5.4 시크릿 관리
GitLab CI/CD 변수 (GitHub Secrets와 동일):



Settings → CI/CD → Variables:
LLM_API_KEY: ********
LANGFUSE_SECRET_KEY: ********
LANGFUSE_PUBLIC_KEY: ********
SESSION_MANAGER_API_KEY: ********
SKILLSET_AGENT_API_KEY: ********
REDIS_PASSWORD: ********
NEXUS_USER: admin
NEXUS_PASSWORD: ********
Protected & Masked: ✓

5.5 Kubernetes Secrets
현재 ConfigMap에서 Secrets로 변환:



# helm-chart/templates/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ .Release.Name }}-secrets
type: Opaque
data:
  LLM_API_KEY: {{ .Values.secrets.llmApiKey | b64enc }}
  LANGFUSE_SECRET_KEY: {{ .Values.secrets.langfuseSecretKey | b64enc }}
  LANGFUSE_PUBLIC_KEY: {{ .Values.secrets.langfusePublicKey | b64enc }}
  # ... 기타 시크릿
5.6 ArgoCD 구성
Nexus 레지스트리를 사용하도록 Application 업데이트:



# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: master-agent
spec:
  source:
    repoURL: https://gitlab.your-company.com/your-org/shinhanbank-sol-master-agent.git
    targetRevision: main
    path: helm-chart
    helm:
      values: |
        image:
          repository: nexus.your-company.com:8082/master-agent
          tag: latest
          pullPolicy: Always
5.7 모니터링 및 로깅
에어갭 환경 대안 고려:

Prometheus: 자체 호스팅 메트릭 (클라우드 기반 Datadog 대신)

Grafana: 시각화 대시보드

ELK Stack: 로그 집계 (Elasticsearch, Logstash, Kibana)

Loki: 경량 로그 집계

USB 아티팩트에 추가:



usb-migration-artifacts/
└── monitoring/
    ├── prometheus-helm-values.yaml
    ├── grafana-dashboards.json
    └── loki-config.yaml
5.8 백업 및 재해 복구
백업할 중요 데이터:



1. Nexus blob 스토어 (Docker 이미지, Python wheel)
2. GitLab 리포지토리 및 CI/CD 구성
3. Kubernetes PersistentVolumes (Redis 데이터, 애플리케이션 상태)
4. Secrets (sealed-secrets 또는 Vault)
백업 전략:



# Nexus 백업
nexus-backup.sh → /mnt/backup/nexus/$(date +%Y%m%d).tar.gz
# GitLab 백업
gitlab-rake gitlab:backup:create
# K8s 리소스
kubectl get all --all-namespaces -o yaml > k8s-backup.yaml
6. 검증 체크리스트
프로덕션 전환 전:

[ ] 모든 Docker 이미지가 Nexus Docker 레지스트리에 로드됨

[ ] 모든 Python wheel이 Nexus PyPI 리포지토리에 업로드됨

[ ] Dockerfile.onprem이 Nexus 미러를 사용하여 성공적으로 빌드됨

[ ] GitLab CI/CD 파이프라인이 성공적으로 실행됨 (lint → test → build → deploy)

[ ] K8s 클러스터가 Nexus에서 이미지를 풀할 수 있음

[ ] ArgoCD가 GitLab 리포지토리에서 Helm 차트를 동기화함

[ ] 애플리케이션 헬스 체크 통과 (/health가 200 반환)

[ ] Secrets가 올바르게 주입됨 (먼저 더미 값으로 테스트)

[ ] TLS 인증서가 모든 구성 요소에서 신뢰됨

[ ] 모든 내부 서비스에 대한 DNS 해석이 작동함

[ ] 모니터링 및 로깅이 애플리케이션 메트릭을 캡처함

[ ] 백업 및 복원 절차가 테스트됨

7. 문제 해결
문제: Docker 빌드가 "failed to resolve" 오류로 실패
원인: BuildKit이 외부 레지스트리에 액세스하려고 시도

해결:



# 필요한 경우 BuildKit 비활성화
DOCKER_BUILDKIT=0 docker build -f Dockerfile.onprem .
# 또는 비보안 레지스트리 구성
# /etc/docker/daemon.json
{
  "insecure-registries": ["nexus.your-company.com:8082"]
}
문제: UV가 Nexus에서 패키지 설치 실패
원인: Nexus PyPI 프록시가 올바르게 구성되지 않음

해결:



# Nexus PyPI 엔드포인트 테스트
curl http://nexus.your-company.com:8081/repository/pypi-all/simple/
# Nexus를 신뢰하도록 UV 구성
export UV_INDEX_URL=http://nexus.your-company.com:8081/repository/pypi-all/simple
export UV_TRUSTED_HOST=nexus.your-company.com
# 설치 테스트
uv pip install fastapi
문제: GitLab Runner가 이미지를 풀할 수 없음
원인: Runner가 Nexus에 인증되지 않음

해결:



# Nexus 인증을 위한 Kubernetes secret 생성
kubectl create secret docker-registry nexus-registry-secret \
  --docker-server=nexus.your-company.com:8082 \
  --docker-username=admin \
  --docker-password=admin123 \
  --namespace=gitlab
# GitLab Runner 구성 업데이트
helm upgrade gitlab-runner gitlab/gitlab-runner \
  --set runners.imagePullSecrets[0]=nexus-registry-secret
8. 마이그레이션 일정
권장 단계:

1단계: 준비 (1-2일)
prepare-migration-artifacts.sh 스크립트 실행

USB 저장소의 모든 아티팩트 확인

체크섬 생성 및 무결성 확인

2단계: 온프레미스 설정 (2-3일)
Nexus 리포지토리 구성 (PyPI, Docker)

모든 아티팩트를 Nexus에 업로드

GitLab 및 러너 설정

3단계: 테스트 (3-5일)
Dockerfile.onprem 빌드 테스트

GitLab CI/CD 파이프라인 엔드투엔드 실행

K8s 개발 환경에 배포

애플리케이션 기능 검증

4단계: 프로덕션 전환 (1일)
아티팩트의 최종 동기화

DNS/네트워킹 업데이트

K8s 프로덕션 환경에 배포

24-48시간 모니터링

총 예상 시간: 7-11일

부록: 빠른 명령어 참조
대상 시스템에서 Docker 이미지 로드


cd usb-migration-artifacts/docker-images
docker load < python-3.12-slim.tar.gz
docker load < uv-latest.tar.gz
대상 시스템에 UV 바이너리 설치


cp usb-migration-artifacts/binaries/uv-binary-Linux-x86_64 /usr/local/bin/uv
chmod +x /usr/local/bin/uv
오프라인 Python 패키지 설치


cd usb-migration-artifacts/python-packages
pip install --no-index --find-links=./wheels -r requirements.txt
Nexus를 사용하여 Docker 이미지 빌드


docker build \
  --build-arg NEXUS_REGISTRY=nexus.your-company.com:8082 \
  -f Dockerfile.onprem \
  -t master-agent:latest \
  .
K8s에 배포


helm upgrade --install master-agent ./helm-chart \
  --namespace master-agent-dev \
  --set image.repository=nexus.your-company.com:8082/master-agent \
  --set image.tag=latest
연락처 및 지원
질문 또는 문제?

문서 소유자: [귀하의 이름]

최종 업데이트: 2026년 1월 8일

버전: 1.0