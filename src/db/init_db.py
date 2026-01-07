import logging
import sys
import time
from sqlalchemy import text
from .base import engine, Base
# Import all models to ensure they are registered with Base metadata
from .models import StyleRef, NovelBible, Character, CharacterRelationship, PlotOutline, Chapter, LogicAudit

# 配置日志 - 企业级标准
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_init")

def create_extensions():
    """创建必要的扩展，如 pgvector"""
    logger.info("🔧 检查并创建数据库扩展 (pgvector)...")
    try:
        with engine.connect() as conn:
            # pgvector 扩展通常需要超级用户权限或特定权限
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        logger.info("✅ 数据库扩展检查完毕")
    except Exception as e:
        logger.warning(f"⚠️ 创建扩展 'vector' 失败: {e}")
        logger.warning("请确保您的数据库支持 pgvector 且当前用户有权创建扩展。")

def check_connection():
    """验证数据库连接"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接验证失败: {e}")
        return False

def wait_for_db(retries: int = 5, delay: int = 2) -> bool:
    """等待数据库就绪"""
    for i in range(retries):
        if check_connection():
            return True
        logger.info(f"⏳ 正在同步等待数据库启动... ({i+1}/{retries})")
        time.sleep(delay)
    return False

def init_db(drop_all: bool = False):
    """
    初始化数据库表结构
    
    Args:
        drop_all: 是否删除所有现有表重新创建 (慎用!)
    """
    logger.info("🚀 启动数据库初始化程序...")
    
    if not wait_for_db():
        logger.error("终止初始化: 数据库连接超时，无法连接至数据库。")
        return

    # 1. 创建扩展
    create_extensions()

    # 2. 处理表结构
    try:
        if drop_all:
            logger.warning("🧨 正在删除所有现有表结构 (drop_all=True)...")
            Base.metadata.drop_all(bind=engine)
            logger.info("✅ 旧表结构已清理")

        logger.info("🏗️ 正在同步数据库架构 (create_all)...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表结构同步成功！")
        
    except Exception as e:
        logger.error(f"❌ 表结构同步失败: {e}")
        raise e

if __name__ == "__main__":
    # 可以通过命令行参数或环境变量控制是否 drop_all
    import argparse
    parser = argparse.ArgumentParser(description="Initializes the database schema.")
    parser.add_argument("--drop", action="store_true", help="Drop all tables before creating them.")
    args = parser.parse_args()
    
    init_db(drop_all=args.drop)
