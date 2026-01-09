import asyncio
import argparse
from .schemas.state import NGEState, NovelBible, character_state, PlotPoint, MemoryContext, WorldItemSchema
from .graph import NGEGraph
from .schemas.style import StyleFeatures
from .db.base import SessionLocal
from .db.models import Novel, NovelBible as DBBible, Character as DBCharacter, PlotOutline as DBOutline, StyleRef as DBStyle, WorldItem as DBWorldItem
from .scripts.import_novel import import_novel_data

async def load_initial_state(novel_id: int, branch_id: str = "main") -> NGEState | None:
    """从数据库加载指定小说的初始状态"""
    db = SessionLocal()
    try:
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            print(f"❌ 错误: 在数据库中未找到 ID 为 {novel_id} 的小说。")
            return None

        print(f"✨ 正在为小说 '{novel.title}' (ID: {novel_id}) 加载数据...")

        db_bible = db.query(DBBible).filter(DBBible.novel_id == novel_id).all()
        db_chars = db.query(DBCharacter).filter(DBCharacter.novel_id == novel_id).all()
        db_outlines = db.query(DBOutline).filter(
            DBOutline.novel_id == novel_id,
            DBOutline.branch_id == branch_id
        ).order_by(DBOutline.chapter_number).all()
        db_world_items = db.query(DBWorldItem).filter(DBWorldItem.novel_id == novel_id).all()

        if not all([db_bible, db_chars, db_outlines]):
            print(f"⚠️ 警告: 小说 '{novel.title}' 的核心数据不完整 (世界观、人物或大纲缺失)。")
            # 即使数据不完整，也尝试构建基础状态
            
        bible_content = "\n".join([f"{b.key}: {b.content}" for b in db_bible])
        
        characters = {
            c.name: character_state(
                name=c.name,
                personality_traits=c.personality_traits or {},
                skills=c.skills or [],
                assets=c.assets or {},
                inventory=[WorldItemSchema.from_orm(item) for item in c.inventory],
                relationships={},
                evolution_log=c.evolution_log or ["初始导入"],
                current_mood=c.current_mood or "平静"
            ) for c in db_chars
        }
        
        plot_progress = [
            PlotPoint(
                id=str(o.id),
                title=o.title or f"第{o.chapter_number}章",
                description=o.summary or "无描述",
                key_events=[o.key_conflict] if o.key_conflict else []
            ) for o in db_outlines
        ]
        
        world_items = [WorldItemSchema.from_orm(item) for item in db_world_items]
        
        # 简化风格加载，实际应用中可以更复杂
        style_refs = db.query(DBStyle).filter(DBStyle.novel_id == novel_id).limit(5).all()
        example_sentences = [s.source_text for s in style_refs]

        initial_state = NGEState(
            novel_bible=NovelBible(
                world_view=bible_content,
                core_settings={},
                style_description=StyleFeatures(
                    sentence_length_distribution={"short": 0.4, "medium": 0.4, "long": 0.2},
                    common_rhetoric=["暗喻"],
                    dialogue_narration_ratio="5:5",
                    emotional_tone="待定",
                    vocabulary_preference=[],
                    rhythm_description="稳健",
                    example_sentences=example_sentences
                )
            ),
            characters=characters,
            world_items=world_items,
            plot_progress=plot_progress,
            memory_context=MemoryContext(
                recent_summaries=["故事开篇"],
                global_foreshadowing=[]
            ),
            current_branch=branch_id,
            current_novel_id=novel_id
        )
        return initial_state

    except Exception as e:
        print(f"⚠️ 从数据库加载数据时发生严重错误: {e}")
        return None
    finally:
        db.close()

async def run_generation_task(novel_id: int, branch_id: str = "main"):
    """为指定小说运行生成任务"""
    initial_state = await load_initial_state(novel_id, branch_id)
    if not initial_state:
        print(f"❌ 无法为小说 ID {novel_id} 加载初始状态，任务中止。")
        return

    print(f"🚀 启动 NovelGen-Enterprise (NGE) 引擎，目标: 小说 ID {novel_id}...")
    graph = NGEGraph()
    
    final_state = await graph.app.ainvoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ 章节生成任务完成！")
    print(f"小说 ID: {final_state.get('current_novel_id')}")
    print(f"当前进度：第 {final_state.get('current_plot_index', 0)} 章节点已处理")
    print("生成样章片段（前200字）：")
    draft = final_state.get('current_draft', "")
    print(draft[:200] if draft else "无内容生成。")
    print("="*50)

async def main():
    parser = argparse.ArgumentParser(description="NovelGen-Enterprise (NGE) CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Init Command ---
    parser_init = subparsers.add_parser("init", help="从文档初始化或更新小说数据")
    parser_init.add_argument("file_path", help="小说设定文档的路径")
    parser_init.add_argument("--novel-id", type=int, help="要更新的现有小说的 ID")
    parser_init.add_argument("--title", help="创建新小说的标题 (如果未提供 novel-id)")
    parser_init.add_argument("--author", help="新小说的作者")
    parser_init.add_argument("--description", help="新小说的描述")
    parser_init.add_argument("--no-llm", action="store_true", help="使用本地回退解析器而非 LLM")

    # --- Run Command ---
    parser_run = subparsers.add_parser("run", help="运行章节生成任务")
    parser_run.add_argument("--novel-id", type=int, required=True, help="要生成章节的小说的 ID")
    parser_run.add_argument("--branch", default="main", help="要生成的分支 (默认: main)")

    args = parser.parse_args()

    if args.command == "init":
        db = SessionLocal()
        novel_id_to_use = args.novel_id
        try:
            if not novel_id_to_use:
                if not args.title:
                    print("❌ 错误: 创建新小说必须提供 --title。")
                    return
                new_novel = Novel(title=args.title, author=args.author, description=args.description)
                db.add(new_novel)
                db.commit()
                novel_id_to_use = new_novel.id
                print(f"✨ 成功创建新小说 '{args.title}' (ID: {novel_id_to_use})")
            else:
                # 验证小说是否存在
                if not db.query(Novel).filter(Novel.id == novel_id_to_use).first():
                    print(f"❌ 错误: 未找到 ID 为 {novel_id_to_use} 的小说。")
                    return
        finally:
            db.close()
        
        await import_novel_data(args.file_path, novel_id_to_use, use_llm=not args.no_llm)

    elif args.command == "run":
        await run_generation_task(novel_id=args.novel_id, branch_id=args.branch)

if __name__ == "__main__":
    asyncio.run(main())
