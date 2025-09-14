from abc import ABC, abstractmethod
from typing import Any, List
from uuid import UUID


class AbstractAuditService(ABC):
    """
    抽象審計服務介面，用於記錄和查詢應用程式中的重要事件。
    """

    @abstractmethod
    async def log_download(self, document_id: UUID, user_id: UUID, ip_address: str, user_agent: str) -> None:
        """
        記錄文件下載事件。
        Args:
            document_id (UUID): 被下載文件的 ID。
            user_id (UUID): 發起下載的用戶 ID。
            ip_address (str): 用戶的 IP 地址。
            user_agent (str): 用戶的 User-Agent 字符串。
        """
        pass

    @abstractmethod
    async def get_download_logs(self, document_id: UUID, skip: int = 0, limit: int = 100) -> List[Any]:
        """
        獲取指定文件的下載日誌。
        Args:
            document_id (UUID): 文件的 ID。
            skip (int): 跳過的記錄數。
            limit (int): 返回的記錄數限制。
        Returns:
            List[Any]: 下載日誌記錄列表。
        """
        pass
