"""
Web 層路由
"""

from .health import router as health_router
from .processing import router as processing_router
from .templates import router as templates_router

__all__ = ["health_router", "templates_router", "processing_router"]
