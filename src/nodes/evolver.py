import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..schemas.state import NGEState
from ..agents.constants import OutlineStatus
from ..db.base import SessionLocal
from ..db.models import (
    Character, CharacterRelationship, CharacterBranchStatus,
    NovelBible, Chapter as DBChapter, PlotOutline
)
from ..agents.evolver import CharacterEvolver
from ..agents.summarizer import ChapterSummarizer
from ..monitoring import monitor
from ..config import Config
from .base import BaseNode

logger = logging.getLogger(__name__)

class EvolveNode(BaseNode):
    def __init__(self, evolver: CharacterEvolver, summarizer: ChapterSummarizer):
        self.evolver = evolver
        self.summarizer = summarizer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """
        最终确定本章内容，并根据内容演化角色状态。
        遵循 Rule 3.2 (人物立体与成长)。
        """
        print("--- EVOLVING CHARACTERS & FINALIZING CHAPTER ---")
        db = SessionLocal()
        try:
            # 1. 调用 Evolver Agent 分析人物变化
            evolution_result = await self.evolver.evolve(state)
            
            char_map = {c.name: c for c in db.query(Character).filter(Character.novel_id == state.current_novel_id).all()}

            # 更新角色状态和 DB
            for evo in evolution_result.evolutions:
                char = char_map.get(evo.character_name)
                if not char:
                    continue

                print(f"  - Evolving {char.name}: {evo.evolution_summary}")
                
                # 更新心情
                if evo.mood_change:
                    char.current_mood = evo.mood_change
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].current_mood = evo.mood_change

                # 更新技能
                if evo.skill_update:
                    current_skills = set(char.skills or [])
                    current_skills.update(evo.skill_update)
                    char.skills = list(current_skills)
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].skills = char.skills

                # 更新状态
                if evo.status_change:
                    char.status = evo.status_change
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].status = evo.status_change

                # 更新成长日志
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                log_entry = f"[{timestamp}] Ch.{state.current_plot_index + 1}: {evo.evolution_summary}"
                char.evolution_log = (char.evolution_log or []) + [log_entry]
                if evo.character_name in state.characters:
                    state.characters[evo.character_name].evolution_log.append(log_entry)

                # 处理关系变更
                if hasattr(evo, 'relationship_change') and evo.relationship_change:
                    for target_name, description in evo.relationship_change.items():
                        target_char = char_map.get(target_name)
                        if target_char:
                            rel = db.query(CharacterRelationship).filter(
                                ((CharacterRelationship.char_a_id == char.id) & (CharacterRelationship.char_b_id == target_char.id)) |
                                ((CharacterRelationship.char_a_id == target_char.id) & (CharacterRelationship.char_b_id == char.id))
                            ).first()
                            
                            if not rel:
                                rel = CharacterRelationship(
                                    char_a_id=char.id,
                                    char_b_id=target_char.id,
                                    relation_type="Neutral",
                                    intimacy=0.0,
                                    history=[]
                                )
                                db.add(rel)
                            
                            history = list(rel.history or [])
                            history.append({"chapter": state.current_plot_index + 1, "desc": description})
                            rel.history = history
                            db.commit()

                # 保存分支快照
                existing_snapshot = db.query(CharacterBranchStatus).filter_by(
                    character_id=char.id,
                    branch_id=state.current_branch,
                    chapter_number=state.current_plot_index + 1
                ).first()

                if existing_snapshot:
                    existing_snapshot.current_mood = char.current_mood
                    existing_snapshot.status = char.status
                    existing_snapshot.skills = char.skills
                    existing_snapshot.assets = char.assets
                    existing_snapshot.is_active = char.status.get("is_active", True)
                else:
                    snapshot = CharacterBranchStatus(
                        character_id=char.id,
                        branch_id=state.current_branch,
                        chapter_number=state.current_plot_index + 1,
                        current_mood=char.current_mood,
                        status=char.status,
                        skills=char.skills,
                        assets=char.assets,
                        is_active=char.status.get("is_active", True)
                    )
                    db.add(snapshot)

            # 处理剧情线更新
            if evolution_result.story_updates:
                updates = evolution_result.story_updates
                
                if updates.new_foreshadowing:
                    for f in updates.new_foreshadowing:
                        if f not in state.memory_context.global_foreshadowing:
                            state.memory_context.global_foreshadowing.append(f)
                            print(f"📖 New Foreshadowing: {f}")

                if updates.resolved_threads:
                    original_threads = list(state.memory_context.global_foreshadowing)
                    for resolved in updates.resolved_threads:
                        for existing in original_threads:
                            if existing in resolved or resolved in existing:
                                if existing in state.memory_context.global_foreshadowing:
                                    state.memory_context.global_foreshadowing.remove(existing)
                                    print(f"✅ Resolved Thread: {existing}")

                sys_bible = db.query(NovelBible).filter(
                    NovelBible.novel_id == state.current_novel_id,
                    NovelBible.category == "system_state",
                    NovelBible.key == "global_foreshadowing"
                ).first()

                new_content = json.dumps(state.memory_context.global_foreshadowing, ensure_ascii=False)
                
                if sys_bible:
                    sys_bible.content = new_content
                else:
                    sys_bible = NovelBible(
                        novel_id=state.current_novel_id,
                        category="system_state",
                        key="global_foreshadowing",
                        content=new_content,
                        importance=10
                    )
                    db.add(sys_bible)

            db.commit()
            print("✅ Character evolution & Plot Threads saved to DB.")

            # 将最终章节内容写入数据库
            current_chapter_num = state.current_plot_index + 1
            
            chapter_entry = db.query(DBChapter).filter_by(
                novel_id=state.current_novel_id,
                branch_id=state.current_branch,
                chapter_number=current_chapter_num
            ).first()

            if not chapter_entry:
                chapter_entry = DBChapter(
                    novel_id=state.current_novel_id,
                    branch_id=state.current_branch,
                    chapter_number=current_chapter_num,
                    previous_chapter_id=state.last_chapter_id
                )
                db.add(chapter_entry)

            chapter_entry.title = f"第 {current_chapter_num} 章"
            if state.current_plot_index < len(state.plot_progress):
                chapter_entry.title = state.plot_progress[state.current_plot_index].title
                
            chapter_entry.content = state.current_draft
            
            # 使用新的结构化摘要生成器
            try:
                summary_result = await self.summarizer.generate_summary(
                    state.current_draft, 
                    state=state
                )
                chapter_entry.summary = summary_result.get("summary", state.current_draft[:200])
                
                # 提取新伏笔并添加到全局伏笔列表
                new_foreshadowing = summary_result.get("new_foreshadowing", [])
                for f in new_foreshadowing:
                    if f and f not in state.memory_context.global_foreshadowing:
                        state.memory_context.global_foreshadowing.append(f)
                        print(f"📖 从摘要中提取新伏笔: {f}")
            except Exception as e:
                logger.error(f"摘要生成失败，使用回退方案: {e}", exc_info=True)
                # 回退到简单摘要
                from ..utils import generate_chapter_summary
                chapter_entry.summary = generate_chapter_summary(state.current_draft)
            
            chapter_entry.logic_checked = True
            
            outline = db.query(PlotOutline).filter_by(
                novel_id=state.current_novel_id,
                branch_id=state.current_branch,
                chapter_number=current_chapter_num
            ).first()
            if outline:
                outline.status = OutlineStatus.COMPLETED

            db.commit()
            db.refresh(chapter_entry)
            
            state.memory_context.recent_summaries.append(chapter_entry.summary)
            # 使用配置中的最近章节上下文数量限制
            max_recent_summaries = Config.antigravity.RECENT_CHAPTERS_CONTEXT
            if len(state.memory_context.recent_summaries) > max_recent_summaries:
                state.memory_context.recent_summaries.pop(0)

            print(f"✅ Chapter {current_chapter_num} finalized and saved to DB (ID: {chapter_entry.id}).")
            
            monitor.end_session(state.current_plot_index, success=True, retry_count=state.retry_count)
            
            return {
                "current_plot_index": state.current_plot_index + 1,
                "last_chapter_id": chapter_entry.id,
                "retry_count": 0
            }

        except Exception as e:
            logger.error(f"Error during evolution/finalizing for chapter {state.current_plot_index + 1}: {e}", exc_info=True)
            print(f"❌ Error during evolution/finalizing: {e}")
            db.rollback()
            monitor.end_session(state.current_plot_index, success=False)
            return {}
        finally:
            db.close()
