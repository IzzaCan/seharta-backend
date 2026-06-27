import logging
from datetime import datetime
from fastapi import UploadFile, HTTPException

from app.services.ai_service import AiService

logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self, ai_service: AiService):
        self.ai_service = ai_service

    def scan_receipt(self, file: UploadFile) -> dict:
        """
        Validates file, normalizes MIME type, reads file content and parses receipt using Gemini AI.
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
                
            if self.ai_service.is_mock_mode():
                logger.info("No Gemini API key set. Returning mock receipt extraction response.")
                return self._get_mock_response()

            # Dapatkan tanggal hari ini secara dinamis untuk diinjeksikan ke prompt
            current_date_str = datetime.now().strftime("%Y-%m-%d")

            # Prompt untuk memandu Gemini mengekstraksi data dalam bentuk JSON terstruktur
            prompt = f"""
            You are a highly capable receipt and transaction slip parsing assistant.
            Analyze the image carefully. It can be a shopping receipt (e.g. Indomaret, Alfamart, supermarket), a restaurant bill, or a bank/ATM transaction slip (e.g., BCA ATM receipt, transfer slip, payment confirmation).
            
            Extract the key transaction details and return ONLY a raw JSON object matching the schema below.
            Do not explain anything. Do not wrap the JSON in Markdown code blocks (do not use ```json ... ```).
            
            Guidelines for different receipt types:
            1. Shopping/Restaurant Receipts:
               - merchant_name: The store/restaurant name (e.g., "Indomaret", "Starbucks").
               - total_amount: The final amount paid.
               - items: List of individual item descriptions.
               - category: Choose the best match ('Makanan', 'Belanja', 'Transportasi', 'Hiburan', 'Kesehatan', 'Tagihan', 'Lainnya').
            2. Bank/ATM/Transfer Receipts:
               - merchant_name: The bank name or transfer service (e.g., "ATM BCA", "Bank Mandiri", "Transfer BCA").
               - total_amount: The transfer, withdrawal, or payment amount.
               - items: Summarize the transaction details (e.g., ["Tarik Tunai", "Transfer ke Rekening 123456", "Biaya Admin Rp 2500"]).
               - category: Set to 'Tagihan' or 'Lainnya' depending on context.
            
            Guidelines for Dates:
            - Carefully read the transaction date from the receipt.
            - Recognize Indonesian date formats like DD/MM/YY, DD-MM-YYYY, DD MMM YYYY, or TGL: DD/MM/YY (e.g., "17/05/26" should be parsed as "2026-05-17").
            - If the transaction date is not clearly visible or not present on the receipt, you MUST use the current system date of {current_date_str}.
            
            Output Schema:
            {{
              "merchant_name": "String",
              "date": "String (Transaction date in YYYY-MM-DD format)",
              "total_amount": Float (The final numeric transaction value, without currency symbols, e.g., 50000.0)",
              "category": "String (Choose exactly one: 'Makanan', 'Belanja', 'Transportasi', 'Hiburan', 'Kesehatan', 'Tagihan', 'Lainnya')",
              "items": ["Array of Strings listing the items or transaction details"]
            }}
            """
                
            # Panggil AiService
            result = self.ai_service.generate_json(
                prompt=prompt,
                image_bytes=file_bytes,
                mime_type=safe_mime_type
            )
            
            return result
            
        except ValueError as ve:
            raise HTTPException(status_code=422, detail=str(ve))
        except Exception as e:
            if not self.ai_service.is_mock_mode():
                logger.error(f"Error parsing receipt with Gemini: {e}")
                logger.info("Falling back to simulated parsing due to API error.")
                return self._get_mock_response(error_info=str(e))
            raise HTTPException(status_code=500, detail=f"Gagal memproses struk: {str(e)}")

    def _get_mock_response(self, error_info: str = None) -> dict:
        """
        Returns a highly realistic simulated OCR response for testing.
        """
        notice = " [Mock Fallback]" if error_info else " [Simulasi]"
        return {
            "merchant_name": f"Indomaret Juanda{notice}",
            "date": "2026-05-17",
            "total_amount": 145000.0,
            "category": "Belanja",
            "items": [
                "Susu Cair UHT 1L (2x)",
                "Roti Kasur Cokelat",
                "Air Mineral 600ml",
                "Sabun Mandi Cair"
            ]
        }
