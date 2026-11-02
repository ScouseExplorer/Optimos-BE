from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.credit_transaction import CreditTransaction
from app.models.credit_wallet import CreditWallet
from app.models.feature_cost import FeatureCost


class CreditService:
    DEFAULT_FEATURE_COSTS = {
        "generate_post": 10,
        "deep_post_analysis": 5,
        "personal_content_audit": 15,
        "historical_analysis": 30,
        "competitor_analysis": 20,
        "content_strategy": 20,
        "batch_generation": 25,
        "deep_audience_analysis": 40,
    }

    @staticmethod
    def ensure_feature_costs(db: Session) -> None:
        existing = {
            row.feature_key for row in db.query(FeatureCost.feature_key).all()
        }
        created = False
        for feature_key, cost in CreditService.DEFAULT_FEATURE_COSTS.items():
            if feature_key not in existing:
                db.add(FeatureCost(feature_key=feature_key, credit_cost=cost, is_active=True))
                created = True
        if created:
            db.commit()

    @staticmethod
    def get_or_create_wallet(db: Session, user_id: int) -> CreditWallet:
        wallet = db.query(CreditWallet).filter(CreditWallet.user_id == user_id).first()
        if not wallet:
            wallet = CreditWallet(user_id=user_id, balance=0)
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
        return wallet

    @staticmethod
    def get_feature_cost(db: Session, feature_key: str) -> int:
        CreditService.ensure_feature_costs(db)
        feature = db.query(FeatureCost).filter(FeatureCost.feature_key == feature_key).first()
        if not feature or not feature.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_key}' is not available",
            )
        return feature.credit_cost

    @staticmethod
    def list_feature_costs(db: Session) -> list[FeatureCost]:
        CreditService.ensure_feature_costs(db)
        return db.query(FeatureCost).order_by(FeatureCost.feature_key.asc()).all()

    @staticmethod
    def reserve_credits(
        db: Session,
        user_id: int,
        feature_key: str,
        request_id: str,
        description: str,
    ) -> CreditTransaction | None:
        cost = CreditService.get_feature_cost(db, feature_key)
        if cost <= 0:
            return None

        existing = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.request_id == request_id,
                CreditTransaction.transaction_type == "RESERVATION",
            )
            .first()
        )
        if existing:
            return existing

        wallet = (
            db.query(CreditWallet)
            .filter(CreditWallet.user_id == user_id)
            .with_for_update()
            .first()
        )
        if not wallet:
            wallet = CreditWallet(user_id=user_id, balance=0)
            db.add(wallet)
            db.flush()

        if wallet.balance < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Not enough credits for this operation",
            )

        wallet.balance -= cost
        tx = CreditTransaction(
            user_id=user_id,
            amount=-cost,
            transaction_type="RESERVATION",
            source=feature_key,
            request_id=request_id,
            status="reserved",
            description=description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def settle_reservation(db: Session, reservation_id: int, user_id: int) -> CreditTransaction | None:
        tx = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.id == reservation_id,
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "RESERVATION",
            )
            .with_for_update()
            .first()
        )
        if not tx:
            return None
        if tx.status == "settled":
            return tx
        if tx.status != "reserved":
            return tx

        tx.status = "settled"
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def release_reservation(db: Session, reservation_id: int, user_id: int) -> CreditTransaction | None:
        tx = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.id == reservation_id,
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "RESERVATION",
            )
            .with_for_update()
            .first()
        )
        if not tx:
            return None
        if tx.status == "released":
            return tx
        if tx.status != "reserved":
            return tx

        wallet = (
            db.query(CreditWallet)
            .filter(CreditWallet.user_id == user_id)
            .with_for_update()
            .first()
        )
        if wallet:
            wallet.balance += abs(tx.amount)
        tx.status = "released"
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def admin_adjust_credits(
        db: Session,
        user_id: int,
        amount: int,
        description: str | None,
        actor_id: int,
    ) -> CreditTransaction:
        wallet = (
            db.query(CreditWallet)
            .filter(CreditWallet.user_id == user_id)
            .with_for_update()
            .first()
        )
        if not wallet:
            wallet = CreditWallet(user_id=user_id, balance=0)
            db.add(wallet)
            db.flush()

        new_balance = wallet.balance + amount
        if new_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Credit adjustment would make balance negative",
            )

        wallet.balance = new_balance
        tx = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type="ADMIN_ADJUSTMENT",
            source="admin",
            reference_id=str(actor_id),
            status="settled",
            description=description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def apply_billing_purchase(
        db: Session,
        user_id: int,
        amount: int,
        reference_id: str,
        description: str | None,
    ) -> tuple[CreditTransaction, bool]:
        """Apply a billing purchase exactly once per user/reference pair."""
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchased credits amount must be greater than zero",
            )

        wallet = (
            db.query(CreditWallet)
            .filter(CreditWallet.user_id == user_id)
            .with_for_update()
            .first()
        )
        if not wallet:
            wallet = CreditWallet(user_id=user_id, balance=0)
            db.add(wallet)
            db.flush()

        existing = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.reference_id == reference_id,
                CreditTransaction.transaction_type == "BILLING_PURCHASE",
            )
            .first()
        )
        if existing:
            return existing, False

        wallet.balance += amount
        tx = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type="BILLING_PURCHASE",
            source="billing_webhook",
            reference_id=reference_id,
            status="settled",
            description=description,
        )
        db.add(tx)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(CreditTransaction)
                .filter(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.reference_id == reference_id,
                    CreditTransaction.transaction_type == "BILLING_PURCHASE",
                )
                .first()
            )
            if existing:
                return existing, False
            raise

        db.refresh(tx)
        return tx, True

    @staticmethod
    def list_transactions(db: Session, user_id: int, limit: int = 100, offset: int = 0) -> tuple[list[CreditTransaction], int]:
        query = (
            db.query(CreditTransaction)
            .filter(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
        )
        total = query.count()
        return query.limit(limit).offset(offset).all(), total
