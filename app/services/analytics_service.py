import logging
import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional, Tuple, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, distinct, and_

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.models.wallet import Wallet
from app.models.family import Family
from app.models.asset import Asset, OwnershipType
from app.models.asset_category import AssetCategory
from app.models.budget import Budget
from app.models.user import User
from app.services.ai_service import AiService

from app.schemas.analytics import (
    AnalyticsResponse, AnalyticsOverview, AnalyticsIncomeVsExpense,
    AnalyticsCategoryBreakdown, AnalyticsBudgetAnalysis, AnalyticsAssetDistribution,
    AssetDistributionByType, AssetDistributionByOwnership, AssetDistributionByCategory,
    AnalyticsBehavioralAnalytics, BehavioralSummary, UserSpenderSummary,
    UserActivitySummary, UserSpendingDistribution, UserSpendingHabit,
    AnalyticsFilterMetadata, AnalyticsCurrentFilter
)

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session, ai_service: AiService):
        self.db = db
        self.ai_service = ai_service

    def _get_date_range(self, month: Optional[int], year: Optional[int], start_date: Optional[str], end_date: Optional[str]) -> Tuple[datetime, datetime, int, int]:
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end, start.month, start.year

        today = datetime.now()
        y = year or today.year
        m = month or today.month
        _, last_day = calendar.monthrange(y, m)
        start = datetime(y, m, 1, 0, 0, 0, 0)
        end = datetime(y, m, last_day, 23, 59, 59, 999999)
        return start, end, m, y

    def get_analytics(
        self,
        family_id: UUID,
        month: Optional[int] = None,
        year: Optional[int] = None,
        ownership_type: str = "ALL",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> AnalyticsResponse:
        start_dt, end_dt, target_month, target_year = self._get_date_range(month, year, start_date, end_date)
        
        # Income vs Expense Base
        inc_exp = self._get_income_vs_expense(family_id, start_dt, end_dt)
        total_income = inc_exp.total_income
        total_expense = inc_exp.total_expense
        
        # Overview
        overview = self._get_overview(family_id, total_income, inc_exp.net_surplus, ownership_type)
        
        # Category Breakdown
        cat_breakdown = self._get_category_breakdown(family_id, start_dt, end_dt, total_expense)
        
        # Budget Analysis
        budget_analysis = self._get_budget_analysis(family_id, start_dt, end_dt, target_month, target_year)
        
        # Asset Distribution
        asset_dist = self._get_asset_distribution(family_id, ownership_type)
        
        # Behavioral Analytics
        behavioral = self._get_behavioral_analytics(family_id, start_dt, end_dt)
        
        # Filter Metadata
        filter_meta = self._get_filter_metadata(family_id, target_month, target_year, ownership_type)
        
        return AnalyticsResponse(
            overview=overview,
            income_vs_expense=inc_exp,
            category_breakdown=cat_breakdown,
            budget_analysis=budget_analysis,
            asset_distribution=asset_dist,
            behavioral_analytics=behavioral,
            filter_metadata=filter_meta
        )

    def _base_expense_filter(self, family_id: UUID, start_dt: datetime, end_dt: datetime):
        return (
            Transaction.family_id == family_id,
            func.upper(Transaction.transaction_type) == TransactionType.EXPENSE.value,
            Transaction.transaction_date >= start_dt,
            Transaction.transaction_date <= end_dt
        )

    def _get_overview(self, family_id: UUID, total_income: float, net_surplus: float, ownership_type: str) -> AnalyticsOverview:
        # Liquidity
        liquidity = self.db.query(func.coalesce(func.sum(Wallet.balance), 0.0)).filter(
            Wallet.family_id == family_id,
            Wallet.is_active == True
        ).scalar()
        
        # Asset Value
        asset_query = self.db.query(func.coalesce(func.sum(Asset.purchase_price), 0.0)).filter(
            Asset.family_id == family_id
        )
        if ownership_type.upper() in ["JOINT", "PERSONAL"]:
            asset_query = asset_query.filter(func.upper(Asset.ownership_type) == ownership_type.upper())
        asset_value = asset_query.scalar()
        
        net_worth = float(liquidity) + float(asset_value)
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = (net_surplus / total_income) * 100.0
            
        return AnalyticsOverview(
            net_worth=net_worth,
            total_liquidity=float(liquidity),
            total_asset_value=float(asset_value),
            savings_rate_percentage=savings_rate
        )

    def _get_income_vs_expense(self, family_id: UUID, start_dt: datetime, end_dt: datetime) -> AnalyticsIncomeVsExpense:
        res = self.db.query(
            func.coalesce(func.sum(case((func.upper(Transaction.transaction_type) == TransactionType.INCOME.value, Transaction.amount), else_=0.0)), 0.0).label('income'),
            func.coalesce(func.sum(case((func.upper(Transaction.transaction_type) == TransactionType.EXPENSE.value, Transaction.amount), else_=0.0)), 0.0).label('expense')
        ).filter(
            Transaction.family_id == family_id,
            Transaction.transaction_date >= start_dt,
            Transaction.transaction_date <= end_dt
        ).first()
        
        income = float(res.income) if res else 0.0
        expense = float(res.expense) if res else 0.0
        net = income - expense
        ratio = (expense / income) * 100.0 if income > 0 else 0.0
        
        return AnalyticsIncomeVsExpense(
            total_income=income,
            total_expense=expense,
            net_surplus=net,
            expense_to_income_ratio=ratio
        )

    def _get_category_breakdown(self, family_id: UUID, start_dt: datetime, end_dt: datetime, total_expense: float) -> List[AnalyticsCategoryBreakdown]:
        rows = self.db.query(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label('amount')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            *self._base_expense_filter(family_id, start_dt, end_dt),
            Category.name != "Balance Adjustment"
        ).group_by(Category.id, Category.name).order_by(func.sum(Transaction.amount).desc()).all()
        
        results = []
        for r in rows:
            amt = float(r.amount)
            pct = (amt / total_expense) * 100.0 if total_expense > 0 else 0.0
            results.append(AnalyticsCategoryBreakdown(
                category_id=r.id,
                category_name=r.name,
                amount=amt,
                percentage=pct
            ))
        return results

    def _get_budget_analysis(self, family_id: UUID, start_dt: datetime, end_dt: datetime, month: int, year: int) -> AnalyticsBudgetAnalysis:
        # Sum of active budgets for the month/year
        total_budgeted_raw = self.db.query(func.coalesce(func.sum(Budget.budget_amount), 0.0)).filter(
            Budget.family_id == family_id,
            Budget.month == month,
            Budget.year == year
        ).scalar()
        total_budgeted = float(total_budgeted_raw)
        
        # Get spending per budgeted category
        budget_spending = self.db.query(
            Budget.category_id,
            Budget.budget_amount,
            func.coalesce(func.sum(Transaction.amount), 0.0).label('spent')
        ).outerjoin(
            Transaction, 
            (Transaction.category_id == Budget.category_id) & 
            and_(*self._base_expense_filter(family_id, start_dt, end_dt))
        ).filter(
            Budget.family_id == family_id,
            Budget.month == month,
            Budget.year == year
        ).group_by(Budget.category_id, Budget.budget_amount).all()
        
        total_spent = sum(float(r.spent) for r in budget_spending)
        over_budget = sum(1 for r in budget_spending if float(r.spent) > float(r.budget_amount))
        adherence = (total_spent / total_budgeted) * 100.0 if total_budgeted > 0 else 0.0
        
        return AnalyticsBudgetAnalysis(
            total_budgeted=total_budgeted,
            total_spent_on_budget=total_spent,
            overall_adherence_percentage=adherence,
            over_budget_categories_count=over_budget
        )

    def _get_asset_distribution(self, family_id: UUID, ownership_type: str) -> AnalyticsAssetDistribution:
        wallets = self.db.query(func.coalesce(func.sum(Wallet.balance), 0.0)).filter(
            Wallet.family_id == family_id,
            Wallet.is_active == True
        ).scalar()
        
        assets_query = self.db.query(
            func.coalesce(func.sum(case((func.upper(Asset.ownership_type) == 'JOINT', Asset.purchase_price), else_=0.0)), 0.0).label('joint'),
            func.coalesce(func.sum(case((func.upper(Asset.ownership_type) == 'PERSONAL', Asset.purchase_price), else_=0.0)), 0.0).label('personal')
        ).filter(Asset.family_id == family_id)
        
        if ownership_type.upper() in ["JOINT", "PERSONAL"]:
            assets_query = assets_query.filter(func.upper(Asset.ownership_type) == ownership_type.upper())
            
        assets_res = assets_query.first()
        joint_assets = float(assets_res.joint) if assets_res else 0.0
        personal_assets = float(assets_res.personal) if assets_res else 0.0
        total_physical = joint_assets + personal_assets

        # By Category Aggregation
        cat_query = self.db.query(
            AssetCategory.id,
            AssetCategory.name,
            AssetCategory.icon_name,
            func.count(Asset.id).label('asset_count'),
            func.coalesce(func.sum(Asset.purchase_price), 0.0).label('total_value')
        ).join(
            Asset, Asset.category_id == AssetCategory.id
        ).filter(
            Asset.family_id == family_id
        )

        if ownership_type.upper() in ["JOINT", "PERSONAL"]:
            cat_query = cat_query.filter(func.upper(Asset.ownership_type) == ownership_type.upper())

        cat_rows = cat_query.group_by(
            AssetCategory.id, AssetCategory.name, AssetCategory.icon_name
        ).order_by(
            func.sum(Asset.purchase_price).desc()
        ).all()

        by_category_res = []
        for row in cat_rows:
            cat_val = float(row.total_value)
            pct = (cat_val / total_physical) * 100.0 if total_physical > 0 else 0.0
            by_category_res.append(AssetDistributionByCategory(
                category_id=row.id,
                category_name=row.name,
                icon_name=row.icon_name,
                asset_count=row.asset_count,
                total_value=cat_val,
                percentage=pct
            ))
        
        return AnalyticsAssetDistribution(
            by_type=AssetDistributionByType(
                wallets=float(wallets),
                physical_assets=total_physical
            ),
            by_ownership=AssetDistributionByOwnership(
                joint=joint_assets,
                personal=personal_assets
            ),
            by_category=by_category_res
        )

    def _get_behavioral_analytics(self, family_id: UUID, start_dt: datetime, end_dt: datetime) -> AnalyticsBehavioralAnalytics:
        # Expenses per user
        expenses_query = self.db.query(
            User.id,
            User.full_name,
            User.avatar_url,
            func.coalesce(func.sum(Transaction.amount), 0.0).label('total_spent'),
            func.count(Transaction.id).label('tx_count')
        ).join(
            Transaction, Transaction.user_id == User.id
        ).filter(
            *self._base_expense_filter(family_id, start_dt, end_dt),
            Category.name != "Balance Adjustment"
        ).group_by(User.id, User.full_name, User.avatar_url).all()
        
        total_fam_expense = sum(float(r.total_spent) for r in expenses_query)
        
        highest_spender = None
        most_active = None
        if expenses_query:
            hs_row = max(expenses_query, key=lambda r: float(r.total_spent))
            ma_row = max(expenses_query, key=lambda r: r.tx_count)
            highest_spender = UserSpenderSummary(
                user_id=hs_row.id,
                user_name=hs_row.full_name,
                total_spent=float(hs_row.total_spent)
            )
            most_active = UserActivitySummary(
                user_id=ma_row.id,
                user_name=ma_row.full_name,
                transaction_count=ma_row.tx_count
            )
            
        distributions = []
        habits = []
        
        days_map = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"}
        
        # --- OPTIMIZATION: Eliminate N+1 loop for Favorite Categories ---
        # 1. CTE: Group spending by User & Category
        cat_spent_subq = self.db.query(
            Transaction.user_id,
            Category.name.label('category_name'),
            func.sum(Transaction.amount).label('total_cat_spent')
        ).join(
            Category, Transaction.category_id == Category.id
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            *self._base_expense_filter(family_id, start_dt, end_dt),
            Category.name != "Balance Adjustment"
        ).group_by(Transaction.user_id, Category.name).subquery()

        # 2. Outer query with Window Function to pick the top category per user
        fav_cat_query = self.db.query(
            cat_spent_subq.c.user_id,
            cat_spent_subq.c.category_name,
            func.row_number().over(
                partition_by=cat_spent_subq.c.user_id,
                order_by=cat_spent_subq.c.total_cat_spent.desc()
            ).label('rn')
        ).subquery()

        top_cats = self.db.query(fav_cat_query.c.user_id, fav_cat_query.c.category_name).filter(fav_cat_query.c.rn == 1).all()
        fav_cat_map = {row.user_id: row.category_name for row in top_cats}

        # --- OPTIMIZATION: Eliminate N+1 loop for Habits ---
        # 1. CTE: Group transaction counts by User, DOW, Hour
        habits_subq = self.db.query(
            Transaction.user_id,
            extract('dow', Transaction.transaction_date).label('dow'),
            extract('hour', Transaction.transaction_date).label('hour'),
            func.count(Transaction.id).label('cnt')
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            *self._base_expense_filter(family_id, start_dt, end_dt),
            Category.name != "Balance Adjustment"
        ).group_by(
            Transaction.user_id,
            extract('dow', Transaction.transaction_date),
            extract('hour', Transaction.transaction_date)
        ).subquery()

        # 2. Outer query with Window Function to pick the top habit per user
        top_habits_subq = self.db.query(
            habits_subq.c.user_id,
            habits_subq.c.dow,
            habits_subq.c.hour,
            func.row_number().over(
                partition_by=habits_subq.c.user_id,
                order_by=habits_subq.c.cnt.desc()
            ).label('rn')
        ).subquery()

        top_habits = self.db.query(top_habits_subq.c.user_id, top_habits_subq.c.dow, top_habits_subq.c.hour).filter(top_habits_subq.c.rn == 1).all()
        habits_map = {row.user_id: (row.dow, row.hour) for row in top_habits}

        for u in expenses_query:
            pct = (float(u.total_spent) / total_fam_expense) * 100.0 if total_fam_expense > 0 else 0.0
            avg = float(u.total_spent) / u.tx_count if u.tx_count > 0 else 0.0
            
            fav_cat = fav_cat_map.get(u.id)
            
            distributions.append(UserSpendingDistribution(
                user_id=u.id,
                user_name=u.full_name,
                avatar_url=u.avatar_url,
                total_spent=float(u.total_spent),
                transaction_count=u.tx_count,
                average_transaction=avg,
                percentage_of_total=pct,
                favorite_category=fav_cat
            ))
            
            habit = habits_map.get(u.id)
            if habit:
                dow_val, hour_val = habit
                dow_int = int(dow_val)
                hour_int = int(hour_val)
                day_str = days_map.get(dow_int, "Unknown")
                hour_str = f"{hour_int:02d}:00-{(hour_int+1)%24:02d}:00"
                habits.append(UserSpendingHabit(
                    user_id=u.id,
                    user_name=u.full_name,
                    most_active_day=day_str,
                    most_active_hour=hour_str
                ))
            else:
                habits.append(UserSpendingHabit(
                    user_id=u.id,
                    user_name=u.full_name,
                    most_active_day=None,
                    most_active_hour=None
                ))
                
        return AnalyticsBehavioralAnalytics(
            summary=BehavioralSummary(
                highest_spender=highest_spender,
                most_active_member=most_active
            ),
            spending_distribution=distributions,
            spending_habit=habits
        )

    def _get_filter_metadata(self, family_id: UUID, target_month: int, target_year: int, ownership_type: str) -> AnalyticsFilterMetadata:
        earliest_tx = self.db.query(func.min(Transaction.transaction_date)).filter(
            Transaction.family_id == family_id
        ).scalar()
        
        years_query = self.db.query(distinct(extract('year', Transaction.transaction_date))).filter(
            Transaction.family_id == family_id
        ).all()
        avail_years = sorted([int(y[0]) for y in years_query if y[0]])
        
        months_query = self.db.query(distinct(extract('month', Transaction.transaction_date))).filter(
            Transaction.family_id == family_id,
            extract('year', Transaction.transaction_date) == target_year
        ).all()
        avail_months = sorted([int(m[0]) for m in months_query if m[0]])
        
        return AnalyticsFilterMetadata(
            earliest_transaction_date=earliest_tx,
            available_years=avail_years,
            available_months=avail_months,
            current_filter=AnalyticsCurrentFilter(
                month=target_month,
                year=target_year,
                ownership_type=ownership_type
            )
        )

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
                if datetime.utcnow() - generated_at < timedelta(hours=6):
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
                func.upper(Transaction.transaction_type).in_([TransactionType.INCOME.value, TransactionType.EXPENSE.value]),
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
                t_type = "Pengeluaran" if txn.transaction_type.upper() == TransactionType.EXPENSE else "Pemasukan"
                summary_lines.append(f"- {txn.transaction_date.strftime('%Y-%m-%d')}: {t_type} Rp{txn.amount} ({cat_name}) - {txn.description or ''}")
                if txn.transaction_type.upper() == TransactionType.INCOME:
                    total_income += txn.amount
                elif txn.transaction_type.upper() == TransactionType.EXPENSE:
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
