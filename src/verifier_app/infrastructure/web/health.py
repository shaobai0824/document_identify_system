"""
健康檢查路由
"""

from fastapi import APIRouter

from ...application.dtos.health_check import HealthCheckResponse

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse, summary="健康檢查")
async def health_check():
    return HealthCheckResponse(status="ok", message="API 服務健康運行！")
