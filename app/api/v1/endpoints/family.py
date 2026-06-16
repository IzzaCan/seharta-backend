from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.family import (
    CreateFamilyRequest,
    JoinFamilyRequest,
    FamilyCreateResponse,
    FamilyJoinResponse,
    FamilyResponse,
    UpdateFamilyNameRequest,
    LeaveFamilyResponse
)
from app.services.family_service import FamilyService

router = APIRouter()

@router.post("/create", response_model=FamilyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_family(
    request: CreateFamilyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new family and generate a 6-digit pairing code."""
    pin_code = FamilyService(db).create_family(current_user=current_user, request=request)
    return FamilyCreateResponse(message="Keluarga berhasil dibuat", code=pin_code)

@router.post("/join", response_model=FamilyJoinResponse, status_code=status.HTTP_200_OK)
def join_family(
    request: JoinFamilyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Join an existing family using a 6-digit pairing code."""
    family_id = FamilyService(db).join_family(current_user=current_user, request=request)
    return FamilyJoinResponse(message="Berhasil bergabung dengan dompet bersama!", family_id=family_id)


@router.get("/info", response_model=FamilyResponse)
def get_family_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Get the family information of the current user."""
    return FamilyService(db).get_family_info(current_user=current_user)

@router.put("/name", response_model=FamilyResponse)
def update_family_name(
    request: UpdateFamilyNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Update the family name of the current user's family."""
    return FamilyService(db).update_family_name(current_user=current_user, request=request)


@router.post("/leave", response_model=LeaveFamilyResponse)
def leave_family(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Leave the current family."""
    FamilyService(db).leave_family(current_user=current_user)
    return LeaveFamilyResponse(message="Successfully left the family")
