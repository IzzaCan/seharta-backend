import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.email_verification import EmailVerification
from app.repositories.user_repository import UserRepository


class OTPService:
    """Service handling OTP business logic and database interactions"""

    def __init__(self, db: Session):
        self.db = db

    def generate_otp(self, user: User, purpose: str = "email_verification") -> str:
        """
        Invalidates existing active OTPs, generates a new one, saves it, and returns the OTP value.
        """
        # Invalidate old OTPs
        active_otps = self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.is_used == False,
            EmailVerification.purpose == purpose
        ).all()
        
        for old_otp in active_otps:
            old_otp.is_used = True

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Create new OTP record (valid for 10 minutes)
        new_otp = EmailVerification(
            user_id=user.id,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            attempt_count=0,
            is_used=False,
            purpose=purpose
        )
        
        self.db.add(new_otp)
        self.db.commit()
        
        return otp_code

    def verify_otp(self, email: str, otp: str, purpose: str = "email_verification") -> bool:
        """
        Verifies the provided OTP for the given email.
        """
        # Find user
        user = UserRepository.get_by_email(self.db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email tidak ditemukan"
            )

        # Find active OTP for user
        active_otp = self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.is_used == False,
            EmailVerification.purpose == purpose
        ).order_by(EmailVerification.created_at.desc()).first()

        if not active_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP tidak ditemukan atau sudah digunakan"
            )

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

        # If correct
        user.is_verified = True
        active_otp.is_used = True
        self.db.commit()
        
        return True

    def resend_otp(self, user: User, purpose: str = "email_verification") -> str:
        """
        Generates and returns a new OTP for resending.
        """
        return self.generate_otp(user, purpose)
