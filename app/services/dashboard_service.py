from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.schemas.dashboard import DashboardResponse, DashboardBudgetSummary
from app.services.budget_service import BudgetService


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
        
        # Calculate income and expense this month in a single query
        from sqlalchemy import case
        inc_exp_res = self.db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (func.upper(Transaction.transaction_type) == "INCOME", Transaction.amount),
                            else_=0
                        )
                    ),
                    0
                ).label("income"),
                func.coalesce(
                    func.sum(
                        case(
                            (func.upper(Transaction.transaction_type) == "EXPENSE", Transaction.amount),
                            else_=0
                        )
                    ),
                    0
                ).label("expense")
            ).where(
                Transaction.family_id == family_id,
                Transaction.transaction_date >= start_of_month,
                Transaction.category_id.isnot(None)
            )
        ).first()
        
        income = Decimal(str(inc_exp_res.income)) if inc_exp_res else Decimal("0")
        expense = Decimal(str(inc_exp_res.expense)) if inc_exp_res else Decimal("0")
        
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
        
        # Calculate budget summary for current month
        budgets = BudgetService.list_budgets(self.db, family_id, month=now.month, year=now.year)
        budget_summary = None
        if budgets:
            total_budget = sum(b.budget_amount for b in budgets)
            total_spent = sum(b.spent_amount for b in budgets)
            total_remaining = total_budget - total_spent
            total_budget_categories = len(budgets)
            over_budget_categories = sum(1 for b in budgets if b.is_over_budget)
            
            budget_summary = DashboardBudgetSummary(
                total_budget=total_budget,
                total_spent=total_spent,
                total_remaining=total_remaining,
                total_budget_categories=total_budget_categories,
                over_budget_categories=over_budget_categories,
                preview=budgets[:3] # Max 3 items for preview
            )
        
        return DashboardResponse(
            total_balance=total_balance,
            income_this_month=Decimal(str(income)),
            expense_this_month=Decimal(str(expense)),
            wallets=wallets,
            recent_transactions=recent_transactions,
            budget_summary=budget_summary
        )
