import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add project root to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.learner import LearnerAgent
from src.db.base import SessionLocal
from src.db.models import Novel, Character, NovelBible, PlotOutline, StyleRef, WorldItem
from src.utils import get_embedding
from sqlalchemy.orm import Session
import json

async def import_novel_data(file_path: str, novel_id: int, use_llm: bool = True):
    """
    Imports novel data from a file into the database for a specific novel.
    """
    print(f"📂 Reading document: {file_path}")
    if not os.path.exists(file_path):
        print("❌ File not found")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = None
    if use_llm:
        print("🧠 Calling LearnerAgent to parse the document... (This might take a minute)")
        agent = LearnerAgent()
        try:
            data = await agent.parse_document(content)
            print("✅ Parsing successful! Writing to the database...")
        except Exception as e:
            print(f"❌ Error during LLM parsing: {e}. Will proceed with fallback.")
    
    if data is None:
        print("🔧 Using local fallback parsing mode. Data will be minimal.")
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        world = [{"category": "Setting", "key": "Initial Scene", "content": lines[0] if lines else "A new world begins."}]
        fallback = {
            "world_view_items": world, 
            "characters": [], 
            "outlines": [{"chapter_number": 1, "title": "The Beginning", "summary": "The story starts here."}],
            "items": [],
            "style": {"tone": "Neutral", "rhetoric": [], "keywords": [], "example_sentence": "This is a sample sentence."}
        }
        from pydantic import BaseModel
        class FallbackModel(BaseModel):
            world_view_items: list; characters: list; outlines: list; items: list; style: dict
        data = FallbackModel.model_validate(fallback)

    db: Session = SessionLocal()
    try:
        # 1. Save Worldview (Novel Bible)
        for item in data.world_view_items:
            item_dict = item if isinstance(item, dict) else item.dict()
            key = item_dict.get("key", "Unknown")
            content_text = item_dict.get("content", "")
            emb = get_embedding(f"{key}: {content_text}")
            
            existing = db.query(NovelBible).filter_by(novel_id=novel_id, key=key).first()
            if existing:
                existing.content = content_text
                existing.embedding = emb
            else:
                db.add(NovelBible(novel_id=novel_id, key=key, content=content_text, embedding=emb, category=item_dict.get("category", "Setting")))
        db.commit()
        print(f"✔ Imported {len(data.world_view_items)} worldview settings.")

        # 2. Save Characters
        for char in data.characters:
            char_dict = char if isinstance(char, dict) else char.dict()
            name = char_dict.get("name", "Unnamed Character")
            if not name: continue
            existing = db.query(Character).filter_by(novel_id=novel_id, name=name).first()
            if not existing:
                db.add(Character(novel_id=novel_id, name=name, role=char_dict.get("role"), personality_traits=char_dict.get("personality")))
        db.commit()
        print(f"✔ Imported {len(data.characters)} characters.")

        # 3. Save Items
        char_map = {c.name: c.id for c in db.query(Character).filter_by(novel_id=novel_id).all()}
        for item in data.items:
            item_dict = item if isinstance(item, dict) else item.dict()
            name = item_dict.get("name", "Unnamed Item")
            if not name: continue
            owner_id = char_map.get(item_dict.get("owner_name"))
            existing = db.query(WorldItem).filter_by(novel_id=novel_id, name=name).first()
            if not existing:
                db.add(WorldItem(novel_id=novel_id, name=name, description=item_dict.get("description"), owner_id=owner_id))
        db.commit()
        print(f"✔ Imported {len(data.items)} key items.")

        # 4. Save Plot Outlines
        for outline in data.outlines:
            outline_dict = outline if isinstance(outline, dict) else outline.dict()
            chapter_num = outline_dict.get("chapter_number")
            if not chapter_num: continue
            existing = db.query(PlotOutline).filter_by(novel_id=novel_id, chapter_number=chapter_num, branch_id="main").first()
            if not existing:
                db.add(PlotOutline(
                    novel_id=novel_id,
                    chapter_number=chapter_num,
                    title=outline_dict.get("title", f"Chapter {chapter_num}"),
                    scene_description=outline_dict.get("summary", "No summary provided."),
                    branch_id="main"
                ))
        db.commit()
        print(f"✔ Imported {len(data.outlines)} plot outlines.")

        # 5. Save Style Reference
        style_info = data.style if isinstance(data.style, dict) else data.style.dict()
        example_sentence = style_info.get("example_sentence")
        if example_sentence:
            emb = get_embedding(example_sentence)
            # For simplicity, we store one representative style sentence.
            # A more complex system could store multiple examples.
            existing = db.query(StyleRef).filter_by(novel_id=novel_id, content=example_sentence).first()
            if not existing:
                db.add(StyleRef(novel_id=novel_id, content=example_sentence, embedding=emb))
                db.commit()
                print("✔ Imported 1 style reference.")

    finally:
        db.close()

async def main():
    parser = argparse.ArgumentParser(description="NovelGen-Enterprise Data Importer")
    parser.add_argument("file_path", help="Path to the novel setup document.")
    parser.add_argument("--novel-id", type=int, help="ID of an existing novel to append data to.")
    parser.add_argument("--title", help="Title for a new novel to be created.")
    parser.add_argument("--author", help="Author for a new novel.")
    parser.add_argument("--description", help="Description for a new novel.")
    parser.add_argument("--no-llm", action="store_true", help="Use fallback parser instead of LLM.")
    
    args = parser.parse_args()

    db: Session = SessionLocal()
    novel_id_to_use = args.novel_id

    try:
        if not novel_id_to_use:
            if not args.title:
                print("❌ Error: You must provide either --novel-id or --title.")
                return
            
            new_novel = Novel(
                title=args.title,
                author=args.author,
                description=args.description
            )
            db.add(new_novel)
            db.commit()
            novel_id_to_use = new_novel.id
            print(f"✨ Created new novel '{args.title}' with ID: {novel_id_to_use}")
        else:
            # Verify the novel exists
            existing_novel = db.query(Novel).filter_by(id=novel_id_to_use).first()
            if not existing_novel:
                print(f"❌ Error: Novel with ID {novel_id_to_use} not found.")
                return
            print(f"📚 Appending data to existing novel '{existing_novel.title}' (ID: {novel_id_to_use})")

    finally:
        db.close()
    
    await import_novel_data(args.file_path, novel_id_to_use, use_llm=not args.no_llm)

if __name__ == "__main__":
    asyncio.run(main())
