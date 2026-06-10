from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class CreateFamilyRequest(BaseModel):
    family_name: str

class JoinFamilyRequest(BaseModel):
    code: str

class FamilyResponse(BaseModel):
    id: uuid.UUID
    family_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class FamilyCreateResponse(BaseModel):
    message: str
    code: str

class FamilyJoinResponse(BaseModel):
    message: str
    family_id: uuid.UUID
