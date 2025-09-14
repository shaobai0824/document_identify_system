"""
儲存服務介面定義
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import UploadFile


class AbstractStorageService(ABC):
    """
    抽象儲存服務介面，定義了儲存服務需要實現的功能。
    所有具體的儲存適配器 (例如本地檔案系統、S3、MinIO) 都應實現此介面。
    """

    @abstractmethod
    async def upload_file(self, file: UploadFile, destination: str) -> str:
        """
        上傳檔案到指定目的地。
        
        Args:
            file (UploadFile): FastAPI 的 UploadFile 對象，包含上傳的檔案。
            destination (str): 檔案在儲存系統中的目標路徑 (相對路徑)。
        
        Returns:
            str: 儲存後檔案的唯一識別符或路徑。
        """
        pass

    @abstractmethod
    async def get_file(self, file_path: str) -> Optional[AsyncGenerator[bytes, None]]:
        """
        從指定路徑獲取檔案內容的異步生成器。
        
        Args:
            file_path (str): 檔案在儲存系統中的路徑。
        
        Returns:
            Optional[AsyncGenerator[bytes, None]]: 異步字節生成器，如果檔案不存在則返回 None。
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        刪除指定路徑的檔案。
        
        Args:
            file_path (str): 檔案在儲存系統中的路徑。
        
        Returns:
            bool: 如果成功刪除則為 True，否則為 False。
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        檢查檔案是否存在。
        
        Args:
            file_path (str): 檔案在儲存系統中的路徑。
        
        Returns:
            bool: 如果檔案存在則為 True，否則為 False。
        """
        pass