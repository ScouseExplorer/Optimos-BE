from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.opinion import OpinionCreate, OpinionResponse, OpinionUpdate
from app.services.opinion_service import OpinionService

router = APIRouter(prefix="/api/opinions", tags=["opinions"])


@router.get("")
async def list_opinions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows, total = OpinionService.list_for_user(db, current_user.id, limit, offset)
    return {
        "items": [OpinionResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=OpinionResponse, status_code=status.HTTP_201_CREATED)
async def create_opinion(
    data: OpinionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return OpinionService.create_for_user(db, current_user.id, data)


@router.patch("/{opinion_id}", response_model=OpinionResponse)
async def update_opinion(
    opinion_id: int,
    data: OpinionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = OpinionService.update_for_user(db, current_user.id, opinion_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Opinion not found")
    return row


@router.delete("/{opinion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opinion(
    opinion_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    deleted = OpinionService.delete_for_user(db, current_user.id, opinion_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Opinion not found")
    return None
