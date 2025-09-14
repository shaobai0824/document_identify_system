"""
儲存適配器實作
"""

import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class StorageAdapter(ABC):
    """儲存適配器基礎類別"""
    
    @abstractmethod
    async def upload_file(self, local_path: str, storage_path: str) -> str:
        """上傳檔案"""
        pass
    
    @abstractmethod
    async def upload_file_content(self, file_content: bytes, storage_path: str) -> str:
        """上傳檔案內容"""
        pass
    
    @abstractmethod
    async def download_file(self, storage_path: str, local_path: str) -> bool:
        """下載檔案"""
        pass
    
    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """刪除檔案"""
        pass
    
    @abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """檢查檔案是否存在"""
        pass
    
    @abstractmethod
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """取得檔案 URL"""
        pass


class LocalStorageAdapter(StorageAdapter):
    """本地儲存適配器"""
    
    def __init__(self, base_path: str = "./storage"):
        """初始化本地儲存適配器"""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_path}")
    
    async def upload_file(self, local_path: str, storage_path: str) -> str:
        """上傳檔案到本地儲存"""
        try:
            source = Path(local_path)
            destination = self.base_path / storage_path
            
            # 建立目標目錄
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 複製檔案
            shutil.copy2(source, destination)
            
            logger.info(f"File uploaded: {local_path} -> {destination}")
            return str(destination)
            
        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            raise
    
    async def upload_file_content(self, file_content: bytes, storage_path: str) -> str:
        """上傳檔案內容到本地儲存"""
        try:
            destination = self.base_path / storage_path
            
            # 建立目標目錄
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 寫入檔案內容
            with open(destination, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File content uploaded: {storage_path}")
            return str(destination)
            
        except Exception as e:
            logger.error(f"Failed to upload file content {storage_path}: {e}")
            raise
    
    async def download_file(self, storage_path: str, local_path: str) -> bool:
        """從本地儲存下載檔案"""
        try:
            source = self.base_path / storage_path
            destination = Path(local_path)
            
            if not source.exists():
                logger.warning(f"Source file not found: {source}")
                return False
            
            # 建立目標目錄
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 複製檔案
            shutil.copy2(source, destination)
            
            logger.info(f"File downloaded: {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file {storage_path}: {e}")
            return False
    
    async def delete_file(self, storage_path: str) -> bool:
        """從本地儲存刪除檔案"""
        try:
            file_path = self.base_path / storage_path
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {storage_path}: {e}")
            return False
    
    async def file_exists(self, storage_path: str) -> bool:
        """檢查檔案是否存在"""
        file_path = self.base_path / storage_path
        return file_path.exists()
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """取得檔案 URL（本地儲存返回檔案路徑）"""
        file_path = self.base_path / storage_path
        if file_path.exists():
            return f"file://{file_path.absolute()}"
        return None


class S3StorageAdapter(StorageAdapter):
    """AWS S3 儲存適配器"""
    
    def __init__(self, 
                 bucket_name: str,
                 region_name: str = "us-east-1",
                 endpoint_url: Optional[str] = None,
                 access_key_id: Optional[str] = None,
                 secret_access_key: Optional[str] = None):
        """初始化 S3 儲存適配器"""
        self.bucket_name = bucket_name
        self.region_name = region_name
        
        # 建立 S3 客戶端
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name
        )
        
        self.s3_client = session.client(
            's3',
            endpoint_url=endpoint_url
        )
        
        # 驗證 bucket 存在
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"S3 storage initialized with bucket: {bucket_name}")
        except ClientError as e:
            logger.error(f"S3 bucket not accessible: {e}")
            raise
    
    async def upload_file(self, local_path: str, storage_path: str) -> str:
        """上傳檔案到 S3"""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, storage_path)
            
            storage_url = f"s3://{self.bucket_name}/{storage_path}"
            logger.info(f"File uploaded to S3: {local_path} -> {storage_url}")
            return storage_url
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3 {local_path}: {e}")
            raise
    
    async def upload_file_content(self, file_content: bytes, storage_path: str) -> str:
        """上傳檔案內容到 S3"""
        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=storage_path, Body=file_content)
            
            storage_url = f"s3://{self.bucket_name}/{storage_path}"
            logger.info(f"File content uploaded to S3: {storage_path}")
            return storage_url
            
        except ClientError as e:
            logger.error(f"Failed to upload file content to S3 {storage_path}: {e}")
            raise
    
    async def download_file(self, storage_path: str, local_path: str) -> bool:
        """從 S3 下載檔案"""
        try:
            # 建立本地目錄
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.s3_client.download_file(self.bucket_name, storage_path, local_path)
            
            logger.info(f"File downloaded from S3: s3://{self.bucket_name}/{storage_path} -> {local_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to download file from S3 {storage_path}: {e}")
            return False
    
    async def delete_file(self, storage_path: str) -> bool:
        """從 S3 刪除檔案"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_path)
            
            logger.info(f"File deleted from S3: s3://{self.bucket_name}/{storage_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file from S3 {storage_path}: {e}")
            return False
    
    async def file_exists(self, storage_path: str) -> bool:
        """檢查 S3 檔案是否存在"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except ClientError:
            return False
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """取得 S3 檔案預簽名 URL"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': storage_path},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {storage_path}: {e}")
            return None


class MinIOStorageAdapter(StorageAdapter):
    """MinIO 儲存適配器（S3 相容）"""
    
    def __init__(self, 
                 endpoint: str,
                 bucket_name: str,
                 access_key: str,
                 secret_key: str,
                 secure: bool = True):
        """初始化 MinIO 儲存適配器"""
        self.bucket_name = bucket_name
        
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # 建立 bucket（如果不存在）
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
            else:
                logger.info(f"MinIO storage initialized with bucket: {bucket_name}")
        except S3Error as e:
            logger.error(f"MinIO bucket error: {e}")
            raise
    
    async def upload_file(self, local_path: str, storage_path: str) -> str:
        """上傳檔案到 MinIO"""
        try:
            self.client.fput_object(self.bucket_name, storage_path, local_path)
            
            storage_url = f"minio://{self.bucket_name}/{storage_path}"
            logger.info(f"File uploaded to MinIO: {local_path} -> {storage_url}")
            return storage_url
            
        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO {local_path}: {e}")
            raise
    
    async def upload_file_content(self, file_content: bytes, storage_path: str) -> str:
        """上傳檔案內容到 MinIO"""
        try:
            self.client.put_object(self.bucket_name, storage_path, file_content)
            
            storage_url = f"minio://{self.bucket_name}/{storage_path}"
            logger.info(f"File content uploaded to MinIO: {storage_path}")
            return storage_url
            
        except S3Error as e:
            logger.error(f"Failed to upload file content to MinIO {storage_path}: {e}")
            raise
    
    async def download_file(self, storage_path: str, local_path: str) -> bool:
        """從 MinIO 下載檔案"""
        try:
            # 建立本地目錄
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.client.fget_object(self.bucket_name, storage_path, local_path)
            
            logger.info(f"File downloaded from MinIO: minio://{self.bucket_name}/{storage_path} -> {local_path}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to download file from MinIO {storage_path}: {e}")
            return False
    
    async def delete_file(self, storage_path: str) -> bool:
        """從 MinIO 刪除檔案"""
        try:
            self.client.remove_object(self.bucket_name, storage_path)
            
            logger.info(f"File deleted from MinIO: minio://{self.bucket_name}/{storage_path}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO {storage_path}: {e}")
            return False
    
    async def file_exists(self, storage_path: str) -> bool:
        """檢查 MinIO 檔案是否存在"""
        try:
            self.client.stat_object(self.bucket_name, storage_path)
            return True
        except S3Error:
            return False
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """取得 MinIO 檔案預簽名 URL"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name, 
                storage_path, 
                expires=timedelta(seconds=expires_in)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {storage_path}: {e}")
            return None


# 儲存適配器工廠
class StorageAdapterFactory:
    """儲存適配器工廠"""
    
    @classmethod
    def create_adapter(cls, provider: str, **kwargs) -> StorageAdapter:
        """建立儲存適配器"""
        if provider == "local":
            return LocalStorageAdapter(**kwargs)
        elif provider == "s3":
            return S3StorageAdapter(**kwargs)
        elif provider == "minio":
            return MinIOStorageAdapter(**kwargs)
        else:
            raise ValueError(f"Unsupported storage provider: {provider}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """取得可用的儲存提供者"""
        return ["local", "s3", "minio"]
