from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import (
    CreateCategoryRequest,
    UpdateCategoryRequest,
    CategoryResponse,
    CategoryMessageResponse,
)
from app.services.category_service import CategoryService

router = APIRouter()


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    request: CreateCategoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Create a custom category for the current user's family.
    family_id is inferred from the authenticated user.
    """
    service = CategoryService(db)
    return service.create_category(current_user, request)


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    List all categories accessible to the current user's family.
    Returns global categories + family-specific custom categories.
    """
    service = CategoryService(db)
    return service.list_categories(current_user)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    request: UpdateCategoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Update a custom category. Global (default) categories cannot be modified.
    Category type cannot be changed if the category is used in any transaction.
    """
    service = CategoryService(db)
    return service.update_category(current_user, category_id, request)


@router.delete("/{category_id}", response_model=CategoryMessageResponse)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Delete a custom category. Global (default) categories cannot be deleted.
    Categories used in transactions are protected by FK RESTRICT.
    """
    service = CategoryService(db)
    message = service.delete_category(current_user, category_id)
    return CategoryMessageResponse(message=message)
