from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import google.auth.transport.requests
from google.oauth2 import id_token
from google.auth.exceptions import GoogleAuthError

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)

from app.models.user import User

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse
)

from app.repositories.user_repository import UserRepository
from app.services.otp_service import OTPService
from app.services.email_service import EmailService


from app.core.logger import log_activity

class AuthService:
    """Authentication business logic"""

    def __init__(self, db: Session):
        self.db = db

    # Register
    def register(
        self,
        user_data: UserCreate
    ) -> TokenResponse:

        # Check existing email
        existing_user = UserRepository.get_by_email(
            self.db,
            user_data.email
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        user = User(
            full_name=user_data.full_name,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            is_active=True,
            is_verified=False
        )

        # Save user
        user = UserRepository.create(self.db, user)

        # Generate OTP
        otp_service = OTPService(self.db)
        otp_code = otp_service.generate_otp(user)

        # Send Verification Email
        try:
            EmailService.send_verification_email(user.email, otp_code)
        except Exception as e:
            # Log error but don't delete OTP, allow user to resend later
            import logging
            logging.error(f"Failed to send email to {user.email}: {str(e)}")

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Log activity
        log_activity(
            action="USER_REGISTER",
            user_id=str(user.id),
            detail=f"New user registered: {user.email}",
            endpoint="POST /api/v1/auth/register"
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )
        

    # Login
    def login(
        self,
        login_data: UserLogin
    ) -> TokenResponse:

        # Find user
        user = UserRepository.get_by_email(
            self.db,
            login_data.email
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # OAuth-only account
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account uses Google login"
            )

        # Verify password
        if not verify_password(
            login_data.password,
            user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check active status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
            
        # Check verified status
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email belum diverifikasi"
            )

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))


        # Log activity
        log_activity(
            action="USER_LOGIN",
            user_id=str(user.id),
            detail=f"User login: {user.email}",
            endpoint="POST /api/v1/auth/login"
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )

    # Resend Verification
    def resend_verification(self, email: str) -> None:
        user = UserRepository.get_by_email(self.db, email)
        if not user:
            # Silently return to prevent email enumeration, or raise error. 
            # We'll raise error for better UX in mobile app.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email tidak ditemukan"
            )
            
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah diverifikasi"
            )
            
        otp_service = OTPService(self.db)
        otp_code = otp_service.resend_otp(user)
        
        try:
            EmailService.send_verification_email(user.email, otp_code)
        except Exception as e:
            import logging
            logging.error(f"Failed to send email to {user.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mengirim email verifikasi"
            )

    # Google Login
    def google_login(
        self,
        google_token: str
    ) -> TokenResponse:

        try:
            # Verify Google token
            request = google.auth.transport.requests.Request()

            id_info = id_token.verify_oauth2_token(
                google_token,
                request,
                settings.GOOGLE_CLIENT_ID
            )

            # Extract Google user info
            google_id = id_info.get("sub")
            email = id_info.get("email")
            full_name = id_info.get("name", "")
            avatar_url = id_info.get("picture")

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google account email not found"
                )

            # Find existing user
            user = UserRepository.get_by_google_id(
                self.db,
                google_id
            )

            # Fallback check by email
            if not user:
                user = UserRepository.get_by_email(
                    self.db,
                    email
                )

            # Create new user
            if not user:

                user = User(
                    full_name=full_name,
                    email=email,
                    google_id=google_id,
                    avatar_url=avatar_url,
                    password_hash=None,
                    is_active=True,
                    is_verified=True
                )

                user = UserRepository.create(self.db, user)

            else:
                # Update Google info if needed
                updated = False

                if not user.google_id:
                    user.google_id = google_id
                    updated = True

                if not user.avatar_url and avatar_url:
                    user.avatar_url = avatar_url
                    updated = True

                if updated:
                    user = UserRepository.update(
                        self.db,
                        user
                    )

            # Generate tokens
            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(str(user.id))

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                user=UserResponse.model_validate(user)
            )

        except GoogleAuthError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )

    # Get User
    def get_user_by_id(
        self,
        user_id: UUID
    ) -> User:

        user = UserRepository.get_by_id(
            self.db,
            user_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user