from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, exists

from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.wallet import CreateWalletRequest, UpdateWalletRequest, AdjustBalanceRequest
from app.models.notification import NotificationType
from app.schemas.notification import NotificationCreate
from app.services.notification_service import notification_service


class WalletService:
    """Business logic for wallet operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_wallet(self, user: User, data: CreateWalletRequest) -> Wallet:
        """Create a new wallet for the user's family."""
        wallet = Wallet(
            family_id=user.family_id,
            wallet_name=data.wallet_name,
            balance=data.initial_balance,
            is_active=True
        )
        self.db.add(wallet)
        try:
            self.db.flush()
            notification_service.create_notification(
                self.db,
                NotificationCreate(
                    title="Dompet Baru",
                    message=f"Dompet '{wallet.wallet_name}' telah dibuat.",
                    type=NotificationType.ACTIVITY,
                    family_id=user.family_id,
                    actor_user_id=user.id,
                    metadata_payload={
                        "wallet_id": str(wallet.id),
                        "wallet_name": wallet.wallet_name,
                        "balance": float(wallet.balance)
                    }
                )
            )
            self.db.commit()
            self.db.refresh(wallet)
            return wallet
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nama wallet sudah digunakan dalam keluarga ini"
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def create_bootstrap_wallet(self, family_id: UUID) -> Wallet:
        """Create the default 'Cash' wallet when a family is created."""
        wallet = Wallet(
            family_id=family_id,
            wallet_name="Cash",
            balance=Decimal("0.00"),
            is_active=True
        )
        self.db.add(wallet)

        return wallet

    def list_wallets(self, user: User, include_inactive: bool = False) -> list[Wallet]:
        """List all wallets for the user's family."""
        stmt = select(Wallet).where(Wallet.family_id == user.family_id)
        if not include_inactive:
            stmt = stmt.where(Wallet.is_active == True)
        stmt = stmt.order_by(Wallet.created_at)
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def update_wallet(self, user: User, wallet_id: UUID, data: UpdateWalletRequest) -> Wallet:
        """Update wallet name and/or is_active. Never modifies balance."""
        wallet = self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.family_id == user.family_id)
        ).scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet tidak ditemukan"
            )

        # If deactivating, enforce minimum active wallet guard
        if data.is_active is False and wallet.is_active is True:
            active_count = self.db.execute(
                select(func.count(Wallet.id))
                .where(Wallet.family_id == user.family_id)
                .where(Wallet.is_active == True)
            ).scalar()
            if active_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Keluarga harus memiliki minimal satu wallet aktif"
                )
            if wallet.balance > Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tidak dapat menonaktifkan dompet yang masih memiliki saldo"
                )

        old_wallet_name = wallet.wallet_name
        old_is_active = wallet.is_active
        old_balance = wallet.balance

        if data.initial_balance is not None:
            if Decimal(str(wallet.balance)) != Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Saldo awal hanya dapat diatur jika dompet saat ini memiliki saldo 0."
                )

            has_transactions = self.db.execute(
                select(exists().where(Transaction.wallet_id == wallet_id))
            ).scalar()

            if has_transactions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Saldo awal tidak dapat diubah karena dompet ini sudah memiliki riwayat transaksi."
                )
            
            wallet.balance = data.initial_balance

        if data.wallet_name is not None:
            wallet.wallet_name = data.wallet_name
        if data.is_active is not None:
            wallet.is_active = data.is_active

        changes = []
        if data.wallet_name is not None and data.wallet_name != old_wallet_name:
            changes.append(f"nama menjadi '{data.wallet_name}'")
        if data.initial_balance is not None:
            changes.append(f"saldo awal menjadi {data.initial_balance}")
        if data.is_active is not None and data.is_active != old_is_active:
            status_str = "diaktifkan" if data.is_active else "dinonaktifkan"
            changes.append(f"status {status_str}")

        try:
            self.db.flush()
            if changes:
                msg = f"Dompet '{old_wallet_name}' diperbarui: " + ", ".join(changes) + "."
                notification_service.create_notification(
                    self.db,
                    NotificationCreate(
                        title="Dompet Diperbarui",
                        message=msg,
                        type=NotificationType.ACTIVITY,
                        family_id=user.family_id,
                        actor_user_id=user.id,
                        metadata_payload={
                            "wallet_id": str(wallet.id),
                            "wallet_name": wallet.wallet_name,
                            "balance": float(wallet.balance)
                        }
                    )
                )
            self.db.commit()
            self.db.refresh(wallet)
            return wallet
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nama wallet sudah digunakan dalam keluarga ini"
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_wallet(self, user: User, wallet_id: UUID) -> str:
        """Delete or soft-delete a wallet based on transaction history."""
        wallet = self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.family_id == user.family_id)
        ).scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet tidak ditemukan"
            )

        # Minimum active wallet guard
        if wallet.is_active:
            active_count = self.db.execute(
                select(func.count(Wallet.id))
                .where(Wallet.family_id == user.family_id)
                .where(Wallet.is_active == True)
            ).scalar()
            if active_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Keluarga harus memiliki minimal satu wallet aktif"
                )

        # Check for existing transactions
        txn_count = self.db.execute(
            select(func.count(Transaction.id))
            .where(Transaction.wallet_id == wallet_id)
        ).scalar()

        try:
            if txn_count == 0:
                # Hard delete — no transaction history
                self.db.delete(wallet)
                self.db.flush()
                notification_service.create_notification(
                    self.db,
                    NotificationCreate(
                        title="Dompet Dihapus",
                        message=f"Dompet '{wallet.wallet_name}' telah dihapus permanen.",
                        type=NotificationType.ACTIVITY,
                        family_id=user.family_id,
                        actor_user_id=user.id,
                        metadata_payload={"wallet_id": str(wallet.id), "wallet_name": wallet.wallet_name}
                    )
                )
                self.db.commit()
                return "Wallet berhasil dihapus"
            else:
                # Soft delete — preserve transaction history
                if wallet.balance > Decimal("0.00"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Tidak dapat menonaktifkan dompet yang masih memiliki saldo"
                    )
                wallet.is_active = False
                self.db.flush()
                notification_service.create_notification(
                    self.db,
                    NotificationCreate(
                        title="Dompet Dinonaktifkan",
                        message=f"Dompet '{wallet.wallet_name}' telah dinonaktifkan.",
                        type=NotificationType.ACTIVITY,
                        family_id=user.family_id,
                        actor_user_id=user.id,
                        metadata_payload={"wallet_id": str(wallet.id), "wallet_name": wallet.wallet_name}
                    )
                )
                self.db.commit()
                return "Wallet berhasil dinonaktifkan"
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise e

    def adjust_balance(self, user: User, wallet_id: UUID, data: AdjustBalanceRequest) -> Wallet:
        """Adjust wallet balance operationally by generating an audit-safe transaction."""
        from app.services.transaction_service import TransactionService
        from app.schemas.transaction import CreateTransactionRequest
        from app.models.category import Category
        
        wallet = self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.family_id == user.family_id)
        ).scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet tidak ditemukan"
            )

        delta = data.target_balance - Decimal(str(wallet.balance))
        if delta == Decimal("0"):
            return wallet
            
        cat_type = "INCOME" if delta > 0 else "EXPENSE"
        
        category = self.db.execute(
            select(Category).where(
                Category.family_id.is_(None),
                Category.name == "Balance Adjustment",
                Category.type == cat_type
            )
        ).scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Kategori Balance Adjustment tidak ditemukan di sistem."
            )
            
        txn_request = CreateTransactionRequest(
            wallet_id=wallet.id,
            category_id=category.id,
            amount=abs(delta),
            description="Operational balance adjustment"
        )
        
        try:
            txn_service = TransactionService(self.db)
            txn_service.create_transaction(user, txn_request)
            
            # We need to explicitly refresh since create_transaction commits and expires the session state
            self.db.refresh(wallet)
            return wallet
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise e
