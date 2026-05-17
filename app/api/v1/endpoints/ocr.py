from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.ocr_service import OcrService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/scan")
def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to upload a receipt image, perform OCR and parse transaction data
    using Gemini AI. Requires user authentication.
    """
    # Validasi tipe data file (toleransi application/octet-stream atau deteksi ekstensi)
    content_type = file.content_type or ""
    filename = file.filename or ""
    is_image = (
        content_type.startswith("image/") or 
        content_type == "application/octet-stream" or
        filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic"))
    )
    if not is_image:
        raise HTTPException(
            status_code=400, 
            detail="Berkas yang diunggah harus berupa gambar (JPEG, PNG, dll.)"
        )
        
    try:
        # Baca byte data dari file
        file_bytes = file.file.read()
        
        # Panggil OcrService
        ocr_service = OcrService()
        result = ocr_service.parse_receipt(
            file_bytes=file_bytes, 
            content_type=file.content_type
        )
        
        return result
        
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses struk: {str(e)}")
