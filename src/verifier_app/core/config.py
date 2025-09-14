"""
應用程式配置管理
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "文件驗證服務"
    DEBUG_MODE: bool = False
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./verifier_dev.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 文件儲存相關
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./src/storage/documents")

    # 浮水印相關
    WATERMARK_TEXT: str = os.getenv("WATERMARK_TEXT", "CONFIDENTIAL")
    WATERMARK_COLOR: str = "#000000"

    # API 前綴
    API_V1_STR: str = "/api/v1"
    
    # OCR 配置
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "tesseract")  # tesseract, google_vision
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    GOOGLE_VISION_CREDENTIALS_PATH: str = os.getenv("GOOGLE_VISION_CREDENTIALS_PATH", "")
    
    # LLM 配置
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, gemini
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # 文件處理配置
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FILE_TYPES: list = ["pdf", "jpg", "jpeg", "png", "tiff", "bmp"]
    DEFAULT_CONFIDENCE_THRESHOLD: float = float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.8"))
    
    # 儲存配置
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")  # local, s3, minio
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    
    # MinIO 配置
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
