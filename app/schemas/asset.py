from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.asset import OwnershipType, AcquisitionType

class AssetCategoryResponse(BaseModel):
    id: UUID
    family_id: Optional[UUID] = None
    name: str
    icon_name: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetBase(BaseModel):
    category_id: UUID
    asset_name: str
    purchase_price: Decimal = Field(ge=0)
    purchase_date: Optional[datetime] = None
    ownership_type: OwnershipType
    acquisition_type: AcquisitionType
    owner_user_id: Optional[UUID] = None
    location: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    asset_name: Optional[str] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    purchase_date: Optional[datetime] = None
    ownership_type: Optional[OwnershipType] = None
    acquisition_type: Optional[AcquisitionType] = None
    owner_user_id: Optional[UUID] = None
    location: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class AssetResponse(AssetBase):
    id: UUID
    family_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    # Computed fields exposed from ORM properties
    creator_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None
    owner_name: str
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
