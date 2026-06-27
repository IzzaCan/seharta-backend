from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
import shutil
import uuid
import os
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserGoogleLogin,
    TokenResponse,
    UserResponse,
    UserUpdateProfile,
    UserUpdatePassword,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

from app.core.security import verify_password, hash_password

from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.password_reset_service import PasswordResetService

from app.api.dependencies import get_current_user

from app.models.user import User


router = APIRouter()


# Register
@router.post(
    "/register",
    response_model=TokenResponse
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):

    auth_service = AuthService(db)

    return auth_service.register(user_data)


# Verify Email
@router.post("/verify-email")
def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    otp_service = OTPService(db)
    otp_service.verify_otp(verify_data.email, verify_data.otp)
    
    return {"message": "Email berhasil diverifikasi"}


# Resend Verification
@router.post("/resend-verification")
def resend_verification(
    resend_data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    auth_service.resend_verification(resend_data.email)
    
    return {"message": "OTP verifikasi telah dikirim ulang ke email Anda"}


# Login
@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):

    auth_service = AuthService(db)

    return auth_service.login(login_data)


# Forgot Password
@router.post("/forgot-password")
def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    service = PasswordResetService(db)
    service.forgot_password(forgot_data.email)
    
    return {"message": "Jika email terdaftar, instruksi reset password telah dikirim."}


# Reset Password
@router.post("/reset-password")
def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    service = PasswordResetService(db)
    service.reset_password(
        reset_data.email, 
        reset_data.otp, 
        reset_data.new_password
    )
    
    return {"message": "Password berhasil diubah. Silakan login kembali."}


# Google Login
@router.post(
    "/google",
    response_model=TokenResponse
)
def google_login(
    google_data: UserGoogleLogin,
    db: Session = Depends(get_db)
):

    auth_service = AuthService(db)

    return auth_service.google_login(
        google_data.id_token
    )


# Current User
@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):

    return UserResponse.model_validate(current_user)

# Logout
@router.post("/logout")
def logout():

    """
    JWT logout is handled client-side
    by deleting the stored token.
    """

    return {
        "message": "Successfully logged out"
    }

# Update Profile
@router.put("/profile", response_model=UserResponse)
def update_profile(
    data: UserUpdateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.full_name = data.full_name
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)

# Update Password
@router.put("/password", response_model=UserResponse)
def update_password(
    data: UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="Pengguna menggunakan login eksternal")
        
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Password lama salah")
        
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)

# Upload Avatar
@router.post("/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file extension instead of content_type because Flutter Web 
    # multipart without explicit MediaType defaults to application/octet-stream
    if not file.filename:
        raise HTTPException(status_code=400, detail="File tidak ditemukan")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
        raise HTTPException(status_code=400, detail="File harus berupa gambar (jpg, png, webp, gif)")
        
    filename = f"{uuid.uuid4()}.{file_ext}"
    filepath = f"app/static/avatars/{filename}"
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update user
    # Provide the full url for easier frontend loading, or just relative path. 
    # Usually relative path /static/avatars/... works with baseUrl on frontend
    current_user.avatar_url = f"/static/avatars/{filename}"
    
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)

# Google Config
@router.get("/google/config")
def get_google_config():
    from app.core.config import settings
    return {"client_id": settings.GOOGLE_CLIENT_ID}