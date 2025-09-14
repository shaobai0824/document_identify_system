"""
任務管理器
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery.result import AsyncResult
from sqlalchemy.orm import Session

from ..database.base import get_sync_session
from ..database.models import Document, TaskRecord
from .celery_app import celery_app
from .document_tasks import process_document_async, reprocess_document_async

logger = logging.getLogger(__name__)


class TaskManager:
    """任務管理器"""
    
    def __init__(self):
        """初始化任務管理器"""
        self.celery_app = celery_app
    
    def submit_document_processing(self, 
                                 document_id: str, 
                                 template_id: Optional[str] = None,
                                 priority: str = "normal") -> str:
        """
        提交文件處理任務
        
        Args:
            document_id: 文件 ID
            template_id: 驗證模板 ID
            priority: 任務優先級 (low, normal, high)
            
        Returns:
            任務 ID
        """
        try:
            # 根據優先級選擇佇列
            queue = "document_processing"
            if priority == "high":
                queue = "high_priority"
            
            # 提交任務
            result = process_document_async.apply_async(
                args=[document_id, template_id, priority],
                queue=queue
            )
            
            logger.info(f"Submitted document processing task: {result.id} for document {document_id}")
            return result.id
            
        except Exception as e:
            logger.error(f"Failed to submit document processing task: {e}")
            raise
    
    def submit_document_reprocessing(self, 
                                   document_id: str, 
                                   template_id: Optional[str] = None) -> str:
        """
        提交文件重新處理任務
        
        Args:
            document_id: 文件 ID
            template_id: 新的驗證模板 ID
            
        Returns:
            任務 ID
        """
        try:
            result = reprocess_document_async.apply_async(
                args=[document_id, template_id],
                queue="high_priority"  # 重新處理使用高優先級佇列
            )
            
            logger.info(f"Submitted document reprocessing task: {result.id} for document {document_id}")
            return result.id
            
        except Exception as e:
            logger.error(f"Failed to submit document reprocessing task: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        取得任務狀態
        
        Args:
            task_id: 任務 ID
            
        Returns:
            任務狀態資訊
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            # 從資料庫取得額外資訊
            db = get_sync_session()
            try:
                task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
                
                status_info = {
                    "task_id": task_id,
                    "status": result.status,
                    "result": result.result,
                    "traceback": result.traceback if result.failed() else None,
                    "progress": result.info if result.status == "PROGRESS" else None
                }
                
                if task_record:
                    status_info.update({
                        "task_name": task_record.task_name,
                        "task_type": task_record.task_type,
                        "document_id": str(task_record.document_id) if task_record.document_id else None,
                        "created_at": task_record.created_at.isoformat() if task_record.created_at else None,
                        "started_at": task_record.started_at.isoformat() if task_record.started_at else None,
                        "completed_at": task_record.completed_at.isoformat() if task_record.completed_at else None,
                        "execution_time_ms": task_record.execution_time_ms,
                        "retry_count": task_record.retry_count,
                        "error_info": task_record.error_info
                    })
                
                return status_info
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            raise
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任務
        
        Args:
            task_id: 任務 ID
            
        Returns:
            是否成功取消
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            result.revoke(terminate=True)
            
            # 更新資料庫記錄
            db = get_sync_session()
            try:
                task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
                if task_record:
                    task_record.status = "REVOKED"
                    db.commit()
                    
            finally:
                db.close()
            
            logger.info(f"Cancelled task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        取得活躍任務列表
        
        Returns:
            活躍任務列表
        """
        try:
            # 取得 Celery 活躍任務
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()
            
            if not active_tasks:
                return []
            
            # 整理任務資訊
            tasks = []
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks:
                    tasks.append({
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "worker": worker,
                        "args": task.get("args", []),
                        "kwargs": task.get("kwargs", {}),
                        "time_start": task.get("time_start")
                    })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return []
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """
        取得任務統計資訊
        
        Returns:
            任務統計資訊
        """
        try:
            db = get_sync_session()
            try:
                # 統計各狀態的任務數量
                stats = {}
                
                # 按狀態統計
                status_counts = db.query(TaskRecord.status, db.func.count(TaskRecord.id)).group_by(TaskRecord.status).all()
                stats["by_status"] = {status: count for status, count in status_counts}
                
                # 按類型統計
                type_counts = db.query(TaskRecord.task_type, db.func.count(TaskRecord.id)).group_by(TaskRecord.task_type).all()
                stats["by_type"] = {task_type: count for task_type, count in type_counts}
                
                # 總數
                total_tasks = db.query(TaskRecord).count()
                stats["total_tasks"] = total_tasks
                
                # 今日任務數
                from datetime import datetime, timedelta
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_tasks = db.query(TaskRecord).filter(TaskRecord.created_at >= today_start).count()
                stats["today_tasks"] = today_tasks
                
                return stats
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to get task statistics: {e}")
            return {}
