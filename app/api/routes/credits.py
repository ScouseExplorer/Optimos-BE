from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.credits import (
    AdminCreditAdjustmentRequest,
    CreditTransactionResponse,
    CreditWalletResponse,
    FeatureCostResponse,
)
from app.services.credit_service import CreditService

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/wallet", response_model=CreditWalletResponse)
async def get_my_wallet(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return CreditService.get_or_create_wallet(db, current_user.id)


@router.get("/transactions")
async def get_my_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows, total = CreditService.list_transactions(db, current_user.id, limit, offset)
    return {
        "items": [CreditTransactionResponse.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/feature-costs", response_model=list[FeatureCostResponse])
async def list_feature_costs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return CreditService.list_feature_costs(db)


@router.post("/admin/adjust", response_model=CreditTransactionResponse, status_code=status.HTTP_201_CREATED)
async def admin_adjust_credits(
    body: AdminCreditAdjustmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")

    tx = CreditService.admin_adjust_credits(
        db=db,
        user_id=body.user_id,
        amount=body.amount,
        description=body.description,
        actor_id=current_user.id,
    )
    return tx
