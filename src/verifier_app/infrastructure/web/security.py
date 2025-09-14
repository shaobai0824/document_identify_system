import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..adapters.auth import get_current_active_user  # 假設認證工具
from ..services.audit_service import AuditService
from ..services.integrity_checker import IntegrityChecker
from ..services.signature_detector import SignatureDetector
from ..services.storage_service import StorageService
from ..services.tamper_detector import TamperDetector
from ..services.watermark_service import WatermarkService

router = APIRouter()
logger = logging.getLogger(__name__)


class SignatureLocation(BaseModel):
    page: int
    bbox: dict  # {x1, y1, x2, y2}
    similarity: float
    signature_type: str  # handwritten, digital, stamp


class SignatureCheckResponse(BaseModel):
    document_id: str
    present: bool
    locations: List[SignatureLocation]
    processing_time_ms: int


class TamperFinding(BaseModel):
    type: str  # content_modified, page_reordered, watermark_removed, metadata_altered
    severity: str  # low, medium, high, critical
    description: str
    evidence: dict
    confidence: float


class TamperCheckResponse(BaseModel):
    document_id: str
    is_tampered: bool
    findings: List[TamperFinding]
    integrity_score: float  # 0.0-1.0
    processing_time_ms: int


@router.post("/signatures/check", response_model=SignatureCheckResponse)
async def check_signatures(
    document_id: str,
    signature_detector: SignatureDetector = Depends(SignatureDetector)
):
    """檢查文件簽名"""
    try:
        logger.info(f"Starting signature check for document {document_id}")
        result = await signature_detector.check_document(document_id)
        
        response = SignatureCheckResponse(
            document_id=document_id,
            present=len(result.locations) > 0,
            locations=[SignatureLocation(**loc.dict()) for loc in result.locations],
            processing_time_ms=result.processing_time_ms
        )
        
        logger.info(f"Signature check completed for document {document_id}: {len(result.locations)} signatures found")
        return response
        
    except Exception as e:
        logger.error(f"Failed to check signatures for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tamper/check", response_model=TamperCheckResponse)
async def check_tamper(
    document_id: str,
    tamper_detector: TamperDetector = Depends(TamperDetector)
):
    """檢測文件篡改"""
    try:
        logger.info(f"Starting tamper check for document {document_id}")
        result = await tamper_detector.analyze_document(document_id)
        
        response = TamperCheckResponse(
            document_id=document_id,
            is_tampered=result.is_tampered,
            findings=[TamperFinding(**f.dict()) for f in result.findings],
            integrity_score=result.integrity_score,
            processing_time_ms=result.processing_time_ms
        )
        
        logger.info(f"Tamper check completed for document {document_id}: integrity_score={result.integrity_score}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to check tamper for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    watermark: bool = Query(False, description="是否加上浮水印"),
    reason: Optional[str] = Query(None, description="下載原因（用於審計）"),
    current_user: Any = Depends(get_current_active_user), # 使用認證工具獲取當前用戶
    storage_service: StorageService = Depends(StorageService),
    watermark_service: WatermarkService = Depends(WatermarkService),
    audit_service: AuditService = Depends(AuditService)
):
    """安全下載文件（含浮水印和審計）"""
    try:
        # 權限檢查
        # 假設 current_user 物件有 `id` 和 `has_permission` 方法或屬性
        if not current_user.has_permission(f"download:{document_id}"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 記錄下載審計
        await audit_service.log_download(
            user_id=current_user.id,
            document_id=document_id,
            reason=reason,
            watermark_applied=watermark
        )
        logger.info(f"Document {document_id} download by user {current_user.id} logged.")
        
        # 實作實際的文件下載邏輯
        if watermark:
            file_stream, media_type = await watermark_service.apply_watermark(
                document_id=document_id,
                user_info=current_user.id, # 這裡使用 user id 作為浮水印內容
                download_time=datetime.utcnow(),
                reason=reason
            )
        else:
            file_stream, media_type = await storage_service.get_document(document_id)
            
        logger.info(f"Document {document_id} downloaded with watermark={watermark}, reason='{reason}'")
        
        return StreamingResponse(file_stream, media_type=media_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/{document_id}/verify-integrity")
async def verify_document_integrity(
    document_id: str,
    integrity_checker: IntegrityChecker = Depends(IntegrityChecker)
):
    """驗證文件完整性"""
    try:
        logger.info(f"Starting integrity verification for document {document_id}")
        verification_result = await integrity_checker.verify(document_id)
        
        logger.info(f"Integrity verification completed for document {document_id}")
        return verification_result
        
    except Exception as e:
        logger.error(f"Failed to verify integrity for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class DownloadAuditLogEntry(BaseModel):
    id: str
    document_id: str
    user_id: str
    user_name: str
    downloaded_at: datetime
    reason: Optional[str]
    watermark_applied: bool
    ip_address: str
    user_agent: str


class DownloadAuditLogResponse(BaseModel):
    audit_logs: List[DownloadAuditLogEntry]
    total_count: int
    has_more: bool


@router.get("/audit/downloads", response_model=DownloadAuditLogResponse)
async def get_download_audit_log(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    document_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    audit_service: AuditService = Depends(AuditService)
):
    """取得下載審計日誌"""
    try:
        logger.info(f"Fetching download audit logs with limit={limit}, offset={offset}")
        audit_logs_data, total_count = await audit_service.get_download_logs(
            limit=limit,
            offset=offset,
            document_id=document_id,
            user_id=user_id
        )
        
        response = DownloadAuditLogResponse(
            audit_logs=[DownloadAuditLogEntry(**log.dict()) for log in audit_logs_data],
            total_count=total_count,
            has_more=offset + limit < total_count
        )
        
        logger.info(f"Successfully retrieved {len(audit_logs_data)} audit logs.")
        return response
        
    except Exception as e:
        logger.error(f"Failed to get download audit log: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
