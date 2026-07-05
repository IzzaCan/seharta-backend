from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.services.ai_service import AiService
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsResponse

router = APIRouter()

def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    ai_service = AiService()
    return AnalyticsService(db, ai_service)

@router.get("", response_model=AnalyticsResponse)
def get_analytics(
    month: Optional[int] = Query(None, description="Target month (1-12)"),
    year: Optional[int] = Query(None, description="Target year"),
    ownership_type: str = Query("ALL", regex="^(ALL|JOINT|PERSONAL)$"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get aggregated dashboard statistics (BFF).
    """
    return analytics_service.get_analytics(
        family_id=current_user.family_id,
        month=month,
        year=year,
        ownership_type=ownership_type,
        start_date=start_date,
        end_date=end_date
    )

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


