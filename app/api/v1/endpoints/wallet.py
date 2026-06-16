from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.wallet import (
    CreateWalletRequest,
    UpdateWalletRequest,
    WalletResponse,
    WalletMessageResponse,
)
from app.services.wallet_service import WalletService

router = APIRouter()


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
def create_wallet(
    request: CreateWalletRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Create a new wallet for the current user's family.
    """
    service = WalletService(db)
    return service.create_wallet(current_user, request)


@router.get("/", response_model=list[WalletResponse])
def list_wallets(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    List all wallets for the current user's family.
    Optionally include inactive wallets.
    """
    service = WalletService(db)
    return service.list_wallets(current_user, include_inactive)


@router.put("/{wallet_id}", response_model=WalletResponse)
def update_wallet(
    wallet_id: UUID,
    request: UpdateWalletRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Update a wallet's name or active status.
    Balance cannot be modified directly.
    """
    service = WalletService(db)
    return service.update_wallet(current_user, wallet_id, request)


@router.delete("/{wallet_id}", response_model=WalletMessageResponse)
def delete_wallet(
    wallet_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
) -> Any:
    """
    Delete a wallet. Hard-deletes if no transactions exist,
    otherwise soft-deletes (sets is_active=False).
    """
    service = WalletService(db)
    message = service.delete_wallet(current_user, wallet_id)
    return WalletMessageResponse(message=message)
