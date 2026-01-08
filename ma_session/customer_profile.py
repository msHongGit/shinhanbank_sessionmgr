"""Customer profile data models for context-dependent user attributes.

Provides:
- CustomerProfile: Main customer profile container
- ProfileAttribute: Individual customer attribute with governance
- BatchPeriod: Update frequency enumeration
- PermissionScope: Agent access control
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BatchPeriod(str, Enum):
    """Attribute update frequency.

    - DAILY: Updated daily
    - WEEKLY: Updated weekly
    - MONTHLY: Updated monthly
    - ADHOC: Event-driven / ad-hoc updates
    """

    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    ADHOC = "A"


class PermissionScope(BaseModel):
    """Agent access control for profile attributes.

    Attributes:
        allowed_agents: List of agent IDs/types that can access this attribute
    """

    allowed_agents: list[str] = Field(default_factory=list, description="에이전트 접근 권한 목록 (List of allowed agent IDs)")

    def is_allowed(self, agent_id: str) -> bool:
        """Check if agent has access permission.

        Args:
            agent_id: Agent identifier to check

        Returns:
            True if agent is allowed, False otherwise
        """
        return agent_id in self.allowed_agents

    class Config:
        json_schema_extra = {"example": {"allowed_agents": ["knowledge_agent", "banking_agent"]}}


class ProfileAttribute(BaseModel):
    """Context-dependent customer profile attribute.

    Represents a single customer attribute that:
    - Varies by context (not global user property)
    - Has temporal validity (valid_from/valid_to)
    - Includes data governance (source, permissions)
    - Supports batch update tracking
    """

    attribute_id: str = Field(..., description="속성 고유 ID (Unique attribute ID)")

    user_id: str = Field(..., description="사용자 ID (User ID)")

    context_id: str = Field(..., description="컨텍스트 ID (Context ID: session/task/domain)")

    attribute_key: str = Field(..., description="속성 키 (Attribute key)", examples=["전세여부", "우대고객", "신용등급"])

    attribute_value: str | None = Field(None, description="속성 값 (Attribute value)", examples=["Y", "VIP", "A+"])

    source_system: str | None = Field(
        None, description="데이터 출처 시스템 (Source system)", examples=["vertica_db", "crm_api", "external_service"]
    )

    computed_at: datetime = Field(..., description="속성 계산/반영 시점 (Computed timestamp)")

    valid_from: date = Field(..., description="적용 시작일 (Valid from date)")

    valid_to: date | None = Field(None, description="적용 종료일 (Valid to date, None means indefinite)")

    batch_period: BatchPeriod = Field(..., description="업데이트 주기 (Update frequency)")

    permission_scope: PermissionScope = Field(..., description="접근 권한 스코프 (Access permission scope)")

    def is_valid_at(self, as_of_date: date) -> bool:
        """Check if attribute is valid at given date.

        Args:
            as_of_date: Date to check validity

        Returns:
            True if attribute is valid at the given date
        """
        if as_of_date < self.valid_from:
            return False
        return not (self.valid_to and as_of_date > self.valid_to)

    def has_access(self, agent_id: str) -> bool:
        """Check if agent has access to this attribute.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent can access this attribute
        """
        return self.permission_scope.is_allowed(agent_id)

    class Config:
        json_schema_extra = {
            "example": {
                "attribute_id": "attr_00001234",
                "user_id": "user_1084756",
                "context_id": "ctx_2025_000457",
                "attribute_key": "전세여부",
                "attribute_value": "Y",
                "source_system": "vertica_db",
                "computed_at": "2025-03-13T18:00:00Z",
                "valid_from": "2024-01-01",
                "valid_to": "2025-12-31",
                "batch_period": "D",
                "permission_scope": {"allowed_agents": ["knowledge_agent"]},
            }
        }


class CustomerProfile(BaseModel):
    """Customer profile with context-dependent attributes.

    Aggregates multiple ProfileAttributes for a user within a context.
    Supports temporal queries and access control.
    """

    user_id: str = Field(..., description="사용자 ID (User ID)")

    context_id: str = Field(..., description="컨텍스트 ID (Context ID)")

    attributes: list[ProfileAttribute] = Field(default_factory=list, description="프로파일 속성 목록 (List of profile attributes)")

    def get_attribute(self, key: str, as_of_date: date | None = None, agent_id: str | None = None) -> ProfileAttribute | None:
        """Get profile attribute by key with optional filters.

        Args:
            key: Attribute key to retrieve
            as_of_date: Optional date for temporal filtering
            agent_id: Optional agent ID for permission check

        Returns:
            ProfileAttribute if found and accessible, None otherwise
        """
        for attr in self.attributes:
            if attr.attribute_key != key:
                continue

            # Check temporal validity
            if as_of_date and not attr.is_valid_at(as_of_date):
                continue

            # Check access permission
            if agent_id and not attr.has_access(agent_id):
                continue

            return attr

        return None

    def get_attribute_value(self, key: str, as_of_date: date | None = None, agent_id: str | None = None, default: Any = None) -> Any:
        """Get attribute value directly.

        Args:
            key: Attribute key
            as_of_date: Optional date for temporal filtering
            agent_id: Optional agent ID for permission check
            default: Default value if not found

        Returns:
            Attribute value or default
        """
        attr = self.get_attribute(key, as_of_date, agent_id)
        return attr.attribute_value if attr else default

    def get_attributes_by_agent(self, agent_id: str) -> list[ProfileAttribute]:
        """Get all attributes accessible to an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of accessible attributes
        """
        return [attr for attr in self.attributes if attr.has_access(agent_id)]

    def to_dict(self, agent_id: str | None = None, as_of_date: date | None = None) -> dict[str, Any]:
        """Convert profile to simple key-value dict.

        Args:
            agent_id: Optional agent ID for filtering
            as_of_date: Optional date for temporal filtering

        Returns:
            Dict of attribute key-value pairs
        """
        result = {}
        for attr in self.attributes:
            # Apply filters
            if as_of_date and not attr.is_valid_at(as_of_date):
                continue
            if agent_id and not attr.has_access(agent_id):
                continue

            result[attr.attribute_key] = attr.attribute_value

        return result

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_1084756",
                "context_id": "ctx_2025_000457",
                "attributes": [
                    {
                        "attribute_id": "attr_00001234",
                        "user_id": "user_1084756",
                        "context_id": "ctx_2025_000457",
                        "attribute_key": "전세여부",
                        "attribute_value": "Y",
                        "source_system": "vertica_db",
                        "computed_at": "2025-03-13T18:00:00Z",
                        "valid_from": "2024-01-01",
                        "valid_to": "2025-12-31",
                        "batch_period": "D",
                        "permission_scope": {"allowed_agents": ["knowledge_agent"]},
                    },
                    {
                        "attribute_id": "attr_00001235",
                        "user_id": "user_1084756",
                        "context_id": "ctx_2025_000457",
                        "attribute_key": "우대고객",
                        "attribute_value": "VIP",
                        "source_system": "crm_api",
                        "computed_at": "2025-01-01T09:00:00Z",
                        "valid_from": "2025-01-01",
                        "valid_to": None,
                        "batch_period": "M",
                        "permission_scope": {"allowed_agents": ["knowledge_agent", "banking_agent"]},
                    },
                ],
            }
        }
