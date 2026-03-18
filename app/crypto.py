#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HSM Symmetric Key Retrieval (ctypes)
libInisafe.so 를 ctypes로 로드하여 INISAFE Paccel HSM API 호출

환경 변수:
  INISAFE_HSM_IP   - HSM 서버 IP (기본: 127.0.0.1)
  INISAFE_HSM_PORT - HSM 서버 포트 (기본: 9000)

세그멘테이션 오류 가능 원인 및 대응:
  - C에 넘긴 문자열 포인터를 라이브러리가 나중에 사용: create_string_buffer 사용
  - 구조체 레이아웃 불일치(ISP_ADDRESS): C 헤더와 필드 순서/패딩 일치 확인, 필요 시 _pack_ = 1
  - API 인자 개수/순서/타입 불일치: INISAFEPaccel.h 프로토타입과 argtypes/restype 일치 확인
  - Handle을 값으로 쓸지 포인터로 쓸지: ISP_GetSymmKeyWithID 첫 인자가 ISP_HANDLE vs ISP_HANDLE*
"""
import ctypes
import os
import sys
from ctypes import (
    CDLL,
    Structure,
    c_int,
    c_void_p,
    c_char_p,
    c_ubyte,
    c_char,
    POINTER,
    byref,
    create_string_buffer,
    string_at,
)

# 상수 (INISAFEPaccel.h에 정의된 값으로 추정, 필요 시 헤더에 맞게 수정)
ENC_USE = 1
ENC_ALG_SEED_CFB128 = 3  # unsigned int 3 (INISAFEPaccel.h)
PACKET_ENC_MODE = ENC_ALG_SEED_CFB128  # C: PACKET_ENC_MODE

# ISP_ADDRESS 구조체 (ip, port) - C 레이아웃과 일치해야 함 (패딩은 헤더 기준)
class ISP_ADDRESS(Structure):
    _fields_ = [
        ("ip", ctypes.c_char * 64),
        ("port", c_int),
    ]
    # C에서 #pragma pack(1) 사용 시: _pack_ = 1


class PaccelSymmKey:
    """getStoredSymmKey(szKeyID) 반환값에 해당. 대칭키·IV 등."""

    __slots__ = ("key_data", "iv_data", "key_status", "key_start_time", "key_end_time", "key_expired_time")

    def __init__(
        self,
        key_data: bytes,
        iv_data: bytes,
        key_status: bytes = b"",
        key_start_time: bytes = b"",
        key_end_time: bytes = b"",
        key_expired_time: bytes = b"",
    ):
        self.key_data = key_data
        self.iv_data = iv_data
        self.key_status = key_status
        self.key_start_time = key_start_time
        self.key_end_time = key_end_time
        self.key_expired_time = key_expired_time


class INISAFEPaccelClient:
    """
    C/Java: INISAFEPaccelClient paccel = new INISAFEPaccelClient(address[0].ip, address[0].port,
        PACKET_ENC_MODE, "user_id", "user_pw", false);
    packcelSymmKey symm = paccel.getStoredSymmKey(szKeyID);
    """

    def __init__(
        self,
        lib,  # CDLL("libInisafe.so")
        ip: str,
        port: int,
        packet_enc_mode: int,
        user_id: bytes,
        user_pw: bytes,
        use_ssl: bool = False,
        version: bytes = b"V001",
    ):
        self._lib = lib
        self._handle = c_void_p(None)
        self._address = (ISP_ADDRESS * 32)()
        ip_bytes = ip.encode("utf-8")[:63] if isinstance(ip, str) else ip[:63]
        # Structure의 ip 필드는 item 대입이 안 되므로 memmove로 복사 (ip가 첫 필드라 오프셋 0)
        ip_buf = create_string_buffer(64)
        ip_buf.value = ip_bytes
        ctypes.memmove(ctypes.addressof(self._address[0]), ctypes.addressof(ip_buf), 64)
        self._address[0].port = port
        self._buf_version = create_string_buffer(version, 32)
        self._buf_user_id = create_string_buffer(user_id, 256)
        self._buf_user_pw = create_string_buffer(user_pw, 256)
        ret = self._lib.ISP_Init(
            self._buf_version,
            ENC_USE,
            packet_enc_mode,
            self._buf_user_id,
            self._buf_user_pw,
            64,
            self._address,
            1,
        )
        if ret != 0:
            raise RuntimeError(f"ISP_Init failed: {ret:X}")
        ret = self._lib.ISP_HANDLE_New(byref(self._handle))
        if ret != 0:
            self._lib.ISP_Final()
            raise RuntimeError(f"ISP_HANDLE_New failed: {ret:X}")

    def get_stored_symm_key(self, key_id: bytes) -> PaccelSymmKey:
        """C: paccel.getStoredSymmKey(szKeyID)"""
        sz_key_id = create_string_buffer(256)
        sz_key_id.value = key_id
        key_data_ptr = c_void_p()
        key_data_len = c_int(0)
        iv_data_ptr = c_void_p()
        iv_data_len = c_int(0)
        key_status_ptr = c_void_p()
        key_status_len = c_int(0)
        key_start_time_ptr = c_void_p()
        key_start_time_len = c_int(0)
        key_end_time_ptr = c_void_p()
        key_end_time_len = c_int(0)
        key_expired_time_ptr = c_void_p()
        key_expired_time_len = c_int(0)
        ret = self._lib.ISP_SetSymmKeyID(self._handle, sz_key_id, len(key_id))
        if ret != 0:
            raise RuntimeError(f"ISP_SetSymmKeyID failed: {ret:X}")
        ret = self._lib.ISP_GetSymmKeyWithID(
            self._handle,
            byref(key_data_ptr),
            byref(key_data_len),
            byref(iv_data_ptr),
            byref(iv_data_len),
            byref(key_status_ptr),
            byref(key_status_len),
            byref(key_start_time_ptr),
            byref(key_start_time_len),
            byref(key_end_time_ptr),
            byref(key_end_time_len),
            byref(key_expired_time_ptr),
            byref(key_expired_time_len),
        )
        if ret != 0:
            raise RuntimeError("ISP_GetSymmKeyWithID failed")
        key_data = string_at(key_data_ptr.value, key_data_len.value) if key_data_ptr.value and key_data_len.value else b""
        iv_data = string_at(iv_data_ptr.value, iv_data_len.value) if iv_data_ptr.value and iv_data_len.value else b""
        key_status = string_at(key_status_ptr.value, key_status_len.value) if key_status_ptr.value and key_status_len.value else b""
        key_start_time = string_at(key_start_time_ptr.value, key_start_time_len.value) if key_start_time_ptr.value and key_start_time_len.value else b""
        key_end_time = string_at(key_end_time_ptr.value, key_end_time_len.value) if key_end_time_ptr.value and key_end_time_len.value else b""
        key_expired_time = string_at(key_expired_time_ptr.value, key_expired_time_len.value) if key_expired_time_ptr.value and key_expired_time_len.value else b""
        return PaccelSymmKey(
            key_data=key_data,
            iv_data=iv_data,
            key_status=key_status,
            key_start_time=key_start_time,
            key_end_time=key_end_time,
            key_expired_time=key_expired_time,
        )

    def close(self) -> None:
        if self._handle and self._handle.value is not None:
            self._lib.ISP_HANDLE_Free(byref(self._handle))
            self._handle = None
        self._lib.ISP_Final()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _hexdump(buf: bytes, length: int) -> None:
    """버퍼를 16바이트 단위로 hex 출력"""
    if not buf or length <= 0:
        return
    n = min(length, len(buf))
    for i in range(n):
        print(f"{buf[i]:02X} ", end="")
        if (i + 1) % 16 == 0:
            print()
    if n % 16 != 0:
        print()


def _setup_lib_argtypes(lib) -> None:
    """libInisafe.so에 API 시그니처 설정"""
    lib.ISP_Init.argtypes = [
        c_char_p, c_int, c_int, c_char_p, c_char_p, c_int,
        POINTER(ISP_ADDRESS), c_int,
    ]
    lib.ISP_Init.restype = c_int
    lib.ISP_HANDLE_New.argtypes = [POINTER(c_void_p)]
    lib.ISP_HANDLE_New.restype = c_int
    lib.ISP_SetSymmKeyID.argtypes = [c_void_p, c_char_p, c_int]
    lib.ISP_SetSymmKeyID.restype = c_int
    lib.ISP_GetSymmKeyWithID.argtypes = [
        c_void_p,
        POINTER(c_void_p),
        POINTER(c_int),
        POINTER(c_void_p),
        POINTER(c_int),
        POINTER(c_void_p),
        POINTER(c_int),
        POINTER(c_void_p),
        POINTER(c_int),
        POINTER(c_void_p),
        POINTER(c_int),
        POINTER(c_void_p),
        POINTER(c_int),
    ]
    lib.ISP_GetSymmKeyWithID.restype = c_int
    lib.ISP_HANDLE_Free.argtypes = [POINTER(c_void_p)]
    lib.ISP_HANDLE_Free.restype = None
    lib.ISP_Final.argtypes = []
    lib.ISP_Final.restype = None


def get_key(
    key_id: bytes = b"key_id",
    user_id: bytes = b"user_id",
    user_pw: bytes = b"user_pw",
) -> bytes:
    """
    HSM에서 대칭키를 조회하여 key_data(bytes)를 반환합니다.

    환경 변수:
        INISAFE_HSM_IP   - HSM 서버 IP (기본: 127.0.0.1)
        INISAFE_HSM_PORT - HSM 서버 포트 (기본: 9000)

    Args:
        key_id: 키 식별자
        user_id: HSM 사용자 ID
        user_pw: HSM 사용자 비밀번호

    Returns:
        대칭키 바이너리 (key_data). Base64 등 인코딩은 호출 측에서 처리.

    Raises:
        RuntimeError: Crypto.so/libInisafe.so 로드 실패 또는 HSM API 오류 시
        OSError: 공유 라이브러리 로드 실패 시
    """
    RTLD_GLOBAL = getattr(os, "RTLD_GLOBAL", 0x100)
    for crypto_so in ("Crypto.so", "libCrypto.so"):
        try:
            CDLL(crypto_so, mode=RTLD_GLOBAL)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("Crypto.so 로드 실패. LD_LIBRARY_PATH에 Crypto.so 경로를 추가하세요.")

    lib = CDLL("libInisafe.so")
    _setup_lib_argtypes(lib)

    hsm_ip = os.environ.get("INISAFE_HSM_IP", "127.0.0.1").strip()
    try:
        hsm_port = int(os.environ.get("INISAFE_HSM_PORT", "9000").strip())
    except ValueError:
        hsm_port = 9000

    paccel = INISAFEPaccelClient(
        lib,
        hsm_ip,
        hsm_port,
        PACKET_ENC_MODE,
        user_id,
        user_pw,
        False,
    )
    try:
        symm = paccel.get_stored_symm_key(key_id)
        return symm.key_data
    finally:
        paccel.close()


if __name__ == "__main__":
    try:
        key = get_key()
        print("=========================================")
        print("HSM KEY (Python ctypes)")
        print("=========================================")
        print(f"KEY LEN: {len(key)}")
        _hexdump(key, len(key))
        sys.exit(0)
    except (RuntimeError, OSError) as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)