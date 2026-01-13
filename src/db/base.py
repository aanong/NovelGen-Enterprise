from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# 使用配置管理数据库连接
try:
    from ..config import Config
    DATABASE_URL = Config.database.POSTGRES_URL or os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/novelgen")
    POOL_SIZE = Config.database.POOL_SIZE
    MAX_OVERFLOW = Config.database.MAX_OVERFLOW
    POOL_RECYCLE = Config.database.POOL_RECYCLE
except ImportError:
    # 如果 Config 不可用，使用环境变量或默认值
    DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/novelgen")
    POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# 使用连接池配置优化数据库连接
engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # 自动检测和恢复断开的连接
    echo=False  # 设置为 True 可以查看 SQL 日志
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
