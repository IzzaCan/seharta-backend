from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetCreate(BaseModel):
    category_id: UUID
    budget_amount: Decimal = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000)


class BudgetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    budget_amount: Optional[Decimal] = Field(None, gt=0)
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000)


class BudgetResponse(BaseModel):
    id: UUID
    family_id: UUID
    category_id: UUID
    category_name: Optional[str] = None
    
    budget_amount: Decimal
    spent_amount: Decimal = Decimal('0.0')
    remaining_amount: Decimal = Decimal('0.0')
    progress_percentage: float = 0.0
    is_over_budget: bool = False
    
    month: int
    year: int
    
    created_by: UUID
    creator_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
