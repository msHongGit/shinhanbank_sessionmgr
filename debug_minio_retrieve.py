"""MinIO batch profile debug script.

- app.config 에서 MinIO 설정을 읽어와서
- CUSNO=7000001 에 대한 daily/monthly 배치 프로파일을 조회하고
- 결과를 stdout 으로 출력한다.

실행 예시:
    uv run python debug_minio_retrieve.py
"""

from __future__ import annotations

from pprint import pprint

from app import config
from app.services.batch_profile_minio_retrieve import retrieve_cusno
from app.services.batch_profile_utils import (
    PREFIX_DAILY,
    PREFIX_MONTHLY,
    create_minio_client_simple,
    json_loads,
)


def main() -> None:
    print("=== MinIO Config ===")
    print(f"MINIO_ENDPOINT = {config.MINIO_ENDPOINT!r}")
    # Access/Secret 은 보안상 출력하지 않는다.

    cusno = "7000001"

    print("\n=== DAILY (cusno=7000001) ===")
    daily = retrieve_cusno(
        endpoint=config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS_KEY or "",
        secret_key=config.MINIO_SECRET_KEY or "",
        data_type="daily",
        cusno=cusno,
    )
    pprint(daily)

    print("\n=== MONTHLY (cusno=7000001) ===")
    monthly = retrieve_cusno(
        endpoint=config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS_KEY or "",
        secret_key=config.MINIO_SECRET_KEY or "",
        data_type="monthly",
        cusno=cusno,
    )
    pprint(monthly)

    # ------------------------------------------------------------------
    # 샘플 데이터 탐색: 일별/월별 인덱스 파일에서 몇 개의 CUSNO만 확인
    # ------------------------------------------------------------------
    if not config.MINIO_ENDPOINT or not config.MINIO_ACCESS_KEY or not config.MINIO_SECRET_KEY:
        print("\n[INFO] MinIO 자격 증명이 설정되어 있지 않아 인덱스 탐색을 건너뜁니다.")
        return

    bucket = config.MINIO_BUCKET
    client = create_minio_client_simple(
        endpoint=config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS_KEY,
        secret_key=config.MINIO_SECRET_KEY,
    )

    # ------------------------------------------------------------------
    # 객체 존재 여부 직접 확인: bulk.jsonl / 단건 JSON
    # ------------------------------------------------------------------
    print("\n=== OBJECT EXISTENCE CHECK ===")
    try:
        client.stat_object(bucket, "ifc_cus_dd_smry_tot/latest/bulk.jsonl")
        print("exists: ifc_cus_dd_smry_tot/latest/bulk.jsonl")
    except Exception as exc:  # pragma: no cover - 디버그용
        print(f"missing: ifc_cus_dd_smry_tot/latest/bulk.jsonl -> {exc}")

    try:
        client.stat_object(bucket, "ifc_cus_dd_smry_tot/latest/7001000.json")
        print("exists: ifc_cus_dd_smry_tot/latest/7001000.json")
    except Exception as exc:  # pragma: no cover - 디버그용
        print(f"missing: ifc_cus_dd_smry_tot/latest/7001000.json -> {exc}")

    # _latest_date 메타데이터 확인 (daily)
    from app.services.batch_profile_utils import json_loads as _json_loads

    print("\n=== DAILY _latest_date.json (if exists) ===")
    try:
        latest_meta_key = f"{PREFIX_DAILY}/_latest_date.json"
        resp_meta = client.get_object(bucket, latest_meta_key)
        latest_meta = _json_loads(resp_meta.read())
        resp_meta.close()
        resp_meta.release_conn()
        print(f"meta file: {latest_meta_key}")
        print("content:")
        pprint(latest_meta)
    except Exception as exc:  # pragma: no cover - 디버그용
        print(f"[WARN] failed to read _latest_date.json: {exc}")

    print("\n=== SAMPLE DAILY CUSNOs from index_000.json (if exists) ===")
    try:
        index_key = f"{PREFIX_DAILY}/latest/index_000.json"
        resp = client.get_object(bucket, index_key)
        index = json_loads(resp.read())
        resp.close()
        resp.release_conn()
        sample_keys = list(index.keys())[:10]
        print(f"index file: {index_key}")
        print("sample CUSNOs:", sample_keys)

        if sample_keys:
            first_cusno = sample_keys[0]
            first_entry = index.get(first_cusno)
            print("first entry in index_000.json:")
            pprint(first_entry)

            # 인덱스가 가리키는 bulk.jsonl 구간을 직접 확인
            try:
                start_off, length = first_entry
                print("\n[DEBUG] bulk.jsonl range from index_000.json:")
                print(f"start_off={start_off}, length={length}")

                bulk_key = f"{PREFIX_DAILY}/latest/bulk.jsonl"
                try:
                    resp_bulk = client.get_object(bucket, bulk_key, offset=start_off, length=length)
                    chunk = resp_bulk.read()
                    resp_bulk.close()
                    resp_bulk.release_conn()
                except TypeError:
                    # offset/length 미지원인 경우 전체를 읽어서 슬라이스
                    resp_bulk = client.get_object(bucket, bulk_key)
                    data_bulk = resp_bulk.read()
                    resp_bulk.close()
                    resp_bulk.release_conn()
                    chunk = data_bulk[start_off : start_off + length]

                print("chunk (utf-8, up to 500 chars):")
                try:
                    text = chunk.decode("utf-8", errors="replace")
                except Exception:
                    text = str(chunk)
                print(text[:500])
            except Exception as exc:  # pragma: no cover - 디버그용
                print(f"[WARN] failed to inspect bulk.jsonl range: {exc}")
            print(f"\n>>> retrieve_cusno(daily) for first CUSNO: {first_cusno}")
            daily_first = retrieve_cusno(
                endpoint=config.MINIO_ENDPOINT,
                access_key=config.MINIO_ACCESS_KEY or "",
                secret_key=config.MINIO_SECRET_KEY or "",
                data_type="daily",
                cusno=first_cusno,
            )
            pprint(daily_first)

            print(f"\n>>> retrieve_cusno(monthly) for first CUSNO: {first_cusno}")
            monthly_first = retrieve_cusno(
                endpoint=config.MINIO_ENDPOINT,
                access_key=config.MINIO_ACCESS_KEY or "",
                secret_key=config.MINIO_SECRET_KEY or "",
                data_type="monthly",
                cusno=first_cusno,
            )
            pprint(monthly_first)
    except Exception as exc:  # pragma: no cover - 디버그용
        print(f"[WARN] daily index 샘플 조회 실패: {exc}")

    print("\n=== SAMPLE MONTHLY CUSNOs from index_000.json (if exists) ===")
    try:
        index_key_m = f"{PREFIX_MONTHLY}/latest/index_000.json"
        resp_m = client.get_object(bucket, index_key_m)
        index_m = json_loads(resp_m.read())
        resp_m.close()
        resp_m.release_conn()
        sample_keys_m = list(index_m.keys())[:10]
        print(f"index file: {index_key_m}")
        print("sample CUSNOs:", sample_keys_m)
    except Exception as exc:  # pragma: no cover - 디버그용
        print(f"[WARN] monthly index 샘플 조회 실패: {exc}")


if __name__ == "__main__":
    main()
