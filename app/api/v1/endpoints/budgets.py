import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.budget_service import BudgetService

router = APIRouter()

class MessageResponse(BaseModel):
    message: str

@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_in: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Create a new monthly budget.
    """
    try:
        return BudgetService.create_budget(db, budget_in, current_user.family_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[BudgetResponse])
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    List all budgets for the family.
    """
    return BudgetService.list_budgets(db, current_user.family_id)

@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Get a specific budget by ID.
    """
    try:
        return BudgetService.get_budget(db, budget_id, current_user.family_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: uuid.UUID,
    budget_in: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Update a budget.
    """
    try:
        return BudgetService.update_budget(db, budget_id, budget_in, current_user.family_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{budget_id}", response_model=MessageResponse)
def delete_budget(
    budget_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
):
    """
    Delete a budget.
    """
    try:
        BudgetService.delete_budget(db, budget_id, current_user.family_id)
        return MessageResponse(message="Budget successfully deleted")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
