"""
文件處理相關背景任務
"""

import asyncio
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from celery import current_task
from sqlalchemy import and_

from ..database.base import get_sync_session
from ..database.models import (Document, DocumentStatus, TaskRecord,
                               VerificationRecord)
from ..services.document_processor import DocumentProcessor
from ..services.storage_service import StorageService
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_document_async")
def process_document_async(self, 
                          document_id: str, 
                          template_id: Optional[str] = None,
                          priority: str = "normal") -> Dict[str, Any]:
    """
    非同步處理文件任務
    
    Args:
        document_id: 文件 ID
        template_id: 驗證模板 ID
        priority: 任務優先級 (low, normal, high)
    """
    task_id = self.request.id
    logger.info(f"Starting document processing task {task_id} for document {document_id}")
    
    # 建立任務記錄
    db = get_sync_session()
    task_record = TaskRecord(
        task_id=task_id,
        task_name="process_document_async",
        task_type="document_processing",
        document_id=document_id,
        status="STARTED",
        started_at=datetime.utcnow()
    )
    db.add(task_record)
    db.commit()
    
    try:
        # 取得文件記錄
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # 更新文件狀態
        document.status = DocumentStatus.PROCESSING
        db.commit()
        
        # 初始化服務
        storage_service = StorageService()
        
        # 下載檔案到臨時位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(document.filename).suffix) as tmp_file:
            temp_path = tmp_file.name
        
        success = asyncio.run(storage_service.download_file(document.storage_path, temp_path))
        if not success:
            raise RuntimeError(f"Failed to download file: {document.storage_path}")
        
        try:
            # 執行處理
            processor = DocumentProcessor()
            
            # 更新進度
            current_task.update_state(state='PROGRESS', meta={'progress': 0.3, 'step': 'OCR processing'})
            
            # 執行 OCR
            ocr_result = asyncio.run(processor.ocr_service.extract_text_with_metadata(temp_path))
            
            # 更新文件的 OCR 結果
            document.ocr_text = ocr_result["text"]
            document.ocr_confidence = ocr_result["confidence"]
            document.ocr_metadata = ocr_result["metadata"]
            document.status = DocumentStatus.OCR_COMPLETED
            document.processed_at = datetime.utcnow()
            db.commit()
            
            current_task.update_state(state='PROGRESS', meta={'progress': 0.7, 'step': 'Verification'})
            
            # 如果有模板，執行驗證
            verification_result = None
            if template_id:
                verification_result = asyncio.run(processor._verify_document(document, template_id, db))
            
            current_task.update_state(state='PROGRESS', meta={'progress': 1.0, 'step': 'Completed'})
            
            # 更新任務記錄
            task_record.status = "SUCCESS"
            task_record.completed_at = datetime.utcnow()
            task_record.execution_time_ms = int((task_record.completed_at - task_record.started_at).total_seconds() * 1000)
            task_record.result = {
                "document_id": str(document.id),
                "status": document.status.value,
                "ocr_confidence": document.ocr_confidence,
                "verification_result": verification_result
            }
            db.commit()
            
            logger.info(f"Document processing task {task_id} completed successfully")
            
            return {
                "document_id": str(document.id),
                "status": "success",
                "ocr_confidence": document.ocr_confidence,
                "verification_result": verification_result
            }
            
        finally:
            # 清理臨時檔案
            Path(temp_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Document processing task {task_id} failed: {e}")
        
        # 更新文件狀態
        if 'document' in locals():
            document.status = DocumentStatus.FAILED
            db.commit()
        
        # 更新任務記錄
        task_record.status = "FAILURE"
        task_record.completed_at = datetime.utcnow()
        task_record.error_info = {"error": str(e), "type": type(e).__name__}
        if task_record.started_at:
            task_record.execution_time_ms = int((task_record.completed_at - task_record.started_at).total_seconds() * 1000)
        db.commit()
        
        # 重試邏輯
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1})")
            task_record.retry_count += 1
            db.commit()
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # 指數退避
        
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, name="reprocess_document_async")
def reprocess_document_async(self, 
                           document_id: str, 
                           template_id: Optional[str] = None) -> Dict[str, Any]:
    """
    重新處理文件任務
    
    Args:
        document_id: 文件 ID
        template_id: 新的驗證模板 ID
    """
    task_id = self.request.id
    logger.info(f"Starting document reprocessing task {task_id} for document {document_id}")
    
    db = get_sync_session()
    
    try:
        # 檢查文件是否存在
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # 重置狀態並重新處理
        document.status = DocumentStatus.PROCESSING
        db.commit()
        
        # 調用原始處理任務
        return process_document_async.apply_async(
            args=[document_id, template_id],
            kwargs={"priority": "high"}
        ).get()
        
    except Exception as e:
        logger.error(f"Document reprocessing task {task_id} failed: {e}")
        raise
    
    finally:
        db.close()


@celery_app.task(name="cleanup_old_documents")
def cleanup_old_documents(days: int = 30) -> Dict[str, Any]:
    """
    清理舊文件任務
    
    Args:
        days: 保留天數
    """
    logger.info(f"Starting cleanup of documents older than {days} days")
    
    db = get_sync_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 查找要清理的文件
        old_documents = db.query(Document).filter(
            and_(
                Document.created_at < cutoff_date,
                Document.status.in_([DocumentStatus.VERIFIED, DocumentStatus.FAILED, DocumentStatus.ARCHIVED])
            )
        ).all()
        
        storage_service = StorageService()
        cleaned_count = 0
        
        for document in old_documents:
            try:
                # 從儲存系統中刪除檔案
                asyncio.run(storage_service.delete_file(document.storage_path))
                
                # 更新文件狀態
                document.status = DocumentStatus.ARCHIVED
                cleaned_count += 1
                
                logger.info(f"Archived document {document.id}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup document {document.id}: {e}")
        
        db.commit()
        
        logger.info(f"Cleanup completed: {cleaned_count} documents archived")
        
        return {
            "status": "success",
            "documents_archived": cleaned_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise
    
    finally:
        db.close()


@celery_app.task(name="check_failed_tasks")
def check_failed_tasks() -> Dict[str, Any]:
    """
    檢查失敗的任務
    """
    logger.info("Checking for failed tasks")
    
    db = get_sync_session()
    
    try:
        # 查找失敗的任務
        failed_tasks = db.query(TaskRecord).filter(
            and_(
                TaskRecord.status == "FAILURE",
                TaskRecord.retry_count < 3,
                TaskRecord.created_at > datetime.utcnow() - timedelta(hours=24)
            )
        ).all()
        
        retry_count = 0
        
        for task in failed_tasks:
            try:
                # 重新提交任務
                if task.task_name == "process_document_async":
                    process_document_async.apply_async(
                        args=[str(task.document_id)],
                        countdown=300  # 5 分鐘後執行
                    )
                    
                    task.retry_count += 1
                    retry_count += 1
                    
                    logger.info(f"Retried failed task {task.task_id}")
                
            except Exception as e:
                logger.error(f"Failed to retry task {task.task_id}: {e}")
        
        db.commit()
        
        logger.info(f"Failed task check completed: {retry_count} tasks retried")
        
        return {
            "status": "success",
            "tasks_retried": retry_count
        }
        
    except Exception as e:
        logger.error(f"Failed task check failed: {e}")
        raise
    
    finally:
        db.close()
