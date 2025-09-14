from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AbstractIntegrityChecker(ABC):
    """
    抽象文件完整性檢查器介面。
    """

    @abstractmethod
    async def verify(self, document_id: UUID) -> Any:
        """
        驗證文件的完整性。
        Args:
            document_id (UUID): 文件的 ID。
        Returns:
            Any: 驗證結果。
        """
        pass
