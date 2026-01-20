from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from src.schemas.state import NGEState, NovelBible, CharacterState, PlotPoint, MemoryContext, WorldItemSchema
from src.schemas.style import StyleFeatures
from src.db.base import SessionLocal
from src.db.models import Novel, NovelBible as DBBible, Character as DBCharacter, PlotOutline as DBOutline, StyleRef as DBStyle, WorldItem as DBWorldItem, Chapter as DBChapter

from typing import Optional
import json


async def load_initial_state(novel_id: int, branch_id: str = "main") -> Optional[NGEState]:
    """从数据库加载指定小说的初始状态（优化版 - 使用 joinedload 消除 N+1 查询）"""
    db = SessionLocal()
    try:
        # 使用 joinedload 一次性加载所有关系，大幅减少数据库查询次数
        novel = db.query(Novel).options(
            joinedload(Novel.bible_entries),
            joinedload(Novel.characters).joinedload(DBCharacter.inventory),
            joinedload(Novel.outlines).filter(DBOutline.branch_id == branch_id),
            joinedload(Novel.world_items)
        ).filter(Novel.id == novel_id).first()

        if not novel:
            print(f"❌ 错误: 在数据库中未找到 ID 为 {novel_id} 的小说。")
            return None

        print(f"✨ 正在为小说 '{novel.title}' (ID: {novel_id}) 加载数据...")

        # 现在直接使用预加载的数据，无需再次查询
        db_bible = novel.bible_entries
        db_chars = novel.characters
        db_outlines = sorted(novel.outlines, key=lambda o: o.chapter_number)
        db_world_items = novel.world_items

        bible_content = "\n".join([f"{b.key}: {b.content}" for b in db_bible])

        # 构建角色字典
        characters = {}
        for c in db_chars:
            # 处理 inventory（已通过 joinedload 预加载）
            inventory_items = []
            if c.inventory:
                inventory_items = [
                    WorldItemSchema(
                        name=item.name,
                        description=item.description or "",
                        rarity=item.rarity or "Common",
                        powers=item.powers or {},
                        location=item.location
                    ) for item in c.inventory
                ]

            # 安全解析 personality_traits
            if isinstance(c.personality_traits, dict):
                personality = c.personality_traits
            elif c.personality_traits:
                personality = {"description": str(c.personality_traits)}
            else:
                personality = {}

            characters[c.name] = CharacterState(
                name=c.name,
                personality_traits=personality,
                skills=c.skills or [],
                assets=c.assets or {},
                inventory=inventory_items,
                relationships={},
                evolution_log=c.evolution_log or ["初始导入"],
                current_mood=c.current_mood or "平静"
            )

        # 构建剧情进度
        plot_progress = [
            PlotPoint(
                id=str(o.id),
                title=o.title or f"第{o.chapter_number}章",
                description=o.scene_description or "无描述",
                key_events=[o.key_conflict] if o.key_conflict else [],
                is_completed=(o.status == "completed")
            ) for o in db_outlines
        ]

        # 查找最新的已生成章节号
        last_chapter = db.query(func.max(DBChapter.chapter_number)).filter(
            DBChapter.novel_id == novel_id,
            DBChapter.branch_id == branch_id
        ).scalar()

        current_plot_index = (last_chapter or 0)
        print(f"🧠 状态加载器：找到上一章为 {last_chapter}，将从索引 {current_plot_index} 开始生成。")

        # 构建物品列表
        world_items = [
            WorldItemSchema(
                name=item.name,
                description=item.description or "",
                rarity=item.rarity or "Common",
                powers=item.powers or {},
                location=item.location
            ) for item in db_world_items
        ]

        # 加载风格参考
        style_refs = db.query(DBStyle).filter(DBStyle.novel_id == novel_id).limit(5).all()
        example_sentences = [s.content for s in style_refs]

        # 加载全局伏笔
        sys_bible = db.query(DBBible).filter(
            DBBible.novel_id == novel_id,
            DBBible.category == "system_state",
            DBBible.key == "global_foreshadowing"
        ).first()

        saved_foreshadowing = []
        if sys_bible:
            try:
                saved_foreshadowing = json.loads(sys_bible.content)
            except:
                saved_foreshadowing = []

        combined_summary = ["故事开篇"]

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
            current_plot_index=current_plot_index,
            memory_context=MemoryContext(
                recent_summaries=combined_summary,
                global_foreshadowing=saved_foreshadowing
            ),
            current_branch=branch_id,
            current_novel_id=novel_id
        )
        return initial_state

    except Exception as e:
        print(f"⚠️ 从数据库加载数据时发生严重错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()
