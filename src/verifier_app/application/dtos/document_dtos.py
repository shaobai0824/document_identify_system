"""
文件處理相關 DTO
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """文件上傳請求"""
    template_id: Optional[str] = Field(None, description="驗證模板 ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class OCRResultDTO(BaseModel):
    """OCR 結果 DTO"""
    text: str = Field(..., description="提取的文字")
    confidence: float = Field(..., ge=0.0, le=1.0, description="整體信心度")
    regions_count: int = Field(..., ge=0, description="文字區域數量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "身分證號碼：A123456789\n姓名：王小明",
                "confidence": 0.92,
                "regions_count": 15
            }
        }


class VerificationResultDTO(BaseModel):
    """驗證結果 DTO"""
    verification_id: str = Field(..., description="驗證記錄 ID")
    status: str = Field(..., description="驗證狀態")
    confidence: float = Field(..., ge=0.0, le=1.0, description="驗證信心度")
    requires_manual_review: bool = Field(..., description="是否需要人工審核")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="提取的資料")
    
    class Config:
        json_schema_extra = {
            "example": {
                "verification_id": "550e8400-e29b-41d4-a716-446655440001",
                "status": "pass",
                "confidence": 0.89,
                "requires_manual_review": False,
                "extracted_data": {
                    "id_number": "A123456789",
                    "name": "王小明"
                }
            }
        }


class DocumentUploadResponse(BaseModel):
    """文件上傳回應"""
    document_id: str = Field(..., description="文件 ID")
    status: str = Field(..., description="處理狀態")
    message: Optional[str] = Field(None, description="狀態訊息")
    ocr_result: Optional[OCRResultDTO] = Field(None, description="OCR 結果")
    verification_result: Optional[VerificationResultDTO] = Field(None, description="驗證結果")
    storage_url: Optional[str] = Field(None, description="儲存位置 URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "success",
                "message": "Document processed successfully",
                "ocr_result": {
                    "text": "身分證號碼：A123456789",
                    "confidence": 0.92,
                    "regions_count": 15
                },
                "verification_result": {
                    "verification_id": "550e8400-e29b-41d4-a716-446655440001",
                    "status": "pass",
                    "confidence": 0.89,
                    "requires_manual_review": False,
                    "extracted_data": {"id_number": "A123456789"}
                },
                "storage_url": "file:///storage/documents/55/550e8400-e29b-41d4-a716-446655440000.pdf"
            }
        }


class DocumentStatusResponse(BaseModel):
    """文件狀態回應"""
    document_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="原始檔名")
    status: str = Field(..., description="處理狀態")
    processing_progress: float = Field(..., ge=0.0, le=1.0, description="處理進度")
    created_at: str = Field(..., description="建立時間")
    processed_at: Optional[str] = Field(None, description="處理完成時間")
    ocr_result: Optional[Dict[str, Any]] = Field(None, description="OCR 結果")
    verification_result: Optional[VerificationResultDTO] = Field(None, description="驗證結果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "id_card.pdf",
                "status": "verified",
                "processing_progress": 1.0,
                "created_at": "2024-01-01T10:00:00Z",
                "processed_at": "2024-01-01T10:00:30Z",
                "ocr_result": {
                    "text": "身分證號碼：A123456789",
                    "confidence": 0.92,
                    "metadata": {"engine": "tesseract"}
                },
                "verification_result": {
                    "verification_id": "550e8400-e29b-41d4-a716-446655440001",
                    "status": "pass",
                    "confidence": 0.89,
                    "requires_manual_review": False,
                    "extracted_data": {"id_number": "A123456789"}
                }
            }
        }
