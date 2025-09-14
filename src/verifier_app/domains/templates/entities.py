"""
範本領域實體與值物件
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """座標框值物件"""
    x1: float = Field(..., description="左上角 X 座標")
    y1: float = Field(..., description="左上角 Y 座標") 
    x2: float = Field(..., description="右下角 X 座標")
    y2: float = Field(..., description="右下角 Y 座標")
    
    def __post_init__(self):
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError("Invalid bounding box coordinates")
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1


class FieldDefinition(BaseModel):
    """欄位定義實體"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    bbox: BoundingBox
    required: bool = False
    suggested: bool = False
    field_type: str = "text"  # text, number, date, enum, etc.
    validation_rules: Optional[dict] = None
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class DocumentTemplate(BaseModel):
    """文件範本聚合根"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    base_image_url: Optional[str] = None
    field_definitions: List[FieldDefinition] = Field(default_factory=list)
    version: str = "1.0.0"
    status: str = "draft"  # draft, published, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    def add_field(self, name: str, bbox: BoundingBox, required: bool = False) -> FieldDefinition:
        """新增欄位定義"""
        field = FieldDefinition(
            name=name,
            bbox=bbox,
            required=required
        )
        self.field_definitions.append(field)
        self.updated_at = datetime.utcnow()
        return field
    
    def remove_field(self, field_id: str) -> bool:
        """移除欄位定義"""
        for i, field in enumerate(self.field_definitions):
            if field.id == field_id:
                self.field_definitions.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def update_field(self, field_id: str, **updates) -> bool:
        """更新欄位定義"""
        for field in self.field_definitions:
            if field.id == field_id:
                for key, value in updates.items():
                    if hasattr(field, key):
                        setattr(field, key, value)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def get_required_fields(self) -> List[FieldDefinition]:
        """取得必填欄位"""
        return [field for field in self.field_definitions if field.required]
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True
