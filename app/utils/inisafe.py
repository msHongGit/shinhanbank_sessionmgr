"""IniSafe Paccel 암호화 라이브러리 스텁 (외부 공개용 플레이스홀더).

실제 구현은 내부망에서만 사용 가능합니다.
운영 환경에서는 빌드 파이프라인에서 이 파일을 실제 구현으로 교체하세요.

Docker 빌드 시:
  - libINISAFE_Crypto_for_C_v5.3.4_Linux_4.18_64.a
  - libINISAFE_Paccel_for_C_v2.4.4_Linux_4.18_64.a
  - libINISAFE_PKI_for_C_v5.3.9_Linux_4.18_64.a
  위 라이브러리를 소스에 추가하여 SO를 빌드한 후 이미지에 복사하고,
  이 파일을 saa-gateway-ssegw/app/utils/inisafe.py 의 실제 구현으로 교체합니다.

사용법:
    from app.utils.inisafe import ISPSymmKey, IniSafePaccel

    inisafe = IniSafePaccel()
    symm_key: ISPSymmKey = inisafe.get_symm_key()
    # symm_key.symmKey : hex 인코딩된 AES 키 문자열
    # symm_key.symmIV  : hex 인코딩된 IV 문자열
"""


class ISPSymmKey:
    """암호화에 사용할 AES 키와 IV를 담는 IniSafe 대칭키 객체.

    Attributes:
        symmKey: hex 인코딩된 AES 키 (실제: bytes.fromhex(symm_key.symmKey))
        symmIV:  hex 인코딩된 IV  (실제: bytes.fromhex(symm_key.symmIV))
    """

    symmKey: str = ""
    symmIV: str = ""


class IniSafePaccel:
    """IniSafe Paccel 클라이언트 스텁.

    실제 구현에서는 Paccel SO 를 로드하여 HW 가속기에서 키를 조회합니다.
    """

    def get_symm_key(self) -> "ISPSymmKey":
        """AES 대칭키(ISPSymmKey)를 반환합니다.

        Returns:
            ISPSymmKey: .symmKey (hex AES 키) + .symmIV (hex IV)

        Raises:
            NotImplementedError: 내부망 실제 구현이 없을 때 발생합니다.
        """
        raise NotImplementedError(
            "IniSafe Paccel 라이브러리가 설치되지 않았습니다. "
            "내부망 빌드 환경의 실제 inisafe.py 로 교체하세요. "
            "(INISAFE_ENABLED=false 로 설정하면 이 경로를 우회할 수 있습니다.)"
        )
