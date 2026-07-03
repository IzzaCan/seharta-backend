from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import AssetCategoryResponse
from app.services.asset_service import AssetService

router = APIRouter()

@router.get("/", response_model=List[AssetCategoryResponse])
def get_asset_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Retrieve asset categories (global ones + family specific ones).
    Ordered by defaults first, then alphabetically.
    """
    return AssetService.get_asset_categories(db, current_user.family_id)
