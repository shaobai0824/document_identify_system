from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AbstractSignatureDetector(ABC):
    """
    抽象簽名檢測器介面。
    """

    @abstractmethod
    async def check_document(self, document_id: UUID) -> Any:
        """
        檢測文件中的簽名。
        Args:
            document_id (UUID): 文件的 ID。
        Returns:
            Any: 簽名檢測結果。
        """
        pass
