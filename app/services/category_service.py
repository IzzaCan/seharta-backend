from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.category import CreateCategoryRequest, UpdateCategoryRequest


class CategoryService:
    """Business logic for category operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_category(self, user: User, data: CreateCategoryRequest) -> Category:
        """Create a custom category for the user's family."""
        # Check duplicate case-insensitively for name and type, within global or this family
        stmt = select(Category).where(
            (Category.family_id.is_(None) | (Category.family_id == user.family_id)),
            func.lower(Category.name) == func.lower(data.name),
            func.lower(Category.type) == func.lower(data.type)
        )
        existing = self.db.execute(stmt).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategori dengan nama dan tipe yang sama sudah ada"
            )

        category = Category(
            family_id=user.family_id,
            name=data.name,
            type=data.type.upper(),
            icon_name=data.icon_name,
            is_default=False
        )
        self.db.add(category)
        try:
            self.db.commit()
            self.db.refresh(category)
            return category
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategori dengan nama dan tipe yang sama sudah ada"
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def list_categories(self, user: User) -> list[Category]:
        """Return global categories and family-specific categories."""
        stmt = select(Category).where(
            (Category.family_id.is_(None) | (Category.family_id == user.family_id)) &
            (Category.name != "Balance Adjustment")
        )
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def update_category(self, user: User, category_id: UUID, data: UpdateCategoryRequest) -> Category:
        """Update a custom category. Blocks mutation on global categories."""
        category = self.db.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori tidak ditemukan"
            )

        # Block mutation on global/default categories
        if category.is_default:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kategori default tidak dapat diubah"
            )

        # Ensure ownership
        if category.family_id != user.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tidak memiliki akses ke kategori ini"
            )

        # Block type change if category is used in transactions
        if data.type is not None and data.type.upper() != category.type.upper():
            txn_count = self.db.execute(
                select(func.count(Transaction.id))
                .where(Transaction.category_id == category_id)
            ).scalar()
            if txn_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tidak dapat mengubah tipe kategori yang sudah digunakan dalam transaksi"
                )

        # Duplicate check if name or type is changing
        new_name = data.name if data.name is not None else category.name
        new_type = data.type.upper() if data.type is not None else category.type

        if data.name is not None or data.type is not None:
            stmt = select(Category).where(
                (Category.family_id.is_(None) | (Category.family_id == user.family_id)),
                func.lower(Category.name) == func.lower(new_name),
                func.lower(Category.type) == func.lower(new_type),
                Category.id != category_id
            )
            existing = self.db.execute(stmt).scalars().first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kategori dengan nama dan tipe yang sama sudah ada"
                )

        if data.name is not None:
            category.name = data.name
        if data.type is not None:
            category.type = data.type.upper()
        if data.icon_name is not None:
            category.icon_name = data.icon_name

        try:
            self.db.commit()
            self.db.refresh(category)
            return category
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategori dengan nama dan tipe yang sama sudah ada"
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_category(self, user: User, category_id: UUID) -> str:
        """Delete a custom category. Blocks deletion of global categories."""
        category = self.db.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori tidak ditemukan"
            )

        if category.is_default:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kategori default tidak dapat dihapus"
            )

        if category.family_id != user.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tidak memiliki akses ke kategori ini"
            )

        try:
            self.db.delete(category)
            self.db.commit()
            return "Kategori berhasil dihapus"
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategori tidak dapat dihapus karena masih digunakan dalam transaksi"
            )
        except Exception as e:
            self.db.rollback()
            raise e
