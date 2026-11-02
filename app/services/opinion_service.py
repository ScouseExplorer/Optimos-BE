from sqlalchemy.orm import Session

from app.models.opinion import Opinion
from app.schemas.opinion import OpinionCreate, OpinionUpdate


class OpinionService:
    @staticmethod
    def list_for_user(db: Session, user_id: int, limit: int = 100, offset: int = 0) -> tuple[list[Opinion], int]:
        query = (
            db.query(Opinion)
            .filter(Opinion.user_id == user_id)
            .order_by(Opinion.created_at.desc())
        )
        total = query.count()
        return query.limit(limit).offset(offset).all(), total

    @staticmethod
    def create_for_user(db: Session, user_id: int, data: OpinionCreate) -> Opinion:
        row = Opinion(user_id=user_id, **data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_for_user(db: Session, user_id: int, opinion_id: int) -> Opinion | None:
        return (
            db.query(Opinion)
            .filter(Opinion.user_id == user_id, Opinion.id == opinion_id)
            .first()
        )

    @staticmethod
    def update_for_user(db: Session, user_id: int, opinion_id: int, data: OpinionUpdate) -> Opinion | None:
        row = OpinionService.get_for_user(db, user_id, opinion_id)
        if not row:
            return None

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(row, field, value)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_for_user(db: Session, user_id: int, opinion_id: int) -> bool:
        row = OpinionService.get_for_user(db, user_id, opinion_id)
        if not row:
            return False

        db.delete(row)
        db.commit()
        return True
