from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryRequest(BaseModel):
    """Request schema for creating a category. family_id is server-inferred, is_default forced False."""
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal["income", "expense"]
    icon_name: Optional[str] = Field(None, max_length=100)


class UpdateCategoryRequest(BaseModel):
    """Request schema for updating a custom category. type change is blocked if used in transactions."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[Literal["income", "expense"]] = None
    icon_name: Optional[str] = Field(None, max_length=100)


class CategoryResponse(BaseModel):
    """Response schema for a single category."""
    id: UUID
    family_id: Optional[UUID] = None
    name: str
    type: str
    icon_name: Optional[str] = None
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryMessageResponse(BaseModel):
    """Generic message response for category operations."""
    message: str
