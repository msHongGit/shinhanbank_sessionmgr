"""Session Manager - Common Utility Functions.

공통 유틸리티 함수 모음:
- JSON 파싱 (안전한 파싱)
- Datetime 변환 (ISO 문자열 ↔ datetime)
- 에러 처리 통일
"""

import json
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


def safe_json_parse(value: str | dict | list | None, default: T | None = None) -> dict | list | T | None:
    """JSON 문자열을 안전하게 파싱

    Args:
        value: 파싱할 값 (str, dict, list, None)
        default: 파싱 실패 시 반환할 기본값

    Returns:
        파싱된 dict/list 또는 기본값
    """
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return default


def safe_json_dumps(value: dict | list | None, sort_keys: bool = True, ensure_ascii: bool = False) -> str | None:
    """JSON 객체를 안전하게 직렬화

    Args:
        value: 직렬화할 값
        sort_keys: 키 정렬 여부
        ensure_ascii: ASCII만 사용 여부

    Returns:
        JSON 문자열 또는 None
    """
    if value is None:
        return None
    try:
        return json.dumps(value, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    except (TypeError, ValueError):
        return None


def datetime_to_iso(dt: datetime | str | None) -> str | None:
    """datetime을 ISO 문자열로 변환

    Args:
        dt: 변환할 datetime 또는 이미 ISO 문자열인 경우

    Returns:
        ISO 문자열 또는 None
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None


def iso_to_datetime(iso_str: str | None) -> datetime | None:
    """ISO 문자열을 datetime으로 변환

    Args:
        iso_str: ISO 문자열 또는 이미 datetime인 경우

    Returns:
        datetime 또는 None
    """
    if iso_str is None:
        return None
    if isinstance(iso_str, datetime):
        return iso_str
    if isinstance(iso_str, str):
        try:
            # Z를 +00:00으로 변환
            normalized = iso_str.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except (ValueError, AttributeError):
            return None
    return None


def safe_datetime_parse(value: datetime | str | None) -> datetime | None:
    """datetime 또는 ISO 문자열을 안전하게 파싱

    Args:
        value: 파싱할 값

    Returns:
        datetime 또는 None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return iso_to_datetime(value)
