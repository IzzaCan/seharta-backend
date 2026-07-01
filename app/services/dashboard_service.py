from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.schemas.dashboard import DashboardResponse


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self, family_id: UUID) -> DashboardResponse:
        # Get active wallets
        wallets_stmt = select(Wallet).where(
            Wallet.family_id == family_id,
            Wallet.is_active == True
        ).order_by(Wallet.created_at.desc())
        wallets = list(self.db.execute(wallets_stmt).scalars().all())
        
        total_balance = sum((Decimal(str(w.balance)) for w in wallets), Decimal("0"))
        
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate income and expense this month
        income = self.db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.family_id == family_id,
                Transaction.transaction_date >= start_of_month,
                func.upper(Transaction.transaction_type) == "INCOME",
                Transaction.category_id.isnot(None)
            )
        ).scalar() or Decimal("0")
        
        expense = self.db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.family_id == family_id,
                Transaction.transaction_date >= start_of_month,
                func.upper(Transaction.transaction_type) == "EXPENSE",
                Transaction.category_id.isnot(None)
            )
        ).scalar() or Decimal("0")
        
        # Fetch latest 10 transactions
        transactions_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.user),
                selectinload(Transaction.wallet),
                selectinload(Transaction.category)
            )
            .where(
                Transaction.family_id == family_id,
                (
                    (func.upper(Transaction.transaction_type).in_(["INCOME", "EXPENSE"]) & Transaction.category_id.isnot(None)) |
                    (func.upper(Transaction.transaction_type) == "TRANSFER")
                )
            )
            .order_by(Transaction.transaction_date.desc())
            .limit(10)
        )
        recent_transactions = list(self.db.execute(transactions_stmt).scalars().all())
        
        return DashboardResponse(
            total_balance=total_balance,
            income_this_month=Decimal(str(income)),
            expense_this_month=Decimal(str(expense)),
            wallets=wallets,
            recent_transactions=recent_transactions
        )
