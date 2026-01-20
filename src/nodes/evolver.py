"""
EvolveNode 模块
负责章节完成后的人物演化、状态更新和数据持久化
支持：性格演化、能力成长、价值观变迁、关键事件记录、弧光推进
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from ..schemas.state import NGEState, AbilityLevel
from ..agents.constants import OutlineStatus
from ..agents.evolver import (
    CharacterEvolver, EvolutionResult, CharacterEvolution,
    apply_personality_change, apply_value_change, apply_ability_change
)
from ..agents.summarizer import SummarizerAgent
from ..db.base import SessionLocal
from ..db.models import (
    Character, CharacterRelationship, CharacterBranchStatus,
    NovelBible, Chapter as DBChapter, PlotOutline,
    CharacterArc, CharacterKeyEvent
)
from ..monitoring import monitor
from ..config import Config
from .base import BaseNode
from ..core.registry import register_node

logger = logging.getLogger(__name__)

@register_node("evolve")
class EvolveNode(BaseNode):
    """
    增强版演化节点
    
    功能：
    1. 分析章节内容，提取人物变化
    2. 应用性格、价值观、能力的变化
    3. 检测并记录关键事件
    4. 推进人物弧光进度
    5. 保存章节和状态快照
    
    遵循 Antigravity Rules:
    - Rule 2.1: 人物灵魂锚定（变化必须有合理原因）
    - Rule 3.2: 人物立体与成长
    """
    
    def __init__(self, evolver: CharacterEvolver, summarizer: SummarizerAgent):
        self.evolver = evolver
        self.summarizer = summarizer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """
        执行演化节点
        
        Args:
            state: 当前全局状态
            
        Returns:
            状态更新字典
        """
        print("--- EVOLVING CHARACTERS & FINALIZING CHAPTER ---")
        db = SessionLocal()
        
        try:
            # 1. 调用 Evolver Agent 分析人物变化
            evolution_result = await self.evolver.evolve(state)
            
            # 获取数据库中的角色映射
            char_map = {
                c.name: c 
                for c in db.query(Character).filter(
                    Character.novel_id == state.current_novel_id
                ).all()
            }
            
            # 2. 处理每个角色的演化
            for evo in evolution_result.evolutions:
                await self._apply_character_evolution(
                    db, state, evo, char_map
                )
            
            # 3. 处理检测到的关键事件
            await self._process_key_events(
                db, state, evolution_result.detected_key_events, char_map
            )
            
            # 4. 处理剧情线更新（伏笔）
            if evolution_result.story_updates:
                self._process_story_updates(db, state, evolution_result.story_updates)
            
            db.commit()
            print("✅ Character evolution & Plot Threads saved to DB.")
            
            # 5. 保存章节内容
            chapter_entry = await self._save_chapter(db, state)
            
            # 6. 更新监控
            monitor.end_session(
                state.current_plot_index, 
                success=True, 
                retry_count=state.retry_count
            )
            
            return {
                "current_plot_index": state.current_plot_index + 1,
                "last_chapter_id": chapter_entry.id if chapter_entry else None,
                "retry_count": 0
            }
            
        except Exception as e:
            logger.error(
                f"Error during evolution/finalizing for chapter {state.current_plot_index + 1}: {e}",
                exc_info=True
            )
            print(f"❌ Error during evolution/finalizing: {e}")
            db.rollback()
            monitor.end_session(state.current_plot_index, success=False)
            return {}
        finally:
            db.close()

    async def _apply_character_evolution(
        self,
        db,
        state: NGEState,
        evo: CharacterEvolution,
        char_map: Dict[str, Character]
    ):
        """
        应用单个角色的演化
        
        Args:
            db: 数据库会话
            state: 当前状态
            evo: 角色演化数据
            char_map: 角色名称到数据库对象的映射
        """
        char = char_map.get(evo.character_name)
        if not char:
            logger.warning(f"角色 '{evo.character_name}' 不存在于数据库中")
            return
        
        print(f"  - Evolving {char.name}: {evo.evolution_summary}")
        state_char = state.characters.get(evo.character_name)
        
        # 1. 更新心情
        if evo.mood_change:
            char.current_mood = evo.mood_change
            if state_char:
                state_char.current_mood = evo.mood_change
        
        # 2. 应用性格维度变化
        if evo.personality_changes and state_char:
            current_dynamics = dict(state_char.personality_dynamics or {})
            for change in evo.personality_changes:
                current_dynamics = apply_personality_change(current_dynamics, change)
                print(f"    📊 性格变化: {change.dimension} {change.old_value:.2f} → {change.new_value:.2f}")
            
            state_char.personality_dynamics = current_dynamics
            char.personality_dynamics = current_dynamics
        
        # 3. 应用价值观变化
        if evo.value_changes and state_char:
            current_values = dict(state_char.core_values or {})
            for change in evo.value_changes:
                current_values = apply_value_change(current_values, change)
                print(f"    💎 价值观变化: {change.value_name} {change.old_value:.2f} → {change.new_value:.2f}")
            
            state_char.core_values = current_values
            char.core_values = current_values
        
        # 4. 应用能力变化
        if evo.ability_changes and state_char:
            # 将 state 中的 AbilityLevel 对象转换为字典以便处理
            current_abilities = {}
            for name, ability in (state_char.ability_levels or {}).items():
                if isinstance(ability, AbilityLevel):
                    current_abilities[name] = ability
                elif isinstance(ability, dict):
                    current_abilities[name] = AbilityLevel(**ability)
            
            for change in evo.ability_changes:
                current_abilities = apply_ability_change(current_abilities, change)
                print(f"    ⚔️ 能力变化: {change.ability_name} ({change.change_type})")
            
            state_char.ability_levels = current_abilities
            # 将 AbilityLevel 对象转换为字典存储到数据库
            char.ability_levels = {
                name: {"level": a.level, "proficiency": a.proficiency, "description": a.description}
                for name, a in current_abilities.items()
            }
        
        # 5. 更新技能列表（保持兼容）
        if evo.skill_update:
            current_skills = set(char.skills or [])
            current_skills.update(evo.skill_update)
            char.skills = list(current_skills)
            if state_char:
                state_char.skills = char.skills
        
        # 6. 更新状态
        if evo.status_change:
            char.status = evo.status_change
            if state_char:
                state_char.status = evo.status_change
        
        # 7. 更新成长日志
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        log_entry = f"[{timestamp}] Ch.{state.current_plot_index + 1}: {evo.evolution_summary}"
        char.evolution_log = (char.evolution_log or []) + [log_entry]
        if state_char:
            state_char.evolution_log.append(log_entry)
        
        # 8. 处理关系变更
        if evo.relationship_change:
            await self._update_relationships(
                db, char, char_map, evo.relationship_change, state.current_plot_index + 1
            )
        
        # 9. 推进人物弧光
        if evo.arc_progress_delta > 0 and state_char and state_char.character_arc:
            await self._advance_character_arc(
                db, char, state_char, evo, state.current_plot_index + 1
            )
        
        # 10. 保存分支快照
        await self._save_branch_snapshot(db, char, state)

    async def _update_relationships(
        self,
        db,
        char: Character,
        char_map: Dict[str, Character],
        relationship_changes: Dict[str, str],
        chapter_number: int
    ):
        """更新人物关系"""
        for target_name, description in relationship_changes.items():
            target_char = char_map.get(target_name)
            if not target_char:
                continue
            
            # 查找或创建关系
            rel = db.query(CharacterRelationship).filter(
                ((CharacterRelationship.char_a_id == char.id) & 
                 (CharacterRelationship.char_b_id == target_char.id)) |
                ((CharacterRelationship.char_a_id == target_char.id) & 
                 (CharacterRelationship.char_b_id == char.id))
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
            
            # 更新历史记录
            history = list(rel.history or [])
            history.append({"chapter": chapter_number, "desc": description})
            rel.history = history
            
            print(f"    🤝 关系变化: {char.name} ↔ {target_name}: {description}")

    async def _advance_character_arc(
        self,
        db,
        char: Character,
        state_char,
        evo: CharacterEvolution,
        chapter_number: int
    ):
        """推进人物弧光进度"""
        arc = state_char.character_arc
        
        # 更新进度
        new_progress = min(1.0, arc.progress + evo.arc_progress_delta)
        arc.progress = new_progress
        
        print(f"    🌟 弧光进度: {arc.progress:.0%} (+{evo.arc_progress_delta:.0%})")
        
        # 检查是否完成里程碑
        if evo.arc_milestone_completed and arc.milestones:
            if arc.current_milestone_index < len(arc.milestones):
                milestone = arc.milestones[arc.current_milestone_index]
                milestone.is_completed = True
                arc.current_milestone_index += 1
                print(f"    🎯 完成里程碑: {milestone.description}")
        
        # 检查弧光是否完成
        if new_progress >= 1.0:
            arc.status = "completed"
            print(f"    ✨ 人物弧光完成!")
        
        # 更新数据库中的弧光记录
        db_arc = db.query(CharacterArc).filter(
            CharacterArc.character_id == char.id,
            CharacterArc.status == "active"
        ).first()
        
        if db_arc:
            db_arc.progress = new_progress
            db_arc.current_milestone_index = arc.current_milestone_index
            if arc.status == "completed":
                db_arc.status = "completed"
            db_arc.milestones = [m.model_dump() for m in arc.milestones]
            db_arc.updated_at = datetime.utcnow()

    async def _save_branch_snapshot(self, db, char: Character, state: NGEState):
        """保存人物分支状态快照"""
        existing_snapshot = db.query(CharacterBranchStatus).filter_by(
            character_id=char.id,
            branch_id=state.current_branch,
            chapter_number=state.current_plot_index + 1
        ).first()
        
        state_char = state.characters.get(char.name)
        
        snapshot_data = {
            "current_mood": char.current_mood,
            "status": char.status,
            "skills": char.skills,
            "assets": char.assets,
            "is_active": (char.status or {}).get("is_active", True),
            "personality_snapshot": char.personality_dynamics,
            "values_snapshot": char.core_values,
            "ability_levels_snapshot": char.ability_levels
        }
        
        if existing_snapshot:
            for key, value in snapshot_data.items():
                setattr(existing_snapshot, key, value)
        else:
            snapshot = CharacterBranchStatus(
                character_id=char.id,
                branch_id=state.current_branch,
                chapter_number=state.current_plot_index + 1,
                **snapshot_data
            )
            db.add(snapshot)

    async def _process_key_events(
        self,
        db,
        state: NGEState,
        key_events: List,
        char_map: Dict[str, Character]
    ):
        """处理检测到的关键事件"""
        for event in key_events:
            print(f"  📌 关键事件: [{event.event_type}] {event.description}")
            
            # 为每个受影响的角色创建事件记录
            for char_name in event.affected_characters:
                char = char_map.get(char_name)
                if not char:
                    continue
                
                key_event = CharacterKeyEvent(
                    character_id=char.id,
                    chapter_number=state.current_plot_index + 1,
                    branch_id=state.current_branch,
                    event_type=event.event_type,
                    description=event.description,
                    impact=event.suggested_impacts,
                    intensity=event.intensity,
                    is_processed=True  # 已在演化中处理
                )
                db.add(key_event)
                
                # 添加到 state 中的角色记录
                state_char = state.characters.get(char_name)
                if state_char:
                    from ..schemas.state import KeyEventSchema, KeyEventType
                    try:
                        event_type = KeyEventType(event.event_type)
                    except ValueError:
                        event_type = KeyEventType.DECISION
                    
                    state_char.key_events.append(KeyEventSchema(
                        event_type=event_type,
                        chapter_number=state.current_plot_index + 1,
                        description=event.description,
                        impact=event.suggested_impacts,
                        intensity=event.intensity
                    ))

    def _process_story_updates(self, db, state: NGEState, updates):
        """处理剧情线更新（伏笔）"""
        # 添加新伏笔
        if updates.new_foreshadowing:
            for f in updates.new_foreshadowing:
                if f and f not in state.memory_context.global_foreshadowing:
                    state.memory_context.global_foreshadowing.append(f)
                    print(f"  📖 New Foreshadowing: {f}")
        
        # 解决旧伏笔
        if updates.resolved_threads:
            original_threads = list(state.memory_context.global_foreshadowing)
            for resolved in updates.resolved_threads:
                for existing in original_threads:
                    if existing in resolved or resolved in existing:
                        if existing in state.memory_context.global_foreshadowing:
                            state.memory_context.global_foreshadowing.remove(existing)
                            print(f"  ✅ Resolved Thread: {existing}")
        
        # 更新数据库中的伏笔记录
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

    async def _save_chapter(self, db, state: NGEState) -> DBChapter:
        """保存章节内容"""
        current_chapter_num = state.current_plot_index + 1
        
        # 查找或创建章节
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
        
        # 设置标题
        chapter_entry.title = f"第 {current_chapter_num} 章"
        if state.current_plot_index < len(state.plot_progress):
            chapter_entry.title = state.plot_progress[state.current_plot_index].title
        
        # 设置内容
        chapter_entry.content = state.current_draft
        
        # 生成结构化摘要
        try:
            summary_result = await self.summarizer.process(state, state.current_draft)
            chapter_entry.summary = json.dumps(summary_result, ensure_ascii=False)
            
            # 从摘要中提取新伏笔
            new_foreshadowing = summary_result.get("new_foreshadowing", [])
            for f in new_foreshadowing:
                if f and f not in state.memory_context.global_foreshadowing:
                    state.memory_context.global_foreshadowing.append(f)
                    print(f"  📖 从摘要中提取新伏笔: {f}")
            
            # 处理已解决的伏笔
            resolved_threads = summary_result.get("resolved_threads", [])
            if resolved_threads:
                original_threads = list(state.memory_context.global_foreshadowing)
                for resolved in resolved_threads:
                    for existing in original_threads:
                        if existing in resolved or resolved in existing:
                            if existing in state.memory_context.global_foreshadowing:
                                state.memory_context.global_foreshadowing.remove(existing)
                                print(f"  ✅ 从摘要中确认已解决伏笔: {existing}")
        except Exception as e:
            logger.error(f"摘要生成失败，使用回退方案: {e}", exc_info=True)
            from ..utils import generate_chapter_summary
            chapter_entry.summary = generate_chapter_summary(state.current_draft)
        
        chapter_entry.logic_checked = True
        
        # 更新大纲状态
        outline = db.query(PlotOutline).filter_by(
            novel_id=state.current_novel_id,
            branch_id=state.current_branch,
            chapter_number=current_chapter_num
        ).first()
        if outline:
            outline.status = OutlineStatus.COMPLETED
        
        db.commit()
        db.refresh(chapter_entry)
        
        # 更新状态中的摘要列表
        state.memory_context.recent_summaries.append(chapter_entry.summary)
        max_recent_summaries = Config.antigravity.RECENT_CHAPTERS_CONTEXT
        if len(state.memory_context.recent_summaries) > max_recent_summaries:
            state.memory_context.recent_summaries.pop(0)
        
        print(f"✅ Chapter {current_chapter_num} finalized and saved to DB (ID: {chapter_entry.id}).")
        
        return chapter_entry
