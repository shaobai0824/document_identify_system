"""
外部服務適配器模組
"""

from .ocr import OCRResult, TesseractAdapter
from .storage import (LocalStorageAdapter, S3StorageAdapter,
                      StorageAdapterFactory)

__all__ = [
    "TesseractAdapter",
    "OCRResult",
    "LocalStorageAdapter", 
    "S3StorageAdapter",
    "StorageAdapterFactory"
]
