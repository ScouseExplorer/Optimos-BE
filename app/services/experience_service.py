from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.schemas.experience import ExperienceCreate, ExperienceUpdate


class ExperienceService:
    @staticmethod
    def list_for_user(db: Session, user_id: int, limit: int = 100, offset: int = 0) -> tuple[list[Experience], int]:
        query = (
            db.query(Experience)
            .filter(Experience.user_id == user_id)
            .order_by(Experience.created_at.desc())
        )
        total = query.count()
        return query.limit(limit).offset(offset).all(), total

    @staticmethod
    def create_for_user(db: Session, user_id: int, data: ExperienceCreate) -> Experience:
        row = Experience(user_id=user_id, **data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_for_user(db: Session, user_id: int, experience_id: int) -> Experience | None:
        return (
            db.query(Experience)
            .filter(Experience.user_id == user_id, Experience.id == experience_id)
            .first()
        )

    @staticmethod
    def update_for_user(db: Session, user_id: int, experience_id: int, data: ExperienceUpdate) -> Experience | None:
        row = ExperienceService.get_for_user(db, user_id, experience_id)
        if not row:
            return None

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(row, field, value)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_for_user(db: Session, user_id: int, experience_id: int) -> bool:
        row = ExperienceService.get_for_user(db, user_id, experience_id)
        if not row:
            return False

        db.delete(row)
        db.commit()
        return True
