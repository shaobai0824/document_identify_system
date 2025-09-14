"""
檔案服務端點
"""

import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from ..services.storage_service import StorageService

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """提供檔案服務"""
    try:
        storage_service = StorageService()
        
        # 檢查檔案是否存在
        if not await storage_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # 根據儲存適配器類型處理檔案
        adapter = storage_service.adapter
        
        if hasattr(adapter, 'base_path'):  # LocalStorageAdapter
            # 本地儲存
            file_path_obj = adapter.base_path / file_path
            
            if not file_path_obj.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            # 推測 MIME 類型
            mime_type, _ = mimetypes.guess_type(str(file_path_obj))
            if not mime_type:
                mime_type = "application/octet-stream"
            
            return FileResponse(
                path=str(file_path_obj),
                media_type=mime_type,
                filename=file_path_obj.name
            )
        
        else:
            # S3 或 MinIO 儲存 - 重定向到預簽名 URL
            file_url = await storage_service.get_file_url(file_path)
            if not file_url:
                raise HTTPException(status_code=404, detail="File not found")
            
            # 如果是本地檔案 URL，直接提供檔案
            if file_url.startswith("file://"):
                local_path = file_url.replace("file://", "")
                file_path_obj = Path(local_path)
                
                if not file_path_obj.exists():
                    raise HTTPException(status_code=404, detail="File not found")
                
                mime_type, _ = mimetypes.guess_type(str(file_path_obj))
                if not mime_type:
                    mime_type = "application/octet-stream"
                
                return FileResponse(
                    path=str(file_path_obj),
                    media_type=mime_type,
                    filename=file_path_obj.name
                )
            
            # 對於 S3/MinIO，重定向到預簽名 URL
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=file_url)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
