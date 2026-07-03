from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AssetCategory(Base):
    __tablename__ = "asset_categories"

    __table_args__ = (
        Index(
            "ix_asset_categories_global_unique",
            "name",
            unique=True,
            postgresql_where=text("family_id IS NULL")
        ),
        Index(
            "ix_asset_categories_family_unique",
            "family_id", "name",
            unique=True,
            postgresql_where=text("family_id IS NOT NULL")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    family_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    family: Mapped[Optional["Family"]] = relationship("Family")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="category")
