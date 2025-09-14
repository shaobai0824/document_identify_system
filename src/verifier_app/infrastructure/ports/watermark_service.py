from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AbstractWatermarkService(ABC):
    """
    抽象浮水印服務介面。
    """

    @abstractmethod
    async def apply_watermark(self, document_id: UUID, watermark_text: str) -> Any:
        """
        為文件應用浮水印並返回帶浮水印的內容。
        Args:
            document_id (UUID): 文件的 ID。
            watermark_text (str): 應用於文件的浮水印文本。
        Returns:
            Any: 帶浮水印的文件內容（例如，bytes 或文件路徑）。
        """
        pass
