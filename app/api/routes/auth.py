from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.schemas.user import UserCreate, User
from app.schemas.token import Token, RefreshRequest, LogoutRequest
from app.schemas.auth import EmailActionRequest, PasswordResetConfirm, TokenActionRequest
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
from app.services.auth_action_service import AuthActionService
from app.services.email_service import EmailDeliveryError, email_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
user_service = UserService()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        email_service.ensure_configured()
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        ) from exc

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

    user = await user_service.create_user(db, user_data)
    db_user = await user_service.get_user_by_id(db, user.id)
    try:
        await AuthActionService.send_verification(db, db_user)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send email verification. Please try again later.",
        ) from exc
    return user


@router.post("/email-verification/request", status_code=status.HTTP_202_ACCEPTED)
async def request_email_verification(
    body: EmailActionRequest,
    db: Session = Depends(get_db),
):
    """Send an email verification link when the account still needs verification."""
    try:
        email_service.ensure_configured()
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        ) from exc

    user = await user_service.get_user_by_email(db, str(body.email))
    if user and not user.email_verified_at:
        try:
            await AuthActionService.send_verification(db, user)
        except EmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send email verification. Please try again later.",
            ) from exc
    return {"detail": "If the account needs verification, an email has been sent."}


@router.post("/email-verification/confirm")
async def confirm_email_verification(
    body: TokenActionRequest,
    db: Session = Depends(get_db),
):
    """Verify an email address using its single-use token."""
    if not AuthActionService.consume_email_verification(db, body.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token.",
        )
    return {"detail": "Email address verified."}


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: EmailActionRequest,
    db: Session = Depends(get_db),
):
    """Send a password reset link without revealing whether the account exists."""
    try:
        email_service.ensure_configured()
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        ) from exc

    user = await user_service.get_user_by_email(db, str(body.email))
    if user and user.email_verified_at:
        try:
            await AuthActionService.send_password_reset(db, user)
        except EmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send password reset email. Please try again later.",
            ) from exc
    return {"detail": "If the account exists, a password reset email has been sent."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Set a new password using a single-use reset token."""
    if not AuthActionService.reset_password(db, body.token, body.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )
    return {"detail": "Password has been reset. Please log in again."}


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
    if not user.is_active or not user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before logging in.",
        )

    # Record successful login (resets failed-attempt counter, stores IP)
    ProfileService.record_login(
        db, user.id, ip_address=request.client.host if request.client else None
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "auth_version": user.auth_version,
        },
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "auth_version": user.auth_version}
    )

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
    if not user.is_active or payload.get("auth_version", 0) != user.auth_version:
        raise credentials_exception

    # Rotate: blacklist the old refresh token so it cannot be reused
    blacklist_token(
        body.refresh_token,
        expiration_seconds=get_token_remaining_ttl(body.refresh_token),
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "auth_version": user.auth_version,
        },
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "auth_version": user.auth_version}
    )

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
