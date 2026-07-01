import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.wallet import Wallet
from app.models.family import Family
from app.services.ai_service import AiService

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session, ai_service: AiService):
        self.db = db
        self.ai_service = ai_service

    def get_financial_insight(self, family_id) -> str:
        """
        Generate financial insight using Gemini AI based on recent family transactions.
        Caches results in the database (families table) to limit generation to once every 12 hours.
        """
        # 1. Ambil data keluarga dari database untuk cek cache
        family = self.db.query(Family).filter(Family.id == family_id).first()
        if family and family.ai_insight and family.insight_generated_at:
            try:
                # Menghilangkan tzinfo agar bisa dibandingkan dengan datetime.utcnow() yang naive
                generated_at = family.insight_generated_at.replace(tzinfo=None)
                if datetime.utcnow() - generated_at < timedelta(hours=12):
                    logger.info(f"Returning database cached financial insight for family {family_id}")
                    return family.ai_insight
            except Exception as e:
                logger.error(f"Failed to compare insight cache timestamp: {e}")

        # 2. Ambil data transaksi 30 hari terakhir jika cache kedaluwarsa/kosong
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
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
            
        # 3. Ambil total saldo aktif saat ini dari seluruh dompet/rekening keluarga
        wallets = (
            self.db.query(Wallet)
            .filter(
                Wallet.family_id == family_id,
                Wallet.is_active == True
            )
            .all()
        )
        total_balance = sum(w.balance for w in wallets)

        if self.ai_service.is_mock_mode():
            logger.info("No Gemini API key set. Returning mock financial insight.")
            mock_insight = "Pengeluaran Anda bulan ini stabil. Pertimbangkan untuk menyisihkan lebih banyak ke tabungan darurat."
            self._save_to_db_cache(family, mock_insight)
            return mock_insight
            
        prompt = f"""
        Anda adalah asisten keuangan keluarga yang bersahabat, suportif, dan praktis.
        Berikut adalah ringkasan keuangan keluarga saat ini:
        - Total Saldo Bersama saat ini (di semua dompet/rekening): Rp{total_balance}
        - Total Pemasukan 30 hari terakhir: Rp{total_income}
        - Total Pengeluaran 30 hari terakhir: Rp{total_expense}
        
        Riwayat transaksi terbaru:
        {summary_text}
        
        Berikan TEPAT 1 kalimat pendek (maksimal 15-20 kata) berisi insight keuangan yang padat, informatif, dan berupa saran praktis langsung.
        PENTING: Gunakan data Saldo Bersama saat ini sebagai konteks kemampuan finansial mereka. 
        - Jika pengeluaran 30 hari terakhir melebihi pemasukan namun Saldo Bersama saat ini masih sangat aman (lebih besar dari pengeluaran bulanan), jangan panikkan mereka secara berlebihan, cukup ingatkan untuk menjaga konsistensi dan waspada.
        - Jika pengeluaran melebihi pemasukan dan Saldo Bersama menipis, langsung sebutkan 1 tindakan konkret untuk berhemat.
        - Jika pengeluaran dan pemasukan seimbang atau positif, berikan apresiasi singkat atau saran investasi/menabung.
        
        Gunakan bahasa Indonesia sehari-hari yang sopan, jelas, dan bersahabat. Hindari bahasa bertele-tele, kaku/teknis, dan jangan 'sok asik'. Jangan berikan salam pembuka atau pengantar, langsung berikan kalimat sarannya.
        """
        
        try:
            insight = self.ai_service.generate_text(prompt)
            self._save_to_db_cache(family, insight)
            return insight
        except Exception as e:
            logger.error(f"Error generating financial insight: {e}")
            fallback_insight = "Fokus pada pengeluaran prioritas minggu ini. Terus pertahankan pengelolaan keuangan yang baik!"
            return fallback_insight

    def _save_to_db_cache(self, family, insight: str):
        if family:
            try:
                family.ai_insight = insight
                family.insight_generated_at = datetime.utcnow()
                self.db.add(family)
                self.db.commit()
                logger.info(f"Successfully saved generated insight to database cache for family {family.id}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to save insight to database: {e}")
