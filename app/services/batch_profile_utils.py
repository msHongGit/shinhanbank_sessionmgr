#!/usr/bin/env python3
"""
공통 유틸리티 모듈

MinIO 배치 프로파일 단건 조회·복호화·컬럼 매핑에 필요한 유틸리티를 제공합니다.
"""

import base64
import logging

logger = logging.getLogger(__name__)

# orjson import
try:
    import orjson
except ImportError:
    orjson = None


# ============================================================================
# 상수 정의
# ============================================================================

# 일별/월별 prefix
PREFIX_DAILY = "ifc_cus_dd_smry_tot"
PREFIX_MONTHLY = "ifc_cus_mmby_smry_tot"

# Content Type
CONTENT_TYPE = "application/json"

# 복호화 실패 시 필드 제거 여부 (암호문을 Redis에 저장하지 않기 위해 True 권장)
REMOVE_FIELD_ON_DECRYPT_FAILURE: bool = True

# AES-GCM 파라미터
AES_NONCE_SIZE: int = 12   # embedded nonce 크기 (바이트)
AES_GCM_TAG_SIZE: int = 16  # GCM 인증 태그 크기 (바이트)

# cryptography 라이브러리 설치 여부
HAS_CRYPTOGRAPHY: bool = False  # try 블록 밖에서 선언
try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True  # 타입 어노테이션 없이 값만 재할당
except ImportError:
    InvalidTag = Exception  # type: ignore[assignment,misc]  # cryptography 미설치 시 fallback
    pass

# ============================================================================
# JSON 직렬화 유틸리티
# ============================================================================


def json_dumps(doc: dict, compact: bool = True) -> bytes:
    """
    orjson으로 JSON 직렬화 (표준 json 대비 속도 향상)

    Args:
        doc: 직렬화할 딕셔너리
        compact: True면 공백 없이 최소 크기로 직렬화 (기본: True)

    Returns:
        JSON 바이트 문자열

    Raises:
        ImportError: orjson이 설치되지 않은 경우
    """
    if orjson is None:
        import json

        if compact:
            return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return json.dumps(doc, ensure_ascii=False).encode("utf-8")

    # orjson은 기본적으로 compact 형식 (공백 없음)
    # 옵션: OPT_SORT_KEYS 제거 (정렬 불필요, 시간 절약)
    return orjson.dumps(doc)


def json_loads(data: bytes) -> dict:
    """
    orjson으로 JSON 역직렬화

    Args:
        data: 역직렬화할 바이트 데이터

    Returns:
        파싱된 딕셔너리

    Raises:
        ImportError: orjson이 설치되지 않은 경우
    """
    if orjson is None:
        import json

        return json.loads(data.decode("utf-8"))
    return orjson.loads(data)


# ============================================================================
# CUSNO 유틸리티
# ============================================================================


def index_prefix(cusno: str) -> str:
    """
    CUSNO → index 샤드 접두사 (끝 3자리, 0 패딩)

    1000샤드(index_000~999)로 분산하여 단건 조회 시 해당 샤드만 GET합니다.

    Args:
        cusno: 고객번호 문자열

    Returns:
        3자리 접두사 문자열 (000~999)

    예시:
        >>> index_prefix("700000001")
        '001'
        >>> index_prefix("123")
        '123'
        >>> index_prefix("5")
        '005'
    """
    s = str(cusno).strip()
    return (s.zfill(3))[-3:]


# ============================================================================
# MinIO 클라이언트 유틸리티
# ============================================================================


def parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """
    MinIO 엔드포인트를 파싱하여 호스트명과 secure 여부 반환

    Args:
        endpoint: MinIO 엔드포인트 URL

    Returns:
        (host, secure) 튜플
    """
    endpoint = endpoint.strip()
    secure = endpoint.lower().startswith("https://")
    host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    return host, secure


def create_minio_client_simple(endpoint: str, access_key: str, secret_key: str):
    """
    간단한 MinIO 클라이언트 생성 (기본 설정)

    Args:
        endpoint: MinIO 엔드포인트 URL
        access_key: MinIO Access Key
        secret_key: MinIO Secret Key

    Returns:
        MinIO 클라이언트 객체

    Raises:
        Exception: 클라이언트 생성 실패 시
    """
    from minio import Minio

    host, secure = parse_endpoint(endpoint)
    return Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)


# ============================================================================
# 필드 단위 복호화 — AES-256-GCM
# 저장 형식: Base64(nonce[12] + ciphertext + tag[16])  — embedded nonce
# 키 출처: app.utils.inisafe.IniSafePaccel().get_symm_key() (싱글턴)
# ============================================================================

_INISAFE_KEY = None  # ISPSymmKey | None — 런타임 타입, import 없이 선언


def _get_cached_key() -> bytes:
    """IniSafe Paccel 대칭키 캐시 조회. (싱글턴)

    Returns:
        AES-256 원시 키 (32바이트)

    Raises:
        RuntimeError: IniSafe SO 미설치 또는 HSM 연결 실패
    """
    global _INISAFE_KEY  # noqa: PLW0603
    if _INISAFE_KEY is None:
        from app.utils.inisafe import IniSafePaccel
        inisafe = IniSafePaccel()
        _INISAFE_KEY = inisafe.get_symm_key()
    return bytes.fromhex(_INISAFE_KEY.symmKey)[:32]


def decrypt_field_value(encrypted_value: str | None) -> str | None:
    """암호화된 필드 값을 AES-256-GCM 으로 복호화합니다.

    암호문 형식: Base64(nonce[12] + ciphertext + tag[16])  — embedded nonce
    nonce 는 암호문 앞 12바이트에서 추출합니다.

    cryptography 라이브러리가 없으면 원문을 그대로 반환합니다.

    Args:
        encrypted_value: 복호화할 값 (Base64 인코딩된 문자열) 또는 None

    Returns:
        복호화된 값 (문자열) 또는 None
    """
    if not HAS_CRYPTOGRAPHY:
        return encrypted_value

    if encrypted_value is None:
        return None

    if not isinstance(encrypted_value, str):
        return str(encrypted_value)

    try:
        encrypted_data = base64.b64decode(encrypted_value.encode("utf-8"))

        # 최소 길이 확인 (nonce 12 + tag 16)
        if len(encrypted_data) < AES_NONCE_SIZE + AES_GCM_TAG_SIZE:
            # 암호화되지 않은 데이터로 판단 → 원문 반환
            return encrypted_value

        nonce = encrypted_data[:AES_NONCE_SIZE]
        ciphertext = encrypted_data[AES_NONCE_SIZE:]

        key = _get_cached_key()
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    except (ValueError, base64.binascii.Error):
        # Base64 디코딩 실패 또는 암호화되지 않은 데이터 → 원문 반환
        return encrypted_value
    except (InvalidTag, UnicodeDecodeError) as exc:
        # AES-GCM 인증 태그 불일치 또는 UTF-8 디코딩 실패 → 원문 반환
        logger.warning("[배치프로파일] 복호화 실패 — 원문 반환: reason=%s", exc)
        return encrypted_value


def _decrypt_fields(target: dict, encrypted_columns: list[str]) -> dict:
    """dict 내 encrypted_columns 에 해당하는 필드만 복호화.

    복호화 성공: 평문으로 교체
    복호화 실패:
        REMOVE_FIELD_ON_DECRYPT_FAILURE=True  → 해당 필드 제거 (암호문 저장 방지)
        REMOVE_FIELD_ON_DECRYPT_FAILURE=False → 원문 유지 (하위 호환)
    """
    result = dict(target)
    failed_columns: list[str] = []

    for col in encrypted_columns:
        val = result.get(col)
        if isinstance(val, str) and val:
            try:
                result[col] = decrypt_field_value(val)
            except (ValueError, RuntimeError) as exc:
                failed_columns.append(col)
                if REMOVE_FIELD_ON_DECRYPT_FAILURE:
                    result.pop(col, None)  # 암호문 필드 제거
                    logger.warning(
                        "[배치프로파일] 복호화 실패 — 필드 제거: col=%s, reason=%s",
                        col,
                        exc,
                    )
                else:
                    logger.warning(
                        "[배치프로파일] 복호화 실패 — 원문 유지: col=%s, reason=%s",
                        col,
                        exc,
                    )

    if failed_columns:
        logger.error(
            "[배치프로파일] 복호화 실패 컬럼 목록: %s (제거여부=%s)",
            failed_columns,
            REMOVE_FIELD_ON_DECRYPT_FAILURE,
        )

    return result


def decrypt_document(doc: dict, encrypted_columns: list[str]) -> dict:
    """_meta.json 의 encrypted_columns 기준으로 문서 내 암호화 필드 복호화.

    flat / 중첩("data" 키) / 혼합 구조 모두 처리.
    doc 내 encrypted_yn == 0 이면 복호화 없이 원문 반환.

    - flat 구조 (monthly):
        {"CUSNO": "700000001", "CUSNM": "<암호문>", ...}
        → 최상위 키 직접 복호화

    - 중첩 구조 (daily):
        {"CUSNO": "700000001", "encrypted_yn": 1, "data": {"CUSNM": "<암호문>", ...}}
        → "data" 내부 키 복호화

    - encrypted_yn == 0: 평문 데이터 → 복호화 없이 원문 반환

    encrypted_columns 는 _meta.json 에서 읽은 가변 목록이며,
    목록에 없는 컬럼은 암호화 여부와 관계없이 복호화하지 않습니다.

    Args:
        doc: 조회된 원본 문서 dict
        encrypted_columns: 복호화 대상 컬럼 이름 목록 (_meta.json 기준, 가변)

    Returns:
        복호화 적용된 새 dict (원본 불변)
    """
    if not encrypted_columns:
        return doc

    # encrypted_yn == 0 이면 평문 데이터 → 복호화 불필요
    encrypted_yn = doc.get("encrypted_yn")
    if encrypted_yn is not None and int(encrypted_yn) == 0:
        return doc

    result = dict(doc)

    # 중첩 구조 처리 — "data" 키 내부 복호화 (daily 등)
    if "data" in result and isinstance(result["data"], dict):
        result["data"] = _decrypt_fields(result["data"], encrypted_columns)

    # flat 구조 처리 — 최상위 키 복호화 (monthly 등)
    # 중첩 구조여도 최상위에 암호화 컬럼이 있을 수 있으므로 항상 실행
    result = _decrypt_fields(result, encrypted_columns)

    return result


def apply_column_mapping(doc: dict, column_mapping: dict[str, str]) -> dict:
    """영문 컬럼 키를 {"ko": 한글명, "value": 값} 구조로 변환하여 반환.

    column_mapping 에 있는 키는 {"ko": 한글명, "value": 값} 형태로 변환합니다.
    column_mapping 에 없는 키는 원래 형식 그대로 유지합니다.
    daily(중첩 "data"), monthly(flat) 구조 모두 지원합니다.

    변환 예:
        {"CUSNO": "503009840"} → {"CUSNO": {"ko": "고객번호", "value": "503009840"}}

    _meta.json 형식:
        {
            "column_info": {"CUSNO": "고객번호", "CUSNM": "고객명", ...}
        }

    Args:
        doc: 복호화된 문서 dict
        column_mapping: 영문 → 한글 컬럼명 매핑 (_meta.json 의 column_info 에서 읽은 값, 비어있으면 원본 반환)

    Returns:
        영문키: {"ko": 한글명, "value": 값} 구조로 변환된 새 dict (원본 불변)
    """
    if not column_mapping:
        return doc

    def _remap(target: dict) -> dict:
        result: dict = {}
        for key, val in target.items():
            ko_key = column_mapping.get(key)
            if ko_key and not isinstance(val, dict):
                result[key] = {"ko": ko_key, "value": val}
            else:
                result[key] = val
        return result

    # "data" 키 분리
    data_val = doc.get("data")
    top_level = {k: v for k, v in doc.items() if k != "data"}

    # 최상위 키 변환
    result = _remap(top_level)

    # 중첩 구조(daily): "data" 내부 변환
    if isinstance(data_val, dict):
        result["data"] = _remap(data_val)

    return result
