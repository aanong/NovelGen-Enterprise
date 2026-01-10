from src.schemas.state import NGEState, NovelBible, CharacterState, PlotPoint, MemoryContext, WorldItemSchema
from src.schemas.style import StyleFeatures
from src.db.base import SessionLocal
from src.db.models import Novel, NovelBible as DBBible, Character as DBCharacter, PlotOutline as DBOutline, StyleRef as DBStyle, WorldItem as DBWorldItem

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

        # 即使数据不完整，也尝试构建基础状态
            
        bible_content = "\n".join([f"{b.key}: {b.content}" for b in db_bible])
        
        characters = {
            c.name: CharacterState(
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
                description=o.scene_description or "无描述",
                key_events=[o.key_conflict] if o.key_conflict else []
            ) for o in db_outlines
        ]
        
        world_items = [WorldItemSchema.from_orm(item) for item in db_world_items]
        
        # 简化风格加载，实际应用中可以更复杂
        style_refs = db.query(DBStyle).filter(DBStyle.novel_id == novel_id).limit(5).all()
        example_sentences = [s.content for s in style_refs] # 注意：models.py 中是 content 不是 source_text

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
