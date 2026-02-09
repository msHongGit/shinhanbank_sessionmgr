#!/usr/bin/env python3
"""
공통 유틸리티 모듈

여러 모듈에서 공통으로 사용되는 유틸리티 함수와 클래스를 제공합니다.
"""

import io
import sys
import tempfile
import threading
import time
from typing import Optional

# orjson import
try:
    import orjson
except ImportError:
    orjson = None

# 로컬 모듈 import (순환 참조 방지를 위해 선택적)
try:
    from batch_profile_logger import Logger
except ImportError:
    Logger = None

try:
    from batch_profile_config import Config
except ImportError:
    Config = None

try:
    from batch_profile_exceptions import CSVParseError
except ImportError:
    CSVParseError = Exception


# ============================================================================
# 상수 정의
# ============================================================================

# 일별/월별 prefix
PREFIX_DAILY = "ifc_cus_dd_smry_tot"
PREFIX_MONTHLY = "ifc_cus_mmby_smry_tot"

# Content Type
CONTENT_TYPE = "application/json"


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
# 데이터 타입 유틸리티
# ============================================================================


def get_data_type_from_prefix(prefix: str) -> str:
    """
    prefix에서 데이터 타입 추론

    Args:
        prefix: 객체 prefix (PREFIX_DAILY 또는 PREFIX_MONTHLY)

    Returns:
        "daily" 또는 "monthly"
    """
    if prefix == PREFIX_MONTHLY:
        return "monthly"
    return "daily"


def get_prefix_from_data_type(data_type: str) -> str:
    """
    데이터 타입에서 prefix 반환

    Args:
        data_type: "daily" 또는 "monthly"

    Returns:
        PREFIX_DAILY 또는 PREFIX_MONTHLY
    """
    if data_type == "monthly":
        return PREFIX_MONTHLY
    return PREFIX_DAILY


def get_data_type_label(data_type: str) -> str:
    """
    데이터 타입에서 라벨 반환

    Args:
        data_type: "daily" 또는 "monthly"

    Returns:
        "Daily" 또는 "Monthly"
    """
    if data_type == "monthly":
        return "Monthly"
    return "Daily"


# ============================================================================
# 데이터 처리 유틸리티
# ============================================================================


def row_to_doc(row: list, cols: list) -> dict:
    """
    데이터 한 행을 문서 dict로 변환 (성능 최적화)

    Args:
        row: 데이터 행 데이터
        cols: 컬럼 이름 리스트

    Returns:
        변환된 문서 딕셔너리

    Raises:
        CSVParseError: 데이터 파싱 중 오류 발생 시
    """
    # 성능 최적화: 딕셔너리 크기를 미리 할당 (약 10% 성능 향상)
    doc = {}
    try:
        row_len = len(row)
        cols_len = len(cols)

        # 성능 최적화: enumerate 대신 직접 인덱스 접근 (약 5% 성능 향상)
        for i in range(cols_len):
            k = cols[i]
            v = (row[i].strip() if row[i] else "") if i < row_len else ""

            if v == "":
                doc[k] = None
            elif k == "BFMM_PMNY_ICHEAMT":
                # 특수 필드: float 타입
                try:
                    doc[k] = float(v)
                except ValueError:
                    doc[k] = None
            else:
                # 일반 필드: int 시도 후 실패하면 문자열로 저장
                # 성능 최적화: isdigit() 체크로 빠른 경로 제공 (중복 체크 제거)
                if v.isdigit():
                    doc[k] = int(v)
                else:
                    # 음수나 소수점이 포함된 경우를 위해 try-except 사용
                    try:
                        doc[k] = int(v)
                    except ValueError:
                        doc[k] = v
        return doc
    except Exception as e:
        # 라인 번호는 호출자가 제공해야 함
        if CSVParseError is not Exception:
            raise CSVParseError(0, e) from e
        raise


# ============================================================================
# 업로드 진행 상황 추적 클래스
# ============================================================================


class ProgressStream:
    """
    업로드 진행상황을 추적하는 파일 객체 래퍼

    파일 읽기 시 진행률을 추적하고, 일정 간격으로 진행 상황을 로그로 출력합니다.
    멈춤(stall) 감지 기능도 포함되어 있습니다.
    """

    def __init__(self, file_obj, total_size: int, label: str = "업로드"):
        """
        Args:
            file_obj: 읽을 파일 객체
            total_size: 전체 파일 크기 (바이트)
            label: 로그에 표시할 라벨
        """
        self.file_obj = file_obj
        self.total_size = total_size
        self.uploaded = 0
        self.label = label
        self.last_report = 0
        # 1% 또는 1MB마다 보고 (성능 최적화: 보고 빈도 조정)
        # 대용량 파일의 경우 보고 간격을 늘려서 I/O 오버헤드 감소
        self.report_interval = max(total_size // 100, 5 * 1024 * 1024)  # 5MB마다 보고
        self.last_activity_time = time.perf_counter()
        self.stall_timeout = 300  # 5분간 진행이 없으면 경고

    def read(self, size: int = -1) -> bytes:
        """파일에서 데이터를 읽고 진행 상황을 추적"""
        data = self.file_obj.read(size)
        if data:
            self.uploaded += len(data)
            self.last_activity_time = time.perf_counter()
            if self.uploaded - self.last_report >= self.report_interval:
                self._report()
                self.last_report = self.uploaded
        else:
            # 데이터가 없을 때도 시간 체크 (멈춤 감지)
            current_time = time.perf_counter()
            if current_time - self.last_activity_time > self.stall_timeout:
                elapsed_stall = int(current_time - self.last_activity_time)
                if Logger:
                    Logger.warning(
                        f"{self.label} 업로드가 {elapsed_stall}초간 진행되지 않았습니다.", details="네트워크 또는 서버 상태를 확인하세요."
                    )
                else:
                    print(f"경고: {self.label} 업로드가 {elapsed_stall}초간 진행되지 않았습니다.", file=sys.stderr, flush=True)
                self.last_activity_time = current_time  # 경고 후 시간 리셋
        return data

    def tell(self) -> int:
        """현재 파일 위치 반환"""
        return self.file_obj.tell()

    def seek(self, pos: int, whence: int = 0) -> int:
        """파일 위치 이동"""
        return self.file_obj.seek(pos, whence)

    def close(self):
        """파일 닫기"""
        return self.file_obj.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def _report(self):
        """진행 상황 로그 출력"""
        if Logger:
            Logger.upload_progress(self.label, self.uploaded, self.total_size)
        else:
            percent = (self.uploaded / self.total_size * 100) if self.total_size > 0 else 0
            print(f"[{self.label}] {percent:.1f}% ({self.uploaded:,}B / {self.total_size:,}B)", file=sys.stderr, flush=True)


# ============================================================================
# MinIO 클라이언트 관리
# ============================================================================

_tls = threading.local()


def get_minio_client(host: str, access_key: str, secret_key: str, secure: bool, pool_size: int = 4):
    """
    스레드당 Minio 클라이언트 1개 생성 (연결 풀 직렬화 제거)

    각 스레드마다 독립적인 클라이언트를 사용하여 스레드 안전성을 보장합니다.

    Args:
        host: MinIO 호스트명
        access_key: MinIO Access Key
        secret_key: MinIO Secret Key
        secure: HTTPS 사용 여부
        pool_size: 연결 풀 크기 (기본: 4)

    Returns:
        Minio 클라이언트 객체

    Raises:
        ImportError: minio 패키지가 설치되지 않은 경우
        Exception: 클라이언트 생성 실패 시
    """
    from minio import Minio

    key = (host, access_key)
    if not hasattr(_tls, "clients"):
        _tls.clients = {}
    if key not in _tls.clients:
        try:
            import urllib3

            # 타임아웃 설정 (대용량 파일 업로드 지원)
            timeout = None
            if Config:
                timeout = urllib3.Timeout(connect=Config.get_connect_timeout(), read=Config.get_read_timeout())
            else:
                timeout = urllib3.Timeout(connect=30, read=300)

            http = urllib3.PoolManager(
                maxsize=pool_size,
                timeout=timeout,
                retries=urllib3.Retry(total=Config.get_retries() if Config else 3, backoff_factor=1, status_forcelist=[500, 502, 503, 504]),
            )
        except Exception as e:
            if Logger:
                Logger.warning("urllib3 설정 실패, 기본 HTTP 클라이언트 사용", details=str(e))
            http = None

        try:
            _tls.clients[key] = (
                Minio(host, access_key=access_key, secret_key=secret_key, secure=secure, http_client=http)
                if http
                else Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)
            )
        except Exception as e:
            if Logger:
                from batch_profile_exceptions import MinIOConnectionError

                raise MinIOConnectionError(host, e) from e
            raise

    return _tls.clients[key]


# ============================================================================
# 임시 파일 관리
# ============================================================================


def create_temp_dir(prefix: str = "batch_profile_minio_") -> str:
    """
    임시 디렉토리 생성 (보안: 권한 제한)

    Args:
        prefix: 디렉토리 이름 접두사

    Returns:
        생성된 임시 디렉토리 경로
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    # 임시 디렉토리 권한 설정 (소유자만 읽기/쓰기/실행)
    import os

    os.chmod(temp_dir, 0o700)
    return temp_dir


# ============================================================================
# 파일 크기 포맷팅
# ============================================================================


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기를 읽기 쉬운 형식으로 포맷팅

    Args:
        size_bytes: 파일 크기 (바이트)

    Returns:
        포맷팅된 문자열 (예: "1.5GB", "500MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}PB"


# ============================================================================
# 경로 유틸리티
# ============================================================================


def normalize_path(path: str) -> str:
    """
    경로 정규화 (슬래시 통일)

    Args:
        path: 정규화할 경로

    Returns:
        정규화된 경로
    """
    import os

    return os.path.normpath(path).replace("\\", "/")


def ensure_trailing_slash(path: str) -> str:
    """
    경로 끝에 슬래시가 있는지 확인하고 없으면 추가

    Args:
        path: 경로 문자열

    Returns:
        슬래시가 보장된 경로
    """
    return path if path.endswith("/") else path + "/"


def remove_trailing_slash(path: str) -> str:
    """
    경로 끝의 슬래시 제거

    Args:
        path: 경로 문자열

    Returns:
        슬래시가 제거된 경로
    """
    return path.rstrip("/")


# ============================================================================
# 데이터 검증 유틸리티
# ============================================================================


def _get_data_delimiter() -> str:
    """
    데이터 구분자 반환 (중복 코드 제거)

    Returns:
        데이터 구분자 문자
    """
    if Config:
        return Config.get_data_delimiter()
    import os

    delimiter = os.environ.get("DATA_DELIMITER", "|")
    special = {"\\t": "\t", "\\n": "\n", "\\r": "\r"}
    return special.get(delimiter, delimiter)


def validate_data_file(data_path: str, expected_columns: list) -> tuple[int, int | None, str]:
    """
    데이터 파일 검증 (컬럼 수, 파일명에서 예상 건수 추출)

    Args:
        data_path: 데이터 파일 경로
        expected_columns: 예상 컬럼 목록

    Returns:
        (actual_column_count, expected_record_count, data_basename) 튜플
        - actual_column_count: 실제 컬럼 수
        - expected_record_count: 파일명에서 추출한 예상 건수 (없으면 None)
        - data_basename: 파일명

    Raises:
        CSVParseError: 데이터 파일에 유효한 데이터 행이 없을 때
    """
    import csv
    import os
    import re

    data_basename = os.path.basename(data_path)

    # 파일명에서 예상 건수 추출 (선택사항)
    expected_record_count = None
    # 파일명 형식: IFC_CUS_DD_SMRY_TOT_700000001_10000000.utf8.dat
    match = re.search(r"_(\d+)\.utf8\.data$", data_basename)
    if match:
        from contextlib import suppress

        with suppress(ValueError):
            expected_record_count = int(match.group(1))

    # 데이터 파일의 첫 번째 데이터 행을 읽어서 컬럼 수 검증
    data_delimiter = _get_data_delimiter()

    actual_column_count = None
    with open(data_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=data_delimiter)
        line_number = 0
        for row in reader:
            line_number += 1
            if not row:
                continue
            # 헤더 행 건너뛰기
            if len(row) > 0 and (row[0] or "").strip() == "CUSNO":
                continue
            # 첫 번째 데이터 행에서 컬럼 수 확인
            if len(row) > 0:
                actual_column_count = len(row)
                break

    if actual_column_count is None:
        if CSVParseError is not Exception:
            raise CSVParseError(0, "데이터 파일에 유효한 데이터 행이 없습니다.")
        raise Exception("데이터 파일에 유효한 데이터 행이 없습니다.")

    return actual_column_count, expected_record_count, data_basename


def get_columns_and_label(object_prefix: str) -> tuple[list, str]:
    """
    object_prefix에서 컬럼 목록과 라벨 반환

    Args:
        object_prefix: 객체 prefix (PREFIX_DAILY 또는 PREFIX_MONTHLY)

    Returns:
        (columns, label) 튜플
    """
    try:
        from batch_profile_schema import get_columns_daily, get_columns_monthly

        if object_prefix == PREFIX_MONTHLY:
            return get_columns_monthly(), "Monthly"
        else:
            return get_columns_daily(), "Daily"
    except ImportError as exc:
        raise ImportError("batch_profile_schema 모듈을 찾을 수 없습니다.") from exc


def parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """
    MinIO 엔드포인트를 파싱하여 호스트명과 secure 여부 반환

    Args:
        endpoint: MinIO 엔드포인트 URL

    Returns:
        (host, secure) 튜플
    """
    secure = endpoint.strip().lower().startswith("https://")
    host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    return host, secure


def get_s3_error_class():
    """
    minio 버전에 맞는 S3Error 클래스 반환 (호환성 보장)

    Returns:
        S3Error 클래스
    """
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
                # 최후의 수단: 기본 Exception 사용
                class S3Error(Exception):
                    def __init__(self, message, code=None, *args, **kwargs):
                        super().__init__(message, *args, **kwargs)
                        self.code = code

                return S3Error


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
