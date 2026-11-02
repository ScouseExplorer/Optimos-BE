from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.experience import ExperienceCreate, ExperienceResponse, ExperienceUpdate
from app.services.experience_service import ExperienceService

router = APIRouter(prefix="/api/experiences", tags=["experiences"])


@router.get("")
async def list_experiences(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows, total = ExperienceService.list_for_user(db, current_user.id, limit, offset)
    return {
        "items": [ExperienceResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def create_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return ExperienceService.create_for_user(db, current_user.id, data)


@router.patch("/{experience_id}", response_model=ExperienceResponse)
async def update_experience(
    experience_id: int,
    data: ExperienceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = ExperienceService.update_for_user(db, current_user.id, experience_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Experience not found")
    return row


@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    experience_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    deleted = ExperienceService.delete_for_user(db, current_user.id, experience_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Experience not found")
    return None
