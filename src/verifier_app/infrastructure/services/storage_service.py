"""
儲存服務實作
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple

from ...core.config import settings
from ...domains.documents.models import Document
from ...infrastructure.ports.storage import AbstractStorageService
from ..adapters.storage import StorageAdapterFactory

logger = logging.getLogger(__name__)


async def _generate_mock_file_content(document_id: str) -> AsyncGenerator[bytes, None]:
    content = f"This is a mock content for document ID: {document_id}.\n" \
              f"This content is for demonstration purposes only." 
    for chunk in [content[i:i + 10] for i in range(0, len(content), 10)]:
        yield chunk.encode('utf-8')
        await asyncio.sleep(0.01) # 模擬異步讀取延遲

class StorageService(AbstractStorageService):
    """儲存服務實作"""
    
    def __init__(self):
        """初始化儲存服務"""
        self.settings = settings
        
        # 根據配置建立適配器
        if settings.S3_ENDPOINT_URL:
            # 使用 MinIO 或自訂 S3 端點
            self.adapter = StorageAdapterFactory.create_adapter(
                "minio",
                endpoint=settings.S3_ENDPOINT_URL.replace("http://", "").replace("https://", ""),
                bucket_name=settings.S3_BUCKET,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                secure=settings.S3_ENDPOINT_URL.startswith("https://")
            )
        elif settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            # 使用 AWS S3
            self.adapter = StorageAdapterFactory.create_adapter(
                "s3",
                bucket_name=settings.S3_BUCKET,
                region_name=settings.S3_REGION,
                access_key_id=settings.AWS_ACCESS_KEY_ID,
                secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        else:
            # 使用本地儲存
            self.adapter = StorageAdapterFactory.create_adapter(
                "local",
                base_path="./storage"
            )
        
        logger.info(f"Storage service initialized with adapter: {type(self.adapter).__name__}")

    async def get_document(self, document_id: str) -> Tuple[AsyncGenerator[bytes, None], str]:
        # 實際文件獲取邏輯（例如，從S3或本地文件系統讀取）
        print(f"模擬從儲存服務獲取文件：{document_id}")
        # 假設文件類型為 PDF
        return _generate_mock_file_content(document_id), "application/pdf"
        
    async def get_file(self, file_path: str) -> Optional[AsyncGenerator[bytes, None]]:
        """獲取檔案內容"""
        return await self.adapter.get_file(file_path)
    
    async def upload_file(self, local_path: str, storage_path: str) -> str:
        """上傳檔案"""
        return await self.adapter.upload_file(local_path, storage_path)
    
    async def upload_file_content(self, file_content: bytes, storage_path: str) -> str:
        """上傳檔案內容"""
        return await self.adapter.upload_file_content(file_content, storage_path)
    
    async def download_file(self, storage_path: str, local_path: str) -> bool:
        """下載檔案"""
        return await self.adapter.download_file(storage_path, local_path)
    
    async def delete_file(self, storage_path: str) -> bool:
        """刪除檔案"""
        return await self.adapter.delete_file(storage_path)
    
    async def file_exists(self, storage_path: str) -> bool:
        """檢查檔案是否存在"""
        return await self.adapter.file_exists(storage_path)
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """取得檔案 URL"""
        return await self.adapter.get_file_url(storage_path, expires_in)
    
    def generate_storage_path(self, original_filename: str, document_id: str, prefix: str = "documents") -> str:
        """產生儲存路徑"""
        file_extension = Path(original_filename).suffix
        return f"{prefix}/{document_id[:2]}/{document_id}{file_extension}"
