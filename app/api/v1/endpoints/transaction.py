from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transaction import (
    CreateTransactionRequest,
    UpdateTransactionRequest,
    TransactionResponse,
    TransactionListResponse,
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    request: CreateTransactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Create a new transaction.
    family_id and transaction_type are inferred from the backend.
    """
    service = TransactionService(db)
    return service.create_transaction(current_user, request)


@router.get("/", response_model=TransactionListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    wallet_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    List transactions for the current user's family with pagination and filters.
    """
    service = TransactionService(db)
    return service.list_transactions(
        current_user,
        page=page,
        size=size,
        wallet_id=wallet_id,
        category_id=category_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
    )


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    request: UpdateTransactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Update an existing transaction.
    Uses complete reversal before adjust for balance integrity.
    family_id and transaction_type are never accepted from the client.
    """
    service = TransactionService(db)
    return service.update_transaction(current_user, transaction_id, request)


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Delete a transaction and reverse its balance effect.
    """
    service = TransactionService(db)
    message = service.delete_transaction(current_user, transaction_id)
    return {"message": message}
