from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# 使用配置管理数据库连接
try:
    from ..config import Config
    DATABASE_URL = Config.database.POSTGRES_URL or os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/novelgen")
    # 使用动态方法获取连接池配置
    POOL_SIZE = Config.database.get_pool_size()
    MAX_OVERFLOW = Config.database.get_max_overflow()
    POOL_RECYCLE = Config.database.POOL_RECYCLE
except ImportError:
    # 如果 Config 不可用，使用环境变量或默认值
    DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/novelgen")
    concurrent_tasks = int(os.getenv("CONCURRENT_TASKS", "5"))
    POOL_SIZE = int(os.getenv("DB_POOL_SIZE", str(max(10, concurrent_tasks * 2))))
    MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", str(POOL_SIZE * 2)))
    POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# 使用连接池配置优化数据库连接
engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # 自动检测和恢复断开的连接
    echo=False,  # 设置为 True 可以查看 SQL 日志
    pool_reset_on_return='commit'  # 返回连接时重置状态
)

# 连接池监控函数
def get_pool_stats() -> Dict[str, Any]:
    """
    获取连接池统计信息
    
    Returns:
        包含连接池状态的字典
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid()
    }

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
