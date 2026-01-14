# Session Manager - 온프렘 MariaDB 구축 가이드

> **Sprint 4 기준** - 필드명 통일 완료 (`action_owner`, `updated_at`)

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [신규 설치 (Fresh Install)](#신규-설치-fresh-install)
3. [스키마 검증](#스키마-검증)
4. [트러블슈팅](#트러블슈팅)

---

## 사전 요구사항

### 필수 소프트웨어

- **MariaDB 10.5+** 또는 **MySQL 8.0+**
- **MariaDB Client** 또는 **MySQL Client**
- **데이터베이스 관리자 권한** (CREATE DATABASE, CREATE TABLE, ALTER TABLE 등)

### 네트워크 접근

- MariaDB 서버 접근 가능 (호스트, 포트, 인증 정보)
- Kubernetes 클러스터 내부의 경우: `kubectl port-forward` 사용 가능

### 접속 정보 확인

온프렘 환경의 MariaDB 접속 정보:

```
Host: my-mariadb.mariadb.svc.cluster.local (클러스터 내부 DNS)
Port: 3306
Username: root
Password: ChangeMe! (실제 비밀번호로 변경 필요)
Database: session_manager
```

---

## 신규 설치 (Fresh Install)

온프렘 환경에 처음으로 Session Manager DB를 구축하는 경우입니다.

### 1. 로컬에서 접속 (kubectl port-forward)

```bash
# MariaDB 서비스 포트 포워딩
kubectl port-forward svc/my-mariadb -n mariadb 3306:3306

# 별도 터미널에서 MariaDB 클라이언트로 접속
mysql -h 127.0.0.1 -P 3306 -u root -p
# 비밀번호 입력: ChangeMe!
```

### 2. 클러스터 내부 Pod에서 접속

```bash
# MariaDB 클라이언트 Pod 실행
kubectl run mariadb-client --rm -it --image=bitnami/mariadb:latest \
  --namespace mariadb -- bash

# Pod 안에서 실행
mysql -h my-mariadb.mariadb.svc.cluster.local -u root -p
# 비밀번호 입력: ChangeMe!
```

### 3. 스키마 초기화 스크립트 실행

```bash
# 방법 1: mysql 클라이언트로 직접 실행
mysql -h 127.0.0.1 -P 3306 -u root -p session_manager < scripts/init_db.sql

# 방법 2: Pod 내부에서 실행
kubectl exec -it <mariadb-pod-name> -n mariadb -- \
  mysql -u root -p session_manager < scripts/init_db.sql

# 방법 3: mysql 클라이언트에 접속 후 실행
mysql> source /path/to/scripts/init_db.sql;
```

### 4. 실행 결과 확인

```sql
-- 데이터베이스 확인
SHOW DATABASES LIKE 'session_manager';

-- 테이블 목록 확인
USE session_manager;
SHOW TABLES;

-- sessions 테이블 스키마 확인
DESCRIBE sessions;

-- 필수 필드 확인 (action_owner, updated_at)
SHOW COLUMNS FROM sessions LIKE 'action_owner';
SHOW COLUMNS FROM sessions LIKE 'updated_at';
```

**예상 결과:**

```
+------------------+
| Tables           |
+------------------+
| agent_sessions   |
| contexts         |
| conversation_turns |
| profile_attributes |
| sessions         |
+------------------+
```

---

## 스키마 검증

### 필수 테이블 확인

```sql
USE session_manager;

-- 1. sessions 테이블
SHOW CREATE TABLE sessions\G

-- 필수 필드 확인
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    IS_NULLABLE, 
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'session_manager' 
  AND TABLE_NAME = 'sessions'
  AND COLUMN_NAME IN ('action_owner', 'updated_at', 'reference_information', 'turn_ids')
ORDER BY ORDINAL_POSITION;
```

### 인덱스 확인

```sql
-- sessions 테이블 인덱스
SHOW INDEXES FROM sessions;

-- 필수 인덱스 확인
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    SEQ_IN_INDEX
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'session_manager'
  AND TABLE_NAME = 'sessions'
  AND INDEX_NAME IN ('idx_global_session_key', 'idx_sessions_state_updated')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
```

### 외래 키 확인

```sql
-- 외래 키 제약 조건 확인
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'session_manager'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;
```

---

## 트러블슈팅

### 문제 1: "Table 'session_manager.sessions' doesn't exist"

**원인:** 데이터베이스 또는 테이블이 생성되지 않음

**해결:**

```bash
# 초기화 스크립트 실행
mysql -h 127.0.0.1 -P 3306 -u root -p < scripts/init_db.sql
```

### 문제 2: "Access denied for user 'root'@'localhost'"

**원인:** 인증 정보 오류

**해결:**

```bash
# 올바른 호스트/포트/사용자/비밀번호 확인
mysql -h <correct-host> -P <correct-port> -u <correct-user> -p

# 또는 환경변수 사용
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=ChangeMe!
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD
```

### 문제 3: "Can't connect to MySQL server"

**원인:** 네트워크 연결 문제 또는 MariaDB 서비스 미실행

**해결:**

```bash
# Kubernetes 클러스터 내부에서 확인
kubectl get svc -n mariadb
kubectl get pods -n mariadb

# 포트 포워딩 확인
kubectl port-forward svc/my-mariadb -n mariadb 3306:3306

# 연결 테스트
mysql -h 127.0.0.1 -P 3306 -u root -p -e "SELECT 1;"
```

### 문제 4: "Duplicate key name 'idx_sessions_state_updated'"

**원인:** 인덱스가 이미 존재함

**해결:**

```sql
-- 기존 인덱스 삭제 후 재생성
DROP INDEX idx_sessions_state_updated ON sessions;
CREATE INDEX idx_sessions_state_updated ON sessions(session_state, updated_at);
```

---

## 빠른 참조

### 전체 스키마 재생성 (주의: 데이터 삭제됨)

```bash
# 1. 데이터베이스 삭제 (주의!)
mysql -h 127.0.0.1 -P 3306 -u root -p -e "DROP DATABASE IF EXISTS session_manager;"

# 2. 스키마 재생성
mysql -h 127.0.0.1 -P 3306 -u root -p < scripts/init_db.sql
```

### 데이터베이스 백업

```bash
# 전체 데이터베이스 백업
mysqldump -h 127.0.0.1 -P 3306 -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  session_manager > session_manager_backup_$(date +%Y%m%d_%H%M%S).sql

# 스키마만 백업 (데이터 제외)
mysqldump -h 127.0.0.1 -P 3306 -u root -p \
  --no-data \
  session_manager > session_manager_schema_$(date +%Y%m%d_%H%M%S).sql
```

### 데이터베이스 복원

```bash
# 백업 파일로 복원
mysql -h 127.0.0.1 -P 3306 -u root -p session_manager < session_manager_backup_YYYYMMDD.sql
```

---

## 체크리스트

### 신규 설치 시

- [ ] MariaDB 서버 접근 가능 확인
- [ ] `scripts/init_db.sql` 실행 완료
- [ ] 모든 테이블 생성 확인 (5개 테이블)
- [ ] 필수 필드 확인 (`action_owner`, `updated_at`)
- [ ] 인덱스 생성 확인
- [ ] 외래 키 제약 조건 확인
- [ ] 애플리케이션 연결 테스트

---

## 관련 파일

- `scripts/init_db.sql` - 신규 설치용 스키마 초기화 스크립트
- `scripts/create_db.py` - Python으로 스키마 생성 (대안)
- `app/models/mariadb_models.py` - SQLAlchemy 모델 정의

---

## 참고 문서

- `docs/Session_Manager_API_Sprint4.md` - Sprint 4 API 명세서
- `README.md` - 프로젝트 개요 및 시작 가이드

---

**작성일**: 2026년 1월 14일  
**버전**: Sprint 4  
**작성자**: Session Manager Team
