import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationFilter, NotificationPaginatedResponse
from app.services.notification_service import notification_service

router = APIRouter()

@router.get("/", response_model=NotificationPaginatedResponse)
def get_notifications(
    filter_params: NotificationFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get notifications for the current family.
    Supports filtering by type (ACTIVITY or NOTIFICATION).
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not part of a family")

    notifications, total = notification_service.get_notifications(
        db=db,
        family_id=current_user.family_id,
        filter_params=filter_params
    )
    
    return {
        "items": notifications,
        "total": total,
        "limit": filter_params.limit,
        "offset": filter_params.offset
    }

@router.get("/unread-count", response_model=Dict[str, int])
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the unread count for NOTIFICATION types only.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not part of a family")

    count = notification_service.get_unread_count(db=db, family_id=current_user.family_id)
    return {"unread_count": count}

@router.patch("/read-all", response_model=Dict[str, int])
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Mark all NOTIFICATION types as read for the current family.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not part of a family")

    updated_count = notification_service.mark_all_as_read(db=db, family_id=current_user.family_id)
    return {"updated_count": updated_count}

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Mark a specific notification as read.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not part of a family")

    notification = notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        family_id=current_user.family_id
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    return notification
