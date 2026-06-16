from decimal import Decimal
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateWalletRequest(BaseModel):
    """Request schema for creating a wallet. family_id is server-inferred."""
    wallet_name: str = Field(..., min_length=1, max_length=255)
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class UpdateWalletRequest(BaseModel):
    """Request schema for updating a wallet. Balance is never client-modifiable."""
    wallet_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class WalletResponse(BaseModel):
    """Response schema for a single wallet."""
    id: UUID
    family_id: UUID
    wallet_name: str
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletMessageResponse(BaseModel):
    """Generic message response for wallet operations."""
    message: str
