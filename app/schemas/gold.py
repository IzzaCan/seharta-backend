from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date

class GoldPriceItem(BaseModel):
    id: str = Field(alias="_id", description="Internal MongoDB ID")
    source: str
    buy_price: int
    sell_price: int
    currency: str = "IDR"
    market_date: date
    scraped_at: datetime

    model_config = {
        "populate_by_name": True
    }

class GoldPriceLatestResponse(BaseModel):
    success: bool = True
    data: Optional[GoldPriceItem]

class GoldPriceHistoryResponse(BaseModel):
    success: bool = True
    data: List[GoldPriceItem]
    total: int
