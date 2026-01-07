import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add project root to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.learner import LearnerAgent
from src.db.base import SessionLocal, engine, Base
from src.db.models import Character, NovelBible, PlotOutline, StyleRef
from sqlalchemy.orm import Session
import json

async def import_novel(file_path: str):
    print(f"📂 读取文档: {file_path}")
    if not os.path.exists(file_path):
        print("❌ 文件不存在")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("🧠 正在调用 LearnerAgent 解析文档... (这可能需要一分钟)")
    agent = LearnerAgent()
    try:
        data = await agent.parse_document(content)
        print("✅ 解析成功！正在写入数据库...")
    except Exception as e:
        print(f"❌ 解析过程出错: {e}")
        return

    # Create tables if they don't exist
    print("🛠 正在检查/创建数据库表...")
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✅ pgvector 扩展已就绪")
    except Exception as e:
        print(f"⚠️ 无法创建 pgvector 扩展 (可能权限不足或已存在): {e}")

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表已同步")
    except Exception as e:
        print(f"⚠️ 创建/同步数据库表时出错: {e}")
        # Continue anyway, maybe tables already exist
    
    db: Session = SessionLocal()
    try:
        # 1. 保存世界观 (Novel Bible)
        for item in data.world_view_items:
            bible = NovelBible(
                category=item.category,
                key=item.key,
                content=item.content,
                tags=json.dumps([item.category]) # 简单tag
            )
            db.add(bible)
        print(f"✔ 已导入 {len(data.world_view_items)} 条世界观设定")

        # 2. 保存角色 (Characters)
        for char in data.characters:
            # 简单构建 trait 和 info
            traits = {
                "role": char.role,
                "personality": char.personality,
                "background": char.background
            }
            db_char = Character(
                name=char.name,
                role=char.role,
                personality_traits=traits,
                current_mood="平静", # 初始状态
                evolution_log=["初始设定导入"],
                status={"health": "healthy"}
            )
            # 我们暂不处理 CharacterRelationship 表，需在后续通过分析 relationship_summary 填充
            db.add(db_char)
        print(f"✔ 已导入 {len(data.characters)} 个角色")

        # 3. 保存大纲 (PlotOutlines)
        for outline in data.outlines:
            db_outline = PlotOutline(
                novel_id=1, # 默认 ID
                chapter_number=outline.chapter_number,
                scene_description=outline.scene_description,
                key_conflict=outline.key_conflict,
                foreshadowing=[], 
                recalls=[],
                status="pending" # 初始为 pending
            )
            db.add(db_outline)
        print(f"✔ 已导入 {len(data.outlines)} 章大纲")

        # 4. 保存文风 (StyleRef)
        style_ref = StyleRef(
            content=f"基调: {data.style.tone}\n修辞: {', '.join(data.style.rhetoric)}\n范例: {data.style.example_sentence}",
            source_author="Initial Import",
            style_metadata={
                "tone": data.style.tone,
                "keywords": data.style.keywords
            }
        )
        db.add(style_ref)
        print("✔ 已导入文风设定")

        db.commit()
        print("\n✨ 所有数据导入完成！")
        print("现在你可以运行 'python -m src.main' 开始生成了。")

    except Exception as e:
        db.rollback()
        print(f"❌ 数据库写入失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize NovelGen project from a document.")
    parser.add_argument("file", help="Path to the text file containing novel setup.")
    args = parser.parse_args()

    asyncio.run(import_novel(args.file))
