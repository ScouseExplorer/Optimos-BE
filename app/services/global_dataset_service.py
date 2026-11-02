from sqlalchemy.orm import Session

from app.models.global_dataset_item import GlobalDatasetItem
from app.schemas.global_dataset import GlobalDatasetItemCreate, GlobalDatasetItemUpdate


class GlobalDatasetService:
    @staticmethod
    def list_active(
        db: Session,
        dataset_key: str | None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[GlobalDatasetItem], int]:
        query = db.query(GlobalDatasetItem).filter(GlobalDatasetItem.is_active.is_(True))
        if dataset_key:
            query = query.filter(GlobalDatasetItem.dataset_key == dataset_key)

        query = query.order_by(GlobalDatasetItem.priority.desc(), GlobalDatasetItem.created_at.desc())
        total = query.count()
        return query.limit(limit).offset(offset).all(), total

    @staticmethod
    def list_all(
        db: Session,
        dataset_key: str | None,
        include_inactive: bool,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[GlobalDatasetItem], int]:
        query = db.query(GlobalDatasetItem)
        if dataset_key:
            query = query.filter(GlobalDatasetItem.dataset_key == dataset_key)
        if not include_inactive:
            query = query.filter(GlobalDatasetItem.is_active.is_(True))

        query = query.order_by(GlobalDatasetItem.priority.desc(), GlobalDatasetItem.created_at.desc())
        total = query.count()
        return query.limit(limit).offset(offset).all(), total

    @staticmethod
    def get_active_by_id(db: Session, item_id: int) -> GlobalDatasetItem | None:
        return (
            db.query(GlobalDatasetItem)
            .filter(GlobalDatasetItem.id == item_id, GlobalDatasetItem.is_active.is_(True))
            .first()
        )

    @staticmethod
    def create(db: Session, payload: GlobalDatasetItemCreate) -> GlobalDatasetItem:
        row = GlobalDatasetItem(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_by_id(db: Session, item_id: int) -> GlobalDatasetItem | None:
        return db.query(GlobalDatasetItem).filter(GlobalDatasetItem.id == item_id).first()

    @staticmethod
    def update(
        db: Session,
        item_id: int,
        payload: GlobalDatasetItemUpdate,
    ) -> GlobalDatasetItem | None:
        row = GlobalDatasetService.get_by_id(db, item_id)
        if not row:
            return None

        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(row, field, value)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete(db: Session, item_id: int) -> bool:
        row = GlobalDatasetService.get_by_id(db, item_id)
        if not row:
            return False

        db.delete(row)
        db.commit()
        return True
