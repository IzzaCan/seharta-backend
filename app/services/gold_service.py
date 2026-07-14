from typing import List, Optional
from datetime import date
from pymongo import DESCENDING
from app.db.mongo import get_gold_collection

class GoldService:
    def __init__(self):
        self.collection = get_gold_collection()

    def get_latest_price(self) -> Optional[dict]:
        """
        Retrieves the latest gold price based on timestamp.
        """
        doc = self.collection.find_one({}, sort=[("scraped_at", DESCENDING)])
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def get_history(self, skip: int = 0, limit: int = 100, market_date_from: Optional[date] = None, market_date_to: Optional[date] = None) -> tuple[List[dict], int]:
        """
        Retrieves historical gold prices with optional date range filtering and pagination.
        """
        query = {}
        if market_date_from or market_date_to:
            query["market_date"] = {}
            if market_date_from:
                query["market_date"]["$gte"] = market_date_from.strftime("%Y-%m-%d")
            if market_date_to:
                query["market_date"]["$lte"] = market_date_to.strftime("%Y-%m-%d")

        total = self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("market_date", DESCENDING).skip(skip).limit(limit)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
            
        return results, total
