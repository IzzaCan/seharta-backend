import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> None:
        """
        Private helper to send an email using Resend API.
        This enforces the Best Effort Principle; failures are logged but not raised.
        """
        try:
            resend.api_key = settings.RESEND_API_KEY
            
            params = {
                "from": f"{settings.RESEND_SENDER_NAME} <{settings.RESEND_SENDER_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Email sent to {to_email}, subject: '{subject}', response: {response}")
            
        except Exception as e:
            # Best Effort Principle: Log the error, but do NOT raise exception.
            # This ensures database transactions and main API flows are not interrupted by email failures.
            logger.error(f"Failed to send email to {to_email} (subject: '{subject}'): {str(e)}")

    @staticmethod
    def send_verification_email(email: str, otp_code: str) -> None:
        """
        Sends an email with the verification OTP.
        """
        html_content = f"""
        <h2>Verifikasi Email Seharta</h2>
        <p>Halo,</p>
        <p>Terima kasih telah mendaftar di Seharta. Kode verifikasi (OTP) Anda adalah:</p>
        <h1 style="color: #4CAF50; letter-spacing: 5px;">{otp_code}</h1>
        <p>Kode ini akan kadaluarsa dalam 10 menit.</p>
        <p>Jika Anda tidak merasa mendaftar di Seharta, abaikan email ini.</p>
        <br>
        <p>Salam hangat,<br>Tim Seharta</p>
        """
        
        EmailService._send_email(
            to_email=email,
            subject="Kode Verifikasi Seharta",
            html_content=html_content
        )

    @staticmethod
    def send_liquidation_email(email: str, pdf_relative_url: str) -> None:
        """
        Sends a liquidation report email with the absolute URL to download the PDF.
        """
        # Ensure API_BASE_URL doesn't end with slash, and pdf_url starts with slash
        base_url = settings.API_BASE_URL.rstrip("/")
        pdf_path = pdf_relative_url if pdf_relative_url.startswith("/") else f"/{pdf_relative_url}"
        absolute_pdf_url = f"{base_url}{pdf_path}"
        
        html_content = f"""
        <h2>Pemberitahuan Likuidasi Akun Keluarga</h2>
        <p>Halo,</p>
        <p>Tautan akun keluarga Anda di aplikasi Seharta telah resmi diputuskan.</p>
        <p>Berikut adalah tautan untuk mengunduh dokumen Berita Acara penyelesaian aset bersama Anda:</p>
        <p>
            <a href="{absolute_pdf_url}" style="color: #4CAF50; font-weight: bold; text-decoration: none; padding: 10px 15px; border: 1px solid #4CAF50; border-radius: 5px; display: inline-block;">
                Unduh Berita Acara Likuidasi
            </a>
        </p>
        <p>Harap simpan dokumen ini sebagai bukti mutlak.</p>
        <br>
        <p>Salam hangat,<br>Tim Seharta</p>
        """
        
        EmailService._send_email(
            to_email=email,
            subject="Dokumen Berita Acara Likuidasi Seharta",
            html_content=html_content
        )
