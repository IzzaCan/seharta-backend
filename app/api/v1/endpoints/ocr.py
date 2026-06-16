from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.ai_service import AiService
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
        
        # Normalisasi MIME type untuk menghindari error dari Gemini (Gemini menolak application/octet-stream)
        safe_mime_type = "image/jpeg"
        if content_type.startswith("image/") and content_type != "application/octet-stream":
            safe_mime_type = content_type
        else:
            # Tebak dari ekstensi
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            mapping = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp',
                'heic': 'image/heic',
                'heif': 'image/heif'
            }
            safe_mime_type = mapping.get(ext, 'image/jpeg')
            
        # Panggil AiService
        ai_service = AiService()
        result = ai_service.parse_receipt(
            file_bytes=file_bytes, 
            content_type=safe_mime_type
        )
        
        return result
        
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses struk: {str(e)}")
