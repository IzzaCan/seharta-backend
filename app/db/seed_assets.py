"""
Idempotent seeder for global (default) asset categories.
Uses INSERT ... ON CONFLICT DO NOTHING equivalent via SQLAlchemy.
"""
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.asset_category import AssetCategory


GLOBAL_ASSET_CATEGORIES = [
    {"name": "Property", "icon_name": "home"},
    {"name": "Vehicle", "icon_name": "directions_car"},
    {"name": "Electronics", "icon_name": "devices"},
    {"name": "Jewelry", "icon_name": "watch"},
    {"name": "Gold & Precious Metals", "icon_name": "monetization_on"},
    {"name": "Furniture", "icon_name": "chair"},
    {"name": "Valuable Documents", "icon_name": "description"},
    {"name": "Other", "icon_name": "category"},
]


def seed_global_asset_categories(db: Session) -> None:
    """
    Seed global asset categories idempotently.
    Checks for existing name with family_id IS NULL
    and only inserts missing ones.
    """
    for cat_data in GLOBAL_ASSET_CATEGORIES:
        existing = db.execute(
            select(AssetCategory).where(
                AssetCategory.family_id.is_(None),
                AssetCategory.name == cat_data["name"]
            )
        ).scalar_one_or_none()

        if not existing:
            category = AssetCategory(
                id=uuid.uuid4(),
                family_id=None,
                name=cat_data["name"],
                icon_name=cat_data["icon_name"],
                is_default=True,
            )
            db.add(category)

    db.commit()
