from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import settings
from app.core.logger import gold_logger as logger

MONGO_DB_NAME = "seharta_gold_db"

# Global MongoDB client and database instance (Singleton pattern)
mongo_client = None
db = None

def init_mongo():
    global mongo_client, db
    
    if mongo_client is not None:
        return
        
    try:
        mongo_client = MongoClient(settings.MONGODB_URL)
        db = mongo_client[MONGO_DB_NAME]
        
        # Initialize collection
        collection = db["gold_prices"]
        
        # Unik indeks untuk mendeteksi duplikat secara otomatis di level database
        collection.create_index(
            [("source", ASCENDING), ("market_date", ASCENDING)],
            unique=True,
            name="idx_unique_source_market_date"
        )
        
        collection.create_index([("scraped_at", DESCENDING)])
        
        logger.info("MongoDB initialized and indexes created successfully.")
    except Exception as e:
        logger.error("Failed to initialize MongoDB: %s", e)

def get_gold_collection():
    if db is None:
        init_mongo()
    return db["gold_prices"]

def close_mongo():
    global mongo_client, db
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
        db = None
