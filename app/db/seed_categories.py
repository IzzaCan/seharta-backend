"""
Idempotent seeder for global (default) categories.
Uses INSERT ... ON CONFLICT DO NOTHING equivalent via SQLAlchemy.
"""
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.category import Category


GLOBAL_CATEGORIES = [
    # Income
    {"name": "Gaji", "type": "income"},
    {"name": "Hadiah", "type": "income"},
    {"name": "Investasi", "type": "income"},
    # Expense
    {"name": "Makanan", "type": "expense"},
    {"name": "Transportasi", "type": "expense"},
    {"name": "Tagihan", "type": "expense"},
    {"name": "Belanja", "type": "expense"},
    {"name": "Hiburan", "type": "expense"},
]


def seed_global_categories(db: Session) -> None:
    """
    Seed global categories idempotently.
    Checks for existing (name, type) pairs with family_id IS NULL
    and only inserts missing ones.
    """
    for cat_data in GLOBAL_CATEGORIES:
        existing = db.execute(
            select(Category).where(
                Category.family_id.is_(None),
                Category.name == cat_data["name"],
                Category.type == cat_data["type"],
            )
        ).scalar_one_or_none()

        if not existing:
            category = Category(
                id=uuid.uuid4(),
                family_id=None,
                name=cat_data["name"],
                type=cat_data["type"],
                icon_name=None,
                is_default=True,
            )
            db.add(category)

    db.commit()
