from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


class RefreshRequest(BaseModel):
    """Body payload for POST /api/auth/refresh."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Optional body for POST /api/auth/logout — also revokes the refresh token."""
    refresh_token: Optional[str] = None
