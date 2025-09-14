import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .application.dtos.health_check import HealthCheckResponse
from .infrastructure.web.classification import router as classification_router
from .infrastructure.web.health import router as health_router
from .infrastructure.web.processing import router as processing_router
from .infrastructure.web.review import router as review_router
from .infrastructure.web.security import router as security_router  # 假設安全路由存在
from .infrastructure.web.settings import router as settings_router
from .infrastructure.web.storage import router as storage_router
from .infrastructure.web.templates import router as templates_router
from .infrastructure.web.uploads import router as uploads_router
from .infrastructure.web.versions import router as versions_router
from .infrastructure.web.webhooks import router as webhooks_router
from .infrastructure.web.websockets import router as websockets_router

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="文件驗證服務 API",
    description="提供文件上傳、簽名檢測、篡改檢測、完整性驗證、審計日誌等功能。",
    version="1.0.0",
)

# 配置 CORS
origins = [
    "http://localhost",
    "http://localhost:3000",  # 前端應用程式的地址
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(security_router, tags=["Security"])
api_router.include_router(uploads_router, tags=["Uploads"])
api_router.include_router(classification_router, tags=["Classification"])
api_router.include_router(processing_router, prefix="/process", tags=["Processing"])
api_router.include_router(review_router, tags=["Review"])
api_router.include_router(templates_router, tags=["Templates"])
api_router.include_router(settings_router, tags=["Settings"])
api_router.include_router(versions_router, tags=["Versions"])
api_router.include_router(webhooks_router, tags=["Webhooks"])
api_router.include_router(websockets_router, tags=["Websockets"])

# 檔案服務路由（不需要 API 前綴）
app.include_router(storage_router)

app.include_router(api_router)



@app.get("/", response_model=HealthCheckResponse, summary="應用程式根路徑")
async def read_root():
    return HealthCheckResponse(status="ok", message="文件驗證服務正在運行！")

# 其他應用程式啟動或關閉事件，例如數據庫連接
@app.on_event("startup")
async def startup_event():
    logger.info("應用程式啟動中...")
    # 初始化資料庫連接
    from .infrastructure.database.base import init_database
    init_database()
    logger.info("資料庫初始化完成")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("應用程式關閉中...")
    # TODO: 關閉數據庫連接、任務佇列等
