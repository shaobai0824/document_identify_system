from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ...core.config import settings

# 根據配置決定資料庫連接字串
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 創建 SQLAlchemy 引擎
# connect_args 僅適用於 SQLite
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={
            "check_same_thread": False
        },
        poolclass=StaticPool, # For SQLite only, to avoid connection issues with multiple threads
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 創建 SessionLocal 類別，每個請求都會創建一個獨立的會話
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    依賴注入器，用於獲取資料庫會話。
    每個請求都會提供一個新的資料庫會話，並在請求結束時關閉。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
