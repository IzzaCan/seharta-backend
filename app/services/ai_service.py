import json
import logging
import re
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

class AiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                logger.info("Gemini AI successfully configured.")
            except Exception as e:
                logger.error(f"Error configuring Gemini AI: {e}")
        else:
            logger.warning("GEMINI_API_KEY is not set. AiService will operate in MOCK fallback mode.")

    def parse_receipt(self, file_bytes: bytes, content_type: str = "image/jpeg") -> dict:
        """
        Parses a receipt image using Gemini 2.5 Flash.
        If no API key is present, falls back to a smart mock response.
        """
        if not self.api_key:
            logger.info("No Gemini API key set. Returning mock receipt extraction response.")
            return self._get_mock_response()

        # Dapatkan tanggal hari ini secara dinamis untuk diinjeksikan ke prompt
        from datetime import datetime
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

        try:
            # Inisialisasi model gemini-2.5-flash
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # Format image data untuk SDK Gemini
            image_part = {
                "mime_type": content_type,
                "data": file_bytes
            }

            logger.info("Sending receipt image to Gemini 2.5 Flash...")
            response = model.generate_content([image_part, prompt])
            
            # Bersihkan dan parsing response teks ke JSON
            response_text = response.text.strip()
            logger.info(f"Raw response from Gemini: {response_text}")

            parsed_data = self._clean_and_parse_json(response_text)
            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing receipt with Gemini: {e}")
            # Jika API error (misalnya quota exceeded atau key tidak valid), gunakan fallback mock agar user flow tidak pecah
            logger.info("Falling back to simulated parsing due to API error.")
            return self._get_mock_response(error_info=str(e))

    def _clean_and_parse_json(self, text: str) -> dict:
        """
        Helper to extract and parse JSON from the model response, 
        even if it wraps it in markdown code blocks.
        """
        # Hapus markdown codeblocks jika model keras kepala menyisipkannya
        cleaned = text
        if "```json" in text:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if match:
                cleaned = match.group(1)
        elif "```" in text:
            match = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if match:
                cleaned = match.group(1)
                
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse text as JSON. Text: {cleaned}. Error: {jde}")
            raise ValueError("Respons dari AI OCR tidak berformat JSON yang valid")

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

    def generate_financial_insight(self, transactions_summary: str) -> str:
        """
        Generates a short financial insight based on recent transactions using Gemini 2.5 Flash.
        """
        if not self.api_key:
            logger.info("No Gemini API key set. Returning mock financial insight.")
            return "Pengeluaran Anda bulan ini stabil. Pertimbangkan untuk menyisihkan lebih banyak ke tabungan darurat."

        prompt = f"""
        Anda adalah asisten perencana keuangan keluarga yang cerdas dan ramah.
        Berikut adalah ringkasan transaksi terbaru dari sebuah keluarga:
        {transactions_summary}
        
        Berikan 1 hingga 2 kalimat insight (wawasan) singkat, positif, dan membangun mengenai pengeluaran atau pemasukan mereka.
        Gunakan bahasa Indonesia yang santai, ringkas, dan memotivasi. Tidak perlu memberikan salam.
        Langsung berikan insight-nya.
        """

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            logger.info("Sending transaction summary to Gemini 2.5 Flash for insights...")
            response = model.generate_content(prompt)
            
            insight = response.text.strip()
            logger.info(f"Generated insight: {insight}")
            return insight

        except Exception as e:
            logger.error(f"Error generating financial insight with Gemini: {e}")
            return "Fokus pada pengeluaran prioritas minggu ini. Terus pertahankan pengelolaan keuangan yang baik!"

