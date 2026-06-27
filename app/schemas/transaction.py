from decimal import Decimal
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateTransactionRequest(BaseModel):
    """
    Request schema for creating a transaction.
    family_id and transaction_type are NEVER accepted from the client.
    transaction_date is optional; defaults to UTC now in the service layer.
    """
    wallet_id: UUID
    category_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    transaction_date: Optional[datetime] = None


class UpdateTransactionRequest(BaseModel):
    """
    Request schema for updating a transaction.
    family_id and transaction_type are NEVER accepted from the client.
    """
    wallet_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    transaction_date: Optional[datetime] = None


class TransactionResponse(BaseModel):
    """Response schema for a single transaction."""
    id: UUID
    family_id: UUID
    wallet_id: UUID
    user_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    amount: Decimal
    transaction_type: str
    description: Optional[str] = None
    transaction_date: datetime
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """Paginated response for listing transactions."""
    items: list[TransactionResponse]
    total: int
    page: int
    size: int
