"""
資料庫基礎設定和連線管理
"""

import logging
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ...core.config import settings

logger = logging.getLogger(__name__)

# 建立基礎模型類別
Base = declarative_base()

# 全域資料庫引擎和會話
engine = None
SessionLocal = None


def init_database() -> None:
    """初始化資料庫連線"""
    global engine, SessionLocal
    
    # settings = get_settings() # 移除此行，因為 settings 已在頂部導入
    
    # 根據資料庫 URL 決定引擎配置
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite 配置（開發環境）
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DEBUG_MODE
        )
    else:
        # PostgreSQL 或其他資料庫配置（生產環境）
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.DEBUG_MODE
        )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 建立所有表格（僅在開發環境，生產環境應使用 Alembic）
    if settings.DEBUG_MODE:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (development mode)")
    
    logger.info(f"Database initialized with URL: {settings.DATABASE_URL}")


def get_database_session() -> Generator[Session, None, None]:
    """取得資料庫會話（FastAPI 依賴注入用）"""
    if SessionLocal is None:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_session() -> Session:
    """取得同步資料庫會話（背景任務用）"""
    if SessionLocal is None:
        init_database()
    
    return SessionLocal()
