# 필드 단위 암호화 가이드

프로파일 데이터를 MinIO에 적재·조회할 때 **필드 단위**로만 암호화/복호화하는 방식과 설정을 정리합니다.

---

## 1. 개요

- **알고리즘**: AES-256-GCM (Nonce 12바이트, 키 32바이트)
- **CUSNO**: 항상 평문 유지 (조회·인덱싱용)
- **암호화 대상**: 스키마의 `encrypted_columns`에 정의된 컬럼만 암호화. 한 레코드에 평문 필드와 암호화 필드가 함께 저장됨.
- **모듈**: `src/batch_profile_encryption.py`, `src/batch_profile_config.py`

---

## 2. 환경 변수

| 변수 | 설명 | 기본값 | 비고 |
|------|------|--------|------|
| **MINIO_ENCRYPTION** | 암호화 사용 여부 | `0` | `1`, `true`, `yes` 이면 활성화 |
| **ENCRYPTION_KEY** | 암호화 키 (Base64) | 없음 | **32바이트** 키를 Base64 인코딩한 문자열 |

### 암호화 키 생성 (32바이트 → Base64)

```bash
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

적재·조회 시 **동일한 ENCRYPTION_KEY**를 사용해야 복호화가 가능합니다.

---

## 3. 키 조회 우선순위

1. **환경 변수** `ENCRYPTION_KEY` (Base64 디코딩 후 32바이트 검증)
2. **KMS** `get_encryption_key_from_kms()` (현재 stub)
3. 둘 다 실패 시 `RuntimeError`

HSM(Inisafe Paccel) 사용 시 프로젝트 루트 **crypto.py**의 `get_key()`로 키를 가져온 뒤 Base64 인코딩하여 `ENCRYPTION_KEY`에 설정할 수 있습니다.

---

## 4. 스키마: encrypted_columns

암호화할 필드는 스키마 JSON의 **`encrypted_columns`** 배열로 지정합니다.  
반드시 `columns`에 있는 컬럼명만 넣어야 합니다.

- **일별**: `schema/columns_daily.json` → `encrypted_columns`: `[]` 또는 원하는 컬럼명
- **월별**: `schema/columns_monthly.json` → `encrypted_columns`: `["CUSNM", "BIRYR_M_DT", "HOME_ADR", "CO_ADR"]` 등

```json
{
  "columns": ["CUSNO", "CUSNM", "AGE", "HOME_ADR", ...],
  "encrypted_columns": ["CUSNM", "BIRYR_M_DT", "HOME_ADR", "CO_ADR"]
}
```

**필드 단위 암호화를 쓰려면 `encrypted_columns`에 1개 이상의 컬럼을 넣어야 합니다.**  
비어 있으면 암호화를 켜도 이 가이드의 필드 단위 방식이 적용되지 않습니다.

---

## 5. 필드 단위 암호화 방식

- **조건**: `MINIO_ENCRYPTION=1` 이고, 스키마의 `encrypted_columns`에 **컬럼이 1개 이상** 있음
- **저장 형식**: 한 레코드 한 줄(한 JSON 객체). 지정된 컬럼만 암호화된 Base64 문자열, 나머지는 평문  
  예: `{"CUSNO": "700000001", "CUSNM": "Base64암호문", "AGE": 30, "HOME_ADR": "Base64암호문", ...}`
- **복호화**: `_meta.json`의 `encrypted_columns`에 있는 키만 복호화

---

## 6. 적재 시 (MinIO Load)

- **스크립트**: `./shl/batch_profile_minio_load.sh` → `src/batch_profile_minio_load.py`
- **동작**:
  1. `MINIO_ENCRYPTION`으로 암호화 사용 여부 결정
  2. 일별/월별 스키마에서 `encrypted_columns` 로드
  3. `encrypted_columns`가 있으면 `encrypt_document(doc, encrypted_yn=1, encrypt_fields=encrypted_columns)`로 **필드 단위** 암호화
  4. **`_meta.json`**에 `encrypted_columns` 포함하여 업로드 (조회 시 복호화에 사용)

### 적재 예시

```bash
export MINIO_ENCRYPTION=1
export ENCRYPTION_KEY="(32바이트 키 Base64 문자열)"
./shl/batch_profile_minio_load.sh M IFC_CUS_MMBY_SMRY_TOT_700000001_100.utf8.dat 20260304
```

---

## 7. 조회 시 복호화 (MinIO Retrieve)

- **스크립트**: `./shl/batch_profile_minio_retrieve.sh` → `src/batch_profile_minio_retrieve.py`
- **동작**:
  1. 해당 prefix/일자의 **`_meta.json`**에서 `encrypted_columns` 로드
  2. CUSNO로 1건 조회 후 `decrypt_document(doc, encrypted_columns=encrypted_columns)` 호출
  3. `encrypted_columns`에 있는 키만 복호화하여 평문 문서로 만든 뒤 JSON 출력

조회 시에도 **동일한 ENCRYPTION_KEY**가 설정되어 있어야 합니다.

### 조회 예시

```bash
export ENCRYPTION_KEY="(적재 시와 동일한 Base64 키)"
./shl/batch_profile_minio_retrieve.sh M 700000001
```

---

## 8. API 요약 (필드 단위 기준)

| 함수 | 설명 |
|------|------|
| **encrypt_document(doc, encrypted_yn=1, encrypt_fields=...)** | `encrypt_fields`에 지정된 필드만 암호화, 나머지 평문 유지. 한 레코드 한 줄(평문+암호화 혼합) |
| **decrypt_document(encrypted_doc, encrypted_columns=...)** | `encrypted_columns`에 있는 키만 복호화 |
| **encrypt_field_value(value)** | 단일 값 AES-256-GCM 암호화 → Base64 문자열 |
| **decrypt_field_value(encrypted_value)** | Base64 암호문 → 평문 문자열 |

---

## 9. _meta.json

각 일자(또는 latest) 디렉터리의 **`_meta.json`**에 `encrypted_columns`가 들어갑니다.

- **적재 시**: `total`, `total_size`, `load_date`, `date_str`, **`encrypted_columns`** 포함
- **조회 시**: 같은 경로의 `_meta.json`에서 `encrypted_columns`를 읽어 `decrypt_document(..., encrypted_columns=...)`에 전달

어떤 컬럼이 암호화되었는지는 항상 `_meta.json`의 `encrypted_columns`로 판단합니다.

---

## 10. 의존성

- **cryptography**: `pip install cryptography` (AES-GCM)
- 미설치 시 암호화/복호화가 동작하지 않으며 경고가 출력됩니다.

---

## 11. 참고 파일

| 파일 | 역할 |
|------|------|
| `src/batch_profile_encryption.py` | 암호화/복호화, 키 조회 |
| `src/batch_profile_config.py` | `MINIO_ENCRYPTION`, `ENCRYPTION_KEY` |
| `src/batch_profile_schema.py` | `get_encrypted_columns_daily()`, `get_encrypted_columns_monthly()` |
| `schema/columns_daily.json`, `schema/columns_monthly.json` | `encrypted_columns` 정의 |
| `src/batch_profile_minio_load.py` | 적재 시 필드 단위 암호화, _meta.json 작성 |
| `src/batch_profile_minio_retrieve.py` | 조회 시 _meta.json 기반 복호화 |
| `crypto.py` | HSM 키 조회 `get_key()` (선택) |

---

## 12. 다른 프로젝트에서 복호화 모듈 사용 예제

다른 프로젝트에서 본 프로젝트의 복호화 모듈을 사용할 때는 아래를 참고합니다.

- **필수**: `ENCRYPTION_KEY` 환경 변수 설정 (적재 시와 동일한 32바이트 키 Base64)
- **필수**: `batch_profile_encryption` 모듈이 import 가능한 경로에 있거나, 해당 모듈의 `decrypt_document`, `decrypt_field_value` 로직을 복사해 사용

### 12.1 최소 예제 (문서 1건 복호화)

```python
import os
import json

# 1) batch_profile_encryption이 PYTHONPATH에 있다고 가정 (또는 sys.path에 src 추가)
# 다른 프로젝트에서 사용 시: sys.path.append("/path/to/shinhanbank-sol-batch-minio-load/src")
import sys
sys.path.insert(0, "/path/to/shinhanbank-sol-batch-minio-load/src")

from batch_profile_encryption import decrypt_document

# 2) 복호화할 문서 (필드 단위 암호화된 1건, 예: MinIO/API에서 조회한 JSON)
encrypted_doc = {
    "CUSNO": "700000001",
    "CUSNM": "plG/qOgz8gNvjOGvOZGUf8c0PGluMKsi...",  # 암호문
    "AGE": "896",
    "HOME_ADR": "Base64암호문...",
    "CO_ADR": "Base64암호문...",
}

# 3) _meta.json에서 가져온 암호화 대상 컬럼 목록 (조회 경로와 동일한 _meta.json 사용)
encrypted_columns = ["CUSNM", "BIRYR_M_DT", "HOME_ADR", "CO_ADR"]

# 4) 환경 변수 ENCRYPTION_KEY 설정 필수 (적재 시와 동일한 키)
# os.environ["ENCRYPTION_KEY"] = "..."

decrypted_doc = decrypt_document(encrypted_doc, encrypted_columns=encrypted_columns)
print(json.dumps(decrypted_doc, indent=2, ensure_ascii=False))
```

### 12.2 _meta.json에서 encrypted_columns 로드 후 복호화

```python
import os
import json
import sys

sys.path.insert(0, "/path/to/shinhanbank-sol-batch-minio-load/src")
from batch_profile_encryption import decrypt_document

def load_meta(meta_path: str) -> list:
    """로컬 파일 또는 HTTP 등에서 _meta.json 로드."""
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return meta.get("encrypted_columns") or []

def decrypt_record(encrypted_doc: dict, encrypted_columns: list) -> dict:
    return decrypt_document(encrypted_doc, encrypted_columns=encrypted_columns)

# 사용 예: MinIO 등에서 1건 조회한 뒤 복호화
# encrypted_columns = load_meta("/path/to/_meta.json")  # 또는 MinIO get_object 후 json.loads
# decrypted = decrypt_record(encrypted_doc, encrypted_columns)
```

### 12.3 실행 가능한 예제 파일

프로젝트 내 실행 가능 예제는 **`examples/decrypt_from_other_project.py`** 를 참고합니다.  
(다른 프로젝트에서 사용할 때는 경로만 본인 환경에 맞게 수정하면 됩니다.)