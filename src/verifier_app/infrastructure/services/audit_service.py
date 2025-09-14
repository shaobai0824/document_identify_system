from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel


class DownloadAuditLogEntry(BaseModel):
    id: str
    document_id: str
    user_id: str
    user_name: str
    downloaded_at: datetime
    reason: Optional[str]
    watermark_applied: bool
    ip_address: str = ""
    user_agent: str = ""

class AuditService:
    async def log_download(
        self,
        user_id: str,
        document_id: str,
        reason: Optional[str],
        watermark_applied: bool
    ):
        # 實際日誌記錄邏輯（例如，寫入數據庫）
        print(f"模擬記錄下載：用戶 {user_id} 下載文件 {document_id}, 原因: {reason}, 浮水印: {watermark_applied}")

    async def get_download_logs(
        self,
        limit: int,
        offset: int,
        document_id: Optional[str],
        user_id: Optional[str]
    ) -> Tuple[List[DownloadAuditLogEntry], int]:
        # 模擬從數據庫獲取日誌
        mock_logs = [
            DownloadAuditLogEntry(
                id="audit_001",
                document_id="doc_123",
                user_id="user_456",
                user_name="張三",
                downloaded_at=datetime.utcnow(),
                reason="法務審查",
                watermark_applied=True,
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0..."
            ),
            DownloadAuditLogEntry(
                id="audit_002",
                document_id="doc_456",
                user_id="user_789",
                user_name="李四",
                downloaded_at=datetime.utcnow(),
                reason="內部審核",
                watermark_applied=False,
                ip_address="192.168.1.101",
                user_agent="Chrome/..."
            )
        ]

        filtered_logs = []
        for log in mock_logs:
            if document_id and log.document_id != document_id:
                continue
            if user_id and log.user_id != user_id:
                continue
            filtered_logs.append(log)

        total_count = len(filtered_logs)
        return filtered_logs[offset:offset + limit], total_count
