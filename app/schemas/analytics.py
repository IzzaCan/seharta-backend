from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AnalyticsOverview(BaseModel):
    net_worth: float = 0.0
    total_liquidity: float = 0.0
    total_asset_value: float = 0.0
    savings_rate_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsIncomeVsExpense(BaseModel):
    total_income: float = 0.0
    total_expense: float = 0.0
    net_surplus: float = 0.0
    expense_to_income_ratio: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsCategoryBreakdown(BaseModel):
    category_id: UUID
    category_name: str
    amount: float = 0.0
    percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsBudgetAnalysis(BaseModel):
    total_budgeted: float = 0.0
    total_spent_on_budget: float = 0.0
    overall_adherence_percentage: float = 0.0
    over_budget_categories_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AssetDistributionByType(BaseModel):
    wallets: float = 0.0
    physical_assets: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AssetDistributionByOwnership(BaseModel):
    joint: float = 0.0
    personal: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AssetDistributionByCategory(BaseModel):
    category_id: UUID
    category_name: str
    icon_name: Optional[str] = None
    asset_count: int = 0
    total_value: float = 0.0
    percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsAssetDistribution(BaseModel):
    by_type: AssetDistributionByType
    by_ownership: AssetDistributionByOwnership
    by_category: List[AssetDistributionByCategory]

    model_config = ConfigDict(from_attributes=True)


class UserSpenderSummary(BaseModel):
    user_id: UUID
    user_name: str
    total_spent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class UserActivitySummary(BaseModel):
    user_id: UUID
    user_name: str
    transaction_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BehavioralSummary(BaseModel):
    highest_spender: Optional[UserSpenderSummary] = None
    most_active_member: Optional[UserActivitySummary] = None

    model_config = ConfigDict(from_attributes=True)


class UserSpendingDistribution(BaseModel):
    user_id: UUID
    user_name: str
    avatar_url: Optional[str] = None
    total_spent: float = 0.0
    transaction_count: int = 0
    average_transaction: float = 0.0
    percentage_of_total: float = 0.0
    favorite_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserSpendingHabit(BaseModel):
    user_id: UUID
    user_name: str
    most_active_day: Optional[str] = None
    most_active_hour: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsBehavioralAnalytics(BaseModel):
    summary: BehavioralSummary
    spending_distribution: List[UserSpendingDistribution]
    spending_habit: List[UserSpendingHabit]

    model_config = ConfigDict(from_attributes=True)


class AnalyticsCurrentFilter(BaseModel):
    month: int = 0
    year: int = 0
    ownership_type: str = "ALL"

    model_config = ConfigDict(from_attributes=True)


class AnalyticsFilterMetadata(BaseModel):
    earliest_transaction_date: Optional[datetime] = None
    available_years: List[int] = []
    available_months: List[int] = []
    current_filter: AnalyticsCurrentFilter

    model_config = ConfigDict(from_attributes=True)


class AnalyticsResponse(BaseModel):
    overview: AnalyticsOverview
    income_vs_expense: AnalyticsIncomeVsExpense
    category_breakdown: List[AnalyticsCategoryBreakdown]
    budget_analysis: AnalyticsBudgetAnalysis
    asset_distribution: AnalyticsAssetDistribution
    behavioral_analytics: AnalyticsBehavioralAnalytics
    filter_metadata: AnalyticsFilterMetadata

    model_config = ConfigDict(from_attributes=True)
