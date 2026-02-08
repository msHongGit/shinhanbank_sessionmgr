-- ============================================
-- 배치 프로파일 Mock 데이터 삽입 스크립트
-- 테스트용 샘플 데이터
-- ============================================

-- 데이터베이스 선택 (실행 전에 데이터베이스 이름을 변경하세요)
-- USE your_database_name;
-- 주의: 위의 USE 문의 주석을 해제하고 실제 데이터베이스 이름을 입력하세요!

-- 현재 날짜/월 계산
SET @today = DATE_FORMAT(NOW(), '%Y%m%d');
SET @this_month = DATE_FORMAT(NOW(), '%Y%m');

-- 1. 고객일별요약집계 Mock 데이터 삽입
INSERT INTO IFC_CUS_DD_SMRY_TOT (
    CUSNO,
    STD_DT,
    -- 계좌 관련 정보 (Image 1)
    LM1_ACML_TP_FUND_BOYU_ACNT,
    LM1_PENS_FUND_BOYU_ACNT,
    LM1_ICY_BOYU_ACNT,
    LM1_MMT_BOYU_ACNT,
    SHB_CRCD_BYYN,
    SHB_CHKCD_BYYN,
    NLV_CD_BYYN,
    CRCD_KJAC_BOYU_YN,
    PAY_SJRECG_YN,
    MCHT_SJRECG_YN,
    -- 고객 정보 (Image 2)
    ITV_JEONDAM_CUS_YN,
    WM_CUS_YN,
    WM_EXCLT_CUS_YN,
    SOL_ENT_YN,
    SHPLUS_MBSH_ENT_YN,
    MNYVS_ENT_YN,
    CUS_INVS_PRPST_GD,
    -- 고객번호 및 기본정보 (Image 3)
    REP_CUSNO,
    CUSNM,
    BIRYR_M_DT,
    NTLTY_NAT_C,
    TRXPSN_PSNT_C,
    TRXPSN_PSNT_NM,
    SEX_G,
    AGE,
    AGE_C,
    MANAGE,
    MANAGE_G,
    CHLD_CNT,
    HOME_ADR,
    OCCP_C,
    OCCP_C_NM,
    -- 추가 정보 (Image 4)
    CUS_C,
    ACT_YN,
    TOPS_GRBRRNO,
    HALDANG_YN,
    PAYICHE_YN,
    PENS_ICHE_YN,
    CR_CD_BYYN,
    CHK_CD_BYYN
) VALUES (
    '0616001905',  -- CUSNO
    @today,         -- STD_DT (오늘 날짜)
    -- 계좌 관련 정보
    2,              -- LM1_ACML_TP_FUND_BOYU_ACNT: 적립식펀드보유계좌수
    1,              -- LM1_PENS_FUND_BOYU_ACNT: 연금펀드보유계좌수
    0,              -- LM1_ICY_BOYU_ACNT: 청약보유계좌수
    1,              -- LM1_MMT_BOYU_ACNT: MMT보유계좌수
    1,              -- SHB_CRCD_BYYN: 신한체크카드보유여부
    1,              -- SHB_CHKCD_BYYN: 신한체크카드보유여부
    0,              -- NLV_CD_BYYN: 나라사랑카드보유여부
    1,              -- CRCD_KJAC_BOYU_YN: 신용카드결제계좌보유여부
    1,              -- PAY_SJRECG_YN: 급여실적인정여부
    1,              -- MCHT_SJRECG_YN: 가맹점실적인정여부
    -- 고객 정보
    0,              -- ITV_JEONDAM_CUS_YN: 대면전담고객여부
    0,              -- WM_CUS_YN: WM고객여부
    0,              -- WM_EXCLT_CUS_YN: WM우수고객여부
    1,              -- SOL_ENT_YN: SOL가입여부
    1,              -- SHPLUS_MBSH_ENT_YN: 신한플러스멤버십가입여부
    0,              -- MNYVS_ENT_YN: 머니버스가입여부
    3,              -- CUS_INVS_PRPST_GD: 고객투자성향등급 (1-5)
    -- 고객번호 및 기본정보
    '0616001905',   -- REP_CUSNO: 대표고객번호
    '홍길동',       -- CUSNM: 고객명
    '19800101',     -- BIRYR_M_DT: 생년월일자
    'KR',           -- NTLTY_NAT_C: 국적국가CODE
    1,              -- TRXPSN_PSNT_C: 거래자인적CODE
    '내국인',       -- TRXPSN_PSNT_NM: 거래자인적명
    1,              -- SEX_G: 성별구분 (1: 남성, 2: 여성)
    44,             -- AGE: 연호
    'S',            -- AGE_C: 연호구분
    44,             -- MANAGE: 만나이
    'S',            -- MANAGE_G: 만나이구분
    2,              -- CHLD_CNT: 자녀수
    '서울특별시 강남구 테헤란로 123',  -- HOME_ADR: 자택주소
    1001,           -- OCCP_C: 직업CODE
    '사무직',       -- OCCP_C_NM: 직업CODE명
    -- 추가 정보
    'A',            -- CUS_C: 고객구분
    'Y',            -- ACT_YN: 활동성여부
    1001,           -- TOPS_GRBRRNO: TOPS관리점
    'Y',            -- HALDANG_YN: 할당고객 여부
    'Y',            -- PAYICHE_YN: 급여이체여부
    'N',            -- PENS_ICHE_YN: 연금이체여부
    'Y',            -- CR_CD_BYYN: 신용카드 보유여부
    'Y'             -- CHK_CD_BYYN: 체크카드 보유여부
);

-- 2. 고객월별요약집계 Mock 데이터 삽입
INSERT INTO IFC_CUS_MMBY_SMRY_TOT (
    CUSNO,
    STD_YM,
    -- 계좌 관련 정보 (Image 1)
    LM1_ACML_TP_FUND_BOYU_ACNT,
    LM1_PENS_FUND_BOYU_ACNT,
    LM1_ICY_BOYU_ACNT,
    LM1_MMT_BOYU_ACNT,
    SHB_CRCD_BYYN,
    SHB_CHKCD_BYYN,
    NLV_CD_BYYN,
    CRCD_KJAC_BOYU_YN,
    PAY_SJRECG_YN,
    MCHT_SJRECG_YN,
    -- 고객 정보 (Image 2)
    ITV_JEONDAM_CUS_YN,
    WM_CUS_YN,
    WM_EXCLT_CUS_YN,
    SOL_ENT_YN,
    SHPLUS_MBSH_ENT_YN,
    MNYVS_ENT_YN,
    CUS_INVS_PRPST_GD,
    -- 고객번호 및 기본정보 (Image 3)
    REP_CUSNO,
    CUSNM,
    BIRYR_M_DT,
    NTLTY_NAT_C,
    TRXPSN_PSNT_C,
    TRXPSN_PSNT_NM,
    SEX_G,
    AGE,
    AGE_C,
    MANAGE,
    MANAGE_G,
    CHLD_CNT,
    HOME_ADR,
    OCCP_C,
    OCCP_C_NM,
    -- 추가 정보 (Image 4)
    CUS_C,
    ACT_YN,
    TOPS_GRBRRNO,
    HALDANG_YN,
    PAYICHE_YN,
    PENS_ICHE_YN,
    CR_CD_BYYN,
    CHK_CD_BYYN
) VALUES (
    '0616001905',  -- CUSNO
    @this_month,   -- STD_YM (이번 달)
    -- 계좌 관련 정보
    2,              -- LM1_ACML_TP_FUND_BOYU_ACNT: 적립식펀드보유계좌수
    1,              -- LM1_PENS_FUND_BOYU_ACNT: 연금펀드보유계좌수
    0,              -- LM1_ICY_BOYU_ACNT: 청약보유계좌수
    1,              -- LM1_MMT_BOYU_ACNT: MMT보유계좌수
    1,              -- SHB_CRCD_BYYN: 신한체크카드보유여부
    1,              -- SHB_CHKCD_BYYN: 신한체크카드보유여부
    0,              -- NLV_CD_BYYN: 나라사랑카드보유여부
    1,              -- CRCD_KJAC_BOYU_YN: 신용카드결제계좌보유여부
    1,              -- PAY_SJRECG_YN: 급여실적인정여부
    1,              -- MCHT_SJRECG_YN: 가맹점실적인정여부
    -- 고객 정보
    0,              -- ITV_JEONDAM_CUS_YN: 대면전담고객여부
    0,              -- WM_CUS_YN: WM고객여부
    0,              -- WM_EXCLT_CUS_YN: WM우수고객여부
    1,              -- SOL_ENT_YN: SOL가입여부
    1,              -- SHPLUS_MBSH_ENT_YN: 신한플러스멤버십가입여부
    0,              -- MNYVS_ENT_YN: 머니버스가입여부
    3,              -- CUS_INVS_PRPST_GD: 고객투자성향등급 (1-5)
    -- 고객번호 및 기본정보
    '0616001905',   -- REP_CUSNO: 대표고객번호
    '홍길동',       -- CUSNM: 고객명
    '19800101',     -- BIRYR_M_DT: 생년월일자
    'KR',           -- NTLTY_NAT_C: 국적국가CODE
    1,              -- TRXPSN_PSNT_C: 거래자인적CODE
    '내국인',       -- TRXPSN_PSNT_NM: 거래자인적명
    1,              -- SEX_G: 성별구분 (1: 남성, 2: 여성)
    44,             -- AGE: 연호
    'S',            -- AGE_C: 연호구분
    44,             -- MANAGE: 만나이
    'S',            -- MANAGE_G: 만나이구분
    2,              -- CHLD_CNT: 자녀수
    '서울특별시 강남구 테헤란로 123',  -- HOME_ADR: 자택주소
    1001,           -- OCCP_C: 직업CODE
    '사무직',       -- OCCP_C_NM: 직업CODE명
    -- 추가 정보
    'A',            -- CUS_C: 고객구분
    'Y',            -- ACT_YN: 활동성여부
    1001,           -- TOPS_GRBRRNO: TOPS관리점
    'Y',            -- HALDANG_YN: 할당고객 여부
    'Y',            -- PAYICHE_YN: 급여이체여부
    'N',            -- PENS_ICHE_YN: 연금이체여부
    'Y',            -- CR_CD_BYYN: 신용카드 보유여부
    'Y'             -- CHK_CD_BYYN: 체크카드 보유여부
);

-- 데이터 확인
SELECT * FROM IFC_CUS_DD_SMRY_TOT WHERE CUSNO = '0616001905';
SELECT * FROM IFC_CUS_MMBY_SMRY_TOT WHERE CUSNO = '0616001905';


-- ALTER TABLE IFC_CUS_DD_SMRY_TOT
-- MODIFY COLUMN CUSNO VARCHAR(20);

-- ALTER TABLE IFC_CUS_MMBY_SMRY_TOT
-- MODIFY COLUMN CUSNO VARCHAR(20);