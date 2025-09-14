"""
Celery 應用程式配置
"""

import logging
import os

from celery import Celery
from kombu import Queue

from ...core.config import settings

logger = logging.getLogger(__name__)

# 取得設定
# settings = get_settings() # This line is removed as per the edit hint

# 建立 Celery 應用程式
celery_app = Celery(
    "document_verifier",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "verifier_app.infrastructure.tasks.document_tasks"
    ]
)

# Celery 配置
celery_app.conf.update(
    # 任務序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # 任務路由
    task_routes={
        "verifier_app.infrastructure.tasks.document_tasks.process_document_async": {"queue": "document_processing"},
        "verifier_app.infrastructure.tasks.document_tasks.reprocess_document_async": {"queue": "document_processing"},
        "verifier_app.infrastructure.tasks.document_tasks.cleanup_old_documents": {"queue": "maintenance"},
    },
    
    # 佇列配置
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("document_processing", routing_key="document_processing"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("high_priority", routing_key="high_priority"),
    ),
    
    # 任務執行配置
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # 結果過期時間
    result_expires=3600,  # 1 小時
    
    # 任務時間限制
    task_time_limit=300,  # 5 分鐘硬限制
    task_soft_time_limit=240,  # 4 分鐘軟限制
    
    # 重試配置
    task_default_retry_delay=60,  # 重試間隔 60 秒
    task_max_retries=3,
    
    # 監控配置
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 日誌配置
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# 定期任務配置
celery_app.conf.beat_schedule = {
    # 每天清理舊文件
    "cleanup-old-documents": {
        "task": "verifier_app.infrastructure.tasks.document_tasks.cleanup_old_documents",
        "schedule": 86400.0,  # 24 小時
    },
    # 每小時檢查失敗的任務
    "check-failed-tasks": {
        "task": "verifier_app.infrastructure.tasks.document_tasks.check_failed_tasks", 
        "schedule": 3600.0,  # 1 小時
    },
}

logger.info("Celery application configured")


@celery_app.task(bind=True)
def debug_task(self):
    """除錯任務"""
    print(f'Request: {self.request!r}')
