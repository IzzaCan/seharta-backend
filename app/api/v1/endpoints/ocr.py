from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.ai_service import AiService
from app.services.receipt_service import ReceiptService

router = APIRouter()

def get_receipt_service() -> ReceiptService:
    ai_service = AiService()
    return ReceiptService(ai_service)

@router.post("/scan")
def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service)
):
    """
    Endpoint to upload a receipt image, perform OCR and parse transaction data
    using Gemini AI. Requires user authentication.
    """
    result = receipt_service.scan_receipt(file)
    return result
