from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserGoogleLogin,
    TokenResponse,
    UserResponse
)

from app.services.auth_service import AuthService

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