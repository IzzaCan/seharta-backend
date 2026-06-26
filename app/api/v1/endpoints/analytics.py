from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.services.ai_service import AiService

router = APIRouter()

@router.get("/insight")
def get_financial_insight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """
    Generate financial insight using Gemini AI based on recent family transactions.
    """
    family_id = current_user.family_id
    
    # Ambil transaksi 30 hari terakhir
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Query transaksi beserta kategori
    recent_transactions = (
        db.query(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.family_id == family_id,
            Transaction.transaction_date >= thirty_days_ago
        )
        .order_by(Transaction.transaction_date.desc())
        .limit(20)
        .all()
    )
    
    if not recent_transactions:
        summary_text = "Belum ada transaksi dalam 30 hari terakhir."
    else:
        # Buat ringkasan transaksi
        summary_lines = []
        for txn, cat in recent_transactions:
            cat_name = cat.name if cat else "Lainnya"
            t_type = "Pengeluaran" if txn.transaction_type.upper() == "EXPENSE" else "Pemasukan"
            summary_lines.append(f"- {txn.transaction_date.strftime('%Y-%m-%d')}: {t_type} Rp{txn.amount} ({cat_name}) - {txn.description or ''}")
        
        summary_text = "\n".join(summary_lines)
    
    # Gunakan AiService untuk men-generate insight
    ai_service = AiService()
    insight_text = ai_service.generate_financial_insight(summary_text)
    
    return {"insight": insight_text}

@router.get("/summary")
def get_balance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """
    Get family balance summary and percentage change compared to 30 days ago.
    """
    from app.models.wallet import Wallet
    family_id = current_user.family_id

    # Get current total balance
    total_balance = db.query(func.sum(Wallet.balance)).filter(
        Wallet.family_id == family_id,
        Wallet.is_active == True
    ).scalar() or 0.0

    # Get net flow from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Calculate total income
    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.family_id == family_id,
        Transaction.transaction_date >= thirty_days_ago,
        func.upper(Transaction.transaction_type) == "INCOME"
    ).scalar() or 0.0
    
    # Calculate total expense
    expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.family_id == family_id,
        Transaction.transaction_date >= thirty_days_ago,
        func.upper(Transaction.transaction_type) == "EXPENSE"
    ).scalar() or 0.0

    net_flow = income - expense
    balance_30_days_ago = total_balance - net_flow

    if balance_30_days_ago == 0:
        if net_flow > 0:
            percentage_change = 100.0
        elif net_flow < 0:
            percentage_change = -100.0
        else:
            percentage_change = 0.0
    else:
        percentage_change = (net_flow / balance_30_days_ago) * 100

    return {
        "current_balance": float(total_balance),
        "percentage_change": float(percentage_change),
        "is_positive": percentage_change >= 0
    }
