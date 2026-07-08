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
    """Request schema for updating a wallet. Balance is never client-modifiable except for initial setup."""
    wallet_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    initial_balance: Optional[Decimal] = Field(None, ge=0, description="Initial balance. Can only be set once before the wallet has any transaction history.")


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


class AdjustBalanceRequest(BaseModel):
    """Payload for adjusting operational wallet balances securely."""
    target_balance: Decimal = Field(..., ge=0, description="The real-world cash balance of the wallet.")
