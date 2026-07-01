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
                Transaction.transaction_date >= thirty_days_ago,
                func.upper(Transaction.transaction_type).in_(["INCOME", "EXPENSE"]),
                Transaction.category_id.isnot(None)
            )
            .order_by(Transaction.transaction_date.desc())
            .limit(20)
            .all()
        )
        
        total_income = 0
        total_expense = 0
        
        if not recent_transactions:
            summary_text = "Belum ada transaksi dalam 30 hari terakhir."
        else:
            # Buat ringkasan transaksi
            summary_lines = []
            for txn, cat in recent_transactions:
                cat_name = cat.name if cat else "Lainnya"
                t_type = "Pengeluaran" if txn.transaction_type.upper() == "EXPENSE" else "Pemasukan"
                summary_lines.append(f"- {txn.transaction_date.strftime('%Y-%m-%d')}: {t_type} Rp{txn.amount} ({cat_name}) - {txn.description or ''}")
                if txn.transaction_type.upper() == "INCOME":
                    total_income += txn.amount
                elif txn.transaction_type.upper() == "EXPENSE":
                    total_expense += txn.amount
            
            summary_text = "\n".join(summary_lines)
            
        if self.ai_service.is_mock_mode():
            logger.info("No Gemini API key set. Returning mock financial insight.")
            return "Pengeluaran Anda bulan ini stabil. Pertimbangkan untuk menyisihkan lebih banyak ke tabungan darurat."
            
        prompt = f"""
        Anda adalah asisten keuangan keluarga yang bersahabat, suportif, dan praktis.
        Berikut adalah ringkasan keuangan keluarga selama 30 hari terakhir:
        - Total Pemasukan: Rp{total_income}
        - Total Pengeluaran: Rp{total_expense}
        
        Riwayat transaksi terbaru:
        {summary_text}
        
        Berikan TEPAT 1 kalimat pendek (maksimal 15-20 kata) berisi insight keuangan yang padat, informatif, dan berupa saran praktis langsung.
        Jika pengeluaran melebihi pemasukan, langsung sebutkan 1 tindakan konkret untuk berhemat.
        Gunakan bahasa Indonesia sehari-hari yang sopan, jelas, dan bersahabat. Hindari bahasa bertele-tele, kaku/teknis, dan jangan 'sok asik'. Jangan berikan salam pembuka atau pengantar, langsung berikan kalimat sarannya.
        """
        
        try:
            return self.ai_service.generate_text(prompt)
        except Exception as e:
            logger.error(f"Error generating financial insight: {e}")
            return "Fokus pada pengeluaran prioritas minggu ini. Terus pertahankan pengelolaan keuangan yang baik!"
