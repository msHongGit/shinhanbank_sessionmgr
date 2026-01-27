# 데이터베이스 컬럼 정리

## 계좌 관련 테이블 (Image 1)

| 컬럼명 | 컬럼명글벌 | 밑줄 | 컬럼설명 | 사용여부 | 대문류 | 중분류 |
|--------|-----------|------|----------|---------|--------|--------|
| LM1_ACML_TP_FUND_BOYU_ACNT | 최근1개월적립식펀드보유계좌수 | INT | 최근1개월적립식펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_PENS_FUND_BOYU_ACNT | 최근1개월연금펀드보유계좌수 | INT | 최근1개월연금펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_ICY_BOYU_ACNT | 최근1개월청약보유계좌수 | INT | 최근1개월청약보유계좌수 | Y | 현황정보 | 수신 |
| LM1_LIM_TY_ISA_BOYU_ACNT | 최근1개월일임형ISA보유계좌수 | INT | 최근1개월일임형ISA보유계좌수 | Y | 현황정보 | 수신 |
| LM1_STS_TYPE_ISA_BOYU_ACNT | 최근1개월실적형ISA보유계좌수 | INT | 최근1개월실적형ISA보유계좌수 | Y | 현황정보 | 수신 |
| LM1_MMT_BOYU_ACNT | 최근1개월MMT보유계좌수 | INT | 최근1개월MMT보유계좌수 | Y | 현황정보 | 수신 |
| LM1_PSTS_BOYU_ACNT | 최근1개월재산신탁보유계좌수 | INT | 최근1개월재산신탁보유계좌수 | Y | 현황정보 | 수신 |
| LM1_MNEY_STS_BOYU_ACNT | 최근1개월금전신탁보유계좌수 | INT | 최근1개월금전신탁보유계좌수 | Y | 현황정보 | 수신 |
| LM1_PIRP_BOYU_ACNT | 최근1개월퇴직연금보유계좌수 | INT | 최근1개월퇴직연금보유계좌수 | Y | 현황정보 | 수신 |
| LM1_BNKAGC_BOYU_ACNT | 최근1개월방카가지식보유계좌수 | INT | 최근1개월방카가지식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_ACML_TP_PRDT_BOYU_ACNT | 최근1개월적립식상품보유계좌수 | INT | 최근1개월방카가지식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_PSNT_PENS_BOYU_ACNT | 최근1개월연금연금보유계좌수 | INT | 최근1개월연금연금보유계좌수 | Y | 현황정보 | 수신 |
| LM1_PROVR_BBK_BOYU_ACNT | 최근1개월개인연금보유계좌수 | INT | 최근1개월개인연금보유계좌수 | Y | 현황정보 | 수신 |
| LM1_SODKGJ_PRDT_BOYU_ACNT | 최근1개월소득공제상품보유계좌수 | INT | 최근1개월소득공제상품보유계좌수 | Y | 현황정보 | 수신 |
| LM1_NTPRDT_BOYU_ACNT | 최근1개월비과세상품보유계좌수 | INT | 최근1개월비과세상품보유계좌수 | Y | 현황정보 | 수신 |
| LM1_LGTM_FRKTP_FUND_BOYU_ACNT | 최근1개월장기주식형펀드보유계좌수 | INT | 최근1개월장기주식형펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_LGTM_HS_RSV_SV_BOYU_ACNT | 최근1개월장기예적금보유계좌수 | INT | 최근1개월장기예적금펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_MTRX_BBK_BOYU_ACNT | 최근1개월주거래통장보유계좌수 | INT | 최근1개월장기주택마련저축보유계좌수 | Y | 현황정보 | 수신 |
| LM1_RPM_IRP_EXCPT_BOYU_ACNT | 최근1개월퇴직연금IRP제외보유계좌수 | INT | 최근1개월퇴직연금IRP제외보유계좌수 | Y | 현황정보 | 수신 |
| LM1_NET_REBNB_DC_BOYU_ACNT | 최근1개월순수텍당보유계좌수 | INT | 최근1개월순수텍당보유계좌수 | Y | 현황정보 | 수신 |
| LM1_MDAMT_DC_BOYU_ACNT | 최근1개월중수텍당보유계좌수 | INT | 최근1개월중수텍당보유계좌수 | Y | 현황정보 | 여신 |
| LM1_UU_BI_DC_BOYU_ACNT | 최근1개월일주택대출보유계좌수 | INT | 최근1개월중수텍당보유계좌수 | Y | 현황정보 | 여신 |
| LM1_JS_MRAMT_DC_BOYU_ACNT | 최근1개월전세자금대출보유계좌수 | INT | 최근1개월일주택대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_UN_NE_EST_DMBDC_BOYU_ACNT | 최근1개월무주택담보대출보유계좌수 | INT | 최근1개월전세자금대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_MCAR_DC_BOYU_ACNT | 최근1개월마이카대출보유계좌수 | INT | 최근1개월무주택담보대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_STS_DMBDC_BOYU_ACNT | 최근1개월상택담보대출보유계좌수 | INT | 최근1개월마이카대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_ORGNN_URYAMC_DC_BOYU_ACNT | 최근1개월직장인용당대출보유계좌수 | INT | 최근1개월상택담보대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_ELTLN_BOYU_ACNT | 최근1개월엘린대출보유계좌수 | INT | 최근1개월직장인용당대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_OFCMN_DC_PAYLN_BOYU_ACNT | 최근1개월직장인대출보유계좌수 | INT | 최근1개월엘린대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_PBSVT_UDAE_LN_BOYU_ACNT | 최근1개월공무원우대대출보유계좌수 | INT | 최근1개월공무원우대대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_MINR_LN_BOYU_ACNT | 최근1개월군인우대대출보유계좌수 | INT | 최근1개월군인우대대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_ILBAN_CSS_DC_BOYU_ACNT | 최근1개월일반신용대출보유계좌수 | INT | 최근1개월일반신용대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_SEOMIN_DC_BOYU_ACNT | 최근1개월서민대출보유계좌수 | INT | 최근1개월서민대출보유계좌수 | Y | 현황정보 | 여신 |
| LM1_SB_DC_BOYU_ACNT | 최근1개월기타대출보유계좌수 | INT | 최근1개월기타대출보유계좌수 | Y | 현황정보 | 여신 |
| SHB_CRCD_BYYN | 신한체크카드보유여부 | NUMERIC(18) | 신한체크카드보유여부 | Y | 현황정보 | 카탁 |
| SHB_CHKCD_BYYN | 신한체크카드보유여부 | NUMERIC(18) | | Y | 현황정보 | 카탁 |
| NLV_CD_BYYN | 나라사랑카드보유여부 | INT | 나라사랑카드보유여부 | Y | 현황정보 | 카탁 |
| CRCD_KJAC_BOYU_YN | 신용카드결제계좌보유여부 | INT | 신용카드결제계좌보유여부 | Y | 현황정보 | 카탁 |
| PAY_SJRECG_YN | 급여실적인정여부 | INT | | Y | 현황정보 | |
| MCHT_SJRECG_YN | 가맹점실적인정여부 | | 가맹점실적인정여부 | Y | 현황정보 | |

## 고객 정보 테이블 (Image 2)

| 컬럼명 | 컬럼명글벌 | 밑줄 | 컬럼설명 | 사용여부 | 대문류 |
|--------|-----------|------|----------|---------|--------|
| ITV_JEONDAM_CUS_YN | 대면전담고객여부 | INT | 대면전담고객여부 | Y | 행태정보 |
| WM_CUS_YN | WM고객여부 | INT | WM고객여부 | Y | 행태정보 |
| WM_EXCLT_CUS_YN | WM우수고객여부 | INT | WM우수고객여부 | Y | 행태정보 |
| MKTG_MFUSE_AGR_YN | 마케팅활용동의여부 | INT | WM우수고객여부 | Y | 행태정보 |
| HASST_PTTL_CUS_YN | 고자산잠재고객여부 | INT | 마케팅활용동의여부 | Y | 행태정보 |
| ELD_CUS_YN | PB고객여부 | INT | 고자산잠재고객여부 | Y | 행태정보 |
| PBIZR_EXIM_SJRECG_YN | 개인사업자수출입실적인정여부 | INT | PB고객여부 | Y | 행태정보 |
| PBIZR_YN | 개인사업자여부 | INT | 개인사업자수출입실적인정여부 | Y | 행태정보 |
| PPENS_SUGEUB_YN | 공적연금수급여부 | INT | 개인사업자여부 | Y | 행태정보 |
| MINR_CUS_YN | 미성년자고객여부 | INT | 공적연금수급여부 | Y | 행태정보 |
| PRDT_TRX_CUS_YN | 상품거래고객여부 | INT | 미성년자고객여부 | Y | 행태정보 |
| SNIR_CUS_YN | 시니어고객여부 | INT | 상품거래고객여부 | Y | 행태정보 |
| ELTLN_MFR_JAEJK_YN | 엘린트론첼직여부 | INT | 시니어고객여부 | Y | 행태정보 |
| FML_CUS_YN | 여성고객여부 | INT | 엘린트론첼직여부 | Y | 행태정보 |
| CHAIKIN_CUS_YN | 위대한고객여부 | INT | 여성고객여부 | Y | 행태정보 |
| LEAS_PROVR_CUS_YN | 임대사업자고객여부 | INT | 외국인고객여부 | Y | 행태정보 |
| SMCO_CUS_YN | 중소기업고객여부 | INT | 임대사업자고객여부 | Y | 행태정보 |
| OFCMN_CUS_YN | 직장인고객여부 | INT | 중소기업고객여부 | Y | 행태정보 |
| PAY_OFCMN_CUS_YN | 급여직장인고객여부 | NUMERIC(18) | 직장인고객여부 | Y | 행태정보 |
| CIF_OFCMN_CUS_YN | OIF직장인고객여부 | NUMERIC(18) | 급여직장인고객여부 | Y | 행태정보 |
| MY_PAY_CLB_ENT_YN | MY급여CLUB가입여부 | NUMERIC(18) | CIF직장인고객여부 | Y | 행태정보 |
| HEYYG_CUS_YN | 해외송고객여부 | INT | MY급여CLUB가입여부 | Y | 행태정보 |
| CD_BAL_JAGYEOK_YN | 카드발급자격여부 | INT | 해외송고객여부 | Y | 행태정보 |
| PAY_ICHE_YN | 급여이체여부 | NUMERIC(18) | 카드발급자격여부 | Y | 행태정보 |
| PAY_ICHE_AC_BYYN | 급여이체결제유여부 | NUMERIC(18) | 급여이체여부 | Y | 행태정보 |
| SOL_ENT_YN | SOL가입여부 | INT | 급여이체결제유여부 | Y | 행태정보 |
| SHPLUS_MBSH_ENT_YN | 신한플러스멤버십가입여부 | INT | SOL가입여부 | Y | 행태정보 |
| MNYVS_ENT_YN | 머니버스가입여부 | INT | 신한플러스멤버십가입여부 | Y | 행태정보 |
| DGY_MEMB_YN | 명거요회원여부 | INT | 머니버스가입여부 | Y | 행태정보 |
| DGY_PROVR_YN | 명거요사업자여부 | INT | 명거요회원여부 | Y | 행태정보 |
| IGWORK_YN | 망뚜이여부 | NUMERIC(1) | 명거요사업자여부 | Y | 행태정보 |
| CUS_INVS_PRPST_GD | 고객투자성향등급 | INT | 망뚜이여부 | Y | 행태정보 |
| LM1_SDD_ILBAN_BOYU_ACNT | 최근1개월유종실일반보유계좌수 | INT | 최근1개월유종실일반보유계좌수 | Y | 현황정보 | 수신 |
| LM1_MMF_BOYU_ACNT | 최근1개월MMF보유계좌수 | INT | 최근1개월MMF보유계좌수 | Y | 현황정보 | 수신 |
| LM1_SDD_GOLD_SLVR_BOYU_ACNT | 최근1개월유종실금은보유계좌수 | INT | 최근1개월유종실금은보유계좌수 | Y | 현황정보 | 수신 |
| LM1_FCUR_GCTP_BOYU_ACNT | 최근1개월외화거치식보유계좌수 | INT | 최근1개월외화거치식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_WCUR_GCTP_BOYU_ACNT | 최근1개월원화거치식보유계좌수 | INT | 최근1개월원화거치식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_FCUR_ACML_TP_BOYU_ACNT | 최근1개월외화적립식보유계좌수 | INT | 최근1개월외화적립식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_WCUR_ACML_TP_BOYU_ACNT | 최근1개월원화적립식보유계좌수 | INT | 최근1개월원화적립식보유계좌수 | Y | 현황정보 | 수신 |
| LM1_OPTTP_FUND_BOYU_ACNT | 최근1개월임의식펀드보유계좌수 | INT | 최근1개월임의식펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_GCTP_FUND_BOYU_ACNT | 최근1개월거치식펀드보유계좌수 | INT | 최근1개월거치식펀드보유계좌수 | Y | 현황정보 | 수신 |
| LM1_ACML_TP_FUND_BOYU_ACNT | 최근1개월적립식펀드보유계좌수 | INT | 최근1개월적립식펀드보유계좌수 | Y | 현황정보 | 수신 |

## 고객번호 및 기본정보 (Image 3)

| 컬럼명 | 컬럼명글벌 | 밑줄 | 컬럼설명 | 사용여부 | 대문류 |
|--------|-----------|------|----------|---------|--------|
| CUSNO | 고객번호 | NUMERIC(10) | 고객번호 | Y | 프로파일 |
| SOL_ENT_YN | SOL가입여부 | INT | SOL가입여부 | Y | 프로파일 |
| LM1_SOL_LOGIN_YN | 최근1개월SOL로그인여부 | INT | 최근1개월SOL로그인여부 | Y | 행태정보 |
| SHPLUS_ENT_YN | 신한플러스가입여부 | INT | 최근1개월SOL로그인여부 | Y | 행태정보 |
| INET_BNKG_ENT_YN | 인터넷뱅킹가입여부 | INT | 신한플러스가입여부 | Y | 행태정보 |
| IBNK_ACTV_YN | 인터넷뱅킹활동여부 | INT | 인터넷뱅킹가입여부 | Y | 행태정보 |
| PB_ENT_YN | 본행킹가입여부 | INT | 인터넷뱅킹활동여부 | Y | 행태정보 |
| PB_ACTV_YN | 본행킹활동여부 | INT | 본행킹가입여부 | Y | 행태정보 |
| SOL_DEP_PRDT_EXPR_YN | SOL수신상품종료여부 | INT | 본행킹활동여부 | Y | 행태정보 |
| NFCNG_DEP_PRDT_BVYN | 비대면수신상품보유여부 | INT | SOL수신상품종료여부 | Y | 행태정보 |
| SOL_DEP_PRDT_BYYN | SOL수신상품보유여부 | INT | 비대면수신상품보유여부 | Y | 행태정보 |
| LM1_FRNT_CHAN_USE_YN | 최근1개월창구채널이용여부 | INT | SOL수신상품보유여부 | Y | 행태정보 |
| REP_CUSNO | 대표고객번호 | NUMERIC(10) | 최근1개월창구채널이용여부 | Y | 프로파일 |
| CUS_MK_DRDT | 고객신규등록일자 | CHAR(8) | 대표고객번호 | Y | 프로파일 |
| CUSNM | 고객명 | VARCHAR(150) | 고객신규등록일자 | Y | 프로파일 |
| BIRYR_M_DT | 생년월일자 | CHAR(8) | 고객명 | Y | 프로파일 |
| NTLTY_NAT_C | 국적국가CODE | CHAR(2) | 생년월일자 | Y | 프로파일 |
| TRXPSN_PSNT_C | 거래자인적CODE | NUMERIC(3) | 국적국가CODE | Y | 프로파일 |
| TRXPSN_PSNT_NM | 거래자인적명 | VARCHAR(300) | 거래자인적CODE | Y | 프로파일 |
| SEX_G | 성별구분 | INT | 거래자인적명 | Y | 프로파일 |
| AGE | 연호 | INT | 성별구분 | Y | 프로파일 |
| AGE_C | 연호구분 | VARCHAR(1) | 연호 | Y | 프로파일 |
| MANAGE | 만나이 | INT | 연호구분 | Y | 프로파일 |
| MANAGE_G | 만나이구분 | VARCHAR(1) | 만나이 | Y | 프로파일 |
| CHLD_CNT | 자녀수 | NUMERIC(2) | 만나이구분 | Y | 프로파일 |
| JUGEO_G | 주거구분 | NUMERIC(1) | 자녀수 | Y | 프로파일 |
| JUGEO_K | 주거종류 | NUMERIC(1) | 주거구분 | Y | 프로파일 |
| HOME_ADR | 자택주소 | VARCHAR(300) | 주거종류 | Y | 프로파일 |
| CO_ADR | 회사주소 | VARCHAR(300) | 자택주소 | Y | 프로파일 |
| OCCP_C | 직업CODE | NUMERIC(4) | 회사주소 | Y | 프로파일 |
| OCCP_C_NM | 직업CODE명 | VARCHAR(300) | 직업CODE | Y | 프로파일 |
| JKWI_C | 직위CODE | NUMERIC(2) | 직업CODE명 | Y | 프로파일 |
| JKWI_C_NM | 직위CODE명 | VARCHAR(300) | 직위CODE | Y | 프로파일 |
| OCCP_GUN_G | 직업군구분 | INT | 직위CODE명 | Y | 프로파일 |
| OCCP_GUN_G_NM | 직업군구분명 | VARCHAR(30) | 직업군구분 | Y | 프로파일 |
| HIGH_SODK_OCCP_GUN_G | 고소득직업군구분 | INT | 직업군구분명 | Y | 프로파일 |
| HIGH_SODK_OCCP_GUN_G_NM | 고소득직업군구분명 | VARCHAR(15) | 고소득직업군구분 | Y | 프로파일 |
| OFG_NM | 직장명 | VARCHAR(150) | 고소득직업군구분명 | Y | 프로파일 |
| ACTV_YN | 활동성여부 | NUMERIC(3) | 직장명 | Y | 행태정보 |
| PWM_CUS_YN | PWM고객여부 | INT | 활동성여부 | Y | 행태정보 |
| JEONDAM_CUS_YN | 전담고객여부 | INT | PWM고객여부 | Y | 행태정보 |
| ITV_JEONDAM_CUS_YN | 대면전담고객여부 | INT | 전담고객여부 | Y | 행태정보 |

## 추가 정보 (Image 4)

| 컬럼명 | 컬럼명글벌 | 밑줄 | 컬럼설명 | 사용여부 | 대문류 |
|--------|-----------|------|----------|---------|--------|
| MCHT_SJRECG_YN | 가맹점실적인정여부 | INT | 가맹점실적인정여부 | Y | 행태정보 |
| AUTOICHE_SJRECG_YN | 자동이체실적인정여부 | INT | (UCS_CRRSAL_MASTER_V_(yyyymm)) V 위치의 <br> 1_VIEW 명의 YYYYMM 이 작업기준년 | Y | 행태정보 |
| AUTOICH_SJRECG_YN | 자동이체실적인정여부 | INT | 고객번호 7자리 고유번호번 42 | | 행태정보 |
| LM1_APT_FEE_ICHE_YN | 최근1개월아파트관리비이체여부 | INT | 최근1개월아파트관리비이체여부 | Y | 행태정보 |
| LM1_JUNGR_ICHE_YN | 최근1개월전기요금이체여부 | INT | 최근1개월전기요금이체여부 | Y | 행태정보 |
| LM1_CMFEE_ICHE_YN | 최근1개월통신비이체여부 | INT | 최근1개월통신비이체여부 | Y | 행태정보 |
| LM1_WS_CHRG_ICHE_YN | 최근1개월수도요금이체여부 | INT | 최근1개월수도요금이체여부 | Y | 행태정보 |
| LM1_GSFEE_ICHE_YN | 최근1개월가스요금이체여부 | INT | 최근1개월가스요금이체여부 | Y | 행태정보 |
| LM1_PMNV_ICHE_YN | 최근1개월공과금이체여부 | INT | 최근1개월공과금이체여부 | Y | 행태정보 |
| CUS_C | 고객구분(PABC, BI 비활) | string | | Y | 행태정보 |
| ACT_YN | 활동성여부 | string | | Y | 프로파일 |
| TRXPSN_PSNT_C | 거래자인적CODE | string | | Y | 프로파일 |
| NTLTY_NAT_C | 국적-국가CODE | string | | Y | 프로파일 |
| SEX_G | 성별 | string | | Y | 프로파일 |
| AGE | 나이 | string | | Y | 프로파일 |
| AGE_G | 연호구분 | string | | Y | 프로파일 |
| MAN_AGE | 만나이 | string | | Y | 프로파일 |
| MAN_AGE_G | 만나이구분 | string | | Y | 프로파일 |
| JUSO_G | 주소구분(시도기준, 지역) | string | | Y | 프로파일 |
| TOPS_GRBRRNO | TOPS관리점 | decimal(4) | | Y | 행태정보 |
| HALDANG_YN | 할당고객 여부 | string | | Y | 행태정보 |
| PAYICHE_YN | 급여이체여부(여기준) | string | | Y | 현황정보 |
| PENS_ICHE_YN | 연금이체여부 | string | | Y | 현황정보 | 수신 |
| EMP_ACTIVE_YN | 직장인관리고객여부 | string | | Y | 행태정보 |
| CR_CD_BYYN | 신용카드 보유여부 | string | | Y | 현황정보 | 카탁 |
| CHK_CD_BYYN | 체크카드 보유여부 | string | | Y | 현황정보 | 카탁 |
| CDKJ_AC_BYYN | 신용카드 결제계좌 보유여부 | string | | Y | 현황정보 | 카탁 |
| MCHT_KJAC_BYYN | 가맹점 결제계좌 보유 | string | | Y | 현황정보 | 카탁 |

---

**주요 컬럼 카테고리:**
- **대문류:** 현황정보, 행태정보, 프로파일
- **중분류:** 수신, 여신, 카탁, 기탁
- **데이터 타입:** INT, VARCHAR, NUMERIC, CHAR, string, decimal
- **사용여부:** 대부분 'Y' (사용중)
