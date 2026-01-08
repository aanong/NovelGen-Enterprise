import asyncio
import argparse
import sys
import os
from .schemas.state import NGEState, NovelBible, character_state, PlotPoint, MemoryContext, WorldItemSchema
from .graph import NGEGraph
from .schemas.style import StyleFeatures
from .db.base import SessionLocal
from .db.models import NovelBible as DBBible, Character as DBCharacter, PlotOutline as DBOutline, StyleRef as DBStyle
from .scripts.import_novel import import_novel

async def main():
    parser = argparse.ArgumentParser(description="NovelGen-Enterprise (NGE) CLI")
    parser.add_argument("--init", type=str, help="从文档初始化小说数据 (路径)")
    parser.add_argument("--run", action="store_true", help="运行章节生成任务")
    args = parser.parse_args()

    if args.init:
        await import_novel(args.init)
        return

    # 1. 尝试从数据库加载初始状态
    db = SessionLocal()
    initial_state = None
    
    try:
        # 检查是否有导入的数据
        db_bible = db.query(DBBible).all()
        db_chars = db.query(DBCharacter).all()
        db_outlines = db.query(DBOutline).order_by(DBOutline.chapter_number).all()
        
        if db_bible and db_chars:
            print("✨ 发现数据库中已有导入的小说设定，正在加载...")
            
            # 转换 Bible
            bible_content = "\n".join([f"{b.key}: {b.content}" for b in db_bible])
            
            # 转换人物
            characters = {}
            for c in db_chars:
                inventory = [
                    WorldItemSchema(
                        name=item.name,
                        description=item.description,
                        rarity=item.rarity,
                        powers=item.powers or {},
                        location=item.location
                    ) for item in c.inventory
                ]
                characters[c.name] = character_state(
                    name=c.name,
                    personality_traits=c.personality_traits or {},
                    skills=c.skills or [],
                    assets=c.assets or {},
                    inventory=inventory,
                    relationships={}, # 基础导入暂不处理复杂关系
                    evolution_log=c.evolution_log or ["初始导入"],
                    current_mood=c.current_mood or "平静"
                )
            
            # 转换大纲
            plot_progress = []
            for o in db_outlines:
                plot_progress.append(PlotPoint(
                    id=str(o.id),
                    title=f"第{o.chapter_number}章",
                    description=o.scene_description,
                    key_events=[o.key_conflict]
                ))
            
            # 增加：转换世界物品
            from .db.models import WorldItem
            db_world_items = db.query(WorldItem).all()
            world_items = [
                WorldItemSchema(
                    name=item.name,
                    description=item.description,
                    rarity=item.rarity,
                    powers=item.powers or {},
                    location=item.location
                ) for item in db_world_items
            ]
            
            initial_state = NGEState(
                novel_bible=NovelBible(
                    world_view=bible_content,
                    core_settings={},
                    style_description=StyleFeatures(
                        sentence_length_distribution={"short": 0.4, "medium": 0.4, "long": 0.2},
                        common_rhetoric=["暗喻", "排比"],
                        dialogue_narration_ratio="5:5",
                        emotional_tone="待定",
                        vocabulary_preference=[],
                        rhythm_description="稳健"
                    )
                ),
                characters=characters,
                world_items=world_items, # 新增
                plot_progress=plot_progress,
                memory_context=MemoryContext(
                    recent_summaries=["故事开篇"],
                    global_foreshadowing=[]
                )
            )
    except Exception as e:
        print(f"⚠️ 无法从数据库加载数据 ({e})，将使用模拟数据运行...")
    finally:
        db.close()

    # if not initial_state:
    #     # 模拟初始化状态 (Fallback)
    #     initial_state = NGEState(
    #         novel_bible=NovelBible(
    #             world_view="高武玄幻，人人皆可觉醒魂力，魂力分九品。",
    #             core_settings={"修炼体系": "一品初入门，九品震天下"},
    #             style_description=StyleFeatures(
    #                 sentence_length_distribution={"short": 0.4, "medium": 0.4, "long": 0.2},
    #                 common_rhetoric=["暗喻", "排比", "留白"],
    #                 dialogue_narration_ratio="4:6",
    #                 emotional_tone="热血且带有宿命感",
    #                 vocabulary_preference=["魂力", "颤栗", "虚妄", "怒火"],
    #                 rhythm_description="节奏紧凑，爆发力强"
    #             )
    #         ),
    #         characters={
    #             "林枫": character_state(
    #                 name="林枫",
    #                 personality_traits={"mbti": "INTJ", "goal": "报家仇"},
    #                 relationships={"苏雅": "青梅竹马"},
    #                 evolution_log=["初登场：寒门少年，魂力未觉醒"],
    #                 current_mood="坚毅"
    #             )
    #         },
    #         plot_progress=[
    #             PlotPoint(id="1", title="魂力觉醒仪式", description="林枫在嘲笑声中走向觉醒石。", key_events=["林枫被测出废魂", "金手指开启"]),
    #             PlotPoint(id="2", title="初试锋芒", description="在家族后山遭遇挑衅。", key_events=["反打脸", "获得第一部功法"])
    #         ],
    #         memory_context=MemoryContext(
    #             recent_summaries=["故事开篇"],
    #             global_foreshadowing=["林枫脖子上的吊坠"]
    #         )
    #     )

    # 2. 启动 LangGraph
    if args.run:
        print("🚀 启动 NovelGen-Enterprise (NGE) 生成引擎...")
        graph = NGEGraph()
        
        # 3. 运行（默认运行当前进度对应的章节）
        final_state = await graph.app.ainvoke(initial_state)
        
        print("\n" + "="*50)
        print("✅ 章节生成任务完成！")
        print(f"当前进度：第 {final_state['current_plot_index']} 章节点已处理")
        print("生成样章片段（前200字）：")
        print(final_state['current_draft'][:200])
        print("="*50)
    else:
        print("\n💡 提示: 使用 --init <file> 初始化小说，使用 --run 开始生成。")
        print("示例: python -m src.main --run")

if __name__ == "__main__":
    asyncio.run(main())
