"""
Session Manager - CustomerProfile Model
개인화 프로파일 테이블 (VDB 배치 연동)
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.models import Base


class CustomerProfile(Base):
    """
    개인화 프로파일 테이블

    VDB(Vertical DB)에서 배치로 가져온 고객 프로파일 정보.
    attribute_key/value 쌍으로 저장.
    """

    __tablename__ = "customer_profiles"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 사용자 정보
    user_id = Column(String(100), nullable=False, index=True, comment="사용자 ID")

    # Context 연동 (선택)
    context_id = Column(String(255), index=True, comment="Context ID (FK 선택)")

    # 속성 정보
    attribute_key = Column(String(255), nullable=False, comment="속성 키")
    attribute_value = Column(Text, comment="속성 값")

    # 소스 정보
    source_system = Column(String(100), comment="소스 시스템 (VDB/CRM/etc)")

    # 시간 정보
    computed_at = Column(DateTime, comment="계산된 시각")
    valid_from = Column(DateTime, comment="유효 시작 시각")
    valid_to = Column(DateTime, comment="유효 종료 시각")

    # 배치 정보
    batch_period = Column(String(50), comment="배치 주기 (daily/weekly/monthly)")

    # 권한 정보
    permission_scope = Column(String(100), comment="권한 범위")

    # 메타 정보
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index("idx_user_attribute", "user_id", "attribute_key"),
        Index("idx_user_validity", "user_id", "valid_from", "valid_to"),
        Index("idx_context_user", "context_id", "user_id"),
    )

    def __repr__(self):
        return f"<CustomerProfile(id={self.id}, user_id={self.user_id}, key={self.attribute_key})>"
