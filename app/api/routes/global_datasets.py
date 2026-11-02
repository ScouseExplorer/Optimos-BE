from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.global_dataset import (
    GlobalDatasetItemCreate,
    GlobalDatasetItemResponse,
    GlobalDatasetItemUpdate,
)
from app.services.global_dataset_service import GlobalDatasetService

router = APIRouter(prefix="/api/global-datasets", tags=["global-datasets"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("")
async def list_global_dataset_items(
    dataset_key: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    rows, total = GlobalDatasetService.list_active(db, dataset_key, limit, offset)
    return {
        "items": [GlobalDatasetItemResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/admin/all")
async def list_global_dataset_items_admin(
    include_inactive: bool = Query(default=True),
    dataset_key: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    rows, total = GlobalDatasetService.list_all(
        db,
        dataset_key=dataset_key,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [GlobalDatasetItemResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{item_id}", response_model=GlobalDatasetItemResponse)
async def get_global_dataset_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    row = GlobalDatasetService.get_active_by_id(db, item_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global dataset item not found")
    return row


@router.post("", response_model=GlobalDatasetItemResponse, status_code=status.HTTP_201_CREATED)
async def create_global_dataset_item(
    payload: GlobalDatasetItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    return GlobalDatasetService.create(db, payload)


@router.patch("/{item_id}", response_model=GlobalDatasetItemResponse)
async def update_global_dataset_item(
    item_id: int,
    payload: GlobalDatasetItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    row = GlobalDatasetService.update(db, item_id, payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global dataset item not found")
    return row


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_dataset_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    deleted = GlobalDatasetService.delete(db, item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global dataset item not found")
    return None
