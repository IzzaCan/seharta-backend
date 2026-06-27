from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.services.ai_service import AiService
from app.services.analytics_service import AnalyticsService

router = APIRouter()

def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    ai_service = AiService()
    return AnalyticsService(db, ai_service)

@router.get("/insight")
def get_financial_insight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Generate financial insight using Gemini AI based on recent family transactions.
    """
    insight_text = analytics_service.get_financial_insight(current_user.family_id)
    return {"insight": insight_text}

@router.get("/summary")
def get_balance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get family balance summary and percentage change compared to 30 days ago.
    """
    return analytics_service.get_balance_summary(current_user.family_id)
