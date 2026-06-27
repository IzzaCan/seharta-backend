from pydantic import BaseModel, ConfigDict, Field, computed_field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

class GoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_amount: Decimal = Field(..., gt=0)
    deadline: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=500)

class GoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_amount: Optional[Decimal] = Field(None, gt=0)
    deadline: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=500)

class GoalContributionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    transaction_type: str = Field(..., pattern="^(DEPOSIT|WITHDRAWAL)$", description="DEPOSIT or WITHDRAWAL")
    wallet_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=500)
    contribution_date: Optional[datetime] = None

class GoalContributionResponse(BaseModel):
    id: UUID
    goal_id: UUID
    contributor_id: Optional[UUID] = None
    wallet_id: Optional[UUID] = None
    transaction_id: Optional[UUID] = None
    amount: Decimal
    transaction_type: str
    note: Optional[str] = None
    contribution_date: datetime
    created_at: datetime
    
    contributor_name: Optional[str] = None
    contributor_avatar_url: Optional[str] = None
    wallet_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class GoalResponse(BaseModel):
    id: UUID
    family_id: UUID
    created_by: Optional[UUID] = None
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    def progress_percentage(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        pct = (float(self.current_amount) / float(self.target_amount)) * 100.0
        return round(min(pct, 100.0), 2)

    @computed_field
    def remaining_amount(self) -> Decimal:
        rem = self.target_amount - self.current_amount
        return rem if rem > 0 else Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)

class GoalDetailResponse(GoalResponse):
    contributions: List[GoalContributionResponse]

class GoalMessageResponse(BaseModel):
    message: str
