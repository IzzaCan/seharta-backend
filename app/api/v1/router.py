from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.ocr import router as ocr_router
from app.api.v1.endpoints.family import router as family_router
from app.api.v1.endpoints.wallet import router as wallet_router
from app.api.v1.endpoints.category import router as category_router
from app.api.v1.endpoints.transaction import router as transaction_router
from app.api.v1.endpoints.analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    ocr_router,
    prefix="/ocr",
    tags=["Receipt OCR"]
)

api_router.include_router(
    family_router,
    prefix="/family",
    tags=["Family"]
)

api_router.include_router(
    wallet_router,
    prefix="/wallets",
    tags=["Wallets"]
)

api_router.include_router(
    category_router,
    prefix="/categories",
    tags=["Categories"]
)

api_router.include_router(
    transaction_router,
    prefix="/transactions",
    tags=["Transactions"]
)

api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["Analytics"]
)