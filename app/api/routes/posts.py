from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.post_analysis import PostAnalysisRequest, PostAnalysisResponse
from app.schemas.user_post import UserPostCreate, UserPostResponse, UserPostUpdate
from app.services.feature_gate_service import FeatureGateService
from app.services.post_analysis_service import PostAnalysisService
from app.services.user_post_service import UserPostService

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
async def list_posts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows, total = UserPostService.list_for_user(db, current_user.id, limit, offset)
    return {
        "items": [UserPostResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=UserPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: UserPostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return UserPostService.create_for_user(db, current_user.id, data)


@router.patch("/{post_id}", response_model=UserPostResponse)
async def update_post(
    post_id: int,
    data: UserPostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = UserPostService.update_for_user(db, current_user.id, post_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return row


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    deleted = UserPostService.delete_for_user(db, current_user.id, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return None


@router.post("/{post_id}/analyze", response_model=PostAnalysisResponse)
async def analyze_post(
    post_id: int,
    payload: PostAnalysisRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = UserPostService.get_for_user(db, current_user.id, post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")

    reservation = None
    request_id = idempotency_key or str(uuid4())

    try:
        reservation = FeatureGateService.assert_and_reserve(
            db=db,
            user_id=current_user.id,
            feature_key="deep_post_analysis",
            request_id=request_id,
            description=f"Post analysis request for post_id={post_id}",
        )

        analysis = PostAnalysisService.analyze(row.content)

        if payload.save_to_post:
            row = UserPostService.update_for_user(
                db,
                current_user.id,
                post_id,
                UserPostUpdate(
                    topic=analysis.get("topic"),
                    post_format=analysis.get("post_format"),
                    hook_type=analysis.get("hook_type"),
                    media_type=analysis.get("media_type"),
                ),
            )
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")

        FeatureGateService.settle_if_reserved(db, reservation, current_user.id)
    except HTTPException:
        FeatureGateService.release_if_reserved(db, reservation, current_user.id)
        raise
    except Exception:
        FeatureGateService.release_if_reserved(db, reservation, current_user.id)
        raise

    return PostAnalysisResponse(**analysis)
