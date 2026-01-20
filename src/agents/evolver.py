"""
CharacterEvolver Agent 模块
负责分析章节内容，触发人物性格、能力、价值观的动态演化
支持：自动分析 + 关键事件触发 + 人物弧光推进 + 成长系统管理
"""
from ..schemas.state import (
    NGEState, CharacterState, KeyEventType, KeyEventSchema,
    AbilityLevel, CharacterArcSchema, ArcType,
    MasteryStage, GrowthCurveType, GrowthMilestone,
    CharacterGrowthSystem, MindsetDimension
)
from ..utils import normalize_llm_content, extract_json_from_text, strip_think_tags
from ..config import Config
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


# ============ CharacterEvolver Agent ============

from .base import BaseAgent
from ..config.prompts import PromptTemplates
from ..core.registry import register_agent
from langchain_core.prompts import ChatPromptTemplate

# ============ 演化结果数据模型 ============

class PersonalityChange(BaseModel):
    """性格维度变化"""
    dimension: str = Field(description="性格维度名称，如 courage, empathy, trust")
    old_value: float = Field(description="原始值 0.0-1.0")
    new_value: float = Field(description="新值 0.0-1.0")
    reason: str = Field(description="变化原因")


class ValueChange(BaseModel):
    """价值观变化"""
    value_name: str = Field(description="价值观名称，如 正义, 复仇, 家族")
    old_value: float = Field(description="原始坚定程度 0.0-1.0")
    new_value: float = Field(description="新的坚定程度 0.0-1.0")
    reason: str = Field(description="变化原因")


class AbilityChange(BaseModel):
    """能力变化"""
    ability_name: str = Field(description="能力/技能名称")
    change_type: str = Field(description="变化类型: new(新获得), level_up(升级), proficiency(熟练度提升)")
    old_level: Optional[int] = Field(None)
    new_level: Optional[int] = Field(None)
    old_proficiency: Optional[float] = Field(None)
    new_proficiency: Optional[float] = Field(None)
    description: str = Field(default="", description="能力描述或变化说明")


class DetectedKeyEvent(BaseModel):
    """检测到的关键事件"""
    event_type: str = Field(description="事件类型: trauma, epiphany, decision, loss, gain, betrayal, sacrifice, confrontation")
    description: str = Field(description="事件描述")
    intensity: float = Field(default=0.5, description="影响强度 0.0-1.0")
    affected_characters: List[str] = Field(default_factory=list, description="受影响的角色")
    suggested_impacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="建议的影响: {personality_changes: {...}, value_changes: {...}, ability_changes: {...}}"
    )


class MindsetChange(BaseModel):
    """思想维度变化"""
    dimension: str = Field(description="维度名称：openness/depth/emotional_maturity/empathy/decisiveness/resilience/insight")
    old_value: float = Field(description="原始值 0.0-1.0")
    new_value: float = Field(description="新值 0.0-1.0")
    reason: str = Field(description="变化原因")


class GrowthEvent(BaseModel):
    """成长事件"""
    event_type: str = Field(description="事件类型：breakthrough/bottleneck/insight/regression")
    description: str = Field(description="事件描述")
    affected_abilities: List[str] = Field(default_factory=list, description="影响的能力")
    is_major: bool = Field(default=False, description="是否为重大成长事件")


class CharacterEvolution(BaseModel):
    """单个人物的完整演化报告"""
    character_name: str = Field(description="角色姓名")
    
    # 心情变化（保持兼容）
    mood_change: str = Field(default="", description="心情变化描述")
    
    # 性格维度变化
    personality_changes: List[PersonalityChange] = Field(
        default_factory=list,
        description="性格维度的变化列表"
    )
    
    # 价值观变化
    value_changes: List[ValueChange] = Field(
        default_factory=list,
        description="价值观的变化列表"
    )
    
    # 能力变化
    ability_changes: List[AbilityChange] = Field(
        default_factory=list,
        description="能力/技能的变化列表"
    )
    
    # 技能列表更新（保持兼容）
    skill_update: List[str] = Field(default_factory=list, description="新增的技能名称")
    
    # 关系变化（保持兼容）
    relationship_change: Dict[str, str] = Field(
        default_factory=dict,
        description="与其他角色关系的变化"
    )
    
    # 状态变化（保持兼容）
    status_change: Optional[Dict[str, Any]] = Field(None, description="生理/心理状态变更")
    
    # 弧光进度推进
    arc_progress_delta: float = Field(
        default=0.0,
        description="人物弧光进度增量 0.0-1.0"
    )
    arc_milestone_completed: bool = Field(
        default=False,
        description="是否完成了当前里程碑"
    )
    
    # ========== 新增：思想成长 ==========
    mindset_changes: List[MindsetChange] = Field(
        default_factory=list,
        description="思想维度的变化列表"
    )
    
    growth_events: List[GrowthEvent] = Field(
        default_factory=list,
        description="本章发生的成长事件"
    )
    
    growth_theme_update: Optional[str] = Field(
        None,
        description="成长主题更新"
    )
    
    mastery_stage_changes: Dict[str, str] = Field(
        default_factory=dict,
        description="技能掌握阶段变化，如：{'剑法': 'competent -> proficient'}"
    )
    
    # 演化总结
    evolution_summary: str = Field(description="角色变化的简短摘要")


class PlotUpdate(BaseModel):
    """剧情线更新"""
    new_foreshadowing: List[str] = Field(default_factory=list, description="本章埋下的新伏笔")
    resolved_threads: List[str] = Field(default_factory=list, description="本章解决或回收的旧伏笔")


class EvolutionResult(BaseModel):
    """完整的章节演化结果"""
    evolutions: List[CharacterEvolution] = Field(default_factory=list)
    detected_key_events: List[DetectedKeyEvent] = Field(
        default_factory=list,
        description="本章检测到的关键事件"
    )
    story_updates: Optional[PlotUpdate] = None

@register_agent("evolver")
class CharacterEvolver(BaseAgent):
    """
    增强版人物演化 Agent
    
    功能：
    1. 自动分析章节内容，提取人物变化
    2. 检测关键事件（创伤、顿悟、重大决定等）
    3. 推进人物弧光进度
    4. 计算性格维度、价值观、能力的变化
    
    遵循 Antigravity Rules:
    - Rule 2.1: 人物灵魂锚定（变化必须有合理原因）
    - Rule 3.2: 人物立体与成长
    - Rule 3.4: 伏笔回收
    """
    
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",  # 使用 Gemini 进行深度分析
            temperature=temperature or 0.3,
            mock_responses=[
                json.dumps({
                    "evolutions": [],
                    "detected_key_events": [],
                    "story_updates": {"new_foreshadowing": [], "resolved_threads": []}
                })
            ]
        )

    async def process(self, state: NGEState) -> EvolutionResult:
        """BaseAgent 必需方法，委托给 evolve"""
        return await self.evolve(state)

    async def evolve(self, state: NGEState) -> EvolutionResult:
        """
        分析章节内容，返回完整的人物演化数据
        
        Args:
            state: 当前全局状态
            
        Returns:
            EvolutionResult: 包含所有角色演化、关键事件、剧情更新
        """
        chapter_content = state.current_draft
        
        # 构建角色上下文
        characters_context = self._build_characters_context(state)
        
        # 构建弧光上下文
        arc_context = self._build_arc_context(state)
        
        # 当前伏笔
        active_threads = state.memory_context.global_foreshadowing
        active_threads_str = "\n".join([f"- {t}" for t in active_threads]) if active_threads else "无"

        prompt = self._create_evolution_prompt()
        
        messages = prompt.format_messages(
            chapter_content=chapter_content[:8000],  # 限制长度
            characters_context=characters_context,
            arc_context=arc_context,
            active_threads_str=active_threads_str,
            current_chapter=state.current_plot_index + 1
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            content = normalize_llm_content(response.content)
            content = strip_think_tags(content)
            data = extract_json_from_text(content)
            
            if not data:
                logger.warning(f"无法解析演化结果，返回空结果。响应内容前200字: {content[:200]}")
                return EvolutionResult(evolutions=[], story_updates=PlotUpdate())
            
            return EvolutionResult.model_validate(data)
            
        except Exception as e:
            logger.error(f"人物演化分析失败: {e}", exc_info=True)
            return EvolutionResult(evolutions=[], story_updates=PlotUpdate())

    def _build_characters_context(self, state: NGEState) -> str:
        """构建角色当前状态的上下文字符串"""
        lines = []
        for name, char in state.characters.items():
            lines.append(f"\n【{name}】")
            lines.append(f"  角色定位: {char.personality_traits.get('role', '未知')}")
            lines.append(f"  当前心情: {char.current_mood}")
            
            # 性格动态维度
            if char.personality_dynamics:
                dynamics_str = ", ".join([
                    f"{k}: {v:.1f}" for k, v in char.personality_dynamics.items()
                ])
                lines.append(f"  性格维度: {dynamics_str}")
            
            # 价值观
            if char.core_values:
                values_str = ", ".join([
                    f"{k}: {v:.1f}" for k, v in char.core_values.items()
                ])
                lines.append(f"  核心价值观: {values_str}")
            
            # 能力等级
            if char.ability_levels:
                abilities_str = ", ".join([
                    f"{k}(Lv{v.level}, 熟练{v.proficiency:.0%})" 
                    for k, v in char.ability_levels.items()
                ])
                lines.append(f"  能力等级: {abilities_str}")
            
            # 核心需求与缺陷
            if char.core_need:
                lines.append(f"  核心需求: {char.core_need}")
            if char.core_flaw:
                lines.append(f"  核心缺陷: {char.core_flaw}")
        
        return "\n".join(lines)

    def _build_arc_context(self, state: NGEState) -> str:
        """构建人物弧光上下文"""
        lines = []
        for name, char in state.characters.items():
            if char.character_arc and char.character_arc.status == "active":
                arc = char.character_arc
                lines.append(f"\n【{name}的人物弧光】")
                lines.append(f"  弧光类型: {arc.arc_type}")
                lines.append(f"  当前进度: {arc.progress:.0%}")
                lines.append(f"  起点状态: {json.dumps(arc.starting_state, ensure_ascii=False)}")
                lines.append(f"  目标状态: {json.dumps(arc.target_state, ensure_ascii=False)}")
                
                # 当前里程碑
                if arc.milestones and arc.current_milestone_index < len(arc.milestones):
                    milestone = arc.milestones[arc.current_milestone_index]
                    lines.append(f"  当前里程碑: {milestone.description}")
                    lines.append(f"    章节范围: {milestone.chapter_range}")
                    if milestone.trigger_event:
                        lines.append(f"    触发事件: {milestone.trigger_event}")
        
        return "\n".join(lines) if lines else "暂无预设人物弧光"

    def _create_evolution_prompt(self) -> ChatPromptTemplate:
        """创建演化分析的提示词模板"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的小说编辑，专精于人物弧光分析和角色成长轨迹设计。

你的任务是仔细阅读章节内容，分析每个角色的变化，并输出结构化的演化报告。

【分析维度】
1. **性格维度变化** (personality_changes)
   - courage（勇气）、rationality（理性）、empathy（同理心）、openness（开放性）、trust（信任）
   - 值域 0.0-1.0，每次变化通常 ±0.05 到 ±0.15
   - 重大事件可能导致 ±0.2 到 ±0.3 的剧烈变化

2. **价值观变化** (value_changes)
   - 如：正义、复仇、家族、自由、权力、爱情、生存
   - 值域 0.0-1.0，表示坚定程度
   - 信念动摇或强化都需要充分的剧情支撑

3. **能力变化** (ability_changes)
   - 新获得技能 (new)、等级提升 (level_up)、熟练度提升 (proficiency)
   - 等级 1-10，熟练度 0.0-1.0
   - 能力成长需要有实战、顿悟或修炼的剧情依据

4. **关键事件检测** (detected_key_events)
   类型包括：
   - trauma: 创伤事件（亲人死亡、重大失败、背叛）
   - epiphany: 顿悟时刻（突破认知、理解真相）
   - decision: 重大决定（改变命运走向的选择）
   - loss: 失去（失去重要的人、物、信仰）
   - gain: 获得（获得力量、认可、真相）
   - betrayal: 背叛
   - sacrifice: 牺牲
   - confrontation: 直面恐惧/阴影

5. **人物弧光推进** (arc_progress_delta)
   - 根据角色在本章的表现，判断其向目标状态前进了多少
   - 通常每章 0.02-0.10，关键章节可达 0.15-0.25
   - 如果完成了当前里程碑，设置 arc_milestone_completed = true

【重要原则】
- 变化必须有剧情依据，不能凭空产生
- 渐进式变化优于突变（除非有重大事件支撑）
- 保持人物行为与性格的一致性
- 关键事件的强度 (intensity) 决定其影响程度

请严格按照 JSON 格式输出。"""),
            ("human", """**第 {current_chapter} 章内容:**
---
{chapter_content}
---

**当前各角色状态:**
{characters_context}

**人物弧光规划:**
{arc_context}

**当前未解决伏笔:**
{active_threads_str}

请分析本章内容，输出以下 JSON 格式的演化报告：

```json
{{
    "evolutions": [
        {{
            "character_name": "角色名",
            "mood_change": "心情变化描述",
            "personality_changes": [
                {{"dimension": "courage", "old_value": 0.5, "new_value": 0.6, "reason": "..."}}
            ],
            "value_changes": [
                {{"value_name": "正义", "old_value": 0.7, "new_value": 0.8, "reason": "..."}}
            ],
            "ability_changes": [
                {{"ability_name": "剑法", "change_type": "proficiency", "old_proficiency": 0.3, "new_proficiency": 0.4, "description": "..."}}
            ],
            "skill_update": ["新技能名"],
            "relationship_change": {{"其他角色": "关系变化描述"}},
            "status_change": null,
            "arc_progress_delta": 0.05,
            "arc_milestone_completed": false,
            "evolution_summary": "本章角色变化的简短摘要"
        }}
    ],
    "detected_key_events": [
        {{
            "event_type": "epiphany",
            "description": "事件描述",
            "intensity": 0.6,
            "affected_characters": ["角色A", "角色B"],
            "suggested_impacts": {{
                "personality_changes": {{"courage": 0.1}},
                "value_changes": {{"信念": 0.15}}
            }}
        }}
    ],
    "story_updates": {{
        "new_foreshadowing": ["新埋下的伏笔"],
        "resolved_threads": ["已回收的伏笔"]
    }}
}}
```

注意：
- 只为发生了显著变化的角色生成演化报告
- 如果没有检测到关键事件，detected_key_events 可以为空数组
- 性格维度和价值观的 old_value 应与上面提供的当前状态一致""")
        ])


# ============ 辅助函数 ============

def apply_personality_change(
    current_dynamics: Dict[str, float],
    change: PersonalityChange,
    max_change: float = 0.3
) -> Dict[str, float]:
    """
    应用性格维度变化，带边界检查
    
    Args:
        current_dynamics: 当前性格动态维度
        change: 要应用的变化
        max_change: 单次最大变化量
        
    Returns:
        更新后的性格动态维度
    """
    new_dynamics = current_dynamics.copy()
    
    if change.dimension in new_dynamics:
        delta = change.new_value - change.old_value
        # 限制单次变化幅度
        delta = max(-max_change, min(max_change, delta))
        new_value = new_dynamics[change.dimension] + delta
        # 限制在 0.0-1.0 范围内
        new_dynamics[change.dimension] = max(0.0, min(1.0, new_value))
    
    return new_dynamics


def apply_value_change(
    current_values: Dict[str, float],
    change: ValueChange,
    max_change: float = 0.25
) -> Dict[str, float]:
    """
    应用价值观变化，带边界检查
    """
    new_values = current_values.copy()
    
    if change.value_name in new_values:
        delta = change.new_value - change.old_value
        delta = max(-max_change, min(max_change, delta))
        new_value = new_values[change.value_name] + delta
        new_values[change.value_name] = max(0.0, min(1.0, new_value))
    else:
        # 新的价值观
        new_values[change.value_name] = max(0.0, min(1.0, change.new_value))
    
    return new_values


def apply_ability_change(
    current_abilities: Dict[str, AbilityLevel],
    change: AbilityChange
) -> Dict[str, AbilityLevel]:
    """
    应用能力变化
    """
    new_abilities = current_abilities.copy()
    
    if change.change_type == "new":
        # 新获得的能力
        new_abilities[change.ability_name] = AbilityLevel(
            level=change.new_level or 1,
            proficiency=change.new_proficiency or 0.1,
            description=change.description,
            mastery_stage=MasteryStage.NOVICE
        )
    elif change.ability_name in new_abilities:
        ability = new_abilities[change.ability_name]
        
        if change.change_type == "level_up" and change.new_level:
            ability.level = min(10, change.new_level)
            # 升级时重置熟练度
            ability.proficiency = 0.0
            # 更新掌握阶段
            ability.mastery_stage = _calculate_mastery_stage(ability.level)
            
        elif change.change_type == "proficiency" and change.new_proficiency is not None:
            ability.proficiency = min(1.0, change.new_proficiency)
        
        if change.description:
            ability.description = change.description
        
        # 记录成长历史
        ability.growth_history.append({
            "type": change.change_type,
            "value": change.new_level or change.new_proficiency
        })
    
    return new_abilities


def _calculate_mastery_stage(level: int) -> MasteryStage:
    """根据等级计算掌握阶段"""
    if level <= 1:
        return MasteryStage.NOVICE
    elif level <= 3:
        return MasteryStage.COMPETENT
    elif level <= 5:
        return MasteryStage.PROFICIENT
    elif level <= 8:
        return MasteryStage.MASTER
    else:
        return MasteryStage.TRANSCENDENT


def apply_mindset_change(
    current_mindset: MindsetDimension,
    change: MindsetChange,
    max_change: float = 0.2
) -> MindsetDimension:
    """
    应用思想维度变化
    
    Args:
        current_mindset: 当前思想维度
        change: 要应用的变化
        max_change: 单次最大变化量
        
    Returns:
        更新后的思想维度
    """
    # 创建副本
    new_mindset = current_mindset.model_copy()
    
    # 获取当前值
    dimension_name = change.dimension.lower()
    if hasattr(new_mindset, dimension_name):
        current_value = getattr(new_mindset, dimension_name)
        
        # 计算变化量
        delta = change.new_value - change.old_value
        delta = max(-max_change, min(max_change, delta))
        
        # 应用变化
        new_value = max(0.0, min(1.0, current_value + delta))
        setattr(new_mindset, dimension_name, new_value)
    
    return new_mindset


def process_growth_event(
    growth_system: CharacterGrowthSystem,
    event: GrowthEvent,
    chapter: int
) -> CharacterGrowthSystem:
    """
    处理成长事件
    
    Args:
        growth_system: 当前成长系统
        event: 成长事件
        chapter: 当前章节
        
    Returns:
        更新后的成长系统
    """
    # 记录里程碑
    growth_system.record_milestone(
        milestone_type=event.event_type,
        chapter=chapter,
        description=event.description,
        is_major=event.is_major
    )
    
    # 处理不同类型的事件
    if event.event_type == "breakthrough":
        # 突破 - 移除阻碍
        if growth_system.growth_blockers:
            growth_system.growth_blockers.pop(0)
    
    elif event.event_type == "bottleneck":
        # 遇到瓶颈 - 添加阻碍
        growth_system.growth_blockers.append(event.description)
    
    elif event.event_type == "insight":
        # 顿悟 - 提升领悟力
        growth_system.mindset.insight = min(1.0, growth_system.mindset.insight + 0.1)
    
    elif event.event_type == "regression":
        # 退步 - 降低某些维度
        growth_system.mindset.resilience = max(0.0, growth_system.mindset.resilience - 0.05)
    
    return growth_system


def apply_evolution_to_character(
    character: CharacterState,
    evolution: CharacterEvolution,
    chapter: int = 0
) -> CharacterState:
    """
    将演化结果完整应用到角色状态
    
    Args:
        character: 当前角色状态
        evolution: 演化结果
        chapter: 当前章节号
        
    Returns:
        更新后的角色状态
    """
    # 1. 更新心情
    if evolution.mood_change:
        character.current_mood = evolution.mood_change
    
    # 2. 应用性格维度变化
    for change in evolution.personality_changes:
        character.personality_dynamics = apply_personality_change(
            character.personality_dynamics, change
        )
    
    # 3. 应用价值观变化
    for change in evolution.value_changes:
        character.core_values = apply_value_change(
            character.core_values, change
        )
    
    # 4. 应用能力变化
    for change in evolution.ability_changes:
        character.ability_levels = apply_ability_change(
            character.ability_levels, change
        )
        
        # 更新驾驭曲线
        if hasattr(character, 'growth_system') and character.growth_system:
            ability = character.ability_levels.get(change.ability_name)
            if ability:
                character.growth_system.update_proficiency_curve(
                    change.ability_name, 
                    ability.proficiency
                )
    
    # 5. 添加新技能
    for skill in evolution.skill_update:
        if skill not in character.skills:
            character.skills.append(skill)
    
    # 6. 更新关系
    for target, change in evolution.relationship_change.items():
        character.relationships[target] = change
    
    # 7. 更新状态（可扩展）
    if evolution.status_change:
        for key, value in evolution.status_change.items():
            pass
    
    # 8. 推进弧光进度
    if hasattr(character, 'character_arc') and character.character_arc:
        if evolution.arc_progress_delta > 0:
            character.character_arc.progress = min(
                1.0,
                character.character_arc.progress + evolution.arc_progress_delta
            )
            
            if evolution.arc_milestone_completed:
                _advance_arc_milestone(character.character_arc)
    
    # ========== 新增：思想成长处理 ==========
    
    # 9. 应用思想维度变化
    if hasattr(character, 'growth_system') and character.growth_system:
        for mc in evolution.mindset_changes:
            character.growth_system.mindset = apply_mindset_change(
                character.growth_system.mindset, mc
            )
        
        # 10. 处理成长事件
        for event in evolution.growth_events:
            character.growth_system = process_growth_event(
                character.growth_system, event, chapter
            )
        
        # 11. 更新成长主题
        if evolution.growth_theme_update:
            character.growth_system.current_growth_theme = evolution.growth_theme_update
        
        # 12. 更新技能掌握阶段
        for skill_name, stage_change in evolution.mastery_stage_changes.items():
            if skill_name in character.ability_levels:
                if " -> " in stage_change:
                    _, new_stage_str = stage_change.split(" -> ")
                    try:
                        new_stage = MasteryStage(new_stage_str.strip())
                        character.ability_levels[skill_name].mastery_stage = new_stage
                    except ValueError:
                        pass
    
    return character


def _advance_arc_milestone(arc: CharacterArcSchema):
    """推进弧光里程碑"""
    if arc.milestones and arc.current_milestone_index < len(arc.milestones) - 1:
        arc.current_milestone_index += 1
