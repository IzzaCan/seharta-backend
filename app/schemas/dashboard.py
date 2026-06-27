from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class DashboardWalletResponse(BaseModel):
    """
    Lightweight wallet representation for Dashboard/Home.
    """
    id: UUID
    wallet_name: str
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)

class DashboardTransactionResponse(BaseModel):
    """
    Lightweight transaction representation for Dashboard/Home.
    """
    id: UUID
    amount: Decimal
    transaction_type: str
    description: Optional[str] = None
    transaction_date: datetime
    creator_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None
    wallet_name: Optional[str] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DashboardResponse(BaseModel):
    """
    Single response containing aggregated dashboard data.
    """
    total_balance: Decimal
    income_this_month: Decimal
    expense_this_month: Decimal
    wallets: List[DashboardWalletResponse]
    recent_transactions: List[DashboardTransactionResponse]
