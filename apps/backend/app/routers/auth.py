import hmac

from fastapi import APIRouter

from app.auth.jwt import create_access_token
from app.config import settings
from app.errors import AppError
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    username_ok = hmac.compare_digest(payload.username, settings.local_auth_username)
    password_ok = hmac.compare_digest(payload.password, settings.local_auth_password)
    if not (username_ok and password_ok):
        raise AppError(401, "AUTH_INVALID", "Invalid username or password")
    return LoginResponse(
        access_token=create_access_token(settings.local_auth_user_id, settings.local_auth_email)
    )
