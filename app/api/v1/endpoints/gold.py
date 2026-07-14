from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from datetime import date
from app.schemas.gold import GoldPriceLatestResponse, GoldPriceHistoryResponse
from app.services.gold_service import GoldService

router = APIRouter()
gold_service = GoldService()

@router.get("/latest", response_model=GoldPriceLatestResponse)
def get_latest_gold_price():
    """
    Retrieve the latest recorded gold price.
    """
    try:
        latest = gold_service.get_latest_price()
        return GoldPriceLatestResponse(
            success=True,
            data=latest
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the latest gold price."
        )

@router.get("/history", response_model=GoldPriceHistoryResponse)
def get_gold_price_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=1000, description="Pagination limit"),
    market_date_from: Optional[date] = Query(None, description="Start market date for filtering"),
    market_date_to: Optional[date] = Query(None, description="End market date for filtering")
):
    """
    Retrieve historical gold prices with optional filtering and pagination.
    """
    try:
        skip = (page - 1) * limit
        results, total = gold_service.get_history(
            skip=skip,
            limit=limit,
            market_date_from=market_date_from,
            market_date_to=market_date_to
        )
        return GoldPriceHistoryResponse(
            success=True,
            data=results,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching gold price history."
        )
