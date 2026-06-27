from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalDetailResponse,
    GoalContributionCreate,
    GoalContributionResponse,
    GoalMessageResponse
)
from app.services.goal_service import GoalService

router = APIRouter()

@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    request: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Create a new goal for the family."""
    service = GoalService(db)
    return service.create_goal(current_user, request)

@router.get("/", response_model=List[GoalResponse])
def get_family_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """List all goals for the family."""
    service = GoalService(db)
    return service.get_family_goals(current_user)

@router.get("/{goal_id}", response_model=GoalDetailResponse)
def get_goal_detail(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Get goal detail including contribution history."""
    service = GoalService(db)
    return service.get_goal_detail(current_user, goal_id)

@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: UUID,
    request: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Update goal attributes."""
    service = GoalService(db)
    return service.update_goal(current_user, goal_id, request)

@router.post("/{goal_id}/contribute", response_model=GoalContributionResponse)
def add_contribution(
    goal_id: UUID,
    request: GoalContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Add a deposit or withdrawal contribution to a goal."""
    service = GoalService(db)
    return service.add_contribution(current_user, goal_id, request)

@router.delete("/{goal_id}", response_model=GoalMessageResponse)
def delete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """Delete a goal and rollback all associated wallet transactions."""
    service = GoalService(db)
    msg = service.delete_goal(current_user, goal_id)
    return GoalMessageResponse(message=msg)
