from typing import List, Optional, Type
from uuid import UUID

from sqlalchemy.orm import Session

from ...domains.documents.models import Document, DocumentInDB
from ...domains.templates.models import Template, TemplateInDB
from .models import DocumentORM, DownloadAuditLogORM, TemplateORM


class BaseRepository:
    """所有資料庫儲存庫的基礎類別"""

    def __init__(self, db: Session, model: Type[BaseORM], schema: Type[BaseSchema]):
        self.db = db
        self.model = model  # SQLAlchemy ORM 模型
        self.schema = schema  # Pydantic 驗證模式 (用於轉換)

    def get_by_id(self, item_id: UUID) -> Optional[BaseSchema]:
        db_item = self.db.query(self.model).filter(self.model.id == item_id).first()
        return self.schema.from_orm(db_item) if db_item else None

    def get_all(self, skip: int = 0, limit: int = 100) -> List[BaseSchema]:
        db_items = self.db.query(self.model).offset(skip).limit(limit).all()
        return [self.schema.from_orm(item) for item in db_items]

    def create(self, item: BaseSchema) -> BaseSchema:
        db_item = self.model(**item.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return self.schema.from_orm(db_item)

    def update(self, item_id: UUID, item: BaseSchema) -> Optional[BaseSchema]:
        db_item = self.db.query(self.model).filter(self.model.id == item_id).first()
        if db_item:
            for key, value in item.model_dump(exclude_unset=True).items():
                setattr(db_item, key, value)
            self.db.commit()
            self.db.refresh(db_item)
            return self.schema.from_orm(db_item)
        return None

    def delete(self, item_id: UUID) -> bool:
        db_item = self.db.query(self.model).filter(self.model.id == item_id).first()
        if db_item:
            self.db.delete(db_item)
            self.db.commit()
            return True
        return False


# 文件儲存庫
class DocumentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, DocumentORM, Document)

    # 這裡可以添加文件特有的查詢方法
    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        db_document = self.db.query(DocumentORM).filter(DocumentORM.file_hash == file_hash).first()
        return Document.from_orm(db_document) if db_document else None


# 範本儲存庫
class TemplateRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, TemplateORM, Template)

    # 這裡可以添加範本特有的查詢方法
    def get_template_by_name(self, name: str) -> Optional[Template]:
        db_template = self.db.query(TemplateORM).filter(TemplateORM.name == name).first()
        return Template.from_orm(db_template) if db_template else None


# 下載審計日誌儲存庫
class DownloadAuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_log_entry(self, document_id: UUID, user_id: UUID, ip_address: str, user_agent: str) -> DownloadAuditLogORM:
        db_log = DownloadAuditLogORM(
            document_id=document_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    def get_logs_for_document(self, document_id: UUID, skip: int = 0, limit: int = 100) -> List[DownloadAuditLogORM]:
        return self.db.query(DownloadAuditLogORM).filter(DownloadAuditLogORM.document_id == document_id).offset(skip).limit(limit).all()

    def get_all_logs(self, skip: int = 0, limit: int = 100) -> List[DownloadAuditLogORM]:
        return self.db.query(DownloadAuditLogORM).offset(skip).limit(limit).all()
