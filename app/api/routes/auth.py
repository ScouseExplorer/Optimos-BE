from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.schemas.user import UserCreate, User
from app.schemas.token import Token, RefreshRequest, LogoutRequest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_token_remaining_ttl,
)
from app.core.config import settings
from app.db.session import get_db
from app.services.user_service import UserService
from app.services.token_service import blacklist_token, is_token_blacklisted
from app.services.profile_service import ProfileService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
user_service = UserService()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check email uniqueness
    if await user_service.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check username uniqueness (avoids raw DB unique-constraint error)
    if await user_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    return await user_service.create_user(db, user_data)


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username or email and get access + refresh tokens."""
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Record successful login (resets failed-attempt counter, stores IP)
    ProfileService.record_login(
        db, user.id, ip_address=request.client.host if request.client else None
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair (refresh rotation)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    # Reject already-revoked refresh tokens
    if is_token_blacklisted(body.refresh_token):
        raise credentials_exception

    payload = decode_refresh_token(body.refresh_token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await user_service.get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception

    # Rotate: blacklist the old refresh token so it cannot be reused
    blacklist_token(
        body.refresh_token,
        expiration_seconds=get_token_remaining_ttl(body.refresh_token),
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    body: LogoutRequest = Body(default=LogoutRequest()),
    current_user: User = Depends(get_current_user),
):
    """Revoke the current access token and optionally the refresh token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    access_token = auth_header.split(" ", 1)[1]
    blacklist_token(access_token, expiration_seconds=get_token_remaining_ttl(access_token))

    if body.refresh_token:
        blacklist_token(
            body.refresh_token,
            expiration_seconds=get_token_remaining_ttl(body.refresh_token),
        )

    return {"detail": "Successfully logged out"}
