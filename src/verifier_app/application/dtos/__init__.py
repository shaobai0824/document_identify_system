"""
應用層資料傳輸物件
"""

from .document_dtos import (DocumentStatusResponse, DocumentUploadRequest,
                            DocumentUploadResponse, OCRResultDTO,
                            VerificationResultDTO)

__all__ = [
    "DocumentUploadRequest",
    "DocumentUploadResponse", 
    "DocumentStatusResponse",
    "OCRResultDTO",
    "VerificationResultDTO"
]
