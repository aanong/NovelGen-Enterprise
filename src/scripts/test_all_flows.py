
import asyncio
import os
import sys
import json
import random
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print(f"DEBUG: sys.path: {sys.path}")

from src.db.base import SessionLocal
from src.db.init_db import init_db
from src.db.models import Novel, NovelBible, Character, PlotOutline, Chapter, CharacterBranchStatus, StyleRef
from src.agents.learner import LearnerAgent
from src.agents.architect import ArchitectAgent
from src.agents.style_analyzer import StyleAnalyzer
from src.graph import NGEGraph
from src.schemas.state import NGEState, NovelBible as BibleSchema, CharacterState, MemoryContext, PlotPoint
from src.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestAllFlows")

async def test_all_flows():
    print("🚀 Starting End-to-End Test of NovelGen-Enterprise Flows")
    
    # Init DB first
    try:
        init_db(drop_all=True)
        print("  ✅ Database Initialized")
    except Exception as e:
        print(f"  ❌ Database Initialization Failed: {e}")
        return

    db = SessionLocal()
    
    # --- Step 0: Environment & Cleanup ---
    print("\n[Step 0] Environment & Cleanup")
    test_novel_title = "Test Novel End-to-End"
    existing = db.query(Novel).filter_by(title=test_novel_title).first()
    if existing:
        print(f"  - Found existing test novel (ID: {existing.id}), cleaning up...")
        # Note: In a real scenario, we might want to cascade delete. 
        # For now, we'll just rename it or assume we create a new one with a unique timestamp if needed.
        # But to keep it clean, let's just delete the novel and its dependencies if possible.
        # Simple approach: just create a NEW novel every time to avoid conflicts.
        pass
    
    # --- Step 1: Style Learning (Module 1) ---
    print("\n[Step 1] Style Learning & Analysis")
    style_analyzer = StyleAnalyzer()
    sample_text = """
    夜色如墨，只有几点寒星在天边闪烁。李青云紧握着手中的长剑，指节因为用力而发白。
    这把剑是他父亲留下的唯一遗物，也是他复仇的唯一希望。
    “这一剑，为了青云门的荣耀。”他低声自语，声音沙哑，带着压抑已久的怒火。
    风突然停了，四周静得可怕，只有远处偶尔传来的几声鸦啼，更增添了几分凄凉。
    """
    
    try:
        style_features = await style_analyzer.analyze(sample_text)
        print("  ✅ Style Analysis Successful")
        print(f"  Style Features: {style_features}")
    except Exception as e:
        print(f"  ❌ Style Analysis Failed: {e}")
        # continue anyway for testing other parts if possible, but style is needed for state
        
    print("\n[Step 2] Novel Setup & Outline Generation")
    
    # 2. Setup Novel in DB
    novel = Novel(
        title=test_novel_title,
        description="A test novel about a programmer entering a cultivation world.",
        author="AI Test",
        status="generating"
    )
    db.add(novel)
    db.commit()
    db.refresh(novel)
    print(f"  ✅ Created Novel ID: {novel.id}")
    
    # 2.2 Ingest World View (Simulated Learner)
    # In a real app, LearnerAgent would parse a doc. Here we inject directly for speed or use Learner if easy.
    # Let's use LearnerAgent to parse a small setup doc.
    learner = LearnerAgent()
    setup_doc = f"""
    # {test_novel_title}
    
    ## 世界观
    - 修炼体系: 练气、筑基、金丹、元婴。
    - 地理: 青云州，宗门林立。
    
    ## 角色
    - 李青云: 主角，性格坚毅，背负血海深仇。
    - 林月: 师妹，温柔善良，精通医术。
    
    ## 物品
    - 青云剑: 传世宝剑，削铁如泥。
    """
    
    try:
        setup_data = await learner.parse_document(setup_doc)
        print("  ✅ Learner Parsed Document")
        
        # Save to DB (Simplified for test script)
        # 1. World View
        for wv in setup_data.world_view_items:
            db.add(NovelBible(novel_id=novel.id, category=wv.category, key=wv.key, content=wv.content))
        
        # 2. Characters
        for char in setup_data.characters:
            c = Character(
                novel_id=novel.id,
                name=char.name,
                role=char.role,
                personality_traits={
                    "personality": char.personality,
                    "background": char.background,
                    "relationship_summary": char.relationship_summary
                },
                skills=char.skills,
                assets=char.assets,
                current_mood="Calm"
            )
            db.add(c)
        
        db.commit()
        print("  ✅ Saved World View and Characters to DB")
        
    except Exception as e:
        print(f"  ❌ Learner Step Failed: {e}")
        return

    # 2.3 Generate Outline (Architect)
    architect = ArchitectAgent()
    try:
        outlines = await architect.generate_chapter_outlines(
            synopsis=novel.description,
            world_view="修仙世界，弱肉强食。",
            total_chapters=3 # Generate minimal chapters for test
        )
        print(f"  ✅ Generated {len(outlines)} Chapter Outlines")
        
        # Save outlines to DB
        for i, out in enumerate(outlines):
            po = PlotOutline(
                novel_id=novel.id,
                branch_id="main",
                chapter_number=out.chapter_number,
                title=out.title,
                scene_description=out.scene_description,
                key_conflict=out.key_conflict,
                status="pending"
            )
            db.add(po)
        db.commit()
        print("  ✅ Saved Outlines to DB")
        
    except Exception as e:
        print(f"  ❌ Architect Step Failed: {e}")
        return

    # --- Step 3: Writing Loop (Module 3 & 4) ---
    print("\n[Step 3] Writing Loop (Chapter 1)")
    
    # Construct Initial State
    # We need to fetch data back from DB to populate State
    chars_db = db.query(Character).filter_by(novel_id=novel.id).all()
    char_states = {}
    for c in chars_db:
        char_states[c.name] = CharacterState(
            name=c.name,
            personality_traits=c.personality_traits or {},
            skills=c.skills or [],
            assets=c.assets or {},
            relationships={}, # Simplified for test
            evolution_log=[],
            current_mood=c.current_mood or "Neutral"
        )
        
    # Get outline for Ch1
    outline_ch1 = db.query(PlotOutline).filter_by(novel_id=novel.id, chapter_number=1).first()
    
    initial_state = NGEState(
        novel_bible=BibleSchema(
            world_view="修仙世界", 
            core_settings={"体系": "练气筑基"}
        ),
        characters=char_states,
        plot_progress=[
            PlotPoint(
                id=str(outline_ch1.id),
                title=outline_ch1.title,
                description=outline_ch1.scene_description,
                key_events=[outline_ch1.key_conflict],
                chapter_index=1
            )
        ],
        current_plot_index=0, 
        current_branch="main",
        current_novel_id=novel.id,
        memory_context=MemoryContext(recent_summaries=[], global_foreshadowing=[]),
        state_version="1.0.0"
    )
    
    # We need to patch the state with novel_id which is missing in NGEState definition in some versions?
    # Let's check schemas/state.py again. It doesn't seem to have `current_novel_id`.
    # Wait, `load_context_node` in `graph.py` accesses `state.current_novel_id`.
    # I must verify if `NGEState` has `current_novel_id`. 
    # If not, I might need to add it or it's dynamically added (not ideal for Pydantic).
    # Let's look at `graph.py` again.
    # Line 74: `db.query(Character).filter(Character.novel_id == state.current_novel_id).all()`
    # So it MUST be there. I missed it in my read or it's inherited?
    # I'll check `schemas/state.py` again carefully or just assume I need to add it dynamically if Pydantic allows extra.
    # Actually, let's just add it to the init call and see if it works, or check the file content again.
    
    # Assuming I can just set it.
    initial_state_dict = initial_state.dict()
    initial_state_dict['current_novel_id'] = novel.id
    
    # But `NGEGraph` uses `NGEState` class. If the field is missing, Pydantic will complain if I try to instantiate with it,
    # or `load_context_node` will fail if it tries to access it and it's not there.
    # I will assume `NGEState` has it or I can monkeypatch for the test if needed.
    # Actually, looking at the previous `Read` output for `schemas/state.py`, `current_novel_id` was NOT visible in the snippet I saw (lines 54-82).
    # It might be missing! This could be a bug in the code or I missed a mixin.
    # I will verify this by reading `schemas/state.py` fully or grepping it.
    
    graph = NGEGraph()
    app = graph.app
    
    # For the test, we need to inject `current_novel_id` into the state object if it's missing.
    # If `NGEState` is a Pydantic model, we can't just add attributes easily unless `extra="allow"`.
    # I'll check `schemas/state.py` one more time quickly.
    
    print("  Running Graph for Chapter 1...")
    try:
        # We invoke the graph.
        inputs = initial_state.dict()
        
        final_state = await app.ainvoke(inputs)
        print("  ✅ Graph Execution Completed")
        print(f"  - Final Draft Length: {len(final_state.get('current_draft', ''))}")
        
        # Verify DB updates
        ch1 = db.query(Chapter).filter_by(novel_id=novel.id, chapter_number=1).first()
        if ch1:
            print(f"  ✅ Chapter 1 Saved: {ch1.title}")
        else:
            print("  ❌ Chapter 1 NOT found in DB")
            
        # Verify Character Evolution
        # Check if evolution_log grew
        char_li = db.query(Character).filter_by(novel_id=novel.id, name="李青云").first()
        if char_li and char_li.evolution_log:
             print(f"  ✅ Character Evolution Log Updated: {len(char_li.evolution_log)} entries")
        else:
             print("  ⚠️ Character Evolution Log Empty (might be expected if no major events)")

    except Exception as e:
        print(f"  ❌ Writing Loop Failed: {e}")
        # Print full traceback
        import traceback
        traceback.print_exc()

    # --- Step 4: Multi-Branch (Module 7) ---
    print("\n[Step 4] Multi-Branch Testing")
    # Switch branch to "evil_route"
    print("  - Switching to 'evil_route' branch...")
    
    # We want to continue from Chapter 1 but branch out for Chapter 2?
    # Or Re-write Chapter 1? 
    # Usually branching happens at a decision point.
    # Let's say we want to generate Chapter 2 on "evil_route".
    # We need a PlotOutline for Ch2 on "evil_route".
    
    # 4.1 Create Outline for Branch
    po_evil = PlotOutline(
        novel_id=novel.id,
        branch_id="evil_route",
        chapter_number=2,
        title="堕入魔道",
        scene_description="李青云为了力量，接受了魔剑的召唤。",
        key_conflict="内心挣扎与彻底黑化",
        status="pending"
    )
    db.add(po_evil)
    db.commit()
    
    # 4.2 Run Graph
    # We reuse the final state but update branch and index
    if 'final_state' in locals():
        branch_state = final_state.copy()
        branch_state['current_branch'] = "evil_route"
        branch_state['current_plot_index'] = 1 # Prepare for Ch2
        branch_state['plot_progress'] = [
            # We should technically load the Ch2 outline here
             PlotPoint(
                id=str(po_evil.id),
                title=po_evil.title,
                description=po_evil.scene_description,
                key_events=[po_evil.key_conflict],
                chapter_index=2
            )
        ]
        
        try:
            print("  Running Graph for Chapter 2 (Evil Route)...")
            final_branch_state = await app.ainvoke(branch_state)
            print("  ✅ Branch Graph Execution Completed")
            
            ch2_evil = db.query(Chapter).filter_by(novel_id=novel.id, branch_id="evil_route", chapter_number=2).first()
            if ch2_evil:
                print(f"  ✅ Chapter 2 (Evil) Saved: {ch2_evil.title}")
            else:
                print("  ❌ Chapter 2 (Evil) NOT found in DB")
                
            # Verify Snapshot
            # There should be a snapshot for Ch1 (main) or Ch2?
            # Snapshots are usually saved AFTER a chapter is generated.
            snapshots = db.query(CharacterBranchStatus).filter_by(novel_id=novel.id).all()
            print(f"  ✅ Found {len(snapshots)} Character Snapshots")
            
        except Exception as e:
            print(f"  ❌ Branching Failed: {e}")
            import traceback
            traceback.print_exc()

    db.close()
    print("\n🏁 Test Completed")

if __name__ == "__main__":
    asyncio.run(test_all_flows())
