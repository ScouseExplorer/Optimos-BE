from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
from app.schemas.user import UserCreate, User
from app.schemas.token import Token
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.services.user_service import UserService
from app.services.token_service import blacklist_token
from app.services.email_service import EmailService
from app.services.email_verification_service import EmailVerificationService
from app.auth.dependencies import get_current_user

router = APIRouter()
user_service = UserService()


# Request/Response Models
class EmailVerificationRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send verification email."""
    # Check if user already exists
    existing_user = await user_service.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = await user_service.create_user(db, user_data)
    
    # Generate and save verification token
    token, success = EmailVerificationService.send_verification_token(db, new_user.id)
    
    # Send verification email
    if success and token:
        await EmailService.send_verification_email(new_user.email, token)
    
    return new_user


@router.post("/verify-email")
async def verify_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify user email with token."""
    user, success = EmailVerificationService.verify_email_token(db, request.token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {"detail": "Email verified successfully"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access + refresh tokens."""
    # Authenticate user
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    """Exchange refresh token for new access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    
    payload = decode_refresh_token(refresh_token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database
    user = await user_service.get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username},
        expires_delta=access_token_expires
    )
    
    # Optionally create new refresh token
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset email."""
    token, success = EmailVerificationService.send_password_reset_token(db, request.email)
    
    if success and token:
        # Send reset email
        await EmailService.send_password_reset_email(request.email, token)
        return {"detail": "If email exists, password reset link has been sent"}
    
    # Always return same message for security (don't reveal if email exists)
    return {"detail": "If email exists, password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using reset token."""
    user, success = EmailVerificationService.reset_password_with_token(db, request.token, request.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"detail": "Password reset successfully"}


@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """Logout user by blacklisting their access token."""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = auth_header.split(" ")[1]
    blacklist_token(token)
    
    return {"detail": "Successfully logged out", "message": "Your access token has been revoked"}
