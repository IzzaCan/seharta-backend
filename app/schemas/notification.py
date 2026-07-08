import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

from app.models.notification import NotificationType, NotificationPriority

class NotificationBase(BaseModel):
    title: str = Field(..., max_length=255)
    message: str = Field(..., max_length=1000)
    type: NotificationType
    priority: Optional[NotificationPriority] = None
    metadata_payload: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    family_id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None

class NotificationUpdate(BaseModel):
    is_read: bool

class NotificationResponse(NotificationBase):
    id: uuid.UUID
    family_id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NotificationFilter(BaseModel):
    type: Optional[NotificationType] = None
    is_read: Optional[bool] = None
    limit: int = 100
    offset: int = 0

class NotificationPaginatedResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int
