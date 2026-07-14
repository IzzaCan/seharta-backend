from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
from app.schemas.user import UserResponse

class CreateFamilyRequest(BaseModel):
    family_name: str

class UpdateFamilyNameRequest(BaseModel):
    family_name: str

class JoinFamilyRequest(BaseModel):
    code: str

class FamilyResponse(BaseModel):
    id: uuid.UUID
    family_name: str
    created_at: datetime
    users: List[UserResponse] = []

    class Config:
        from_attributes = True

class FamilyCreateResponse(BaseModel):
    message: str
    code: str

class FamilyJoinResponse(BaseModel):
    message: str
    family_id: uuid.UUID


class LeaveFamilyResponse(BaseModel):
    message: str

class UnlinkFamilyData(BaseModel):
    pdf_url: str
    total_joint_asset_value: float
    claim_per_person: float
    member_count: int
    settled_at: datetime

class UnlinkFamilyResponse(BaseModel):
    status: str
    message: str
    data: UnlinkFamilyData
