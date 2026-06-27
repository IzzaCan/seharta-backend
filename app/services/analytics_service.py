import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.wallet import Wallet
from app.services.ai_service import AiService

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session, ai_service: AiService):
        self.db = db
        self.ai_service = ai_service

    def get_financial_insight(self, family_id: int) -> str:
        """
        Generate financial insight using Gemini AI based on recent family transactions.
        """
        # Ambil transaksi 30 hari terakhir
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Query transaksi beserta kategori
        recent_transactions = (
            self.db.query(Transaction, Category)
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
            
        if self.ai_service.is_mock_mode():
            logger.info("No Gemini API key set. Returning mock financial insight.")
            return "Pengeluaran Anda bulan ini stabil. Pertimbangkan untuk menyisihkan lebih banyak ke tabungan darurat."
            
        prompt = f"""
        Anda adalah asisten perencana keuangan keluarga yang cerdas dan ramah.
        Berikut adalah ringkasan transaksi terbaru dari sebuah keluarga:
        {summary_text}
        
        Berikan 1 hingga 2 kalimat insight (wawasan) singkat, positif, dan membangun mengenai pengeluaran atau pemasukan mereka.
        Gunakan bahasa Indonesia yang santai, ringkas, dan memotivasi. Tidak perlu memberikan salam.
        Langsung berikan insight-nya.
        """
        
        try:
            return self.ai_service.generate_text(prompt)
        except Exception as e:
            logger.error(f"Error generating financial insight: {e}")
            return "Fokus pada pengeluaran prioritas minggu ini. Terus pertahankan pengelolaan keuangan yang baik!"

    def get_balance_summary(self, family_id) -> dict:
        """
        Get family balance summary and percentage change compared to 30 days ago.
        """
        # Get current total balance
        total_balance = self.db.query(func.sum(Wallet.balance)).filter(
            Wallet.family_id == family_id,
            Wallet.is_active == True
        ).scalar() or 0.0

        # Get net flow from last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Calculate total income
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.family_id == family_id,
            Transaction.transaction_date >= thirty_days_ago,
            func.upper(Transaction.transaction_type) == "INCOME"
        ).scalar() or 0.0
        
        # Calculate total expense
        expense = self.db.query(func.sum(Transaction.amount)).filter(
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


