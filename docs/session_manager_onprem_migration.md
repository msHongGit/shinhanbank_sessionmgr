# Session Manager 온프레미스 에어갭 마이그레이션 가이드

> 대상: Session Manager (FastAPI + Redis + MariaDB)  \
> 환경: 인터넷이 차단된 온프레미스 K8s / VM 환경, USB 기반 아티팩트 전송  \

---

## 1. 개요
온프레미스 에어갭 환경으로의 마이그레이션은 크게 네 단계로 나눌 수 있습니다.

1. 외부 환경에서 **필요 이미지/패키지/소스 코드 추출** (USB 아티팩트 준비)
2. 온프레미스 환경에 **Docker / Python 패키지 / 소스 코드 로드**
3. 온프레미스 전용 **Nexus(선택), GitLab(선택), K8s** 구성
4. Session Manager를 **빌드/배포/검증**

이 문서는 Session Manager 레포지토리 기준으로 필요한 최소 항목만 다룹니다.

---

## 2. 의존성 목록

### 2.1 Docker 베이스 이미지

Session Manager는 현재 다음 베이스 이미지를 사용합니다.

- `python:3.11-slim` – `Dockerfile` 빌드/런타임 공용 베이스

외부 네트워크가 열려 있는 환경에서 미리 이미지를 풀 받아 tar로 저장합니다.

```bash
# 이미지 풀 및 저장 (외부 네트워크 환경)
docker pull python:3.11-slim

# tar 파일로 저장
docker save python:3.11-slim -o python-3.11-slim.tar

# USB 옮기기 전 압축
gzip python-3.11-slim.tar
```

예상 크기: 수십~100MB 대 (압축 후)

### 2.2 Python 패키지

Session Manager는 `requirements.txt` 기반으로 패키지를 설치합니다.

- 주요 의존성 (발췌):
  - `fastapi`
  - `uvicorn`
  - `redis`
  - `sqlalchemy`
  - `pydantic`
  - `python-dotenv` 등

외부 환경(개발/CI 머신)에서 wheel 파일을 모두 내려받아 USB로 옮기기 위해 다음을 실행합니다.

```bash
cd /path/to/shinhanbacnk-sol-session-manager

# 의존성 고정 (이미 requirements.txt 가 있다면 이 단계는 건너뛰어도 됨)
# pip freeze > requirements.lock (옵션)

# 모든 wheel을 로컬 디렉토리에 다운로드
mkdir -p ./pypi-mirror
pip download -r requirements.txt -d ./pypi-mirror
```

- `pypi-mirror/` 디렉토리에 Session Manager에 필요한 모든 wheel(.whl) 파일이 모입니다.
- 예상 크기: 수백 MB 수준 (환경에 따라 달라짐)

### 2.3 소스 코드

Session Manager 레포지토리 전체를 tar.gz 로 묶어 USB에 담습니다.

```bash
cd /path/to/shinhanbacnk-sol-session-manager

git archive --format=tar.gz --prefix=session-manager/ HEAD > session-manager.tar.gz
```

> Git을 쓰지 않는 환경이라면 `zip` 또는 디렉토리 통째 복사도 무방합니다. 핵심은 `app/`, `Dockerfile`, `requirements.txt`, `docs/` 전체가 포함되는 것입니다.

### 2.4 (선택) 온프레미스 Nexus / GitLab 사용 여부

- **Nexus**를 사용할 경우:
  - Docker Registry: `python:3.11-slim` 및 Session Manager 이미지 저장
  - PyPI Proxy/Hosted: wheel 파일 업로드 후 내부 인덱스로 사용
- **GitLab**을 사용할 경우:
  - GitHub Actions → GitLab CI/CD 변환이 필요하지만, Session Manager는 규모가 작아 **단순 Docker 빌드 스크립트 + 수동 배포**로도 충분할 수 있습니다.

이 문서는 **필수는 Docker + pip 오프라인 설치**만 전제로 하고 Nexus/GitLab 부분은 선택 사항으로 간단하게 언급합니다.

---

## 3. USB 아티팩트 구조 예시

외부 환경에서 준비한 아티팩트를 USB에 아래와 같이 배치하는 것을 권장합니다.

```text
usb-session-manager/
├── docker-images/
│   └── python-3.11-slim.tar.gz
│
├── python-packages/
│   ├── requirements.txt
│   └── wheels/
│       ├── fastapi-*.whl
│       ├── uvicorn-*.whl
│       └── ... (모든 wheel 파일)
│
├── source-code/
│   └── session-manager.tar.gz
│
└── scripts/
    ├── 01-load-docker-images.sh
    ├── 02-install-python-packages.sh
    └── 03-run-session-manager.sh
```

온프렘에 처음 도착했을 때, 이 USB 디렉토리를 통째로 복사한 뒤 스크립트를 순서대로 실행하면 됩니다.

---

## 4. 온프레미스에서의 초기 로딩 절차

### 4.1 Docker 이미지 로드

온프렘 환경(리눅스 서버 또는 K8s 노드)에서 USB 디렉토리를 마운트한 후:

```bash
cd /path/to/usb-session-manager/docker-images

docker load < python-3.11-slim.tar.gz
```

확인:

```bash
docker images | grep python
# python  3.11-slim  ...
```

필요 시 이 이미지를 온프렘 전용 레지스트리(Nexus 등)에 다시 푸시할 수 있습니다.

```bash
# 예: Nexus 레지스트리로 태그 및 푸시
export REGISTRY=nexus.your-company.com:8082

docker tag python:3.11-slim $REGISTRY/python:3.11-slim
docker push $REGISTRY/python:3.11-slim
```

### 4.2 Python 패키지 오프라인 설치 (개발/운영 VM에서)

Session Manager를 VM 위에 직접 띄우는 경우 (Docker 없이) Python 패키지를 오프라인으로 설치해야 합니다.

```bash
cd /path/to/usb-session-manager/python-packages

# 가상환경 생성 (권장)
python3 -m venv .venv
source .venv/bin/activate

# 오프라인 설치
pip install --no-index --find-links=./wheels -r requirements.txt
```

> `--no-index` 옵션은 인터넷을 보지 말고 `./wheels` 에서만 패키지를 찾으라는 의미입니다.

Kubernetes에서 Docker 컨테이너로만 실행한다면, 이 단계는 **개발용/로컬 테스트에만 필요**합니다.

### 4.3 소스 코드 전개

```bash
cd /opt/services

# USB에서 복사
cp /mnt/usb/source-code/session-manager.tar.gz .

tar xzf session-manager.tar.gz
cd session-manager
```

이제 `/opt/services/session-manager` 내에 기존 Git 레포지토리의 내용(`app/`, `Dockerfile`, `docs/` 등)이 모두 존재하게 됩니다.

---

## 5. 온프레미스용 Docker 빌드

Session Manager 기본 `Dockerfile` 은 이미 인터넷 없이도 동작할 수 있도록 단순합니다.

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
...
```

에어갭 환경에서는 `pip install` 단계에서 외부 PyPI에 접근하면 안 되므로, 두 가지 방식 중 하나를 선택합니다.

### 5.1 방식 A – 사설 Nexus PyPI 사용

1. 온프렘에 Nexus를 설치하고, `pypi-internal`(hosted), `pypi-all`(group) 리포지토리를 구성합니다. (자세한 예시는 `ma_session/ma_migration.md` 참고)
2. 외부 환경에서 받은 wheel 파일들을 `pypi-internal` 에 업로드합니다.
3. Dockerfile 을 다음처럼 수정합니다.

```dockerfile
ARG PIP_INDEX_URL=http://nexus.your-company.com:8081/repository/pypi-all/simple
ARG PIP_TRUSTED_HOST=nexus.your-company.com

FROM python:3.11-slim
...
ENV PIP_INDEX_URL=$PIP_INDEX_URL \
    PIP_TRUSTED_HOST=$PIP_TRUSTED_HOST

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

빌드 시:

```bash
docker build \
  --build-arg PIP_INDEX_URL=http://nexus.your-company.com:8081/repository/pypi-all/simple \
  --build-arg PIP_TRUSTED_HOST=nexus.your-company.com \
  -t session-manager:latest .
```

### 5.2 방식 B – wheels 디렉토리를 이미지 안으로 복사

Nexus 같은 중앙 레지스트리가 아직 없다면, USB의 wheel 디렉토리를 이미지 빌드 시 그대로 복사하는 방법도 있습니다.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# wheel 파일 복사
COPY python-packages/wheels/ /wheels/
COPY python-packages/requirements.txt ./requirements.txt

RUN pip install --no-index --find-links=/wheels -r requirements.txt

COPY app/ ./app/
...
```

- 이 경우 `docker build` 실행 경로에 `python-packages/wheels/` 가 존재해야 하므로, 
  - USB에서 레포지토리 루트로 복사하거나
  - `Dockerfile` 을 USB 디렉토리 기준 경로에 맞게 조정해야 합니다.

---

## 6. 환경 변수 및 시크릿 관리

Session Manager는 DB/Redis/포트 등의 설정을 **환경 변수**로 받는 패턴을 사용해야 합니다. (실제 `config.py` 구현을 따릅니다.)

예시 환경 변수 (운영 예시, 실제 값은 모두 시크릿으로 관리):

```bash
export SESSION_MANAGER_PORT=5000

# Redis (Session Manager 앱에서는 REDIS_URL 하나로 관리)
# 온프렘 예시: 비밀번호가 없는 Redis
export REDIS_URL="redis://redis-stack.sas-portal-dev:6379/0"

# 비밀번호가 있는 Redis 의 예시는 아래와 같이 형태만 참고하고,
# 실제 패스워드는 K8s Secret/OS 시크릿 등에 따로 보관해야 합니다.
# export REDIS_URL="redis://user:${REDIS_PASSWORD}@redis.internal:6379/0"

# MariaDB
export DB_HOST=mariadb.internal
export DB_PORT=3306
export DB_USER=session_manager
export DB_PASSWORD="${DB_PASSWORD}"       # 시크릿
export DB_NAME=session_manager
```

Kubernetes에서 배포할 경우:

- `values.yaml` 또는 Helm 차트에서 위 환경 변수들을 `env` 혹은 `envFrom secretRef` 방식으로 주입
- 시크릿 값은 `kubectl create secret` 명령이나 ArgoCD/Helm의 value로 관리

---

## 7. Kubernetes 배포 개요

온프렘 K8s 클러스터가 이미 있다면, Session Manager는 표준 Deployment/Service로 배포할 수 있습니다.

### 7.1 예시 Deployment (요약)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: session-manager
  namespace: session-manager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: session-manager
  template:
    metadata:
      labels:
        app: session-manager
    spec:
      containers:
        - name: session-manager
          image: nexus.your-company.com:8082/session-manager:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 5000
          env:
            - name: SESSION_MANAGER_PORT
              value: "5000"
            - name: REDIS_HOST
              valueFrom:
                secretKeyRef:
                  name: session-manager-secrets
                  key: redis_host
            # ... 기타 DB/Redis 환경변수
          readinessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 30
            periodSeconds: 30
```

### 7.2 예시 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: session-manager
  namespace: session-manager
spec:
  type: ClusterIP
  selector:
    app: session-manager
  ports:
    - port: 5000
      targetPort: 5000
      protocol: TCP
      name: http
```

Ingress, TLS, DNS 등은 고객사 표준에 맞추어 구성합니다.

---

## 8. 온프렘 마이그레이션 체크리스트

프로덕션 전환 전에 다음 항목들을 확인합니다.

- [ ] `python:3.11-slim` 이미지가 온프렘 Docker 또는 Nexus 레지스트리에 로드됨
- [ ] Session Manager Docker 이미지가 온프렘 레지스트리에 빌드/푸시됨
- [ ] 모든 Python wheel 이 오프라인/내부 PyPI에서 정상적으로 설치됨
- [ ] Redis, MariaDB 인스턴스가 준비되고, 방화벽/DNS 설정이 완료됨
- [ ] Session Manager Pod에서 Redis/MariaDB로 접속이 가능한지 확인 (`/health` 및 간단 API 호출)
- [ ] Swagger UI(`/api/v1/docs`)에서 세션/컨텍스트/턴 API 호출이 정상 동작함
- [ ] 시크릿/환경 변수 주입이 올바르게 설정됨 (더미 값으로 먼저 검증)
- [ ] 모니터링/로그 수집 시스템(예: Prometheus/Grafana/ELK)에 지표와 로그가 정상 수집됨
- [ ] 롤백/재배포 절차가 준비되어 있음

---

## 9. 문제 해결 팁

### 9.1 Docker 빌드 시 패키지 설치 실패

증상:

- `pip install ...` 단계에서 외부 PyPI로 나가려다 실패

해결:

- 방식 A (Nexus 사용):
  - `PIP_INDEX_URL`, `PIP_TRUSTED_HOST` 가 내부 Nexus를 가리키는지 확인
  - Nexus `pypi-internal` 에 wheel 이 잘 업로드되었는지 확인
- 방식 B (wheels 복사):
  - `--no-index --find-links=/wheels` 옵션이 있는지 확인
  - 컨테이너 내부 `/wheels` 경로에 wheel 파일이 존재하는지 확인 (`docker run -it --entrypoint sh ...`)

### 9.2 애플리케이션 기동은 되지만 `/api/v1/docs` 접속 실패

체크:

- Pod 내에서 `curl http://localhost:5000/` 실행 시 200/JSON 응답이 오는지
- Service/Ingress 설정이 올바른지 (포트, 경로 `/api/v1/docs` 등)
- 브라우저/보안 소프트웨어가 로컬/내부 도메인 접근을 차단하지 않는지

### 9.3 Redis/MariaDB 연결 오류

체크:

- `REDIS_HOST`, `DB_HOST` 등이 실제 서비스 DNS/호스트와 일치하는지
- K8s에서 `kubectl exec` 으로 Pod 안에 들어가 `nc -vz REDIS_HOST REDIS_PORT` 등으로 포트 체크
- 방화벽/네트워크 팀과 포트/ACL 상태 확인

---

## 10. 마이그레이션 일정 예시

1. **준비 (1~2일)**
   - 외부 환경에서 Docker 이미지 및 wheel 다운로드
   - Session Manager 소스 아카이브 생성
   - USB 아티팩트 구조 정리 및 체크섬 확인

2. **온프렘 환경 세팅 (2~3일)**
   - Docker 및 (선택) Nexus 설치/구성
   - Redis/MariaDB 인스턴스 준비
   - USB 아티팩트 로드 및 레지스트리/파일 시스템 배치

3. **테스트/검증 (2~4일)**
   - Session Manager Docker 빌드
   - 테스트 K8s 네임스페이스에 배포
   - Swagger로 세션/컨텍스트/턴 API 시나리오 검증

4. **프로덕션 전환 (1일)**
   - 운영 네임스페이스/Ingress로 배포
   - 24~48시간 모니터링 및 롤백 계획 유지

---

## 부록: 빠른 명령어 모음

### A. 온프렘에서 Docker 이미지 로드

```bash
cd usb-session-manager/docker-images
docker load < python-3.11-slim.tar.gz
```

### B. 온프렘에서 Session Manager 빌드

```bash
cd /opt/services/session-manager

docker build -t session-manager:latest .
```

### C. 로컬(또는 VM)에서 Session Manager 직접 실행 (Docker 없이)

```bash
cd /opt/services/session-manager

python3 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links=/path/to/usb-session-manager/python-packages/wheels -r requirements.txt

export SESSION_MANAGER_PORT=5000
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

### D. K8s 배포 (Helm 미사용, 순수 kubectl)

```bash
kubectl create namespace session-manager
kubectl apply -f k8s/session-manager-deployment.yaml
kubectl apply -f k8s/session-manager-service.yaml
```

> `k8s/*.yaml` 은 고객사 표준에 맞는 템플릿으로 별도 관리하는 것을 권장합니다.
