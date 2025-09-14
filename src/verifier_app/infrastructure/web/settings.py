"""
系統設定路由
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class ProcessingSettings(BaseModel):
    default_confidence: float = Field(0.9, ge=0.0, le=1.0)
    field_overrides: Dict[str, float] = {}
    rate_limits: Dict[str, int] = {
        "ocr_per_min": 100,
        "llm_per_min": 20,
        "documents_per_hour": 1000
    }
    timeout_seconds: int = Field(300, ge=30, le=3600)
    retry_attempts: int = Field(3, ge=1, le=10)


class ProviderSettings(BaseModel):
    ocr_providers: Dict[str, Dict[str, Any]] = {
        "tesseract": {"enabled": True, "weight": 0.7, "timeout": 30},
        "easyocr": {"enabled": True, "weight": 0.3, "timeout": 45}
    }
    llm_providers: Dict[str, Dict[str, Any]] = {
        "openai": {"enabled": True, "weight": 0.6, "model": "gpt-4-vision-preview"},
        "gemini": {"enabled": True, "weight": 0.4, "model": "gemini-pro-vision"}
    }
    fallback_strategy: str = "round_robin"  # round_robin, failover, load_balance
    health_check_interval: int = Field(60, ge=10, le=3600)


# 模擬配置儲存
processing_config = ProcessingSettings()
provider_config = ProviderSettings()


@router.get("/settings/processing", response_model=ProcessingSettings)
async def get_processing_settings():
    """取得處理設定"""
    try:
        return processing_config
    except Exception as e:
        logger.error(f"Failed to get processing settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/settings/processing", response_model=ProcessingSettings)
async def update_processing_settings(settings: ProcessingSettings):
    """更新處理設定"""
    try:
        global processing_config
        processing_config = settings
        
        # TODO: 實作設定持久化
        # config_service.save_processing_settings(settings)
        
        logger.info("Updated processing settings")
        return processing_config
        
    except Exception as e:
        logger.error(f"Failed to update processing settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/settings/providers", response_model=ProviderSettings)
async def get_provider_settings():
    """取得供應商設定"""
    try:
        return provider_config
    except Exception as e:
        logger.error(f"Failed to get provider settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/settings/providers", response_model=ProviderSettings)
async def update_provider_settings(settings: ProviderSettings):
    """更新供應商設定"""
    try:
        global provider_config
        provider_config = settings
        
        # TODO: 實作設定持久化和供應商重新初始化
        # config_service.save_provider_settings(settings)
        # provider_manager.reload_providers(settings)
        
        logger.info("Updated provider settings")
        return provider_config
        
    except Exception as e:
        logger.error(f"Failed to update provider settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/settings/providers/health-check")
async def check_provider_health():
    """檢查所有供應商健康狀態"""
    try:
        # TODO: 實作供應商健康檢查
        health_status = {
            "ocr_providers": {
                "tesseract": {"status": "healthy", "response_time_ms": 150},
                "easyocr": {"status": "healthy", "response_time_ms": 200}
            },
            "llm_providers": {
                "openai": {"status": "healthy", "response_time_ms": 800},
                "gemini": {"status": "degraded", "response_time_ms": 1200, "error": "Rate limit exceeded"}
            },
            "checked_at": "2025-01-07T12:00:00Z"
        }
        
        logger.info("Performed provider health check")
        return health_status
        
    except Exception as e:
        logger.error(f"Failed to check provider health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/settings/system")
async def get_system_info():
    """取得系統資訊"""
    try:
        import platform

        import psutil
        
        system_info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            },
            "resources": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "api_version": "1.0.0",
            "uptime_seconds": 3600,  # TODO: 實作實際運行時間
            "timezone": "UTC"
        }
        
        return system_info
        
    except ImportError:
        # psutil 未安裝時的回退
        return {
            "platform": {"system": "Unknown"},
            "resources": {"status": "monitoring_unavailable"},
            "api_version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
