from app.services.credit_service import CreditService
from app.services.entitlement_service import EntitlementService


class FeatureGateService:
    """Centralized guard for paid feature entitlement and credit reservations."""

    @staticmethod
    def assert_and_reserve(
        db,
        user_id: int,
        feature_key: str,
        request_id: str,
        description: str,
    ):
        EntitlementService.assert_feature_allowed(db, user_id, feature_key)
        return CreditService.reserve_credits(
            db=db,
            user_id=user_id,
            feature_key=feature_key,
            request_id=request_id,
            description=description,
        )

    @staticmethod
    def settle_if_reserved(db, reservation, user_id: int) -> None:
        if reservation:
            CreditService.settle_reservation(db, reservation.id, user_id)

    @staticmethod
    def release_if_reserved(db, reservation, user_id: int) -> None:
        if reservation and reservation.status == "reserved":
            CreditService.release_reservation(db, reservation.id, user_id)