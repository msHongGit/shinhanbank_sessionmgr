1. AKS
Resource Group: rg-langfuse-aks-test

Subscription: sub-open-axd-project-01

AKS  Cluster Name: shinhan-sol-demo-aks-01

API Server: shinhan-sol-demo-aks-01-dns-annuwtii.hcp.koreacentral.azmk8s.io

ACR: shbsoldemoacr 

Outbound IP: 20.214.122.80

비용 절감 및 빠른 제공을 위해 Azure Bastion은 사용하지 않습니다.

만약, 직접 Cluster에 접근하여 명령어를 사용하려면 다음과 같이 사용 가능합니다.

해당 설정 전에 미리 말씀주셔야 Cluster에 admin 권한으로 할당 가능합니다.

환경: 로컬환경(맥), Kubectl, AZ CLI, Kubectl, Helm, kubelogin설치 필요

설치 안되어 있을 경우

azure cli

brew update && brew install azure-cli

kubectl

brew install kubectl

kubelogin

brew install Azure/kubelogin/kubelogin

az login 및 get credential

az login --tenant "28fad9d9-3a2c-4a2f-b76f-8da5d0da9756"

로그인 이후 구독은 ‘sub-open-axd-project-01’ 선택

az aks get-credentials -g "rg-langfuse-aks-test" -n "shinhan-sol-demo-aks-01"

kubelogin

kubelogin --version (설치확인)

kubelogin convert-kubeconfig -l azurecli

kubectl get pod -A 명령어로 정상 동작 확인

2. CI/CD
CI/CD Flow는 다음과 같습니다.

현재 Application Repositories에 Push가 될 경우 Github Action이 Trigger 됩니다.
Workflow에 정의 된 대로, 파이프라인이 동작합니다.

2-1. CI/CD Flow
1. 시작 조건 (Trigger)
이벤트: main branch에 새로운 커밋이 Push 되었을 때 파이프라인이 시작됩니다.

(참고: 문서 파일 등 소스 코드와 무관한 파일만 수정된 경우는 제외하도록 설정됨)

'.md'         # README.md 등 모든 마크다운 파일 무시 - 'docs/'       # docs 폴더 내부의 변경사항 무시 - '.gitignore'    # gitignore 변경 무시 - 'LICENSE'       # 라이선스 파일 무시

2. 환경 변수 설정 및 준비 
소스 코드 체크아웃: 최신 소스 코드를 가져옵니다.

이미지 태그 생성: Git의 Short Commit Hash(커밋 ID 앞 7자리)를 추출하여 고유한 이미지 태그로 사용합니다.

이미지 이름 설정: 저장소 이름에서 특정 접두사를(shinhanbank-sol-) 제거하여  컨테이너 이미지 이름을 생성합니다.

3. 컨테이너 빌드 및 업로드 (CI)
ACR 로그인: ACR username & pw를 사용하여 ACR에 로그인 합니다.

이미지 빌드 & 푸시:

위에서 생성한 이름과 태그를 사용하여 Docker 이미지를 빌드합니다.

빌드된 이미지를 **ACR(이미지 저장소)**에 업로드합니다.

4. Helm Chart Update(CD)
Helm 차트 저장소 접근: 애플리케이션의 Helm Chart 저장소를 가져옵니다. (shinhanbank-sol-financial-knowledge-agent-chart)

버전 정보 갱신:

Helm Chart 내의 values.yaml 파일을 엽니다.

기존 이미지 태그 정보를 방금 빌드된 새 태그로 교체합니다.

변경 사항 반영:

"CI-Bot" 계정 이름으로 변경된 내용을 커밋 후 push 합니다.

5. Argocd Deployment
Argocd Deplyment: Argocd에서 해당 Helm Chart Repo의 변경점을 감지하고, 변경 된 이미지 태그를 참조하여 애플리케이션을 재 배포합니다.

즉 하기(2-2) Repository에 code 및 Docker file을 작성하여 집어넣은 뒤, push 하면 자동으로 code 및 Docker file을 작성하여 집어넣은 뒤, push 하면 자동으로 Application은 배포 됩니다.

2-2. Git Repository 정보
Organization: Axd-arena

repositories
현재 과거 기준의 Sample code 올라가 있는 상태입니다.

Helm Chart Repositories: shinhanbank-sol-financial-knowledge-agent-chart
*초기 이름설정을 이렇게 지었는데, 중간에 바꾸자니 시간이 걸려서 그냥 사용중입니다.  지식답변 agent의 helm chart가 아니라 모든 helm chart 해당 repo에 저장합니다.

Master: shinhanbank-sol-master-agent

지식답변: shinhanbank-sol-financial-knowledge-agent 

업무처리: shinhanbank-sol-banking-businees-agent 

context-manager: shinhanbank-sol-context-manager
위 4개 레포지토리에는 기존에 제공 받은 오래된 버전의 코드를 사용하였습니다. 

기타: 12월 26일 추가 된 repo:
shinhanbank-sol-skillset-agent

shinhanbank-sol-agent-gw

shinhanbank-sol-session-manager

shinhanbank-sol-api-gw

shinhanbank-sol-profile-batch

shinhanbank-sol-post-processor

해당 repository에는 가장 기본적인 python application을 push 해놓은 상태입니다.

argocd 정보

접속 주소: https://20.214.122.255/login?return_url=https%3A%2F%2F20.214.122.255%2Fapplications

인증서 경고 나와도 그냥 접속 하시면 됩니다.

ID/PW:

id: admin

pw: sNampSSKWlJt35uB

ACR

주소: Azure Container Registry | Microsoft Azure 

Repositories: 

banking-businees-agent

context-manager

financial-knowledge-agent

master-agent

3. 기타 정보
ztna 끄고 접속 가능

Langfuse

접속 주소: sol-langfuse.crewai-axd.com 

ES/Kibana

접속 주소: sol-kibana.crewai-axd.com

Redis

name: redis-shinhan-sol-test

endpoint: redis-shinhan-sol-test.koreacentral.redis.azure.net:10000

access key: 

40eMR6v24M6rghbwNjZeAZJxZIABPERQHAzCaFCHkJY=

y8tPergAuQX0E0MFzTinFuqnzbe52nVbtAzCaHUYXHU=

AI 모델
GPT-OSS-120b: 
Endpoint: https://shinhan-sol-open-ai.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview
Key: 7NT9zVRUJdNwEbUInwPyXryPnFrC3hKd5d0POCJQeGX7iQn7f0t8JQQJ99BLACNns7RXJ3w3AAAAACOGyQ1F

현재, application들은 kibana, langfuse를 제외하고는 도메인 중복 가능여부(path로 라우팅)등이 파악되지 않아 Ingress를 사용하지 않고 LB를 통해 Public IP로 노출시켜놓은 상태입니다.

Cluster에 접근하여 Service 정보를 조회해보면 각 Application별 외부 노출 IP 확인이 가능합니다.
---> 내용추가
Domain 등록하여 Ingress에 매핑시켜 놓았습니다. 다음 도메인으로 외부 접근 가능합니다.(ZTNA Off후 접근)

 Master Agent 그룹 
sol-master.crewai-axd.com

sol-skillset-agent.crewai-axd.com

sol-agent-gw.crewai-axd.com

sol-api-gw.crewai-axd.com

sol-session-manager.crewai-axd.com

sol-profile-batch.crewai-axd.com

sol-post-processor.crewai-axd.com

 개별 Agent 그룹 
sol-financial-knowledge-agent.crewai-axd.com

sol-banking-businees-agent.crewai-axd.com (businees 오타가 있는데, 그냥 사용합니다.)

sol-context-manager.crewai-axd.com

 

 

만약 내부 접근 원하시면 다음 k8s 내부 fqdn도 사용 가능할 것으로 보입니다.

1. Master Agent 그룹
(Namespace: master-agent, Port: 8000)

master-agent.master-agent.svc.cluster.local:8000

skillset-agent.master-agent.svc.cluster.local:8000

agent-gw.master-agent.svc.cluster.local:8000

api-gw.master-agent.svc.cluster.local:8000

session-manager.master-agent.svc.cluster.local:8000

profile-batch.master-agent.svc.cluster.local:8000

post-processor.master-agent.svc.cluster.local:8000

2. 개별 Agent 그룹
(각각 별도 Namespace, Port: 8000)

Financial Knowledge Agent:
financial-knowledge-agent.financial-knowledge-agent.svc.cluster.local:8000

Banking Business Agent:
banking-businees-agent.banking-businees-agent.svc.cluster.local:8000

Context Manager:
context-manager.context-manager.svc.cluster.local:8000