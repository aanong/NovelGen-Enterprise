"""
数据库迁移脚本：为 reference_materials 表添加 novel_id 字段
"""
import sys
import os
from sqlalchemy import text

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.base import SessionLocal, engine


def migrate():
    """执行迁移"""
    db = SessionLocal()
    try:
        print("🔄 开始迁移：为 reference_materials 表添加 novel_id 字段...")
        
        # 检查字段是否已存在
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'reference_materials' 
        AND column_name = 'novel_id'
        """
        result = db.execute(text(check_sql))
        if result.fetchone():
            print("✅ novel_id 字段已存在，跳过迁移")
            return
        
        # 添加 novel_id 字段
        print("  添加 novel_id 字段...")
        db.execute(text("""
            ALTER TABLE reference_materials 
            ADD COLUMN novel_id INTEGER REFERENCES novels(id) ON DELETE CASCADE
        """))
        
        # 添加索引
        print("  添加索引...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reference_materials_novel_id 
            ON reference_materials(novel_id)
        """))
        
        # 添加复合索引
        print("  添加复合索引...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_novel_category 
            ON reference_materials(novel_id, category)
        """))
        
        db.commit()
        print("✅ 迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
