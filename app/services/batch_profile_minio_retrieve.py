#!/usr/bin/env python3
"""
MinIO 단건 조회: CUSNO로 1건 문서 조회 (목표 100ms 이내).
- 최신 일자 메타데이터(_latest_date.json)에서 최신 일자 및 조회 경로 확인
- use_latest=true인 경우: latest/ 디렉토리에서 조회
- use_latest=false인 경우: {최신일자}/ 디렉토리에서 조회
- Fast Load(샤드 인덱스): index_{prefix}.json(소량) → bulk.jsonl Range GET
- 구 형식: index.json(전체) → bulk.jsonl Range GET
- 1건=1객체: {CUSNO}.json GET

사용법:
  batch_profile_minio_retrieve.py <endpoint> <access_key> <secret_key> <data_type> <CUSNO>
  data_type: daily 또는 monthly (prefix 구분용, 실제 버킷은 shinhanobj 사용)
  예: python batch_profile_minio_retrieve.py http://127.0.0.1:9000 minioadmin minioadmin daily 700000001
      python batch_profile_minio_retrieve.py http://127.0.0.1:9000 minioadmin minioadmin monthly 700000001
"""

import logging
import os
import sys
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

from minio.error import S3Error as _S3Error

try:
    from app.services.batch_profile_utils import (
        PREFIX_DAILY,
        PREFIX_MONTHLY,
        apply_column_mapping,
        create_minio_client_simple,
        decrypt_document,
        index_prefix,
        json_dumps,
        json_loads,
    )
except ImportError:
    # 하위 호환성: batch_profile_utils가 없는 경우 기본값 사용
    PREFIX_DAILY = "ifc_cus_dd_smry_tot"
    PREFIX_MONTHLY = "ifc_cus_mmby_smry_tot"

    def index_prefix(cusno):
        """CUSNO → index 샤드 접두사 (끝 3자리, 0 패딩). 1000샤드(index_000~999)."""
        s = str(cusno).strip()
        return (s.zfill(3))[-3:]

    def json_loads(data):
        import json

        return json.loads(data.decode("utf-8"))

    def json_dumps(doc):
        import json

        return json.dumps(doc, ensure_ascii=False).encode("utf-8")

    from minio import Minio

    def create_minio_client_simple(endpoint: str, access_key: str, secret_key: str):
        secure = endpoint.strip().lower().startswith("https://")
        host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        return Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)

    def decrypt_document(doc: dict, encrypted_columns: list) -> dict:  # noqa: F811
        """batch_profile_utils 없을 때 폴백: 복호화 없이 원문 반환."""
        return doc


def _match_cusno(doc: dict, cusno: str, encrypted_columns: list[str]) -> bool:
    """doc 의 CUSNO 가 요청 cusno 와 일치하는지 확인.

    CUSNO 가 encrypted_columns 에 포함된 경우 복호화 후 비교합니다.

    Args:
        doc: bulk.jsonl 에서 읽은 원본 문서
        cusno: 조회할 고객번호 (평문)
        encrypted_columns: _meta.json 에서 읽은 암호화 컬럼 목록

    Returns:
        일치 여부
    """
    raw_cusno = doc.get("CUSNO")
    if raw_cusno is None:
        return False

    # CUSNO 가 암호화 대상인 경우 복호화 후 비교
    if "CUSNO" in encrypted_columns:
        try:
            from app.services.batch_profile_utils import decrypt_field_value

            raw_cusno = decrypt_field_value(str(raw_cusno))
        except (ValueError, RuntimeError, ImportError):
            return False  # 복호화 실패 시 매칭 불가

    return str(raw_cusno) == str(cusno)


def retrieve_cusno(
    *,
    endpoint: str,
    access_key: str,
    secret_key: str,
    data_type: str,
    cusno: str | int,
    bucket: str | None = None,
) -> dict[str, Any] | None:
    """MinIO에서 CUSNO로 단건 조회.

    Repository에서 직접 호출할 수 있도록 main()과 분리된 순수 함수 버전.
    - 메타데이터(_latest_date.json)로 조회 경로 결정
    - 샤드 인덱스(index_{prefix}.json) → index.json → 단일 파일({cusno}.json) 순으로 조회
    - 실패 시 None 반환 (예외나 sys.exit 사용하지 않음)
    """

    # 버킷 이름은 shinhanobj로 통일 (환경변수로 오버라이드 가능)
    if bucket is None:
        bucket = os.environ.get("MINIO_BUCKET", "shinhanobj")

    data_type_normalized = data_type.strip().lower()
    if data_type_normalized not in {"daily", "monthly"}:
        data_type_normalized = "daily"

    object_prefix = PREFIX_MONTHLY if data_type_normalized == "monthly" else PREFIX_DAILY

    # MinIO 클라이언트 생성 (orjson 유무와 무관하게 동작해야 하므로
    # 여기서는 orjson import를 강제하지 않는다.)
    try:
        client = create_minio_client_simple(endpoint, access_key, secret_key)
    except (OSError, ValueError, ImportError):
        return None

    cusno_str = str(cusno).strip()
    if not cusno_str:
        return None

    # 1) 최신 일자 메타데이터(_latest_date.json)에서 조회 경로 결정
    latest_date_meta_key = f"{object_prefix}/_latest_date.json"
    latest_date_str: str | None = None
    query_path: str | None = None
    use_latest = False

    try:
        resp = client.get_object(bucket, latest_date_meta_key)
        latest_date_meta = json_loads(resp.read())
        resp.close()
        resp.release_conn()
        latest_date_str = latest_date_meta.get("latest_date") or latest_date_meta.get("load_date", "").replace("-", "")
        use_latest = bool(latest_date_meta.get("use_latest", False))

        if not latest_date_str or len(latest_date_str) != 8 or not latest_date_str.isdigit():
            latest_date_str = None
        else:
            query_path = f"{object_prefix}/latest/" if use_latest else f"{object_prefix}/{latest_date_str}/"
    except (_S3Error, OSError, ValueError):
        # 메타데이터가 없으면 일자별 디렉토리 목록에서 최신 일자 찾기
        try:
            objects = client.list_objects(bucket, prefix=f"{object_prefix}/", recursive=False)
            date_dirs: list[str] = []
            for obj in objects:
                obj_name = obj.object_name
                if obj_name.startswith(f"{object_prefix}/"):
                    remaining = obj_name[len(f"{object_prefix}/") :]
                    if "/" in remaining:
                        date_dir = remaining.split("/")[0]
                        if date_dir and len(date_dir) == 8 and date_dir.isdigit():
                            date_dirs.append(date_dir)
            if date_dirs:
                latest_date_str = sorted(date_dirs, reverse=True)[0]
                use_latest = False
                query_path = f"{object_prefix}/{latest_date_str}/"
        except (_S3Error, OSError):
            return None

    if not latest_date_str:
        # 메타데이터와 일자별 디렉토리에서 최신 일자를 찾지 못한 경우,
        # latest/ 디렉토리가 있는지 직접 확인 (메타데이터 미구성 환경 지원)
        try:
            test_prefix = index_prefix(cusno_str)
            test_index_key = f"{object_prefix}/latest/index_{test_prefix}.json"
            client.stat_object(bucket, test_index_key)
            latest_date_str = "latest"
            use_latest = True
            query_path = f"{object_prefix}/latest/"
        except (_S3Error, OSError):
            return None

    if not query_path:
        query_path = f"{object_prefix}/{latest_date_str}/"

    # 2) 조회 경로에 따라 키 구성
    #    기본적으로는 메타데이터(use_latest 플래그 포함)를 따르되,
    #    실제 데이터가 latest/ 에만 존재하는 환경을 위해 fallback 키도 준비한다.
    if use_latest:
        bulk_key = f"{object_prefix}/latest/bulk.jsonl"
        single_key = f"{object_prefix}/latest/{cusno_str}.json"
        prefix = index_prefix(cusno_str)
        index_shard_key = f"{object_prefix}/latest/index_{prefix}.json"
        index_full_key = f"{object_prefix}/latest/index.json"

        # use_latest=True 인 경우에는 별도 fallback 이 필요 없다.
        fallback_bulk_key = None
        fallback_single_key = None
        fallback_index_shard_key = None
        fallback_index_full_key = None
    else:
        date_prefix = f"{object_prefix}/{latest_date_str}"
        bulk_key = f"{date_prefix}/bulk.jsonl"
        single_key = f"{date_prefix}/{cusno_str}.json"
        prefix = index_prefix(cusno_str)
        index_shard_key = f"{date_prefix}/index_{prefix}.json"
        index_full_key = f"{date_prefix}/index.json"

        # 메타데이터는 use_latest=False 이지만 실제 데이터가 latest/ 에만
        # 적재된 경우를 위해 latest/ 경로를 fallback 으로 준비한다.
        fallback_bulk_key = f"{object_prefix}/latest/bulk.jsonl"
        fallback_single_key = f"{object_prefix}/latest/{cusno_str}.json"
        fallback_prefix = index_prefix(cusno_str)
        fallback_index_shard_key = f"{object_prefix}/latest/index_{fallback_prefix}.json"
        fallback_index_full_key = f"{object_prefix}/latest/index.json"

    def fetch_via_index(index_key: str, bulk_obj_key: str) -> dict | None:
        """인덱스 파일을 통해 데이터 조회 (Fast Load 모드)."""

        try:
            resp = client.get_object(bucket, index_key)
            index = json_loads(resp.read())
            resp.close()
            resp.release_conn()

            if cusno_str not in index:
                return None

            start_off, length = index[cusno_str]

            try:
                # minio 7.x 방식 (offset, length 파라미터)
                resp = client.get_object(bucket, bulk_obj_key, offset=start_off, length=length)
                line = resp.read()
                resp.close()
                resp.release_conn()
                return json_loads(line)
            except (TypeError, AttributeError):
                # minio 6.x 방식: 전체 객체를 읽고 필요한 부분만 추출
                resp = client.get_object(bucket, bulk_obj_key)
                data = resp.read()
                resp.close()
                resp.release_conn()
                line = data[start_off : start_off + length]
                return json_loads(line)
        except (_S3Error, OSError, ValueError, KeyError):
            return None

    doc: dict[str, Any] | None = None

    # 3) 샤드 인덱스 → 전체 인덱스 → 단건 JSON 순으로 조회
    try:
        doc = fetch_via_index(index_shard_key, bulk_key)
        if doc is None:
            doc = fetch_via_index(index_full_key, bulk_key)
    except (_S3Error, OSError, ValueError):
        doc = None

    if doc is None:
        try:
            resp = client.get_object(bucket, single_key)
            doc = json_loads(resp.read())
            resp.close()
            resp.release_conn()
        except (_S3Error, OSError, ValueError):
            doc = None

    # 메타데이터는 use_latest=False 인데 실제 데이터는 latest/ 에만 존재하는 경우
    # (예: 최신 적재에서 latest/ 만 채워진 상태)를 위해 latest/ 경로를 fallback 으로 재시도한다.
    used_fallback = False
    if doc is None and not use_latest and fallback_bulk_key is not None:
        try:
            doc = fetch_via_index(fallback_index_shard_key, fallback_bulk_key)
            if doc is None:
                doc = fetch_via_index(fallback_index_full_key, fallback_bulk_key)
        except (_S3Error, OSError, ValueError):
            doc = None

        if doc is None:
            try:
                resp = client.get_object(bucket, fallback_single_key)
                doc = json_loads(resp.read())
                resp.close()
                resp.release_conn()
            except (_S3Error, OSError, ValueError):
                doc = None

        if doc is not None:
            used_fallback = True

    if doc is None:
        return None

    # 4) _meta.json 에서 encrypted_columns 읽어 복호화
    #    - 실제 데이터가 latest/ 에서 조회된 경우(used_fallback) latest/_meta.json 우선 시도
    #    - IniSafe Paccel SO 미설치 시 암호화 원문 그대로 반환
    effective_query_path = f"{object_prefix}/latest/" if used_fallback else query_path
    try:
        meta_key = f"{effective_query_path.rstrip('/')}/_meta.json"  # rstrip으로 슬래시 중복 방지
        resp = client.get_object(bucket, meta_key)
        meta = json_loads(resp.read())
        resp.close()
        resp.release_conn()
        encrypted_columns: list[str] = meta.get("encrypted_columns") or []
        column_mapping: dict[str, str] = meta.get("column_info") or {}
        if column_mapping:
            logger.warning(
                "[배치프로파일] 한글 매핑 적용 가능: key=%s, 매핑 컬럼 수=%d, 샘플=%s",
                meta_key,
                len(column_mapping),
                dict(list(column_mapping.items())[:3]),
            )
        else:
            logger.warning(
                "[배치프로파일] column_info 없음 — 한글 매핑 미적용: key=%s",
                meta_key,
            )
    except (_S3Error, OSError, ValueError) as meta_exc:
        logger.warning(
            "[배치프로파일] _meta.json 조회 실패 — 한글 매핑 미적용: key=%s, reason=%s",
            meta_key,
            meta_exc,
        )
        encrypted_columns = []
        column_mapping = {}

    # 5) _match_cusno 로 실제 CUSNO 일치 여부 검증
    #    - 인덱스/단건 조회 결과가 올바른 문서인지 확인 (인덱스 stale 방지)
    #    - CUSNO 가 encrypted_columns 에 포함된 경우 복호화 후 비교
    if not _match_cusno(doc, cusno_str, encrypted_columns):
        # 인덱스나 단건 조회 결과가 불일치 → bulk.jsonl 전체 순차 스캔으로 fallback
        actual_bulk_key = f"{object_prefix}/latest/bulk.jsonl" if used_fallback else bulk_key
        doc = None
        try:
            resp = client.get_object(bucket, actual_bulk_key)
            raw_data = resp.read()
            resp.close()
            resp.release_conn()
            for line in raw_data.decode("utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    candidate = json_loads(line.encode("utf-8"))
                    if _match_cusno(candidate, cusno_str, encrypted_columns):
                        doc = candidate
                        break
                except (ValueError, UnicodeDecodeError):
                    continue
        except (_S3Error, OSError):
            pass

    if doc is None:
        return None

    if encrypted_columns:
        try:
            doc = decrypt_document(doc, encrypted_columns)
        except (ValueError, RuntimeError):
            pass  # IniSafe Paccel SO 미설치 등 → 암호화된 원문 반환

    # _meta.json 의 column_mapping 기준으로 한글 컬럼 키 추가 (영문 키 유지)
    if column_mapping:
        doc = apply_column_mapping(doc, column_mapping)

    return doc


def main() -> None:
    """
    메인 함수: MinIO 단건 조회 (CUSNO 기준)

    Fast Load 모드의 경우 샤드 인덱스를 통해 빠르게 조회합니다 (목표: 100ms 이내).
    """
    if len(sys.argv) < 6:
        print(
            "Usage: batch_profile_minio_retrieve.py <endpoint> <access_key> <secret_key> <data_type> <CUSNO>",
            file=sys.stderr,
        )
        print("  data_type: daily 또는 monthly (prefix 구분용, 실제 버킷은 shinhanobj 사용)", file=sys.stderr)
        print("  CUSNO: 고객번호 (예: 700000001)", file=sys.stderr)
        sys.exit(1)
    endpoint = sys.argv[1]
    access_key = sys.argv[2]
    secret_key = sys.argv[3]
    data_type_arg = sys.argv[4].strip()
    cusno = sys.argv[5].strip()

    # data_type_arg를 그대로 넘기되, retrieve_cusno 내부에서 정규화
    data_type = data_type_arg

    result = retrieve_cusno(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        data_type=data_type,
        cusno=cusno,
    )

    if result is None:
        print(f"해당 CUSNO 없음 또는 데이터 미적재: {cusno}", file=sys.stderr, flush=True)
        sys.exit(1)

    # CLI 모드는 조회 결과를 pretty JSON으로 출력
    try:
        import orjson

        print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode(), flush=True)
    except (ImportError, TypeError, ValueError):
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
