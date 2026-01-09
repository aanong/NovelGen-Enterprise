import asyncio
import argparse
import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.db.base import SessionLocal
from src.db.models import NovelBible, PlotOutline
from src.agents.architect import ArchitectAgent

async def generate_outline(synopsis_path: str, total_chapters: int, refine_mode: bool = False, start_chapter: int = 1, instruction: str = ""):
    if refine_mode:
        print(f"🔧 开始调整大纲 (从第 {start_chapter} 章开始)...")
    else:
        print(f"🚀 开始生成全书大纲 (预计 {total_chapters} 章)...")
    
    # 1. 读取梗概 (仅在非 refine 模式下必须)
    synopsis = ""
    if not refine_mode:
        try:
            with open(synopsis_path, "r", encoding="utf-8") as f:
                synopsis = f.read()
        except FileNotFoundError:
            print(f"❌ 找不到梗概文件: {synopsis_path}")
            return

    # 2. 读取世界观和现有大纲
    db = SessionLocal()
    try:
        bible_entries = db.query(NovelBible).all()
        world_view = "\n".join([f"[{b.key}]: {b.content}" for b in bible_entries])
        if not world_view:
            print("⚠️ 警告: 数据库中没有世界观设定 (NovelBible)。生成的大纲可能缺乏细节。")
            world_view = "暂无具体设定，请自由发挥。"
            
        # 读取现有大纲 (用于 refine)
        current_outlines = []
        if refine_mode:
            outlines = db.query(PlotOutline).filter_by(novel_id=1, branch_id="main").order_by(PlotOutline.chapter_number).all()
            current_outlines = [
                {
                    "chapter_number": o.chapter_number,
                    "scene_description": o.scene_description
                } for o in outlines
            ]
            if not current_outlines:
                print("❌ 数据库中没有现有大纲，无法进行调整。请先生成大纲。")
                return
    finally:
        db.close()

    # 3. 调用 Architect 生成或调整
    architect = ArchitectAgent()
    
    if refine_mode:
        if not instruction:
            instruction = input("请输入调整指导意见 (例如 '让主角遭遇更强的敌人'): ")
        chapters = await architect.refine_outline(current_outlines, instruction, start_chapter, world_view)
    else:
        chapters = await architect.generate_chapter_outlines(synopsis, world_view, total_chapters)
    
    if not chapters:
        print("❌ 大纲生成/调整失败。")
        return

    # 4. 存入数据库
    db = SessionLocal()
    try:
        print(f"💾 正在保存 {len(chapters)} 章大纲到数据库...")
        
        for ch in chapters:
            # 检查是否已存在
            existing = db.query(PlotOutline).filter_by(
                novel_id=1, 
                chapter_number=ch.chapter_number,
                branch_id="main"
            ).first()
            
            if existing:
                print(f"  - 更新第 {ch.chapter_number} 章: {ch.title}")
                existing.scene_description = ch.scene_description
                existing.key_conflict = ch.key_conflict
                existing.foreshadowing = ch.foreshadowing
                existing.status = "pending" # 重置状态，以便重新写作
            else:
                print(f"  - 新增第 {ch.chapter_number} 章: {ch.title}")
                new_outline = PlotOutline(
                    novel_id=1,
                    branch_id="main",
                    chapter_number=ch.chapter_number,
                    scene_description=ch.scene_description,
                    key_conflict=ch.key_conflict,
                    foreshadowing=ch.foreshadowing,
                    status="pending"
                )
                db.add(new_outline)
        
        db.commit()
        print("✅ 大纲更新完毕！")
        
    except Exception as e:
        print(f"❌ 保存数据库失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate or refine full novel outline.")
    parser.add_argument("synopsis_file", nargs='?', help="Path to the synopsis text file (required for generation).")
    parser.add_argument("--chapters", type=int, default=10, help="Estimated total chapters.")
    parser.add_argument("--refine", action="store_true", help="Refine existing outline instead of generating new one.")
    parser.add_argument("--start-chapter", type=int, default=1, help="Chapter number to start refining from.")
    parser.add_argument("--instruction", type=str, default="", help="Instruction for refinement.")
    
    args = parser.parse_args()
    
    if not args.refine and not args.synopsis_file:
        parser.error("synopsis_file is required unless --refine is used.")
    
    asyncio.run(generate_outline(args.synopsis_file, args.chapters, args.refine, args.start_chapter, args.instruction))
