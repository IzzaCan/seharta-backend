import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password
from app.models.email_verification import EmailVerification
from app.repositories.user_repository import UserRepository
from app.services.otp_service import OTPService
from app.services.email_service import EmailService

class PasswordResetService:
    """Service handling password reset business logic"""

    def __init__(self, db: Session):
        self.db = db

    def forgot_password(self, email: str) -> None:
        """
        Validates email, generates password reset OTP, and sends email.
        Security: Never reveal if email doesn't exist, just return successfully.
        """
        user = UserRepository.get_by_email(self.db, email)
        
        # Security: Return early without error if user not found
        if not user:
            return
            
        # Check if local provider
        if not user.password_hash or user.google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Akun ini menggunakan Google Sign-In dan tidak memiliki password lokal."
            )

        try:
            # Generate OTP with purpose password_reset
            otp_service = OTPService(self.db)
            otp_code = otp_service.generate_otp(user, purpose="password_reset")
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

        # Send Email
        try:
            # Assuming EmailService has a method for this, if not we'll use send_verification_email for now
            # Wait, prompt says: Reuse EmailService and existing OTP generation logic. 
            # So I will just use EmailService.send_verification_email
            EmailService.send_verification_email(user.email, otp_code)
        except Exception as e:
            logging.error(f"Failed to send password reset email to {user.email}: {str(e)}")

    def reset_password(self, email: str, otp: str, new_password: str) -> None:
        """
        Validates OTP and atomically updates the password.
        """
        user = UserRepository.get_by_email(self.db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email tidak ditemukan"
            )

        # Get active password reset OTP
        active_otp = self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.is_used == False,
            EmailVerification.purpose == "password_reset"
        ).order_by(EmailVerification.created_at.desc()).first()

        if not active_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP tidak ditemukan atau sudah digunakan"
            )

        try:
            # Check expiration
            if datetime.now(timezone.utc) > active_otp.expires_at:
                active_otp.is_used = True
                self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP sudah kadaluarsa"
                )

            # Check correctness
            if active_otp.otp_code != otp:
                active_otp.attempt_count += 1
                
                if active_otp.attempt_count >= 5:
                    active_otp.is_used = True
                    self.db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Terlalu banyak percobaan. OTP telah hangus, silakan minta ulang."
                    )
                    
                self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"OTP salah. Sisa percobaan: {5 - active_otp.attempt_count}"
                )

            # Valid OTP: Update password, mark OTP used, invalidate other OTPs
            user.password_hash = hash_password(new_password)
            active_otp.is_used = True
            
            # Invalidate other active password reset OTPs just in case
            other_active_otps = self.db.query(EmailVerification).filter(
                EmailVerification.user_id == user.id,
                EmailVerification.is_used == False,
                EmailVerification.purpose == "password_reset",
                EmailVerification.id != active_otp.id
            ).all()
            for other_otp in other_active_otps:
                other_otp.is_used = True

            self.db.commit()
        except HTTPException as he:
            raise he
        except Exception as e:
            # Rollback if anything fails
            self.db.rollback()
            raise e
