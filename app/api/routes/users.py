from fastapi import APIRouter, Depends
from app.schemas.user import User, UserInDB
from app.auth.dependencies import get_current_active_user

router = APIRouter()


@router.get("/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get user by ID (protected route example)."""
    # TODO: Implement user retrieval from database
    return current_user
