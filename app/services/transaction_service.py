from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.models.category import Category
from app.models.user import User
from app.schemas.transaction import CreateTransactionRequest, UpdateTransactionRequest


class TransactionService:
    """Business logic for transaction operations with pessimistic locking."""

    def __init__(self, db: Session):
        self.db = db

    # ── Shared helpers ──────────────────────────────────────────

    def _get_category_for_user(self, user: User, category_id: UUID) -> Category:
        """Fetch and validate category accessibility (global or same family)."""
        category = self.db.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori tidak ditemukan"
            )

        # Category must be global (family_id is None) or belong to user's family
        if category.family_id is not None and category.family_id != user.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tidak memiliki akses ke kategori ini"
            )

        return category

    def _lock_wallet(self, wallet_id: UUID, family_id: UUID) -> Wallet:
        """Acquire a row lock on a wallet and validate ownership + active status."""
        wallet = self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.family_id == family_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet tidak ditemukan"
            )

        if not wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet tidak aktif"
            )

        return wallet

    def _lock_wallets_ordered(self, wallet_ids: list[UUID], family_id: UUID) -> dict[UUID, Wallet]:
        """
        Lock multiple wallets in ascending ID order to prevent deadlocks.
        Returns a dict mapping wallet_id -> Wallet.
        """
        sorted_ids = sorted(wallet_ids)
        wallets = {}
        for wid in sorted_ids:
            wallets[wid] = self._lock_wallet(wid, family_id)
        return wallets

    def _apply_balance_change(self, wallet: Wallet, amount: Decimal, transaction_type: str) -> None:
        """Apply income/expense to wallet balance. Raises 400 if balance < 0."""
        current_balance = Decimal(str(wallet.balance))
        if transaction_type == "income":
            wallet.balance = current_balance + amount
        else:
            new_balance = current_balance - amount
            if new_balance < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Saldo tidak mencukupi"
                )
            wallet.balance = new_balance

    def _reverse_balance_change(self, wallet: Wallet, amount: Decimal, transaction_type: str) -> None:
        """Reverse a previous transaction effect. Raises 400 if balance < 0."""
        current_balance = Decimal(str(wallet.balance))
        if transaction_type == "income":
            # Reversing income = subtract
            new_balance = current_balance - amount
            if new_balance < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Saldo tidak mencukupi"
                )
            wallet.balance = new_balance
        else:
            # Reversing expense = add back
            wallet.balance = current_balance + amount

    # ── CRUD operations ─────────────────────────────────────────

    def create_transaction(self, user: User, data: CreateTransactionRequest) -> Transaction:
        """
        Create a transaction. Infers family_id from user and transaction_type
        from category.type. Locks wallet and adjusts balance atomically.
        """
        category = self._get_category_for_user(user, data.category_id)
        wallet = self._lock_wallet(data.wallet_id, user.family_id)

        amount = Decimal(str(data.amount))
        transaction_type = category.type

        # Apply balance change
        self._apply_balance_change(wallet, amount, transaction_type)

        # Resolve transaction_date
        txn_date = data.transaction_date if data.transaction_date else datetime.now(timezone.utc)

        txn = Transaction(
            family_id=user.family_id,
            wallet_id=data.wallet_id,
            user_id=user.id,
            category_id=data.category_id,
            amount=amount,
            transaction_type=transaction_type,
            description=data.description,
            transaction_date=txn_date
        )
        self.db.add(txn)

        try:
            self.db.commit()
            self.db.refresh(txn)
            return txn
        except Exception as e:
            self.db.rollback()
            raise e

    def list_transactions(
        self,
        user: User,
        page: int = 1,
        size: int = 20,
        wallet_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ):
        """Paginated + filtered transaction listing within the family scope."""
        stmt = select(Transaction).where(Transaction.family_id == user.family_id)

        if wallet_id:
            stmt = stmt.where(Transaction.wallet_id == wallet_id)
        if category_id:
            stmt = stmt.where(Transaction.category_id == category_id)
        if transaction_type:
            stmt = stmt.where(Transaction.transaction_type == transaction_type)
        if date_from:
            stmt = stmt.where(Transaction.transaction_date >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.transaction_date <= date_to)

        # Total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar()

        # Paginated results
        offset = (page - 1) * size
        stmt = stmt.order_by(Transaction.transaction_date.desc()).offset(offset).limit(size)
        items = list(self.db.execute(stmt).scalars().all())

        return {"items": items, "total": total, "page": page, "size": size}

    def update_transaction(self, user: User, txn_id: UUID, data: UpdateTransactionRequest) -> Transaction:
        """
        Update a transaction using Complete Reversal Before Adjust.
        Locks wallets in ascending ID order when wallet changes.
        """
        txn = self.db.execute(
            select(Transaction)
            .where(Transaction.id == txn_id)
            .where(Transaction.family_id == user.family_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaksi tidak ditemukan"
            )

        # Determine new values (or keep old)
        new_wallet_id = data.wallet_id if data.wallet_id is not None else txn.wallet_id
        new_category_id = data.category_id if data.category_id is not None else txn.category_id
        new_amount = Decimal(str(data.amount)) if data.amount is not None else Decimal(str(txn.amount))
        new_description = data.description if data.description is not None else txn.description
        new_txn_date = data.transaction_date if data.transaction_date is not None else txn.transaction_date

        # Resolve new category and transaction_type
        if data.category_id is not None:
            new_category = self._get_category_for_user(user, new_category_id)
            new_txn_type = new_category.type
        else:
            new_txn_type = txn.transaction_type

        old_wallet_id = txn.wallet_id
        old_amount = Decimal(str(txn.amount))
        old_txn_type = txn.transaction_type

        # ── Lock wallets ─────────────────────────────────────
        wallet_ids_to_lock = list({old_wallet_id, new_wallet_id})
        wallets = self._lock_wallets_ordered(wallet_ids_to_lock, user.family_id)

        old_wallet = wallets[old_wallet_id]
        new_wallet = wallets[new_wallet_id]

        # ── Step 1: Complete reversal of old effect ──────────
        self._reverse_balance_change(old_wallet, old_amount, old_txn_type)

        # ── Step 2: Apply new effect ─────────────────────────
        try:
            self._apply_balance_change(new_wallet, new_amount, new_txn_type)
        except HTTPException:
            # Rollback the reversal too
            self.db.rollback()
            raise

        # ── Step 3: Update transaction fields ────────────────
        txn.wallet_id = new_wallet_id
        txn.category_id = new_category_id
        txn.amount = new_amount
        txn.transaction_type = new_txn_type
        txn.description = new_description
        txn.transaction_date = new_txn_date

        try:
            self.db.commit()
            self.db.refresh(txn)
            return txn
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_transaction(self, user: User, txn_id: UUID) -> str:
        """Delete a transaction and reverse its balance effect."""
        txn = self.db.execute(
            select(Transaction)
            .where(Transaction.id == txn_id)
            .where(Transaction.family_id == user.family_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaksi tidak ditemukan"
            )

        wallet = self._lock_wallet(txn.wallet_id, user.family_id)
        amount = Decimal(str(txn.amount))

        # Reverse the effect
        self._reverse_balance_change(wallet, amount, txn.transaction_type)

        try:
            self.db.delete(txn)
            self.db.commit()
            return "Transaksi berhasil dihapus"
        except Exception as e:
            self.db.rollback()
            raise e
