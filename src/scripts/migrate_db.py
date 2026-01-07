"""
数据库迁移脚本
用于更新数据库 schema 以支持新的 Antigravity Rules 特性
"""
from sqlalchemy import text
from src.db.base import SessionLocal, engine
from src.db.models import Base
import sys


def upgrade_database():
    """升级数据库到最新版本"""
    print("🔄 开始数据库迁移...")
    
    db = SessionLocal()
    
    try:
        # 1. 创建所有新表（如果不存在）
        print("📋 创建新表...")
        Base.metadata.create_all(bind=engine)
        
        # 2. 添加新索引（如果不存在）
        print("🔍 添加索引...")
        
        # 检查并创建复合索引
        indexes_to_create = [
            ("novel_bible", "idx_category_importance", "CREATE INDEX IF NOT EXISTS idx_category_importance ON novel_bible(category, importance)"),
            ("character_relationships", "idx_char_pair", "CREATE INDEX IF NOT EXISTS idx_char_pair ON character_relationships(char_a_id, char_b_id)"),
            ("plot_outlines", "idx_novel_chapter", "CREATE UNIQUE INDEX IF NOT EXISTS idx_novel_chapter ON plot_outlines(novel_id, chapter_number)"),
            ("chapters", "idx_novel_chapter_num", "CREATE UNIQUE INDEX IF NOT EXISTS idx_novel_chapter_num ON chapters(novel_id, chapter_number)"),
        ]
        
        for table, index_name, sql in indexes_to_create:
            try:
                db.execute(text(sql))
                print(f"  ✅ 索引 {index_name} 已创建/验证")
            except Exception as e:
                print(f"  ⚠️ 索引 {index_name} 创建失败（可能已存在）: {e}")
        
        # 3. 添加新列（如果不存在）
        print("📝 检查并添加新列...")
        
        columns_to_add = [
            ("chapters", "chapter_number", "ALTER TABLE chapters ADD COLUMN IF NOT EXISTS chapter_number INTEGER"),
            ("logic_audits", "chapter_id", "ALTER TABLE logic_audits ADD COLUMN IF NOT EXISTS chapter_id INTEGER"),
        ]
        
        for table, column, sql in columns_to_add:
            try:
                # PostgreSQL 支持 IF NOT EXISTS
                db.execute(text(sql))
                print(f"  ✅ 列 {table}.{column} 已添加/验证")
            except Exception as e:
                print(f"  ℹ️ 列 {table}.{column} 可能已存在: {e}")
        
        db.commit()
        print("✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def downgrade_database():
    """回滚数据库到之前版本（谨慎使用）"""
    print("⚠️ 警告：回滚操作将删除新增的索引和约束")
    confirm = input("确认回滚？(yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ 取消回滚")
        return
    
    db = SessionLocal()
    
    try:
        print("🔄 开始回滚...")
        
        # 删除新增的索引
        indexes_to_drop = [
            "DROP INDEX IF EXISTS idx_category_importance",
            "DROP INDEX IF EXISTS idx_char_pair",
            "DROP INDEX IF EXISTS idx_novel_chapter",
            "DROP INDEX IF EXISTS idx_novel_chapter_num",
        ]
        
        for sql in indexes_to_drop:
            try:
                db.execute(text(sql))
                print(f"  ✅ 已删除索引")
            except Exception as e:
                print(f"  ⚠️ 删除索引失败: {e}")
        
        db.commit()
        print("✅ 回滚完成")
        
    except Exception as e:
        print(f"❌ 回滚失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("action", choices=["upgrade", "downgrade"], help="迁移操作")
    args = parser.parse_args()
    
    if args.action == "upgrade":
        upgrade_database()
    elif args.action == "downgrade":
        downgrade_database()
