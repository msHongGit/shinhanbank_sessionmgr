#!/usr/bin/env python3
"""
Session Manager - MariaDB 데이터베이스 생성 스크립트
데이터베이스와 테이블을 생성합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from app.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_PASSWORD,
    MARIADB_PORT,
    MARIADB_USER,
)

# SQLAlchemy로 테이블 생성
from app.db.mariadb import Base, engine
from app.models.mariadb_models import (
    AgentSessionModel,
    ContextModel,
    ConversationTurnModel,
    ProfileAttributeModel,
    SessionModel,
)


def create_database():
    """데이터베이스 생성"""
    try:
        # 데이터베이스 없이 연결
        conn = pymysql.connect(
            host=MARIADB_HOST,
            port=MARIADB_PORT,
            user=MARIADB_USER,
            password=MARIADB_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MARIADB_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"✅ 데이터베이스 '{MARIADB_DATABASE}' 생성 완료")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        sys.exit(1)


def create_tables():
    """테이블 생성 (SQLAlchemy 사용)"""
    try:
        # 데이터베이스에 연결된 엔진 사용
        Base.metadata.create_all(engine)
        print("✅ 테이블 생성 완료")
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 MariaDB 데이터베이스 및 테이블 생성 시작...")
    create_database()
    create_tables()
    print("✅ 완료!")
