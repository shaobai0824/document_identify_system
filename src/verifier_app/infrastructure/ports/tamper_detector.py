from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AbstractTamperDetector(ABC):
    """
    抽象篡改檢測器介面。
    """

    @abstractmethod
    async def analyze_document(self, document_id: UUID) -> Any:
        """
        分析文件是否被篡改。
        Args:
            document_id (UUID): 文件的 ID。
        Returns:
            Any: 篡改檢測結果。
        """
        pass
