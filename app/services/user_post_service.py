from sqlalchemy.orm import Session

from app.models.user_post import UserPost
from app.schemas.user_post import UserPostCreate, UserPostUpdate


class UserPostService:
    @staticmethod
    def list_for_user(db: Session, user_id: int, limit: int = 100, offset: int = 0) -> tuple[list[UserPost], int]:
        query = (
            db.query(UserPost)
            .filter(UserPost.user_id == user_id)
            .order_by(UserPost.created_at.desc())
        )
        total = query.count()
        return query.limit(limit).offset(offset).all(), total

    @staticmethod
    def create_for_user(db: Session, user_id: int, data: UserPostCreate) -> UserPost:
        row = UserPost(user_id=user_id, **data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_for_user(db: Session, user_id: int, post_id: int) -> UserPost | None:
        return (
            db.query(UserPost)
            .filter(UserPost.user_id == user_id, UserPost.id == post_id)
            .first()
        )

    @staticmethod
    def update_for_user(db: Session, user_id: int, post_id: int, data: UserPostUpdate) -> UserPost | None:
        row = UserPostService.get_for_user(db, user_id, post_id)
        if not row:
            return None

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(row, field, value)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_for_user(db: Session, user_id: int, post_id: int) -> bool:
        row = UserPostService.get_for_user(db, user_id, post_id)
        if not row:
            return False

        db.delete(row)
        db.commit()
        return True
