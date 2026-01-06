import asyncio
from .schemas.state import NGEState, NovelBible, character_state, PlotPoint, MemoryContext
from .graph import NGEGraph
from .schemas.style import StyleFeatures

async def main():
    # 1. 模拟初始化状态 (实际应用中会从数据库读取)
    initial_state = NGEState(
        novel_bible=NovelBible(
            world_view="高武玄幻，人人皆可觉醒魂力，魂力分九品。",
            core_settings={"修炼体系": "一品初入门，九品震天下", "核心冲突": "寒门与世家的资源之争"},
            style_description=StyleFeatures(
                sentence_length_distribution={"short": 0.4, "medium": 0.4, "long": 0.2},
                common_rhetoric=["暗喻", "排比", "留白"],
                dialogue_narration_ratio="4:6",
                emotional_tone="热血且带有宿命感",
                vocabulary_preference=["魂力", "颤栗", "虚妄", "怒火"],
                rhythm_description="节奏紧凑，爆发力强"
            )
        ),
        characters={
            "林枫": character_state(
                name="林枫",
                personality_traits={"mbti": "INTJ", "goal": "报家仇"},
                relationships={"苏雅": "青梅竹马"},
                evolution_log=["初登场：寒门少年，魂力未觉醒"],
                current_mood="坚毅"
            )
        },
        plot_progress=[
            PlotPoint(id="1", title="魂力觉醒仪式", description="林枫在嘲笑声中走向觉醒石。", key_events=["林枫被测出废魂", "金手指开启"]),
            PlotPoint(id="2", title="初试锋芒", description="在家族后山遭遇挑衅。", key_events=["反打脸", "获得第一部功法"])
        ],
        memory_context=MemoryContext(
            recent_summaries=["故事开篇"],
            global_foreshadowing=["林枫脖子上的吊坠"]
        )
    )

    # 2. 启动 LangGraph
    print("🚀 启动 NovelGen-Enterprise (NGE) 生成引擎...")
    graph = NGEGraph()
    
    # 3. 运行前两个剧情点
    final_state = await graph.app.ainvoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ 章节生成任务完成！")
    print(f"当前进度：{final_state['current_plot_index']}")
    print("生成样章片段（前100字）：")
    print(final_state['current_draft'][:200])
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
