from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    family_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    ai_insight: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    insight_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="family")
    pairing_codes: Mapped[list["PairingCode"]] = relationship("PairingCode", back_populates="family", cascade="all, delete-orphan")
    wallets: Mapped[list["Wallet"]] = relationship("Wallet", back_populates="family", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="family", cascade="all, delete-orphan")


class PairingCode(Base):
    __tablename__ = "pairing_codes"

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
    code: Mapped[str] = mapped_column(String(6), unique=True, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship
    family: Mapped["Family"] = relationship("Family", back_populates="pairing_codes")
