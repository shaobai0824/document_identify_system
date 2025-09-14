"""
文件處理領域實體
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..templates.entities import BoundingBox


class DocumentStatus(str, Enum):
    """文件處理狀態"""
    PENDING = "pending"
    PROCESSING = "processing"
    PASSED = "passed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class OcrBlock(BaseModel):
    """OCR 辨識區塊"""
    page: int = Field(..., ge=1)
    bbox: BoundingBox
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ProcessingEvent(BaseModel):
    """處理事件記錄"""
    at: datetime = Field(default_factory=datetime.utcnow)
    event: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MissingField(BaseModel):
    """缺漏欄位"""
    field_name: str
    bbox: BoundingBox
    reason: str = "not_found"  # not_found, low_confidence, validation_failed


class ValidationResult(BaseModel):
    """驗證結果值物件"""
    is_success: bool
    missing_fields: List[MissingField] = Field(default_factory=list)
    low_confidence_fields: List[str] = Field(default_factory=list)
    ambiguous_fields: List[str] = Field(default_factory=list)
    per_field_confidence: Dict[str, float] = Field(default_factory=dict)
    extracted_data: Dict[str, str] = Field(default_factory=dict)
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubmittedDocument(BaseModel):
    """待審文件聚合根"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str
    file_url: str
    status: DocumentStatus = DocumentStatus.PENDING
    pages: Optional[int] = None
    ocr_blocks: List[OcrBlock] = Field(default_factory=list)
    processing_history: List[ProcessingEvent] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    uploaded_by: Optional[str] = None
    
    def add_processing_event(self, event: str, metadata: Dict[str, Any] = None):
        """新增處理事件"""
        self.processing_history.append(
            ProcessingEvent(event=event, metadata=metadata or {})
        )
        self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status: DocumentStatus, metadata: Dict[str, Any] = None):
        """更新狀態並記錄事件"""
        old_status = self.status
        self.status = new_status
        self.add_processing_event(
            f"status_changed",
            {"from": old_status, "to": new_status, **(metadata or {})}
        )
    
    def set_ocr_result(self, ocr_blocks: List[OcrBlock]):
        """設定 OCR 結果"""
        self.ocr_blocks = ocr_blocks
        self.add_processing_event("ocr_completed", {"blocks_count": len(ocr_blocks)})
    
    def set_validation_result(self, result: ValidationResult):
        """設定驗證結果"""
        self.validation_result = result
        if result.is_success:
            self.update_status(DocumentStatus.PASSED)
        else:
            # 根據缺漏情況決定是否需要人工覆核
            if result.missing_fields or result.low_confidence_fields:
                self.update_status(DocumentStatus.REVIEW_REQUIRED)
            else:
                self.update_status(DocumentStatus.FAILED)
    
    def requires_human_review(self) -> bool:
        """判斷是否需要人工覆核"""
        return self.status == DocumentStatus.REVIEW_REQUIRED
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True
