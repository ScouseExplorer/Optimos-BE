from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsage


class UsageService:
    @staticmethod
    def record_usage(
        db: Session,
        user_id: int,
        action: str,
        model: str,
        status: str,
        credits_charged: int = 0,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost: float | None = None,
        request_id: str | None = None,
        error_message: str | None = None,
    ) -> AIUsage:
        usage = AIUsage(
            user_id=user_id,
            action=action,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            credits_charged=credits_charged,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return usage

    @staticmethod
    def list_usage(db: Session, user_id: int, limit: int = 100, offset: int = 0) -> tuple[list[AIUsage], int]:
        query = (
            db.query(AIUsage)
            .filter(AIUsage.user_id == user_id)
            .order_by(AIUsage.created_at.desc())
        )
        total = query.count()
        return query.limit(limit).offset(offset).all(), total
