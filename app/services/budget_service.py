import uuid
from typing import List, Tuple, Optional
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, extract, func

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:

    @staticmethod
    def _calculate_budget_summary(budget_amount: Decimal, spent_amount: Decimal) -> Tuple[Decimal, float, bool]:
        """
        Shared internal helper to compute remaining_amount, progress_percentage, and is_over_budget.
        """
        spent = spent_amount or Decimal('0.0')
        remaining_amount = budget_amount - spent
        
        if budget_amount > 0:
            progress_percentage = float((spent / budget_amount) * 100)
        else:
            progress_percentage = 0.0
            
        is_over_budget = spent > budget_amount
        
        return remaining_amount, progress_percentage, is_over_budget

    @staticmethod
    def _validate_category(db: Session, category_id: uuid.UUID, family_id: uuid.UUID) -> None:
        category = db.execute(select(Category).where(Category.id == category_id)).scalar_one_or_none()
        if not category:
            raise ValueError("Category not found")
        if category.type.upper() != TransactionType.EXPENSE:
            raise ValueError("Budget can only be created for EXPENSE categories")
        if category.family_id is not None and category.family_id != family_id:
            raise ValueError("Invalid category selected")

    @staticmethod
    def create_budget(db: Session, budget_data: BudgetCreate, family_id: uuid.UUID, user_id: uuid.UUID) -> Budget:
        BudgetService._validate_category(db, budget_data.category_id, family_id)
        
        # Check duplicate
        existing = db.execute(
            select(Budget).where(
                Budget.family_id == family_id,
                Budget.category_id == budget_data.category_id,
                Budget.month == budget_data.month,
                Budget.year == budget_data.year
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError("Budget for this category, month, and year already exists")

        new_budget = Budget(
            family_id=family_id,
            created_by=user_id,
            **budget_data.model_dump()
        )
        
        db.add(new_budget)
        db.commit()
        db.refresh(new_budget)
        
        # Retrieve with calculated fields
        return BudgetService.get_budget(db, new_budget.id, family_id)

    @staticmethod
    def get_budget(db: Session, budget_id: uuid.UUID, family_id: uuid.UUID) -> Budget:
        stmt = (
            select(Budget)
            .options(joinedload(Budget.category), joinedload(Budget.creator))
            .where(Budget.id == budget_id, Budget.family_id == family_id)
        )
        budget = db.execute(stmt).scalar_one_or_none()
        if not budget:
            raise ValueError("Budget not found")

        # Dynamic calc
        spent_stmt = (
            select(func.sum(Transaction.amount))
            .where(
                Transaction.family_id == family_id,
                Transaction.category_id == budget.category_id,
                func.upper(Transaction.transaction_type) == TransactionType.EXPENSE.value,
                extract('month', Transaction.transaction_date) == budget.month,
                extract('year', Transaction.transaction_date) == budget.year
            )
        )
        spent_amount = db.execute(spent_stmt).scalar() or Decimal('0.0')

        rem, prog, over = BudgetService._calculate_budget_summary(budget.budget_amount, spent_amount)
        
        # We manually attach these properties for BudgetResponse to use
        budget.spent_amount = spent_amount
        budget.remaining_amount = rem
        budget.progress_percentage = prog
        budget.is_over_budget = over

        return budget

    @staticmethod
    def list_budgets(db: Session, family_id: uuid.UUID, month: Optional[int] = None, year: Optional[int] = None) -> List[Budget]:
        stmt = (
            select(Budget)
            .options(joinedload(Budget.category), joinedload(Budget.creator))
            .where(Budget.family_id == family_id)
        )
        if month:
            stmt = stmt.where(Budget.month == month)
        if year:
            stmt = stmt.where(Budget.year == year)
            
        stmt = stmt.order_by(Budget.year.desc(), Budget.month.desc())
        budgets = db.execute(stmt).scalars().all()
        
        # Sort in python for category_name ASC since category is joined
        budgets.sort(key=lambda b: (-(b.year), -(b.month), b.category.name if b.category else ""))

        # Grouped aggregate query
        agg_stmt = (
            select(
                Transaction.category_id,
                extract('month', Transaction.transaction_date).label('txn_month'),
                extract('year', Transaction.transaction_date).label('txn_year'),
                func.sum(Transaction.amount).label('total_spent')
            )
            .where(
                Transaction.family_id == family_id,
                func.upper(Transaction.transaction_type) == TransactionType.EXPENSE.value,
                Transaction.category_id.isnot(None)
            )
        )
        if month:
            agg_stmt = agg_stmt.where(extract('month', Transaction.transaction_date) == month)
        if year:
            agg_stmt = agg_stmt.where(extract('year', Transaction.transaction_date) == year)
            
        agg_stmt = agg_stmt.group_by(
            Transaction.category_id,
            extract('month', Transaction.transaction_date),
            extract('year', Transaction.transaction_date)
        )
        
        spending_records = db.execute(agg_stmt).all()
        # map: (category_id, month, year) -> total_spent
        spending_map = {
            (rec.category_id, int(rec.txn_month), int(rec.txn_year)): rec.total_spent
            for rec in spending_records
        }

        for b in budgets:
            spent = spending_map.get((b.category_id, b.month, b.year), Decimal('0.0'))
            rem, prog, over = BudgetService._calculate_budget_summary(b.budget_amount, spent)
            
            b.spent_amount = spent
            b.remaining_amount = rem
            b.progress_percentage = prog
            b.is_over_budget = over

        return budgets

    @staticmethod
    def update_budget(db: Session, budget_id: uuid.UUID, budget_data: BudgetUpdate, family_id: uuid.UUID) -> Budget:
        # Verify ownership by using get_budget (it enforces family_id implicitly)
        stmt = select(Budget).where(Budget.id == budget_id, Budget.family_id == family_id)
        budget = db.execute(stmt).scalar_one_or_none()
        if not budget:
            raise ValueError("Budget not found")

        update_dict = budget_data.model_dump(exclude_unset=True)

        if "category_id" in update_dict:
            BudgetService._validate_category(db, update_dict["category_id"], family_id)

        # Check for unique constraint if category, month, or year changes
        if any(k in update_dict for k in ["category_id", "month", "year"]):
            new_cat = update_dict.get("category_id", budget.category_id)
            new_month = update_dict.get("month", budget.month)
            new_year = update_dict.get("year", budget.year)

            existing = db.execute(
                select(Budget).where(
                    Budget.family_id == family_id,
                    Budget.category_id == new_cat,
                    Budget.month == new_month,
                    Budget.year == new_year,
                    Budget.id != budget_id
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError("Budget for this category, month, and year already exists")

        for key, value in update_dict.items():
            setattr(budget, key, value)

        db.commit()
        db.refresh(budget)
        
        return BudgetService.get_budget(db, budget_id, family_id)

    @staticmethod
    def delete_budget(db: Session, budget_id: uuid.UUID, family_id: uuid.UUID) -> None:
        stmt = select(Budget).where(Budget.id == budget_id, Budget.family_id == family_id)
        budget = db.execute(stmt).scalar_one_or_none()
        if not budget:
            raise ValueError("Budget not found")
            
        db.delete(budget)
        db.commit()
