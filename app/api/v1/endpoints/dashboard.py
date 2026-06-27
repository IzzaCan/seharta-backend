from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_family_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/", response_model=DashboardResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_family_user)
) -> Any:
    """
    Get family dashboard summary including total balance, income/expense this month,
    active wallets, and recent transactions.
    """
    service = DashboardService(db)
    return service.get_dashboard(current_user.family_id)
