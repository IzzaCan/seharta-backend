import uuid
from typing import List

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, nulls_last

from app.models.asset import Asset, OwnershipType, AcquisitionType
from app.models.asset_category import AssetCategory
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetUpdate

class AssetService:

    @staticmethod
    def get_asset_categories(db: Session, family_id: uuid.UUID) -> List[AssetCategory]:
        """
        Fetch all categories where family_id IS NULL OR family_id == current_family_id.
        Ordered by is_default DESC, name ASC.
        """
        stmt = (
            select(AssetCategory)
            .where((AssetCategory.family_id.is_(None)) | (AssetCategory.family_id == family_id))
            .order_by(AssetCategory.is_default.desc(), AssetCategory.name.asc())
        )
        return db.execute(stmt).scalars().all()

    @staticmethod
    def _validate_category(db: Session, category_id: uuid.UUID, family_id: uuid.UUID) -> None:
        """
        Validate that the category belongs either to a global AssetCategory (family_id IS NULL) 
        or to the authenticated user's family.
        """
        category = db.execute(select(AssetCategory).where(AssetCategory.id == category_id)).scalar_one_or_none()
        if not category:
            raise ValueError("Category not found")
        if category.family_id is not None and category.family_id != family_id:
            raise ValueError("Invalid category selected")

    @staticmethod
    def _validate_ownership(db: Session, ownership_type: OwnershipType, owner_user_id: uuid.UUID | None, family_id: uuid.UUID) -> None:
        """
        Validate ownership rules:
        - PERSONAL requires owner_user_id which must belong to the same family.
        - JOINT requires owner_user_id to be NULL.
        """
        if ownership_type == OwnershipType.PERSONAL:
            if not owner_user_id:
                raise ValueError("owner_user_id is required for PERSONAL ownership")
            
            # Validate owner_user_id belongs to the same family
            owner = db.execute(select(User).where(User.id == owner_user_id)).scalar_one_or_none()
            if not owner:
                raise ValueError("Owner user not found")
            if owner.family_id != family_id:
                raise ValueError("Owner must belong to the same family")
        else: # JOINT
            if owner_user_id is not None:
                raise ValueError("owner_user_id must be null for JOINT ownership")

    @staticmethod
    def create_asset(db: Session, asset_data: AssetCreate, family_id: uuid.UUID, user_id: uuid.UUID) -> Asset:
        AssetService._validate_category(db, asset_data.category_id, family_id)
        AssetService._validate_ownership(db, asset_data.ownership_type, asset_data.owner_user_id, family_id)
             
        new_asset = Asset(
            family_id=family_id,
            created_by=user_id,
            **asset_data.model_dump()
        )
        
        db.add(new_asset)
        db.flush()
        
        from app.services.notification_service import NotificationService
        from app.schemas.notification import NotificationCreate
        from app.models.notification import NotificationType
        NotificationService.create_notification(
            db,
            NotificationCreate(
                title="Aset Dibuat",
                message=f"Aset '{new_asset.asset_name}' telah ditambahkan.",
                type=NotificationType.ACTIVITY,
                family_id=family_id,
                actor_user_id=user_id,
                metadata_payload={
                    "asset_id": str(new_asset.id),
                    "asset_name": new_asset.asset_name,
                    "category_id": str(new_asset.category_id),
                    "ownership_type": new_asset.ownership_type,
                    "purchase_price": float(new_asset.purchase_price)
                }
            )
        )
        
        db.commit()
        db.refresh(new_asset)
        return new_asset

    @staticmethod
    def get_family_assets(db: Session, family_id: uuid.UUID) -> List[Asset]:
        stmt = (
            select(Asset)
            .options(
                joinedload(Asset.creator),
                joinedload(Asset.owner),
                joinedload(Asset.category)
            )
            .where(Asset.family_id == family_id)
            .order_by(nulls_last(Asset.purchase_date.desc()), Asset.created_at.desc())
        )
        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_asset_detail(db: Session, asset_id: uuid.UUID, family_id: uuid.UUID) -> Asset:
        stmt = (
            select(Asset)
            .options(
                joinedload(Asset.creator),
                joinedload(Asset.owner),
                joinedload(Asset.category)
            )
            .where(Asset.id == asset_id, Asset.family_id == family_id)
        )
        asset = db.execute(stmt).scalar_one_or_none()
        if not asset:
            raise ValueError("Asset not found")
        return asset

    @staticmethod
    def update_asset(db: Session, asset_id: uuid.UUID, asset_data: AssetUpdate, family_id: uuid.UUID) -> Asset:
        asset = AssetService.get_asset_detail(db, asset_id, family_id)
        
        update_dict = asset_data.model_dump(exclude_unset=True)
        
        # Check category change
        if "category_id" in update_dict:
            AssetService._validate_category(db, update_dict["category_id"], family_id)
            
        # Check ownership change
        if "ownership_type" in update_dict or "owner_user_id" in update_dict:
            new_ownership = update_dict.get("ownership_type", asset.ownership_type)
            if new_ownership == OwnershipType.JOINT:
                new_owner_id = None
                update_dict["owner_user_id"] = None
            else:
                new_owner_id = update_dict.get("owner_user_id", asset.owner_user_id)
            
            AssetService._validate_ownership(db, new_ownership, new_owner_id, family_id)
                  
        for key, value in update_dict.items():
            setattr(asset, key, value)
                
        db.flush()
        
        if update_dict:
            changes = []
            if "asset_name" in update_dict: changes.append(f"nama menjadi '{asset.asset_name}'")
            if "purchase_price" in update_dict: changes.append(f"nilai aset menjadi {float(asset.purchase_price):,.2f}")
            if "ownership_type" in update_dict: changes.append(f"kepemilikan menjadi {asset.ownership_type}")
            
            if changes:
                from app.services.notification_service import NotificationService
                from app.schemas.notification import NotificationCreate
                from app.models.notification import NotificationType
                # In update_asset we don't have user_id, so we use creator as fallback
                NotificationService.create_notification(
                    db,
                    NotificationCreate(
                        title="Aset Diperbarui",
                        message=f"Aset '{asset.asset_name}' diperbarui: " + ", ".join(changes) + ".",
                        type=NotificationType.ACTIVITY,
                        family_id=family_id,
                        actor_user_id=asset.created_by,
                        metadata_payload={
                            "asset_id": str(asset.id),
                            "asset_name": asset.asset_name,
                            "category_id": str(asset.category_id),
                            "ownership_type": asset.ownership_type,
                            "purchase_price": float(asset.purchase_price)
                        }
                    )
                )

        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete_asset(db: Session, asset_id: uuid.UUID, family_id: uuid.UUID) -> None:
        asset = AssetService.get_asset_detail(db, asset_id, family_id)
        
        asset_name = asset.asset_name
        creator_id = asset.created_by
        
        db.delete(asset)
        db.flush()
        
        from app.services.notification_service import NotificationService
        from app.schemas.notification import NotificationCreate
        from app.models.notification import NotificationType
        NotificationService.create_notification(
            db,
            NotificationCreate(
                title="Aset Dihapus",
                message=f"Aset '{asset_name}' telah dihapus.",
                type=NotificationType.ACTIVITY,
                family_id=family_id,
                actor_user_id=creator_id,
                metadata_payload={
                    "asset_id": str(asset_id),
                    "asset_name": asset_name
                }
            )
        )
        
        db.commit()
