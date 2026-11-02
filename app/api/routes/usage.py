from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.usage import AIUsageResponse
from app.services.usage_service import UsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/me")
async def get_my_usage(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows, total = UsageService.list_usage(db, current_user.id, limit, offset)
    return {
        "items": [AIUsageResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
