# Python에서 batch_profile_minio_retrieve.py 호출하기 (단건 조회)

**프로젝트명**: 신한은행 SOL 배치 MinIO 적재 시스템  
**문서 버전**: 1.2  
**작성일**: 2026-02-07  
**최종 업데이트**: 2026-02-08

본 문서는 **다른 Python 프로젝트/모듈에서 이 시스템을 호출하여 고객번호(CUSNO) 기준으로 단건 조회하는 방법**을 설명합니다.

> **📌 이 문서의 대상 독자**
> - 다른 Python 프로젝트에서 이 모듈을 사용하려는 개발자
> - MinIO에서 고객 프로파일 데이터를 **단건 조회**해야 하는 애플리케이션 개발자
> - 재작업 중에도 안정적인 데이터 조회가 필요한 운영자

> **✨ 주요 특징**
> - **단건 조회 전용**: 고객번호(CUSNO) 기준으로 한 건씩 조회
> - **간단한 통합**: 몇 줄의 코드로 바로 사용 가능
> - **자동 경로 관리**: 메타데이터 기반으로 조회 경로 자동 결정
> - **다운타임 최소화**: 재작업 중에도 기존 데이터 조회 가능
> - **에러 처리**: 명확한 에러 메시지와 예외 처리 지원
> - **빠른 조회**: 목표 응답 시간 100ms 이내

## 목차

1. [빠른 시작](#1-빠른-시작)
   - [최소한의 코드로 시작하기](#11-최소한의-코드로-시작하기)
   - [필수 정보](#12-필수-정보)
   - [필요한 정보 확인](#13-필요한-정보-확인)
2. [설치 및 의존성](#2-설치-및-의존성)
   - [필수 패키지 설치](#21-필수-패키지-설치)
   - [프로젝트 파일 복사 또는 경로 설정](#22-프로젝트-파일-복사-또는-경로-설정)
   - [Python 버전 확인](#23-python-버전-확인)
3. [기본 사용법](#3-기본-사용법)
   - [간단한 조회 예시](#31-간단한-조회-예시)
   - [환경 변수 사용](#32-환경-변수-사용)
4. [메타데이터 기반 조회 프로세스](#4-메타데이터-기반-조회-프로세스)
   - [조회 경로 결정 메커니즘](#41-조회-경로-결정-메커니즘)
   - [메타데이터 파일 구조](#42-메타데이터-파일-구조)
   - [다운타임 최소화 메커니즘](#43-다운타임-최소화-메커니즘)
5. [통합 방법](#5-통합-방법)
   - [함수로 리팩토링하여 직접 import (권장)](#51-함수로-리팩토링하여-직접-import-권장)
   - [클래스 기반 래퍼 (고급)](#52-클래스-기반-래퍼-고급-메타데이터-기반-조회)
   - [방법 비교](#53-방법-비교)
   - [권장 사항](#54-권장-사항)
6. [에러 처리](#6-에러-처리)
   - [기본 에러 처리](#61-기본-에러-처리)
   - [일반적인 에러 상황](#62-일반적인-에러-상황)
   - [재시도 로직](#63-재시도-로직)
7. [고급 사용법](#7-고급-사용법)
   - [클래스 래퍼를 사용한 연결 재사용](#71-클래스-래퍼를-사용한-연결-재사용)
8. [FAQ 및 트러블슈팅](#8-faq-및-트러블슈팅)
   - [자주 묻는 질문 (FAQ)](#81-자주-묻는-질문-faq)
   - [트러블슈팅](#82-트러블슈팅)
   - [디버깅 팁](#83-디버깅-팁)
9. [재작업 프로세스 및 다운타임 최소화](#9-재작업-프로세스-및-다운타임-최소화)
   - [재작업 프로세스 개요](#91-재작업-프로세스-개요)
   - [재작업 프로세스 단계](#92-재작업-프로세스-단계)
   - [다운타임 최소화 메커니즘](#93-다운타임-최소화-메커니즘)
   - [Python 애플리케이션에서의 활용](#94-python-애플리케이션에서의-활용)
   - [재작업 시 주의사항](#95-재작업-시-주의사항)
10. [주의 사항 및 참고 정보](#10-주의-사항-및-참고-정보)
11. [API 레퍼런스](#11-api-레퍼런스)
12. [변경 이력](#12-변경-이력)

---

## 1. 빠른 시작

### 1.1 최소한의 코드로 시작하기 (단건 조회)

다른 프로젝트에서 이 모듈을 사용하여 **고객번호(CUSNO) 기준으로 단건 조회**하려면 다음 단계를 따르세요:

**1단계: 필수 패키지 설치**
```bash
pip install minio==7.2.20 orjson==3.11.7 cryptography==46.0.4
```

**2단계: 프로젝트 경로 설정**
```python
import sys
import os

# 방법 1: 절대 경로 사용 (권장)
sys.path.insert(0, '/path/to/shinhanbank-sol-batch-minio-load/src')

# 방법 2: 상대 경로 사용
current_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(current_dir, '..', 'shinhanbank-sol-batch-minio-load', 'src')
sys.path.insert(0, os.path.abspath(project_path))
```

**3단계: 함수 import 및 사용**
```python
from batch_profile_minio_retrieve import retrieve_cusno

# 데이터 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="your-access-key",
    secret_key="your-secret-key",
    data_type="daily",  # 또는 "monthly"
    cusno=700000001
)

if data:
    print(f"조회 성공: {data}")
else:
    print("데이터를 찾을 수 없습니다")
```

**완료!** 이제 다른 프로젝트에서 MinIO 데이터를 **단건 조회**할 수 있습니다.

> **💡 참고**: 이 모듈은 고객번호(CUSNO) 기준으로 **단건 조회**만 지원합니다. 여러 고객번호를 조회하려면 반복문을 사용하여 각각 단건 조회를 호출하세요.

### 1.2 필수 정보

| 항목 | 내용 |
|------|------|
| **버킷** | 통일된 버킷 `shinhanobj` 사용 (환경 변수 `MINIO_BUCKET`으로 변경 가능) |
| **데이터 타입** | `data_type` 파라미터로 일별(`daily`) 또는 월별(`monthly`) 구분 |
| **Python 버전** | 3.12 이상 (권장: 3.12.10) |
| **필수 패키지** | minio (7.2.20), orjson (3.11.7), cryptography (46.0.4) |
| **메타데이터 기반 조회** | `_latest_date.json` 파일로 조회 경로 동적 결정 (자동 처리) |
| **다운타임 최소화** | 재작업 중에도 기존 데이터 조회 가능 (자동 처리) |

### 1.3 필요한 정보 확인

다른 프로젝트에서 사용하기 전에 다음 정보를 확인하세요:

1. **MinIO 서버 정보**
   - 엔드포인트 URL (예: `http://localhost:9000`)
   - Access Key
   - Secret Key

2. **데이터 타입**
   - 일별 데이터: `data_type="daily"`
   - 월별 데이터: `data_type="monthly"`

3. **프로젝트 경로**
   - 이 프로젝트의 소스 코드 경로
   - 또는 필요한 파일을 복사할 위치

---

## 2. 설치 및 의존성

### 2.1 필수 패키지 설치

다른 프로젝트에서 사용하기 전에 필수 패키지를 설치해야 합니다:

```bash
# pip를 사용한 설치
pip install minio==7.2.20
pip install orjson==3.11.7
pip install cryptography==46.0.4

# 또는 requirements.txt 사용
pip install -r requirements.txt
```

**requirements.txt 예시:**
```txt
minio==7.2.20
orjson==3.11.7
cryptography==46.0.4
```

### 2.2 프로젝트 파일 복사 또는 경로 설정

**방법 1: 파일 복사 (간단)**

```bash
# 필요한 파일만 복사
cp /path/to/shinhanbank-sol-batch-minio-load/src/batch_profile_minio_retrieve.py /your/project/
cp /path/to/shinhanbank-sol-batch-minio-load/src/batch_profile_utils.py /your/project/
cp /path/to/shinhanbank-sol-batch-minio-load/src/batch_profile_config.py /your/project/
# ... 기타 필요한 모듈들
```

**방법 2: 경로 추가 (권장)**

```python
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, '/path/to/shinhanbank-sol-batch-minio-load/src')

from batch_profile_minio_retrieve import retrieve_cusno
```

**방법 3: 서브모듈로 추가 (Git 사용 시)**

```bash
# Git 서브모듈로 추가
git submodule add https://github.com/your-org/shinhanbank-sol-batch-minio-load.git vendor/minio-load
```

### 2.3 Python 버전 확인

```python
import sys

if sys.version_info < (3, 12):
    raise RuntimeError("Python 3.12 이상이 필요합니다. 현재 버전: {}".format(sys.version))
```

---

## 3. 기본 사용법

### 3.1 간단한 단건 조회 예시

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 일별 데이터 단건 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001  # 조회할 고객번호 (단건)
)

if data:
    print(f"조회 성공 - 고객번호: {data.get('CUSNO')}")
    print(f"데이터: {data}")
else:
    print("데이터를 찾을 수 없습니다")
```

### 3.2 환경 변수 사용

```python
import os
from batch_profile_minio_retrieve import retrieve_cusno

# 환경 변수에서 설정 읽기
endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

# 단건 조회
data = retrieve_cusno(
    endpoint=endpoint,
    access_key=access_key,
    secret_key=secret_key,
    data_type="daily",
    cusno=700000001  # 조회할 고객번호 (단건)
)

if data:
    print(f"조회 성공: {data}")
else:
    print("데이터 없음")
```

## 4. 메타데이터 기반 조회 프로세스

> **💡 중요**: 이 섹션은 시스템의 내부 동작 방식을 설명합니다. 실제 사용 시에는 자동으로 처리되므로 별도의 코드 작성이 필요 없습니다.

### 조회 경로 결정 메커니즘

`batch_profile_minio_retrieve.py`는 조회 시 다음 순서로 조회 경로를 결정합니다:

1. **메타데이터 조회**: `{prefix}/_latest_date.json` 파일 읽기 시도
   - 성공 시: `use_latest`, `latest_date` 추출
   - 실패 시: 일자별 디렉토리 목록에서 최신 일자 추출

2. **조회 경로 결정**:
   - `use_latest == true`: `{prefix}/latest/` 디렉토리 사용
   - `use_latest == false`: `{prefix}/{latest_date}/` 디렉토리 사용 (예: `ifc_cus_dd_smry_tot/20260206/`)
   - 메타데이터 없음: `{prefix}/{최신일자}/` 사용 (fallback)

3. **데이터 조회**: 결정된 경로에서 인덱스 샤드 및 bulk.jsonl 조회

### 메타데이터 파일 구조

`_latest_date.json` 파일 구조:

```json
{
  "latest_date": "20260206",
  "load_date": "2026-02-06",
  "use_latest": false,
  "updated_at": "2026-02-08T20:29:10.123456+00:00"
}
```

**필드 설명:**
- `latest_date`: 최신 데이터 일자 (YYYYMMDD 형식)
- `load_date`: 적재 일자 (YYYY-MM-DD 형식)
- `use_latest`: 조회 경로 플래그
  - `true`: `latest/` 디렉토리에서 조회
  - `false`: `YYYYMMDD/` 디렉토리에서 조회
- `updated_at`: 메타데이터 업데이트 시각 (ISO 8601 형식)

### 다운타임 최소화 메커니즘

**재작업 프로세스 중 조회 가용성:**

1. **일반 적재 (첫 적재)**:
   - 데이터 적재 → 일자별 보관 → 메타데이터 업데이트 (`use_latest: false`)
   - 조회: 일자별 디렉토리에서 조회

2. **재작업 (기존 일자 데이터 재적재)**:
   - **백업 단계**: 백업기준일자 데이터 → `latest/` 백업
   - **메타데이터 임시 업데이트**: `use_latest: true` (백업된 데이터 조회 가능)
   - **새 데이터 적재**: staging → 기준일자/ 복사
   - **메타데이터 최종 업데이트**: `use_latest: false` (일자별 디렉토리에서 조회)
   - **다운타임**: 메타데이터 업데이트 시간만큼 (1초 미만)

**재작업 중 조회 동작:**
- 백업 단계 완료 후: `latest/`에서 백업된 데이터 조회 가능
- 새 데이터 적재 중: `latest/`에서 백업된 데이터 계속 조회 가능
- 최종 전환: 메타데이터 업데이트 (1초 미만) → 일자별 디렉토리에서 새 데이터 조회

## 5. 통합 방법

### 5.1 함수로 리팩토링하여 직접 import (권장)

더 효율적인 방법은 `batch_profile_minio_retrieve.py`를 리팩토링하여 함수로 분리한 후 직접 import하여 사용하는 것입니다.

### 리팩토링된 retrieve 함수 (메타데이터 기반 조회)

`src/batch_profile_minio_retrieve.py`에 다음 함수를 추가하거나 수정:

```python
def retrieve_cusno(endpoint, access_key, secret_key, data_type, cusno):
    """
    MinIO에서 CUSNO로 단건 조회 (함수 버전, 메타데이터 기반 조회 경로 결정)
    
    Args:
        endpoint: MinIO 엔드포인트 (예: "http://localhost:9000")
        access_key: MinIO Access Key
        secret_key: MinIO Secret Key
        data_type: 데이터 타입 ("daily" 또는 "monthly") - prefix 구분용
        cusno: 고객번호 (문자열 또는 숫자)
    
    Returns:
        dict: 조회된 데이터
        None: 조회 실패 시
    
    Raises:
        Exception: 조회 중 오류 발생 시
    
    Note:
        실제 버킷은 통일된 버킷 "shinhanobj"를 사용하며, data_type으로 prefix를 구분합니다.
        조회 경로는 _latest_date.json 메타데이터 파일을 기반으로 동적으로 결정됩니다.
    """
    import orjson
    from minio import Minio
    import os
    import json
    
    # 버킷 이름은 shinhanobj로 통일
    bucket = os.environ.get("MINIO_BUCKET", "shinhanobj")
    
    # data_type 검증
    data_type = data_type.strip().lower()
    if data_type not in ("daily", "monthly"):
        data_type = os.environ.get("MINIO_DATA_TYPE", "daily").strip().lower()
        if data_type not in ("daily", "monthly"):
            data_type = "daily"
    
    object_prefix = PREFIX_MONTHLY if data_type == "monthly" else PREFIX_DAILY
    
    # S3Error import (minio 버전 호환성)
    try:
        from minio.error import S3Error
    except ImportError:
        try:
            from minio.commonconfig import S3Error
        except ImportError:
            try:
                from minio.error import ResponseError as S3Error
            except ImportError:
                class S3Error(Exception):
                    def __init__(self, message, code=None, *args, **kwargs):
                        super().__init__(message, *args, **kwargs)
                        self.code = code
    
    # MinIO 클라이언트 생성
    secure = endpoint.strip().lower().startswith("https://")
    host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    client = Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)
    
    # 메타데이터 기반 조회 경로 결정
    latest_date_meta_key = f"{object_prefix}/_latest_date.json"
    query_path = None
    latest_date_str = None
    use_latest = False
    
    try:
        # 메타데이터 파일 읽기
        resp = client.get_object(bucket, latest_date_meta_key)
        latest_date_meta = json.loads(resp.read())
        resp.close()
        resp.release_conn()
        
        latest_date_str = latest_date_meta.get("latest_date") or latest_date_meta.get("load_date", "").replace("-", "")
        use_latest = latest_date_meta.get("use_latest", False)
        
        if latest_date_str and len(latest_date_str) == 8:
            if use_latest:
                query_path = f"{object_prefix}/latest/"
            else:
                query_path = f"{object_prefix}/{latest_date_str}/"
    except Exception:
        # 메타데이터가 없거나 읽기 실패 시 일자별 디렉토리 목록에서 최신 일자 찾기
        try:
            objects = client.list_objects(bucket, prefix=f"{object_prefix}/", recursive=False)
            date_dirs = []
            for obj in objects:
                obj_name = obj.object_name
                if obj_name.startswith(f"{object_prefix}/"):
                    remaining = obj_name[len(f"{object_prefix}/"):]
                    if '/' in remaining:
                        date_dir = remaining.split('/')[0]
                        if date_dir and len(date_dir) == 8 and date_dir.isdigit():
                            date_dirs.append(date_dir)
            if date_dirs:
                latest_date_str = sorted(date_dirs, reverse=True)[0]
                query_path = f"{object_prefix}/{latest_date_str}/"
        except Exception:
            pass
    
    # query_path가 설정되지 않은 경우 fallback
    if not query_path:
        if latest_date_str:
            query_path = f"{object_prefix}/{latest_date_str}/"
        else:
            # 최종 fallback: latest/ 사용
            query_path = f"{object_prefix}/latest/"
    
    cusno_str = str(cusno).strip()
    bulk_key = f"{query_path}bulk.jsonl"
    single_key = f"{query_path}{cusno_str}.json"
    prefix = _index_prefix(cusno_str)
    index_shard_key = f"{query_path}index_{prefix}.json"
    index_full_key = f"{query_path}index.json"
    
    def fetch_via_index(index_key):
        try:
            resp = client.get_object(bucket, index_key)
            index = orjson.loads(resp.read())
            resp.close()
            if cusno_str not in index:
                return None
            start_off, length = index[cusno_str]
            
            try:
                resp = client.get_object(bucket, bulk_key, offset=start_off, length=length)
                line = resp.read()
                resp.close()
                return orjson.loads(line)
            except (TypeError, AttributeError):
                resp = client.get_object(bucket, bulk_key)
                data = resp.read()
                resp.close()
                line = data[start_off:start_off + length]
                return orjson.loads(line)
        except Exception:
            return None
    
    # 조회 시도
    doc = None
    try:
        doc = fetch_via_index(index_shard_key)
    except S3Error:
        try:
            doc = fetch_via_index(index_full_key)
        except S3Error:
            try:
                resp = client.get_object(bucket, single_key)
                doc = orjson.loads(resp.read())
                resp.close()
            except S3Error:
                return None
    
    return doc


def main():
    """명령줄 인터페이스"""
    if len(sys.argv) < 6:
        print(
            "Usage: batch_profile_minio_retrieve.py <endpoint> <access_key> <secret_key> <data_type> <CUSNO>",
            file=sys.stderr,
        )
        print("  data_type: daily 또는 monthly (prefix 구분용, 실제 버킷은 shinhanobj 사용)", file=sys.stderr)
        sys.exit(1)
    
    endpoint = sys.argv[1]
    access_key = sys.argv[2]
    secret_key = sys.argv[3]
    data_type = sys.argv[4].strip()
    cusno = sys.argv[5].strip()
    
    doc = retrieve_cusno(endpoint, access_key, secret_key, data_type, cusno)
    
    if doc is None:
        print(f"해당 CUSNO 없음 또는 데이터 미적재: {cusno}", file=sys.stderr, flush=True)
        sys.exit(1)
    
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(orjson.dumps(doc, option=orjson.OPT_INDENT_2).decode(), flush=True)
    print(f"조회 소요시간: {elapsed_ms:.2f} ms", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
```

### 함수를 import하여 사용

```python
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.batch_profile_minio_retrieve import retrieve_cusno

# 사용 예시
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",  # 일별 데이터
    cusno=700000001
)

# 월별 데이터 조회 예시
# data = retrieve_cusno(
#     endpoint="http://localhost:9000",
#     access_key="minioadmin",
#     secret_key="minioadmin",
#     data_type="monthly",  # 월별 데이터
#     cusno=700000001
# )

if data:
    print(f"CUSNO: {data.get('CUSNO')}")
    print(f"암호화 여부: {data.get('encrypted_yn')}")
    print(f"데이터: {data.get('data')}")
else:
    print("데이터 조회 실패")
```

### 5.2 클래스 기반 래퍼 (고급, 메타데이터 기반 조회)

여러 번 조회하는 경우 클래스 기반 래퍼를 만들어 연결을 재사용할 수 있습니다. 메타데이터 기반 조회 경로 결정을 포함합니다:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from minio import Minio
import orjson
import json

class MinIORetrieveClient:
    """MinIO 조회 클라이언트 (메타데이터 기반 조회 경로 결정)"""
    
    def __init__(self, endpoint, access_key, secret_key, bucket="shinhanobj"):
        """
        Args:
            endpoint: MinIO 엔드포인트
            access_key: MinIO Access Key
            secret_key: MinIO Secret Key
            bucket: 버킷 이름 (기본값: "shinhanobj")
        """
        secure = endpoint.strip().lower().startswith("https://")
        host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        self.client = Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        self._query_path_cache = {}  # {prefix: query_path} 캐시
    
    def _get_query_path(self, object_prefix):
        """
        메타데이터 기반 조회 경로 결정 (캐시 사용)
        
        Args:
            object_prefix: 객체 prefix (예: "ifc_cus_dd_smry_tot")
        
        Returns:
            str: 조회 경로 (예: "ifc_cus_dd_smry_tot/20260206/" 또는 "ifc_cus_dd_smry_tot/latest/")
        """
        # 캐시 확인
        if object_prefix in self._query_path_cache:
            return self._query_path_cache[object_prefix]
        
        latest_date_meta_key = f"{object_prefix}/_latest_date.json"
        query_path = None
        
        try:
            # 메타데이터 파일 읽기
            resp = self.client.get_object(self.bucket, latest_date_meta_key)
            latest_date_meta = json.loads(resp.read())
            resp.close()
            resp.release_conn()
            
            latest_date_str = latest_date_meta.get("latest_date") or latest_date_meta.get("load_date", "").replace("-", "")
            use_latest = latest_date_meta.get("use_latest", False)
            
            if latest_date_str and len(latest_date_str) == 8:
                if use_latest:
                    query_path = f"{object_prefix}/latest/"
                else:
                    query_path = f"{object_prefix}/{latest_date_str}/"
        except Exception:
            # 메타데이터가 없거나 읽기 실패 시 일자별 디렉토리 목록에서 최신 일자 찾기
            try:
                objects = self.client.list_objects(self.bucket, prefix=f"{object_prefix}/", recursive=False)
                date_dirs = []
                for obj in objects:
                    obj_name = obj.object_name
                    if obj_name.startswith(f"{object_prefix}/"):
                        remaining = obj_name[len(f"{object_prefix}/"):]
                        if '/' in remaining:
                            date_dir = remaining.split('/')[0]
                            if date_dir and len(date_dir) == 8 and date_dir.isdigit():
                                date_dirs.append(date_dir)
                if date_dirs:
                    latest_date_str = sorted(date_dirs, reverse=True)[0]
                    query_path = f"{object_prefix}/{latest_date_str}/"
            except Exception:
                pass
        
        # query_path가 설정되지 않은 경우 fallback
        if not query_path:
            query_path = f"{object_prefix}/latest/"
        
        # 캐시에 저장
        self._query_path_cache[object_prefix] = query_path
        return query_path
    
    def retrieve_cusno(self, data_type, cusno, refresh_cache=False):
        """
        CUSNO로 단건 조회 (메타데이터 기반 조회 경로 사용)
        
        Args:
            data_type: 데이터 타입 ("daily" 또는 "monthly") - prefix 구분용
            cusno: 고객번호
            refresh_cache: 캐시 갱신 여부 (재작업 후 메타데이터 변경 시 True)
        
        Returns:
            dict: 조회된 데이터 또는 None
        
        Note:
            실제 버킷은 통일된 버킷 "shinhanobj"를 사용하며, data_type으로 prefix를 구분합니다.
            조회 경로는 _latest_date.json 메타데이터 파일을 기반으로 동적으로 결정됩니다.
        """
        # 캐시 갱신 요청 시 캐시 삭제
        if refresh_cache:
            object_prefix = "ifc_cus_mmby_smry_tot" if data_type == "monthly" else "ifc_cus_dd_smry_tot"
            if object_prefix in self._query_path_cache:
                del self._query_path_cache[object_prefix]
        
        # retrieve_cusno 함수 로직 구현
        # (위의 함수 버전 코드 사용, _get_query_path 사용)
        pass


# 사용 예시
client = MinIORetrieveClient(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin"
)

# 단건 조회를 반복할 때 연결 및 조회 경로 캐시 재사용
data1 = client.retrieve_cusno("daily", 700000001)    # 첫 번째 단건 조회 (메타데이터 기반 조회 경로 사용)
data2 = client.retrieve_cusno("daily", 700000002)    # 두 번째 단건 조회 (캐시된 조회 경로 사용)
data3 = client.retrieve_cusno("monthly", 700000001)  # 세 번째 단건 조회 (메타데이터 기반 조회 경로 사용)

# 재작업 후 메타데이터 변경 시 캐시 갱신
data4 = client.retrieve_cusno("daily", 700000001, refresh_cache=True)  # 캐시 갱신 후 단건 조회
```

### 5.3 방법 비교

| 방법 | 장점 | 단점 | 사용 시기 |
|------|------|------|-----------|
| 함수 import | 빠름, 에러 처리 용이, 재사용 가능, 메타데이터 기반 조회 경로 결정 | 코드 리팩토링 필요 | 단건 조회, 간단한 통합 |
| 클래스 래퍼 | 연결 재사용, 조회 경로 캐싱, 최적화 가능, 재작업 후 캐시 갱신 지원 | 구현 복잡도 높음 | 반복 조회, 성능 최적화 필요 |

### 5.4 권장 사항

- **단건 조회**: 함수 import 사용 (메타데이터 기반 조회 자동 적용)
- **반복 조회**: 클래스 래퍼 사용 (연결 재사용 및 조회 경로 캐싱으로 성능 최적화)
- **재작업 후**: 클래스 래퍼 사용 시 `refresh_cache=True` 옵션으로 캐시 갱신

---

## 6. 에러 처리

### 6.1 기본 에러 처리

```python
from batch_profile_minio_retrieve import retrieve_cusno

try:
    data = retrieve_cusno(
        endpoint="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        data_type="daily",
        cusno=700000001
    )
    
    if data is None:
        print("데이터를 찾을 수 없습니다")
    else:
        print(f"조회 성공: {data}")
        
except Exception as e:
    print(f"조회 중 오류 발생: {e}")
    # 로깅 또는 에러 처리
```

### 6.2 일반적인 에러 상황

#### 6.2.1 연결 오류

```python
try:
    data = retrieve_cusno(
        endpoint="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        data_type="daily",
        cusno=700000001
    )
except ConnectionError as e:
    print(f"MinIO 서버 연결 실패: {e}")
    print("MinIO 서버가 실행 중인지 확인하세요")
except Exception as e:
    print(f"예상치 못한 오류: {e}")
```

#### 6.2.2 인증 오류

```python
try:
    data = retrieve_cusno(
        endpoint="http://localhost:9000",
        access_key="wrong-key",
        secret_key="wrong-secret",
        data_type="daily",
        cusno=700000001
    )
except Exception as e:
    if "Access Denied" in str(e) or "403" in str(e):
        print("인증 실패: Access Key 또는 Secret Key를 확인하세요")
    else:
        print(f"오류: {e}")
```

#### 6.2.3 데이터 없음

```python
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=999999999  # 존재하지 않는 고객번호
)

if data is None:
    print("해당 고객번호의 데이터가 없습니다")
    # 또는 기본값 반환
    data = {}
```

### 6.3 재시도 로직

```python
import time
from batch_profile_minio_retrieve import retrieve_cusno

def retrieve_with_retry(endpoint, access_key, secret_key, data_type, cusno, max_retries=3):
    """
    재시도 로직이 포함된 조회 함수
    """
    for attempt in range(max_retries):
        try:
            data = retrieve_cusno(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                data_type=data_type,
                cusno=cusno
            )
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 지수 백오프
                print(f"조회 실패 (시도 {attempt + 1}/{max_retries}), {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                print(f"최대 재시도 횟수 초과: {e}")
                raise
    return None

# 사용 예시
data = retrieve_with_retry(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001
)
```

---

## 7. 고급 사용법

### 7.1 클래스 래퍼를 사용한 연결 재사용

```python
from minio import Minio
import orjson
import json

class MinIORetrieveClient:
    """MinIO 조회 클라이언트 (메타데이터 기반 조회 경로 결정)"""
    
    def __init__(self, endpoint, access_key, secret_key, bucket="shinhanobj"):
        """
        Args:
            endpoint: MinIO 엔드포인트
            access_key: MinIO Access Key
            secret_key: MinIO Secret Key
            bucket: 버킷 이름 (기본값: "shinhanobj")
        """
        secure = endpoint.strip().lower().startswith("https://")
        host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        self.client = Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        self._query_path_cache = {}  # {prefix: query_path} 캐시
    
    def retrieve_cusno(self, data_type, cusno, refresh_cache=False):
        """
        CUSNO로 단건 조회 (메타데이터 기반 조회 경로 사용)
        
        Args:
            data_type: 데이터 타입 ("daily" 또는 "monthly")
            cusno: 고객번호
            refresh_cache: 캐시 갱신 여부 (재작업 후 메타데이터 변경 시 True)
        
        Returns:
            dict: 조회된 데이터 또는 None
        """
        # 실제 구현은 위의 코드 참조
        # ...
        pass

# 사용 예시
client = MinIORetrieveClient(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin"
)

# 단건 조회를 반복할 때 연결 및 조회 경로 캐시 재사용
data1 = client.retrieve_cusno("daily", 700000001)  # 첫 번째 단건 조회
data2 = client.retrieve_cusno("daily", 700000002)  # 두 번째 단건 조회
data3 = client.retrieve_cusno("monthly", 700000001)  # 세 번째 단건 조회

# 재작업 후 메타데이터 변경 시 캐시 갱신
data4 = client.retrieve_cusno("daily", 700000001, refresh_cache=True)  # 캐시 갱신 후 단건 조회
```

---

## 8. FAQ 및 트러블슈팅

### 8.1 자주 묻는 질문 (FAQ)

#### Q1: 함수를 import할 수 없습니다

**A:** 프로젝트 경로를 Python 경로에 추가해야 합니다:

```python
import sys
import os

# 방법 1: 절대 경로 사용
sys.path.insert(0, '/path/to/shinhanbank-sol-batch-minio-load/src')

# 방법 2: 상대 경로 사용
current_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(current_dir, '..', 'shinhanbank-sol-batch-minio-load', 'src')
sys.path.insert(0, os.path.abspath(project_path))

from batch_profile_minio_retrieve import retrieve_cusno
```

#### Q2: "ModuleNotFoundError: No module named 'orjson'" 오류가 발생합니다

**A:** 필수 패키지를 설치하세요:

```bash
pip install orjson==3.11.7
pip install minio==7.2.20
pip install cryptography==46.0.4
```

#### Q3: 조회 결과가 항상 None입니다

**A:** 다음을 확인하세요:

1. **MinIO 서버 연결 확인**:
   ```python
   from minio import Minio
   client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
   buckets = client.list_buckets()
   print(f"접근 가능한 버킷: {[b.name for b in buckets]}")
   ```

2. **데이터 존재 확인**:
   ```python
   # 데이터가 실제로 적재되었는지 확인
   # MinIO 콘솔에서 확인하거나 다른 도구 사용
   ```

3. **고객번호 형식 확인**:
   ```python
   # 고객번호는 숫자 문자열이어야 합니다
   cusno = "700000001"  # 또는 700000001 (숫자)
   ```

#### Q4: 재작업 중에도 데이터를 조회할 수 있나요?

**A:** 네, 가능합니다. 시스템이 자동으로 처리합니다:

- 재작업 중: `latest/`에서 백업된 데이터 조회
- 재작업 완료 후: 일자별 디렉토리에서 새 데이터 조회
- 별도의 코드 변경 불필요

#### Q5: 성능을 최적화하려면 어떻게 해야 하나요?

**A:** 다음 방법을 사용하세요:

1. **클래스 래퍼 사용**: 연결 재사용 및 조회 경로 캐싱으로 성능 최적화
2. **연결 재사용**: 같은 클라이언트 인스턴스를 여러 번 사용하여 연결 재사용

### 8.2 트러블슈팅

#### 문제 1: 연결 타임아웃

**증상**: `ConnectionTimeout` 또는 `ReadTimeout` 오류

**해결 방법**:
```python
from minio import Minio

# 타임아웃 설정
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)
# MinIO 클라이언트의 타임아웃 설정은 내부적으로 처리됩니다
```

#### 문제 2: 메타데이터 파일을 찾을 수 없음

**증상**: 경고 메시지 "최신 일자 메타데이터를 읽을 수 없습니다"

**해결 방법**:
- 데이터가 적재되었는지 확인
- 일자별 디렉토리 목록에서 최신 일자를 자동으로 찾으므로 정상 동작합니다
- 경고 메시지는 무시해도 됩니다 (fallback 메커니즘 작동)

#### 문제 3: Python 버전 호환성

**증상**: `SyntaxError` 또는 버전 관련 오류

**해결 방법**:
```python
import sys

if sys.version_info < (3, 12):
    print("Python 3.12 이상이 필요합니다")
    print(f"현재 버전: {sys.version}")
    sys.exit(1)
```

### 8.3 디버깅 팁

#### 로깅 활성화

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# MinIO 클라이언트 로깅
logging.getLogger('minio').setLevel(logging.DEBUG)
```

#### 조회 경로 확인

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 조회 전에 메타데이터 확인
from minio import Minio
import json

client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
try:
    resp = client.get_object("shinhanobj", "ifc_cus_dd_smry_tot/_latest_date.json")
    meta = json.loads(resp.read())
    resp.close()
    resp.release_conn()
    print(f"메타데이터: {meta}")
    print(f"조회 경로: {'latest/' if meta.get('use_latest') else meta.get('latest_date') + '/'}")
except Exception as e:
    print(f"메타데이터 읽기 실패: {e}")
```


## 10. 주의 사항 및 참고 정보

### 10.1 버킷 및 데이터 타입

- **버킷**: 통일된 버킷 `shinhanobj` 사용 (환경 변수 `MINIO_BUCKET`으로 변경 가능)
- **데이터 타입**: `data_type` 파라미터로 일별(`daily`) 또는 월별(`monthly`) 구분
  - `daily`: prefix `ifc_cus_dd_smry_tot/` 사용
  - `monthly`: prefix `ifc_cus_mmby_smry_tot/` 사용

### 10.2 메타데이터 기반 조회 경로 (자동 처리)

> **💡 중요**: 조회 경로 결정은 시스템이 자동으로 처리합니다. 사용자는 별도의 코드 작성이 필요 없습니다.

- **조회 경로 결정**: `_latest_date.json` 메타데이터 파일을 기반으로 동적 결정
  - `use_latest: true`: `{prefix}/latest/` 디렉토리에서 조회
  - `use_latest: false`: `{prefix}/{latest_date}/` 디렉토리에서 조회 (예: `ifc_cus_dd_smry_tot/20260206/`)
  - 메타데이터 없음: 일자별 디렉토리 목록에서 최신 일자 추출하여 조회 (fallback)

### 10.3 환경 변수

- `MINIO_BUCKET`: 버킷 이름 (기본값: `shinhanobj`)
- `MINIO_DATA_TYPE`: 데이터 타입 (기본값: `daily`)

### 10.4 사용 예시 요약

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 일별 데이터 조회 (메타데이터 기반 조회 경로 자동 결정)
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",  # 일별 데이터
    cusno=700000001
)

# 월별 데이터 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="monthly",  # 월별 데이터
    cusno=700000001
)

# 재작업 전, 중, 후 모두 동일한 코드 사용
# 내부적으로 메타데이터를 확인하여 올바른 경로에서 조회
# - 재작업 전: 일자별 디렉토리에서 조회
# - 재작업 중: latest/에서 백업된 데이터 조회 (다운타임 없음)
# - 재작업 완료 후: 일자별 디렉토리에서 새 데이터 조회
```

---

## 9. 재작업 프로세스 및 다운타임 최소화

> **💡 중요**: 재작업 프로세스는 시스템이 자동으로 처리합니다. 사용자는 별도의 코드 변경 없이 동일한 방식으로 조회하면 됩니다.

### 9.1 재작업 프로세스 개요

재작업(기존 일자 데이터 재적재) 시에도 조회 다운타임을 최소화하기 위해 메타데이터 기반 하이브리드 아키텍처를 사용합니다.

### 9.2 재작업 프로세스 단계

1. **스키마 검증 및 재작업 감지**
   - 기준일자에 데이터 존재 확인
   - 백업기준일자 필수 체크 (없으면 종료)

2. **백업 단계 (다운타임 제로)**
   - 백업기준일자 데이터 → `latest/` 백업 (서버 측 복사)
   - 메타데이터 임시 업데이트: `use_latest: true`, `latest_date: 백업기준일자`
   - **이 시점부터 클라이언트는 `latest/`에서 백업된 데이터 조회 가능**

3. **새 데이터 적재**
   - staging에 새 데이터 업로드
   - staging → 기준일자(YYYYMMDD/) 복사 (일자별 보관)

4. **최종 메타데이터 업데이트 (원자적 전환)**
   - 메타데이터 최종 업데이트: `use_latest: false`, `latest_date: 기준일자`
   - **메타데이터 업데이트는 1초 미만으로 완료되므로 다운타임 최소화**

### 다운타임 최소화 메커니즘

#### 원자적 전환 (Atomic Switch)

메타데이터 파일(`_latest_date.json`) 업데이트는 단일 객체 PUT 작업으로, 1초 미만에 완료됩니다.

**전환 시점:**
- 일반 적재: 일자별 보관 완료 후 메타데이터 업데이트
- 재작업: 백업 완료 후 임시 메타데이터 업데이트 → 새 데이터 적재 완료 후 최종 메타데이터 업데이트

#### 조회 가용성 보장

```
재작업 전: 일자별 디렉토리에서 조회
    ↓
백업 단계: latest/에서 백업된 데이터 조회 (다운타임 없음)
    ↓
적재 단계: latest/에서 백업된 데이터 계속 조회 (다운타임 없음)
    ↓
최종 전환: 메타데이터 업데이트 (1초 미만) → 일자별 디렉토리에서 새 데이터 조회
```

### 9.4 Python 애플리케이션에서의 활용

Python 애플리케이션은 `batch_profile_minio_retrieve.py`를 호출하면 자동으로 메타데이터를 확인하여 올바른 조회 경로를 사용합니다. **별도의 경로 관리 로직이 필요 없습니다.**

**예시:**
```python
from batch_profile_minio_retrieve import retrieve_cusno

# 재작업 전, 중, 후 모두 동일한 코드로 조회 가능
# 내부적으로 메타데이터를 확인하여 올바른 경로에서 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001
)

# 재작업 전: 일자별 디렉토리에서 조회
# 재작업 중: latest/에서 백업된 데이터 조회 (다운타임 없음)
# 재작업 완료 후: 일자별 디렉토리에서 새 데이터 조회
# → 사용자는 코드 변경 없이 항상 최신 데이터 조회 가능
```

### 9.5 재작업 시 주의사항

#### 클래스 래퍼 사용 시

클래스 래퍼를 사용하는 경우, 재작업 후 메타데이터가 변경되면 캐시를 갱신해야 합니다:

```python
from your_module import MinIORetrieveClient

client = MinIORetrieveClient(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin"
)

# 재작업 전: 정상 조회
data = client.retrieve_cusno("daily", 700000001)

# 재작업 중: 백업된 데이터 조회 (다운타임 없음)
data = client.retrieve_cusno("daily", 700000001)

# 재작업 완료 후: 캐시 갱신 후 새 데이터 조회
data = client.retrieve_cusno("daily", 700000001, refresh_cache=True)
```

#### 함수 import 사용 시

함수 import를 사용하는 경우, 재작업 후에도 별도의 캐시 관리가 필요 없습니다:

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 재작업 전, 중, 후 모두 동일한 코드 사용
# 내부적으로 메타데이터를 확인하므로 자동으로 올바른 경로에서 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001
)
```

## 11. API 레퍼런스

### 11.1 retrieve_cusno 함수 (단건 조회)

```python
def retrieve_cusno(
    endpoint: str,
    access_key: str,
    secret_key: str,
    data_type: str,
    cusno: Union[str, int]
) -> Optional[dict]:
    """
    MinIO에서 고객번호(CUSNO) 기준으로 단건 조회 (메타데이터 기반 조회 경로 결정)
    
    이 함수는 한 번의 호출로 하나의 고객번호에 대한 데이터만 조회합니다.
    여러 고객번호를 조회하려면 반복문을 사용하여 각각 호출하세요.
    
    Args:
        endpoint: MinIO 엔드포인트 URL
            예: "http://localhost:9000" 또는 "https://minio.example.com:9000"
        access_key: MinIO Access Key
        secret_key: MinIO Secret Key
        data_type: 데이터 타입
            - "daily": 일별 데이터 (prefix: ifc_cus_dd_smry_tot)
            - "monthly": 월별 데이터 (prefix: ifc_cus_mmby_smry_tot)
        cusno: 조회할 고객번호 (단건)
            - 문자열 또는 정수 모두 가능
            - 예: "700000001" 또는 700000001
    
    Returns:
        Optional[dict]: 조회된 데이터 (JSON 객체)
            - 조회 성공 시: 고객 데이터 딕셔너리 반환
            - 조회 실패 시: None 반환 (데이터 없음 또는 오류)
    
    Raises:
        Exception: 네트워크 오류, 인증 오류 등 발생 시 예외 발생
    
    Note:
        - 메타데이터 기반으로 조회 경로를 자동 결정합니다
        - 재작업 중에도 기존 데이터를 조회할 수 있습니다 (다운타임 최소화)
        - 목표 응답 시간: 100ms 이내
    
    Example:
        >>> # 단건 조회 예시
        >>> data = retrieve_cusno(
        ...     endpoint="http://localhost:9000",
        ...     access_key="minioadmin",
        ...     secret_key="minioadmin",
        ...     data_type="daily",
        ...     cusno=700000001
        ... )
        >>> if data:
        ...     print(f"조회 성공: {data.get('CUSNO')}")
        ... else:
        ...     print("데이터 없음")
        '조회 성공: 700000001'
        
        >>> # 여러 고객번호 조회 시 (반복문 사용)
        >>> for cusno in [700000001, 700000002, 700000003]:
        ...     data = retrieve_cusno(
        ...         endpoint="http://localhost:9000",
        ...         access_key="minioadmin",
        ...         secret_key="minioadmin",
        ...         data_type="daily",
        ...         cusno=cusno
        ...     )
        ...     if data:
        ...         print(f"{cusno}: 조회 성공")
    """
```

### 11.2 반환 데이터 형식

**단건 조회 성공 시** 반환되는 데이터 형식:

```python
{
    "CUSNO": "700000001",
    "IBNK_USYN": 1,
    "PB_ACTV_YN": 1,
    # ... 기타 필드들 (스키마에 따라 다름)
}
```

**단건 조회 실패 시**:
- `None` 반환: 데이터 없음 또는 조회 실패
- 예외 발생: 네트워크 오류, 인증 오류 등

### 11.3 사용 패턴

**단건 조회 (권장 패턴):**

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 단건 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001
)

if data:
    # 조회 성공
    print(f"고객번호: {data.get('CUSNO')}")
else:
    # 데이터 없음
    print("데이터를 찾을 수 없습니다")
```

### 11.4 에러 코드 및 메시지

| 상황 | 반환값 | 예외 | 설명 |
|------|--------|------|------|
| 데이터 없음 | `None` | 없음 | 해당 고객번호의 데이터가 MinIO에 없음 |
| 연결 실패 | `None` | `ConnectionError` | MinIO 서버에 연결할 수 없음 |
| 인증 실패 | `None` | `Exception` (403 또는 Access Denied) | Access Key 또는 Secret Key 오류 |
| 타임아웃 | `None` | `TimeoutError` | 조회 시간 초과 |
| 기타 오류 | `None` | `Exception` | 예상치 못한 오류 발생 |

---

## 12. 변경 이력

### v1.2 (2026-02-08)

- **메타데이터 기반 조회**: `_latest_date.json` 파일로 조회 경로 동적 결정
- **재작업 프로세스**: 백업기준일자 필수 지정, 다운타임 최소화 메커니즘 구현
- **하이브리드 경로 관리**: `latest/`와 `YYYYMMDD/` 디렉토리 하이브리드 관리
- **원자적 전환**: 메타데이터 업데이트로 1초 미만 조회 경로 전환
- **코드 예시 업데이트**: 메타데이터 기반 조회 경로 결정 로직 반영
- **문서 업데이트**: 재작업 및 다운타임 최소화 프로세스 상세 기술

### v1.1 (2026-02-07)

- **버킷 구조 변경**: 2개 버킷(daily/monthly) → 통일된 버킷 `shinhanobj` 사용
- **파라미터 변경**: `bucket` 파라미터 → `data_type` 파라미터로 변경
- **문서 현행화**: Python 버전, 패키지 버전 정보 업데이트
- **예시 코드 업데이트**: 최신 API에 맞게 수정

### v1.0 (초기 버전)

- 초기 문서 작성

---

**문서 버전**: 1.2  
**최종 업데이트**: 2026-02-08

---

## 부록

### A. 전체 예제 코드

다른 프로젝트에서 바로 사용할 수 있는 완전한 예제 (단건 조회):

```python
#!/usr/bin/env python3
"""
MinIO 고객 프로파일 데이터 단건 조회 예제
"""
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, '/path/to/shinhanbank-sol-batch-minio-load/src')

from batch_profile_minio_retrieve import retrieve_cusno

def main():
    # 설정
    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    
    # 조회할 고객번호
    cusno = 700000001
    
    try:
        # 단건 조회
        data = retrieve_cusno(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            data_type="daily",  # 또는 "monthly"
            cusno=cusno
        )
        
        if data:
            print(f"✅ 조회 성공 (CUSNO: {cusno})")
            print(f"   데이터: {data}")
        else:
            print(f"❌ 데이터 없음 (CUSNO: {cusno})")
            
    except Exception as e:
        print(f"⚠️  조회 실패: {e}")

if __name__ == "__main__":
    main()
```

**더 간단한 예제:**

```python
from batch_profile_minio_retrieve import retrieve_cusno

# 단건 조회
data = retrieve_cusno(
    endpoint="http://localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    data_type="daily",
    cusno=700000001
)

if data:
    print(f"조회 성공: {data}")
else:
    print("데이터 없음")
```

### B. 연락처 및 지원

- 프로젝트 관리자: [연락처 정보]
- 기술 지원: [연락처 정보]
- 이슈 리포트: [GitHub Issues 또는 기타 채널]

### C. 관련 문서

- **프로젝트 메인 문서**: [README.md](../README.md)
- **아키텍처 문서**: [Architecture.md](../Architecture.md)
- **운영자 매뉴얼**: [doc/operator-manual.md](operator-manual.md)
- **프로그램 사양서**: [doc/program-specification.md](program-specification.md)