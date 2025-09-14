"""
文件處理路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from ...application.dtos.document_dtos import \
    DocumentStatusResponse as DTODocumentStatusResponse
from ...application.dtos.document_dtos import DocumentUploadResponse
from ...infrastructure.services.document_processor import DocumentProcessor
from ...infrastructure.services.dynamic_table_service import \
    DynamicTableService
from ...infrastructure.tasks.task_manager import TaskManager

logger = logging.getLogger(__name__)
router = APIRouter()


class ProcessResponse(BaseModel):
    document_id: str
    status: str


class DocumentStatusResponse(BaseModel):
    id: str
    template_id: str
    file_url: str
    status: str
    pages: Optional[int] = None
    created_at: str


class ValidationResultResponse(BaseModel):
    is_success: bool
    missing_fields: list = []
    low_confidence_fields: list = []
    extracted_data: dict = {}


@router.post("/process", response_model=ProcessResponse, status_code=202)
async def process_document(
    template_id: str = Form(...),
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """提交文件處理（非同步）"""
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 讀取檔案內容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # 初始化處理器並處理檔案
        processor = DocumentProcessor()
        result = await processor.process_uploaded_file(
            file_content=file_content,
            filename=file.filename,
            template_id=template_id
        )
        
        logger.info(f"Document processing started: {result['document_id']}")
        return ProcessResponse(
            document_id=result["document_id"],
            status=result["status"]
        )
        
    except ValueError as e:
        logger.warning(f"Document processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str):
    """查詢處理狀態與結果"""
    try:
        processor = DocumentProcessor()
        result = await processor.get_document_status(document_id)
        
        return DocumentStatusResponse(
            id=result["document_id"],
            template_id=result["verification_result"]["template_id"] if result.get("verification_result") else "",
            file_url=result["storage_url"] if result.get("storage_url") else "",
            status=result["status"],
            pages=result["pages"] if result.get("pages") else None,
            created_at=result["created_at"]
        )
        
    except ValueError as e:
        logger.warning(f"Document not found: {document_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_id}/result", response_model=ValidationResultResponse)
async def get_validation_result(document_id: str):
    """取得最終驗證結果"""
    try:
        processor = DocumentProcessor()
        result = await processor.get_document_status(document_id)
        
        verification_result = result.get("verification_result")
        if not verification_result:
            raise HTTPException(status_code=404, detail="Verification result not found")
        
        return ValidationResultResponse(
            is_success=verification_result["status"] == "pass",
            missing_fields=verification_result.get("missing_fields", []),
            low_confidence_fields=verification_result.get("low_confidence_fields", []),
            extracted_data=verification_result.get("extracted_data", {})
        )
        
    except ValueError as e:
        logger.warning(f"Document not found: {document_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get validation result: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 新增簡化的上傳端點
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="要處理的文件檔案"),
    template_id: Optional[str] = Form(None, description="驗證模板 ID")
):
    """
    上傳文件進行 OCR 和驗證處理（同步）
    
    支援的檔案格式：PDF, JPG, JPEG, PNG, TIFF
    最大檔案大小：50MB（可在設定中調整）
    """
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 讀取檔案內容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # 初始化處理器並處理檔案
        processor = DocumentProcessor()
        result = await processor.process_uploaded_file(
            file_content=file_content,
            filename=file.filename,
            template_id=template_id
        )
        
        # 轉換為回應 DTO
        response = DocumentUploadResponse(**result)
        
        logger.info(f"Document upload successful: {response.document_id}")
        return response
        
    except ValueError as e:
        logger.warning(f"Document upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status/{document_id}", response_model=DTODocumentStatusResponse)
async def get_document_detailed_status(document_id: str):
    """
    取得文件詳細處理狀態
    
    返回文件的處理進度、OCR 結果和驗證結果
    """
    try:
        processor = DocumentProcessor()
        result = await processor.get_document_status(document_id)
        
        response = DTODocumentStatusResponse(**result)
        return response
        
    except ValueError as e:
        logger.warning(f"Document not found: {document_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# === 背景任務相關端點 ===

@router.post("/process-async", response_model=ProcessResponse, status_code=202)
async def process_document_async_endpoint(
    template_id: str = Form(...),
    file: UploadFile = File(...),
    priority: str = Form("normal", description="任務優先級: low, normal, high"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """提交文件處理（非同步）- 使用背景任務"""
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 讀取檔案內容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # 先同步建立文件記錄和上傳檔案
        processor = DocumentProcessor()
        
        # 只進行基本處理（上傳檔案，不執行 OCR）
        import hashlib
        from pathlib import Path
        from uuid import uuid4

        from ..database.base import get_sync_session
        from ..database.models import Document, DocumentStatus

        # 計算檔案雜湊
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 建立文件記錄
        db = get_sync_session()
        document_id = uuid4()
        document = Document(
            id=document_id,
            filename=f"{document_id}{Path(file.filename).suffix}",
            original_filename=file.filename,
            content_type=processor._get_content_type(Path(file.filename).suffix.lower().lstrip('.')),
            file_size=len(file_content),
            file_hash=file_hash,
            status=DocumentStatus.UPLOADED,
            storage_provider="local"
        )
        
        db.add(document)
        db.commit()
        
        # 上傳檔案
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            tmp_file.write(file_content)
            temp_path = tmp_file.name
        
        try:
            storage_path = processor.storage_service.generate_storage_path(file.filename, str(document_id))
            await processor.storage_service.upload_file(temp_path, storage_path)
            
            # 更新文件記錄
            document.storage_path = storage_path
            db.commit()
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
            db.close()
        
        # 提交背景任務
        task_manager = TaskManager()
        task_id = task_manager.submit_document_processing(
            document_id=str(document_id),
            template_id=template_id,
            priority=priority
        )
        
        logger.info(f"Document processing task submitted: {task_id} for document {document_id}")
        
        return ProcessResponse(
            document_id=str(document_id),
            status="processing_queued"
        )
        
    except ValueError as e:
        logger.warning(f"Document processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reprocess/{document_id}")
async def reprocess_document(
    document_id: str,
    template_id: Optional[str] = Form(None, description="新的驗證模板 ID")
):
    """
    重新處理已上傳的文件
    
    可以使用不同的模板重新驗證文件
    """
    try:
        task_manager = TaskManager()
        task_id = task_manager.submit_document_reprocessing(
            document_id=document_id,
            template_id=template_id
        )
        
        return {
            "document_id": document_id,
            "task_id": task_id,
            "status": "reprocessing_queued",
            "message": "Document reprocessing has been queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to reprocess document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """取得背景任務狀態"""
    try:
        task_manager = TaskManager()
        status = task_manager.get_task_status(task_id)
        return status
        
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """取消背景任務"""
    try:
        task_manager = TaskManager()
        success = task_manager.cancel_task(task_id)
        
        if success:
            return {"task_id": task_id, "status": "cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel task")
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tasks")
async def get_active_tasks():
    """取得活躍任務列表"""
    try:
        task_manager = TaskManager()
        tasks = task_manager.get_active_tasks()
        return {"active_tasks": tasks}
        
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/tasks")
async def get_task_statistics():
    """取得任務統計資訊"""
    try:
        task_manager = TaskManager()
        stats = task_manager.get_task_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get task statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# === 動態資料表相關端點 ===

@router.get("/template/{template_id}/data")
async def get_template_verification_data(template_id: str, limit: int = 100):
    """
    獲取模板的所有驗證資料
    
    返回該模板驗證成功的所有文件資料
    """
    try:
        dynamic_table_service = DynamicTableService()
        data = await dynamic_table_service.get_template_data(template_id, limit)
        
        return {
            "template_id": template_id,
            "total_records": len(data),
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Failed to get template data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/template/{template_id}/document/{document_id}/data")
async def get_document_verification_data(template_id: str, document_id: str):
    """
    獲取特定文件的驗證資料
    
    返回指定文件在指定模板下的驗證結果和提取資料
    """
    try:
        dynamic_table_service = DynamicTableService()
        data = await dynamic_table_service.get_document_data(template_id, document_id)
        
        if not data:
            raise HTTPException(status_code=404, detail="Document verification data not found")
        
        return {
            "template_id": template_id,
            "document_id": document_id,
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/template/{template_id}/table-info")
async def get_template_table_info(template_id: str):
    """
    獲取模板對應的資料表資訊
    
    返回資料表結構和基本資訊
    """
    try:
        from ..database.base import get_sync_session
        from ..database.models import Template
        
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        table_info = None
        if template.validation_rules and 'data_table' in template.validation_rules:
            table_info = template.validation_rules['data_table']
        
        db.close()
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "field_definitions": template.field_definitions,
            "table_info": table_info,
            "has_data_table": table_info is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template table info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
