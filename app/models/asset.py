from datetime import datetime
import uuid
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

from enum import Enum

class OwnershipType(str, Enum):
    JOINT = "JOINT"
    PERSONAL = "PERSONAL"

class AcquisitionType(str, Enum):
    PURCHASE = "PURCHASE"
    GIFT = "GIFT"
    INHERITANCE = "INHERITANCE"
    PRE_MARITAL = "PRE_MARITAL"


class Asset(Base):
    __tablename__ = "assets"

    __table_args__ = (
        CheckConstraint("purchase_price >= 0", name="ck_assets_purchase_price_positive"),
        CheckConstraint(
            "((UPPER(ownership_type) = 'PERSONAL' AND owner_user_id IS NOT NULL) OR "
            "(UPPER(ownership_type) = 'JOINT' AND owner_user_id IS NULL))",
            name="ck_assets_ownership_rules"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    purchase_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    ownership_type: Mapped[OwnershipType] = mapped_column(
        String(20),
        nullable=False,
        default=OwnershipType.JOINT
    )
    acquisition_type: Mapped[AcquisitionType] = mapped_column(
        String(50),
        nullable=False,
        default=AcquisitionType.PURCHASE
    )
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
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
    family: Mapped["Family"] = relationship("Family")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_user_id])
    category: Mapped["AssetCategory"] = relationship("AssetCategory", back_populates="assets")

    @property
    def creator_name(self) -> Optional[str]:
        return self.creator.full_name if self.creator else None

    @property
    def creator_avatar_url(self) -> Optional[str]:
        return self.creator.avatar_url if self.creator else None

    @property
    def owner_name(self) -> str:
        if self.ownership_type == OwnershipType.JOINT:
            return "Joint Ownership"
        return self.owner.full_name if self.owner else "Unknown"

    @property
    def category_name(self) -> Optional[str]:
        return self.category.name if self.category else None
