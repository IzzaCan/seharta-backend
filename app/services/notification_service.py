import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, and_

from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationCreate, NotificationFilter

class NotificationService:
    
    @staticmethod
    def create_notification(db: Session, obj_in: NotificationCreate) -> Notification:
        db_obj = Notification(
            family_id=obj_in.family_id,
            actor_user_id=obj_in.actor_user_id,
            type=obj_in.type.value,
            title=obj_in.title,
            message=obj_in.message,
            priority=obj_in.priority.value if obj_in.priority else None,
            metadata_payload=obj_in.metadata_payload
            # is_read defaults to False naturally for both types
        )
        db.add(db_obj)
        db.flush() # Ensure the object is pushed to the session without prematurely committing the parent transaction
        return db_obj

    @staticmethod
    def get_notifications(
        db: Session,
        family_id: uuid.UUID,
        filter_params: NotificationFilter
    ) -> Tuple[List[Notification], int]:
        
        query = select(Notification).where(Notification.family_id == family_id)
        
        if filter_params.type:
            query = query.where(Notification.type == filter_params.type.value)
        if filter_params.is_read is not None:
            query = query.where(Notification.is_read == filter_params.is_read)
            
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar_one()
        
        query = query.order_by(Notification.created_at.desc())
        query = query.offset(filter_params.offset).limit(filter_params.limit)
        
        result = db.execute(query).scalars().all()
        return list(result), total

    @staticmethod
    def get_unread_count(db: Session, family_id: uuid.UUID) -> int:
        """
        CRITICAL RULE: Only counts NOTIFICATION types where is_read == False.
        ACTIVITY records are ignored.
        """
        query = select(func.count(Notification.id)).where(
            and_(
                Notification.family_id == family_id,
                Notification.type == NotificationType.NOTIFICATION.value,
                Notification.is_read == False
            )
        )
        return db.execute(query).scalar_one()

    @staticmethod
    def mark_as_read(db: Session, notification_id: uuid.UUID, family_id: uuid.UUID) -> Optional[Notification]:
        """
        Mark a specific notification as read, ensuring it belongs to the family.
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.family_id == family_id
                )
            )
            .values(is_read=True)
            .returning(Notification)
        )
        result = db.execute(stmt).scalar_one_or_none()
        if result:
            db.commit()
            # In sqlalchemy 2.0 with returning, we might not need refresh, but just in case
        return result

    @staticmethod
    def mark_all_as_read(db: Session, family_id: uuid.UUID) -> int:
        """
        Bulk update is_read = True strictly where family_id matches,
        type == NOTIFICATION, and is_read == False.
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.family_id == family_id,
                    Notification.type == NotificationType.NOTIFICATION.value,
                    Notification.is_read == False
                )
            )
            .values(is_read=True)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount

notification_service = NotificationService()
