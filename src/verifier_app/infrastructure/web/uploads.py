"""
預簽上傳路由
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ...infrastructure.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)


class PresignRequest(BaseModel):
    mime_type: str
    size: int
    checksum: Optional[str] = None


class PresignResponse(BaseModel):
    url: str
    fields: dict
    expires_at: str
    object_key: str


class UploadResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    document_id: str
    message: str


@router.post("/uploads/presign", response_model=PresignResponse)
async def presign_upload(request: PresignRequest):
    """產生預簽上傳 URL"""
    try:
        # 驗證檔案類型
        allowed_types = [
            "image/png", "image/jpeg", "image/jpg", 
            "application/pdf", "image/tiff", "image/tif"
        ]
        
        if request.mime_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {request.mime_type}. Allowed: {', '.join(allowed_types)}"
            )
        
        # 驗證檔案大小 (50MB)
        max_size = 50 * 1024 * 1024
        if request.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size {request.size} exceeds maximum allowed size {max_size}"
            )
        
        # 生成物件鍵
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = request.mime_type.split('/')[-1]
        if file_extension == "jpeg":
            file_extension = "jpg"
        
        object_key = f"uploads/{timestamp}_{hashlib.md5(str(request.size).encode()).hexdigest()[:8]}.{file_extension}"
        
        # 生成預簽 URL
        storage_service = StorageService()
        
        # TODO: 實作實際的預簽上傳邏輯
        # presigned_data = storage_service.generate_presigned_upload(
        #     object_key=object_key,
        #     mime_type=request.mime_type,
        #     size=request.size,
        #     expires_in=3600  # 1 hour
        # )
        
        # 模擬預簽回應
        expires_at = datetime.utcnow() + timedelta(hours=1)
        presigned_data = {
            "url": f"https://storage.example.com/{object_key}",
            "fields": {
                "key": object_key,
                "Content-Type": request.mime_type,
                "x-amz-meta-size": str(request.size),
                "x-amz-meta-checksum": request.checksum or "",
                "policy": "base64_encoded_policy",
                "x-amz-signature": "generated_signature"
            }
        }
        
        response = PresignResponse(
            url=presigned_data["url"],
            fields=presigned_data["fields"],
            expires_at=expires_at.isoformat(),
            object_key=object_key
        )
        
        logger.info(f"Generated presigned upload URL for {object_key}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate presigned upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/uploads/complete")
async def complete_upload(object_key: str, etag: str):
    """完成分段上傳"""
    try:
        # TODO: 實作分段上傳完成邏輯
        # storage_service = StorageService()
        # result = storage_service.complete_multipart_upload(object_key, etag)
        
        logger.info(f"Completed upload for {object_key}")
        
        return {
            "object_key": object_key,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to complete upload for {object_key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/uploads/{object_key}")
async def cancel_upload(object_key: str):
    """取消上傳"""
    try:
        # TODO: 實作取消上傳邏輯
        # storage_service = StorageService()
        # storage_service.abort_multipart_upload(object_key)
        
        logger.info(f"Cancelled upload for {object_key}")
        
        return {
            "object_key": object_key,
            "status": "cancelled",
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel upload for {object_key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upload/document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上傳單個文件"""
    try:
        # 實際文件處理邏輯
        content = await file.read()
        document_id = f"doc_{hash(content).__abs__()}"  # 模擬生成 document_id

        logger.info(f"Uploaded file: {file.filename}, size: {len(content)} bytes")

        return UploadResponse(
            filename=file.filename,
            content_type=file.content_type,
            size=len(content),
            document_id=document_id,
            message="文件上傳成功！"
        )
    except Exception as e:
        logger.error(f"文件上傳失敗: {e}")
        raise HTTPException(status_code=500, detail="文件上傳失敗")


@router.post("/upload/documents", response_model=List[UploadResponse])
async def upload_multiple_documents(files: List[UploadFile] = File(...)):
    """上傳多個文件"""
    responses = []
    for file in files:
        try:
            content = await file.read()
            document_id = f"doc_{hash(content).__abs__()}"  # 模擬生成 document_id

            logger.info(f"Uploaded file: {file.filename}, size: {len(content)} bytes")

            responses.append(
                UploadResponse(
                    filename=file.filename,
                    content_type=file.content_type,
                    size=len(content),
                    document_id=document_id,
                    message="文件上傳成功！"
                )
            )
        except Exception as e:
            logger.error(f"單個文件 {file.filename} 上傳失敗: {e}")
            responses.append(
                UploadResponse(
                    filename=file.filename,
                    content_type=file.content_type if file.content_type else "application/octet-stream",
                    size=0,
                    document_id="",
                    message=f"文件上傳失敗: {e}"
                )
            )
    return responses
