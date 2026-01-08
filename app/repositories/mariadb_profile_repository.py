"""
Session Manager - MariaDB Profile Repository
사용자 프로파일 저장소 (MariaDB)
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.mariadb_models import ProfileAttributeModel
from app.schemas.common import CustomerProfile, ProfileAttribute


class MariaDBProfileRepository:
    """Profile repository with MariaDB backend."""

    def __init__(self, db_session: Session):
        self._db = db_session

    def get_profile_by_user(
        self,
        user_id: str,
        context_id: str | None = None,
        as_of_date: date | None = None,
    ) -> CustomerProfile | None:
        """Get customer profile from MariaDB.

        Args:
            user_id: User identifier
            context_id: Optional context filter
            as_of_date: Optional date for temporal filtering

        Returns:
            CustomerProfile or None if not found
        """
        query = self._db.query(ProfileAttributeModel).filter(ProfileAttributeModel.user_id == user_id)

        if context_id:
            query = query.filter(ProfileAttributeModel.context_id == context_id)

        if as_of_date:
            query = query.filter(
                ProfileAttributeModel.valid_from <= as_of_date,
                (ProfileAttributeModel.valid_to >= as_of_date) | (ProfileAttributeModel.valid_to.is_(None)),
            )

        rows = query.all()

        if not rows:
            return None

        # Convert ORM rows to simple ProfileAttribute (schemas.common)
        attributes: list[ProfileAttribute] = []
        segment: str | None = None

        for row in rows:
            try:
                attr = ProfileAttribute(
                    key=row.attribute_key,
                    value=row.attribute_value,
                    source_system=row.source_system or "",
                    valid_from=(
                        row.valid_from.date().isoformat()
                        if hasattr(row.valid_from, "date")
                        else str(row.valid_from)
                        if row.valid_from is not None
                        else None
                    ),
                    valid_to=(
                        row.valid_to.date().isoformat()
                        if row.valid_to is not None and hasattr(row.valid_to, "date")
                        else str(row.valid_to)
                        if row.valid_to is not None
                        else None
                    ),
                )
                attributes.append(attr)
                if attr.key == "segment":
                    segment = attr.value
            except Exception:  # noqa: S112
                # Skip invalid attributes by design (logging is handled upstream)
                continue

        if not attributes:
            return None

        return CustomerProfile(
            user_id=user_id,
            attributes=attributes,
            segment=segment,
            preferences=None,
        )

    def create_attribute(self, attribute: ProfileAttribute) -> ProfileAttributeModel:
        """Create a new profile attribute.

        Args:
            attribute: ProfileAttribute to create

        Returns:
            Created ProfileAttributeModel
        """
        model = ProfileAttributeModel(
            attribute_id=attribute.attribute_id,
            user_id=attribute.user_id,
            context_id=attribute.context_id,
            attribute_key=attribute.attribute_key,
            attribute_value=attribute.attribute_value,
            source_system=attribute.source_system,
            computed_at=attribute.computed_at,
            valid_from=attribute.valid_from,
            valid_to=attribute.valid_to,
            batch_period=attribute.batch_period.value,
            permission_scope=attribute.permission_scope.model_dump(),
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model

    def update_attribute(self, attribute_id: str, updates: dict[str, Any]) -> ProfileAttributeModel | None:
        """Update a profile attribute.

        Args:
            attribute_id: Attribute ID to update
            updates: Fields to update

        Returns:
            Updated ProfileAttributeModel or None if not found
        """
        model = self._db.query(ProfileAttributeModel).filter(ProfileAttributeModel.attribute_id == attribute_id).first()

        if not model:
            return None

        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)

        self._db.commit()
        self._db.refresh(model)
        return model

    def delete_attribute(self, attribute_id: str) -> bool:
        """Delete a profile attribute.

        Args:
            attribute_id: Attribute ID to delete

        Returns:
            True if deleted, False if not found
        """
        result = self._db.query(ProfileAttributeModel).filter(ProfileAttributeModel.attribute_id == attribute_id).delete()
        self._db.commit()
        return result > 0

    def get_attributes_by_keys(self, user_id: str, attribute_keys: list[str]) -> list[ProfileAttributeModel]:
        """Get multiple attributes by keys.

        Args:
            user_id: User identifier
            attribute_keys: List of attribute keys to fetch

        Returns:
            List of ProfileAttributeModel
        """
        return (
            self._db.query(ProfileAttributeModel)
            .filter(
                ProfileAttributeModel.user_id == user_id,
                ProfileAttributeModel.attribute_key.in_(attribute_keys),
            )
            .all()
        )
