from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    name: str = Field(..., description="欄位名稱 (e.g., invoice_number, total_amount)")
    field_type: str = Field(..., description="欄位類型 (e.g., text, number, date)")
    is_required: bool = Field(False, description="該欄位是否為必填項")
    validation_regex: Optional[str] = Field(None, description="用於驗證欄位值的正規表達式")
    default_value: Optional[str] = Field(None, description="欄位的預設值")
    order: int = Field(0, description="欄位在範本中的顯示順序")
    description: Optional[str] = Field(None, description="欄位描述")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "invoice_number",
                "field_type": "text",
                "is_required": True,
                "validation_regex": "^[A-Z]{3}-\\d{4}$",
                "default_value": None,
                "order": 1,
                "description": "發票號碼，格式為 AAA-1234",
            }
        }


class Template(BaseModel):
    id: UUID = Field(..., description="範本唯一識別碼")
    name: str = Field(..., description="範本名稱 (e.g., Invoice Template, Receipt Template)")
    description: Optional[str] = Field(None, description="範本描述")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="範本創建時間 (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="範本上次更新時間 (UTC)")
    fields: List[FieldDefinition] = Field([], description="範本中包含的欄位定義列表")
    is_active: bool = Field(True, description="範本是否啟用")
    owner_id: Optional[UUID] = Field(None, description="範本創建者用戶ID")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7890-e12b-34d5-a678-901234567890",
                "name": "Invoice Template",
                "description": "用於處理標準發票的範本",
                "created_at": "2023-10-27T10:00:00Z",
                "updated_at": "2023-10-27T10:00:00Z",
                "fields": [
                    {
                        "name": "invoice_number",
                        "field_type": "text",
                        "is_required": True,
                        "validation_regex": "^[A-Z]{3}-\\d{4}$",
                        "order": 1,
                    }
                ],
                "is_active": True,
                "owner_id": "789e0123-e456-7890-a123-456678912345",
            }
        }


class TemplateInDB(Template):
    # 這裡可以加入資料庫特有的欄位
    pass
