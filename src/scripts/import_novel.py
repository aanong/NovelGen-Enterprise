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
from src.utils import get_embedding
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

async def import_novel(file_path: str, use_llm: bool = True):
    print(f"📂 读取文档: {file_path}")
    if not os.path.exists(file_path):
        print("❌ 文件不存在")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = None
    if use_llm:
        print("🧠 正在调用 LearnerAgent 解析文档... (这可能需要一分钟)")
        agent = LearnerAgent()
        try:
            data = await agent.parse_document(content)
            print("✅ 解析成功！正在写入数据库...")
        except Exception as e:
            print(f"❌ 解析过程出错: {e}")
    if data is None:
        print("🔧 使用本地回退解析模式")
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        world = []
        if lines:
            world.append({"category": "设定", "key": "初始", "content": lines[0]})
        chars = []
        outlines = []
        style = {"tone": "常规", "rhetoric": [], "keywords": [], "example_sentence": "暂无"}
        fallback = {
            "world_view_items": world,
            "characters": chars,
            "outlines": outlines,
            "style": style
        }
        from pydantic import BaseModel
        class F(BaseModel):
            world_view_items: list
            characters: list
            outlines: list
            style: dict
        f = F.model_validate(fallback)
        class D(BaseModel):
            world_view_items: list
            characters: list
            outlines: list
            style: dict
        data = D.model_validate(fallback)

    # Create tables if they don't exist
    print("🛠 正在检查/创建数据库表...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"❌ 无法连接数据库: {e}")
        return
    try:
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                print("✅ pgvector 扩展已就绪")
            except Exception as e:
                print(f"⚠️ 无法创建 pgvector 扩展: {e}")

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表已同步")
    except Exception as e:
        print(f"⚠️ 创建/同步数据库表时出错: {e}")
    
    db: Session = SessionLocal()
    try:
        # 1. 保存世界观 (Novel Bible)
        for item in data.world_view_items:
            category = getattr(item, "category", item.get("category"))
            key = getattr(item, "key", item.get("key"))
            content_text = getattr(item, "content", item.get("content"))
            print(f"  - 正在生成设定 Embedding: {key}...")
            emb = get_embedding(f"{key}: {content_text}")
            bible = NovelBible(
                category=category,
                key=key,
                content=content_text,
                embedding=emb,
                tags=[category]
            )
            db.add(bible)
        db.commit()
        print(f"✔ 已导入 {len(data.world_view_items)} 条世界观设定")

        # 2. 保存角色 (Characters)
        for char in data.characters:
            role = getattr(char, "role", char.get("role", ""))
            personality = getattr(char, "personality", char.get("personality", ""))
            background = getattr(char, "background", char.get("background", ""))
            name = getattr(char, "name", char.get("name", "角色"))
            traits = {"role": role, "personality": personality, "background": background}
            db_char = Character(
                name=name,
                role=role,
                personality_traits=traits,
                current_mood="平静",
                evolution_log=["初始设定导入"],
                status={"health": "healthy"}
            )
            db.add(db_char)
        db.commit()
        print(f"✔ 已导入 {len(data.characters)} 个角色")

        # 3. 保存大纲 (PlotOutlines)
        for outline in data.outlines:
            chapter_number = getattr(outline, "chapter_number", outline.get("chapter_number", 0))
            scene_description = getattr(outline, "scene_description", outline.get("scene_description", ""))
            key_conflict = getattr(outline, "key_conflict", outline.get("key_conflict", ""))
            db_outline = PlotOutline(
                novel_id=1,
                chapter_number=chapter_number,
                scene_description=scene_description,
                key_conflict=key_conflict,
                foreshadowing=[],
                recalls=[],
                status="pending"
            )
            db.add(db_outline)
        db.commit()
        print(f"✔ 已导入 {len(data.outlines)} 章大纲")

        # 4. 保存文风 (StyleRef)
        tone = getattr(data.style, "tone", getattr(data.style, "get", lambda k, d=None: d)("tone", "常规"))
        rhetoric = getattr(data.style, "rhetoric", getattr(data.style, "get", lambda k, d=None: d)("rhetoric", []))
        example_sentence = getattr(data.style, "example_sentence", getattr(data.style, "get", lambda k, d=None: d)("example_sentence", ""))
        keywords = getattr(data.style, "keywords", getattr(data.style, "get", lambda k, d=None: d)("keywords", []))
        
        style_content = f"基调: {tone}\n修辞: {', '.join(rhetoric)}\n范例: {example_sentence}"
        print("  - 正在生成文风 Embedding...")
        style_emb = get_embedding(style_content)
        
        style_ref = StyleRef(
            content=style_content,
            embedding=style_emb,
            source_author="Initial Import",
            style_metadata={"tone": tone, "keywords": keywords}
        )
        db.add(style_ref)
        db.commit()
        print("✔ 已导入文风设定")
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
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()
    asyncio.run(import_novel(args.file, use_llm=not args.no_llm))
