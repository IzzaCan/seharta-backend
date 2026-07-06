from datetime import datetime
import uuid
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Numeric, CheckConstraint, UniqueConstraint, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class Budget(Base):
    __tablename__ = "budgets"

    __table_args__ = (
        CheckConstraint("budget_amount > 0", name="ck_budgets_amount_positive"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_budgets_month_valid"),
        CheckConstraint("year >= 2000", name="ck_budgets_year_valid"),
        UniqueConstraint("family_id", "category_id", "month", "year", name="uq_family_category_month_year"),
        Index("ix_budgets_family_month_year", "family_id", "month", "year"),
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
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    budget_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    month: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    year: Mapped[int] = mapped_column(
        Integer,
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
    family: Mapped["Family"] = relationship("Family", back_populates="budgets")
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")
    creator: Mapped["User"] = relationship("User", back_populates="budgets")

    @property
    def category_name(self) -> Optional[str]:
        return self.category.name if self.category else None

    @property
    def creator_name(self) -> Optional[str]:
        return self.creator.full_name if self.creator else None

    @property
    def creator_avatar_url(self) -> Optional[str]:
        return self.creator.avatar_url if self.creator else None
