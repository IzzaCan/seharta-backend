from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_goal_contributions_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False
    )
    contributor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    wallet_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="SET NULL"),
        nullable=True
    )
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    contribution_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    goal: Mapped["Goal"] = relationship("Goal", back_populates="contributions")
    contributor: Mapped[Optional["User"]] = relationship("User")
    wallet: Mapped[Optional["Wallet"]] = relationship("Wallet")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")

    @property
    def contributor_name(self) -> Optional[str]:
        return self.contributor.full_name if self.contributor else None

    @property
    def contributor_avatar_url(self) -> Optional[str]:
        return self.contributor.avatar_url if self.contributor else None

    @property
    def wallet_name(self) -> Optional[str]:
        return self.wallet.wallet_name if self.wallet else None
