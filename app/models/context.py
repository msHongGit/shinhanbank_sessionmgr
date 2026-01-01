"""
Session Manager - SystemContext Model
시스템 연동 개인화 컨텍스트 테이블
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.models import Base


class SystemContext(Base):
    """
    시스템 연동 개인화 컨텍스트 테이블

    외부 시스템에서 가져온 사용자 컨텍스트 정보.
    attribute_key/value 쌍으로 저장.
    """

    __tablename__ = "system_contexts"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Context 식별자
    context_id = Column(String(255), nullable=False, index=True, comment="Context ID")

    # 속성 정보
    attribute_key = Column(String(255), nullable=False, comment="속성 키")
    attribute_value = Column(Text, comment="속성 값")

    # 소스 정보
    source_system = Column(String(100), comment="소스 시스템 (CRM/VDB/etc)")

    # 시간 정보
    computed_at = Column(DateTime, comment="계산된 시각")
    valid_from = Column(DateTime, comment="유효 시작 시각")
    valid_to = Column(DateTime, comment="유효 종료 시각")

    # 메타 정보
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index("idx_context_attribute", "context_id", "attribute_key"),
        Index("idx_context_validity", "context_id", "valid_from", "valid_to"),
    )

    def __repr__(self):
        return f"<SystemContext(id={self.id}, context_id={self.context_id}, key={self.attribute_key})>"
