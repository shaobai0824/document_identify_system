from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: UUID = Field(..., description="文件唯一識別碼")
    filename: str = Field(..., description="原始檔案名稱")
    file_path: str = Field(..., description="文件儲存路徑")
    file_hash: str = Field(..., description="文件的內容雜湊值，用於完整性驗證")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="文件上傳時間 (UTC)")
    status: str = Field("pending", description="文件處理狀態 (e.g., pending, processing, completed, failed)")
    owner_id: Optional[UUID] = Field(None, description="文件擁有者用戶ID")
    metadata: dict = Field({}, description="任意額外元數據")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "example.pdf",
                "file_path": "/path/to/example.pdf",
                "file_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
                "uploaded_at": "2023-10-27T10:00:00Z",
                "status": "completed",
                "owner_id": "789e0123-e456-7890-a123-456678912345",
                "metadata": {"pages": 10, "language": "zh-TW"},
            }
        }


class DocumentInDB(Document):
    # 這裡可以加入資料庫特有的欄位，例如關聯的外部鍵等
    pass
