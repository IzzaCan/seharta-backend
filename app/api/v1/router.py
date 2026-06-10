from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.ocr import router as ocr_router
from app.api.v1.endpoints.family import router as family_router
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