import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_verification_email(email: str, otp_code: str) -> None:
        """
        Sends an email with the verification OTP.
        """
        try:
            resend.api_key = settings.RESEND_API_KEY
            
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
            
            params = {
                "from": f"{settings.RESEND_SENDER_NAME} <{settings.RESEND_SENDER_EMAIL}>",
                "to": [email],
                "subject": "Kode Verifikasi Seharta",
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Verification email sent to {email}, response: {response}")
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            raise e
