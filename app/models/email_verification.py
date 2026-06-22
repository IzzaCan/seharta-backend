import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    purpose: Mapped[str] = mapped_column(
        String,
        default="email_verification",
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", backref="email_verifications")
