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
import os
import sys
import time
from typing import Optional

try:
    from batch_profile_utils import (
        PREFIX_DAILY, PREFIX_MONTHLY, index_prefix, json_loads, json_dumps,
        get_s3_error_class, parse_endpoint, create_minio_client_simple
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
        return json.loads(data.decode('utf-8'))
    
    def json_dumps(doc):
        import json
        return json.dumps(doc, ensure_ascii=False).encode('utf-8')
    
    def get_s3_error_class():
        try:
            from minio.error import S3Error
            return S3Error
        except ImportError:
            try:
                from minio.commonconfig import S3Error
                return S3Error
            except ImportError:
                try:
                    from minio.error import ResponseError as S3Error
                    return S3Error
                except ImportError:
                    class S3Error(Exception):
                        def __init__(self, message, code=None, *args, **kwargs):
                            super().__init__(message, *args, **kwargs)
                            self.code = code
                    return S3Error
    
    def parse_endpoint(endpoint: str):
        secure = endpoint.strip().lower().startswith("https://")
        host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        return host, secure
    
    def create_minio_client_simple(endpoint: str, access_key: str, secret_key: str):
        from minio import Minio
        host, secure = parse_endpoint(endpoint)
        return Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)


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
    data_type_arg = sys.argv[4].strip()  # data_type 파라미터 (하위 호환성을 위해 bucket으로도 받을 수 있음)
    cusno = sys.argv[5].strip()
    
    # 버킷 이름은 shinhanobj로 통일
    bucket = os.environ.get("MINIO_BUCKET", "shinhanobj")
    
    # data_type 추론 (하위 호환성: daily/monthly 또는 shinhanobj 모두 허용)
    if data_type_arg.lower() == "monthly":
        data_type = "monthly"
    elif data_type_arg.lower() == "daily":
        data_type = "daily"
    elif data_type_arg.lower() == "shinhanobj":
        # shinhanobj를 받은 경우 환경 변수에서 data_type 확인
        data_type = os.environ.get("MINIO_DATA_TYPE", "daily").strip().lower()
        if data_type not in ("daily", "monthly"):
            data_type = "daily"
    else:
        # 환경변수 또는 기본값 사용
        data_type = os.environ.get("MINIO_DATA_TYPE", "daily").strip().lower()
        if data_type not in ("daily", "monthly"):
            data_type = "daily"
    
    object_prefix = PREFIX_MONTHLY if data_type == "monthly" else PREFIX_DAILY

    try:
        import orjson
        from minio import Minio
    except ImportError as e:
        print(f"오류: orjson, minio 필요. pip install orjson minio — {e}", file=sys.stderr)
        sys.exit(1)

    # minio 6.x와 7.x 호환성을 위한 S3Error import
    S3Error = get_s3_error_class()
    
    # 엔드포인트 파싱 및 클라이언트 생성
    client = create_minio_client_simple(endpoint, access_key, secret_key)

    # 최신 일자 메타데이터에서 최신 일자 및 조회 경로 확인
    latest_date_meta_key = f"{object_prefix}/_latest_date.json"
    latest_date_str = None
    use_latest = False
    date_source = None  # 일자 확인 방법 추적
    query_path = None  # 실제 조회 경로
    
    try:
        resp = client.get_object(bucket, latest_date_meta_key)
        latest_date_meta = json_loads(resp.read())
        resp.close()
        resp.release_conn()
        latest_date_str = latest_date_meta.get("latest_date") or latest_date_meta.get("load_date", "").replace("-", "")
        use_latest = latest_date_meta.get("use_latest", False)
        
        if not latest_date_str or len(latest_date_str) != 8:
            latest_date_str = None
            print(f"경고: 최신 일자 메타데이터 형식이 올바르지 않습니다: {latest_date_meta}", file=sys.stderr, flush=True)
        else:
            date_source = "메타데이터(_latest_date.json)"
            if use_latest:
                query_path = f"{object_prefix}/latest/"
            else:
                query_path = f"{object_prefix}/{latest_date_str}/"
    except Exception as e:
        # 메타데이터가 없거나 읽기 실패 시 일자별 디렉토리 목록에서 최신 일자 찾기
        print(f"경고: 최신 일자 메타데이터를 읽을 수 없습니다: {e}", file=sys.stderr, flush=True)
        try:
            # 일자별 디렉토리 목록에서 최신 일자 찾기
            objects = client.list_objects(bucket, prefix=f"{object_prefix}/", recursive=False)
            date_dirs = []
            for obj in objects:
                obj_name = obj.object_name
                if obj_name.startswith(f"{object_prefix}/"):
                    remaining = obj_name[len(f"{object_prefix}/"):]
                    if '/' in remaining:
                        date_dir = remaining.split('/')[0]
                        # YYYYMMDD 형식인지 확인 (8자리 숫자)
                        if date_dir and len(date_dir) == 8 and date_dir.isdigit():
                            date_dirs.append(date_dir)
            if date_dirs:
                latest_date_str = sorted(date_dirs, reverse=True)[0]
                date_source = "일자별 디렉토리 목록"
                use_latest = False  # 메타데이터가 없으면 일자별 디렉토리 사용
                query_path = f"{object_prefix}/{latest_date_str}/"
                print(f"정보: 일자별 디렉토리에서 최신 일자 확인: {latest_date_str}", file=sys.stderr, flush=True)
        except Exception as e2:
            print(f"오류: 일자별 디렉토리 목록 조회 실패: {e2}", file=sys.stderr, flush=True)
    
    if not latest_date_str:
        print(f"오류: 최신 일자를 확인할 수 없습니다. 데이터가 적재되었는지 확인하세요.", file=sys.stderr, flush=True)
        print(f"  버킷: {bucket}, prefix: {object_prefix}", file=sys.stderr, flush=True)
        sys.exit(1)
    
    # query_path가 설정되지 않은 경우 fallback
    if not query_path:
        query_path = f"{object_prefix}/{latest_date_str}/"
        if date_source is None:
            date_source = "일자별 디렉토리 목록"
        use_latest = False
    
    # date_source가 None인 경우 기본값 설정
    if date_source is None:
        date_source = "알 수 없음"
    
    # 조회 일자 정보 출력 (항상 표시)
    print(f"", file=sys.stderr, flush=True)
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr, flush=True)
    print(f"  [ 데이터 조회 정보 ]", file=sys.stderr, flush=True)
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr, flush=True)
    print(f"  조회 일자: {latest_date_str}", file=sys.stderr, flush=True)
    print(f"  일자 확인 방법: {date_source}", file=sys.stderr, flush=True)
    if use_latest:
        print(f"  조회 경로: {query_path} (latest 디렉토리 사용)", file=sys.stderr, flush=True)
    else:
        print(f"  조회 경로: {query_path} (일자별 디렉토리 사용)", file=sys.stderr, flush=True)
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr, flush=True)
    print(f"", file=sys.stderr, flush=True)
    
    # 조회 경로 결정 (use_latest에 따라)
    if use_latest:
        # latest 디렉토리에서 조회
        bulk_key = f"{object_prefix}/latest/bulk.jsonl"
        single_key = f"{object_prefix}/latest/{cusno}.json"
        prefix = index_prefix(cusno)
        index_shard_key = f"{object_prefix}/latest/index_{prefix}.json"
        index_full_key = f"{object_prefix}/latest/index.json"
    else:
        # 일자별 디렉토리에서 조회
        date_prefix = f"{object_prefix}/{latest_date_str}"
        bulk_key = f"{date_prefix}/bulk.jsonl"
        single_key = f"{date_prefix}/{cusno}.json"
        prefix = index_prefix(cusno)
        index_shard_key = f"{date_prefix}/index_{prefix}.json"
        index_full_key = f"{date_prefix}/index.json"

    def fetch_via_index(index_key: str) -> Optional[dict]:
        """
        인덱스 파일을 통해 데이터 조회 (Fast Load 모드)
        
        Args:
            index_key: 인덱스 파일 키 (예: index_001.json 또는 index.json)
        
        Returns:
            조회된 문서 딕셔너리 또는 None (조회 실패 시)
        """
        try:
            resp = client.get_object(bucket, index_key)
            index = json_loads(resp.read())
            resp.close()
            resp.release_conn()  # 연결 즉시 해제 (메모리 최적화)
            
            if cusno not in index:
                return None
            
            start_off, length = index[cusno]
            
            # minio 6.x 호환: Range GET 처리
            try:
                # minio 7.x 방식 (offset, length 파라미터) 시도 (권장)
                resp = client.get_object(bucket, bulk_key, offset=start_off, length=length)
                line = resp.read()
                resp.close()
                resp.release_conn()  # 연결 즉시 해제 (메모리 최적화)
                return json_loads(line)
            except (TypeError, AttributeError):
                # minio 6.x 방식: 전체 객체를 읽고 필요한 부분만 추출
                # (성능은 약간 떨어지지만 호환성 확보)
                resp = client.get_object(bucket, bulk_key)
                data = resp.read()
                resp.close()
                resp.release_conn()  # 연결 즉시 해제 (메모리 최적화)
                line = data[start_off:start_off + length]
                return json_loads(line)
        except Exception:
            # 인덱스 파일 읽기 실패 시 None 반환 (예외 상세 정보는 상위로 전달하지 않음)
            return None

    # 1) Fast Load: 샤드 인덱스(index_{prefix}.json) 우선 → 소량만 GET, 100ms 이내
    t0 = time.perf_counter()
    doc = None
    error_messages = []
    
    # 디버깅: 인덱스 파일 존재 여부 확인
    try:
        client.stat_object(bucket, index_shard_key)
        # 인덱스 파일이 존재하면 샘플 CUSNO 확인
        try:
            resp = client.get_object(bucket, index_shard_key)
            index = json_loads(resp.read())
            resp.close()
            resp.release_conn()
            if index:
                sample_cusnos = list(index.keys())[:3]
                print(f"[DEBUG] 인덱스 파일 존재: {index_shard_key}, 샘플 CUSNO: {', '.join(sample_cusnos)}", file=sys.stderr, flush=True)
        except Exception:
            pass
    except Exception:
        error_messages.append(f"샤드 인덱스 파일 없음: {index_shard_key}")
    
    try:
        doc = fetch_via_index(index_shard_key)
        if doc is None:
            error_messages.append(f"샤드 인덱스({index_shard_key})에 CUSNO 없음: {cusno}")
    except S3Error as e:
        if e.code == "NoSuchKey":
            error_messages.append(f"샤드 인덱스 파일 없음: {index_shard_key}")
        else:
            print(f"오류: 샤드 인덱스 조회 실패: {e}", file=sys.stderr)
            raise
        try:
            doc = fetch_via_index(index_full_key)
            if doc is None:
                error_messages.append(f"전체 인덱스({index_full_key})에 CUSNO 없음")
        except S3Error as e2:
            if e2.code == "NoSuchKey":
                error_messages.append(f"전체 인덱스 파일 없음: {index_full_key}")
            else:
                print(f"오류: 전체 인덱스 조회 실패: {e2}", file=sys.stderr)
                raise
            # 2) index 샤드·전체 모두 없음 → 1건=1객체({최신일자}/{CUSNO}.json) 시도
            try:
                resp = client.get_object(bucket, single_key)
                doc = json_loads(resp.read())
                resp.close()
            except S3Error as e3:
                if e3.code == "NoSuchKey":
                    error_messages.append(f"단건 객체 파일 없음: {single_key}")
                else:
                    print(f"오류: 단건 객체 조회 실패: {e3}", file=sys.stderr)
                    raise
    
    if doc is None:
        print(f"해당 CUSNO 없음 또는 데이터 미적재: {cusno}", file=sys.stderr, flush=True)
        print(f"  버킷: {bucket} (shinhanobj), prefix: {object_prefix}, data_type: {data_type}", file=sys.stderr, flush=True)
        print(f"  조회한 일자: {latest_date_str}", file=sys.stderr, flush=True)
        print(f"  조회 시도한 경로:", file=sys.stderr, flush=True)
        print(f"    - {index_shard_key}", file=sys.stderr, flush=True)
        print(f"    - {index_full_key}", file=sys.stderr, flush=True)
        print(f"    - {single_key}", file=sys.stderr, flush=True)
        if error_messages:
            print(f"  상세:", file=sys.stderr, flush=True)
            for msg in error_messages:
                print(f"    - {msg}", file=sys.stderr, flush=True)
        print("  Fast Load 적재: ./shl/batch_profile_minio_load.sh D|M <데이터파일> [기준일자] (D=일별, M=월별, 기준일자: YYYYMMDD 형식)", file=sys.stderr, flush=True)
        sys.exit(1)

    # 암호화 대상 컬럼 복호화: _meta.json에서 encrypted_columns 로드 후 decrypt_document 호출
    encrypted_columns = []
    meta_key = f"{object_prefix}/latest/_meta.json" if use_latest else f"{object_prefix}/{latest_date_str}/_meta.json"
    try:
        resp = client.get_object(bucket, meta_key)
        meta = json_loads(resp.read())
        resp.close()
        resp.release_conn()
        encrypted_columns = meta.get("encrypted_columns") or []
    except Exception:
        pass  # _meta.json 없거나 읽기 실패 시 encrypted_columns 빈 리스트 유지

    try:
        from batch_profile_encryption import decrypt_document
        doc = decrypt_document(doc, encrypted_columns=encrypted_columns if encrypted_columns else None)
    except ImportError:
        pass  # 암호화 모듈 없으면 원문 그대로 출력
    except Exception as e:
        print(f"경고: 복호화 실패, 암호화된 상태로 출력합니다: {e}", file=sys.stderr, flush=True)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    # JSON 출력 (들여쓰기 포함)
    try:
        import orjson
        print(orjson.dumps(doc, option=orjson.OPT_INDENT_2).decode(), flush=True)
    except ImportError:
        import json
        print(json.dumps(doc, indent=2, ensure_ascii=False), flush=True)
    print(f"조회 소요시간: {elapsed_ms:.2f} ms", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()