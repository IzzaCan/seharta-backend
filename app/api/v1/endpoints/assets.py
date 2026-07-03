from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse, MessageResponse
from app.services.asset_service import AssetService

router = APIRouter()

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Create a new asset for the family.
    """
    try:
        return AssetService.create_asset(db, asset_in, current_user.family_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[AssetResponse])
def get_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Get all assets belonging to the user's family.
    """
    return AssetService.get_family_assets(db, current_user.family_id)

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Get asset details by ID.
    """
    try:
        return AssetService.get_asset_detail(db, asset_id, current_user.family_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: uuid.UUID,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Update an existing asset.
    """
    try:
        return AssetService.update_asset(db, asset_id, asset_in, current_user.family_id)
    except ValueError as e:
        if str(e) == "Asset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{asset_id}", response_model=MessageResponse)
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Delete an asset.
    """
    try:
        AssetService.delete_asset(db, asset_id, current_user.family_id)
        return MessageResponse(message="Asset successfully deleted")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
