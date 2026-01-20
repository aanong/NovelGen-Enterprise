"""
Writer Agent 模块
负责正文撰写与文风模仿
"""
from typing import Optional
import random
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from ..schemas.literary import PRESET_POETRY, PRESET_ALLUSIONS, PRESET_MOTIFS, EmotionalCategory
from ..core.types import SceneType
from ..config.defaults import Defaults
from ..config.prompts import PromptTemplates
from ..config.messages import ErrorMessages
from ..config import Config
from ..utils import strip_think_tags, normalize_llm_content
from .base import BaseAgent
from ..core.registry import register_agent
import json
import logging
import re

logger = logging.getLogger(__name__)

@register_agent("writer")
class WriterAgent(BaseAgent):
    """
    Writer Agent: 负责正文撰写与文风模仿
    
    遵循 Antigravity Rules:
    - Rule 2.1: 人物灵魂锚定
    - Rule 6.1: 场景化强制约束
    - Rule 6.2: 验证前缀
    - Rule 4.1: 清除思考标签
    """
    
    def __init__(self, temperature: Optional[float] = None):
        """
        初始化 Writer Agent
        
        Args:
            temperature: 温度参数，默认使用配置值
        """
        super().__init__(
            model_name="gemini",  # Writer 使用 Gemini
            temperature=temperature or Config.model.GEMINI_TEMPERATURE,
            mock_responses=[
                f"当前遵循：{SceneType.NORMAL} 场景\n这是一个用于测试的章节正文。主角李青云站在青云山巅，俯瞰着云海。"
            ]
        )

    async def process(self, state: NGEState, plan_instruction: str) -> str:
        """
        处理写作任务（实现基类接口）
        
        Args:
            state: 当前状态
            plan_instruction: 规划指令
            
        Returns:
            生成的章节正文
        """
        return await self.write_chapter(state, plan_instruction)
    
    async def write_chapter(self, state: NGEState, plan_instruction: str) -> str:
        """
        撰写章节正文
        
        注入文风特征和角色设定，遵循 Antigravity Rules
        
        Args:
            state: 当前状态
            plan_instruction: 规划指令
            
        Returns:
            生成的章节正文
        """
        # 构建提示词组件
        plot_info = self._extract_plot_info(state)
        style_prompt = self._build_style_prompt(state)
        character_context = self._build_character_context(state)
        scene_rules = self._build_scene_rules(state)
        context_str = self._build_context_string(state)
        
        # 构建并发送提示词
        prompt = self._create_writing_prompt(deep_pov=True)
        messages = prompt.format_messages(
            style_prompt=style_prompt,
            character_context=character_context,
            scene_rules=scene_rules,
            refined_context_str=context_str,
            history_summary=self._build_history_summary(state),
            threads_str=self._build_threads_string(state),
            current_point_title=plot_info["title"],
            current_point_desc=plot_info["description"],
            plan_instruction=plan_instruction,
            target_length=Config.writing.TARGET_CHAPTER_LENGTH,
            min_length=Config.writing.MIN_CHAPTER_LENGTH
        )
        
        # 调用 LLM 并处理响应
        response = await self.llm.ainvoke(messages)
        content = self._process_llm_response(response)
        
        return content
    
    def _extract_plot_info(self, state: NGEState) -> dict:
        """提取剧情点信息"""
        if state.current_plot_index >= len(state.plot_progress):
            return {
                "title": "后续章节",
                "description": "跟随前文剧情自然发展"
            }
        current_point = state.plot_progress[state.current_plot_index]
        return {
            "title": current_point.title,
            "description": current_point.description
        }
    
    def _build_style_prompt(self, state: NGEState) -> str:
        """构建文风提示词（增强版：注入动态文学元素）"""
        style = state.novel_bible.style_description
        if not style:
            return ""
        
        # 1. 基础文风
        base_style = (
            f"文风规范：\n"
            f"- 句式：{style.rhythm_description}，{style.dialogue_narration_ratio} 的对话旁白比。\n"
            f"- 修辞偏好：{', '.join(style.common_rhetoric)}。\n"
            f"- 情绪基调：{style.emotional_tone}。\n"
            f"- 核心词汇：{', '.join(style.vocabulary_preference)}。\n"
        )
        
        # 2. 动态文学素材推荐
        literary_suggestions = []
        
        # 简单的关键词匹配逻辑
        tone = style.emotional_tone
        relevant_poetry = []
        relevant_allusions = []
        
        # 映射 tone 到 EmotionCategory
        target_emotions = []
        if "悲" in tone or "凉" in tone: target_emotions.append(EmotionalCategory.SORROW)
        if "壮" in tone or "热血" in tone: target_emotions.append(EmotionalCategory.AMBITION)
        if "思" in tone or "恋" in tone: target_emotions.append(EmotionalCategory.LONGING)
        if "喜" in tone: target_emotions.append(EmotionalCategory.JOY)
        
        if not target_emotions:
            target_emotions = [EmotionalCategory.HOPE, EmotionalCategory.AMBITION] # 默认
            
        # 筛选诗词
        for p in PRESET_POETRY:
            if p.mood in target_emotions:
                relevant_poetry.append(f"『{p.quote}』(意象：{', '.join(p.imagery)})")
        
        # 筛选典故
        for a in PRESET_ALLUSIONS:
            if any(e in target_emotions for e in a.emotions):
                relevant_allusions.append(f"『{a.title}』({a.core_meaning})")
                
        # 随机取样，避免 Prompt 过长
        if relevant_poetry:
            literary_suggestions.append(f"推荐诗意意象：{', '.join(random.sample(relevant_poetry, min(2, len(relevant_poetry))))}")
        if relevant_allusions:
            literary_suggestions.append(f"推荐典故暗喻：{', '.join(random.sample(relevant_allusions, min(2, len(relevant_allusions))))}")
            
        if literary_suggestions:
            base_style += "\n【文学润色灵感】（请尝试自然融入以下元素）：\n" + "\n".join(literary_suggestions) + "\n"
            
        return base_style
    
    def _build_character_context(self, state: NGEState) -> str:
        """
        构建人物上下文（优化：限制角色数量以减少 token 使用）
        包含基础信息、语言风格、心理状态和价值观约束
        
        Args:
            state: 当前状态
            
        Returns:
            人物上下文字符串（最多包含 N 个主要角色）
        """
        character_lines = []
        speech_style_lines = []
        psychology_lines = []
        value_lines = []
        growth_lines = [] # 新增
        
        # 优化：如果角色太多，只包含前 N 个（通常是主要角色）
        characters_to_include = list(state.characters.items())
        if len(characters_to_include) > Defaults.MAX_CHARACTERS_IN_PROMPT:
            # 优先包含有禁忌行为的角色（更重要的约束）
            characters_with_forbidden = [
                (name, char) for name, char in characters_to_include
                if state.antigravity_context.character_anchors.get(name, [])
            ]
            other_characters = [
                (name, char) for name, char in characters_to_include
                if not state.antigravity_context.character_anchors.get(name, [])
            ]
            # 先包含有禁忌的角色，再补充其他角色
            characters_to_include = (characters_with_forbidden + other_characters)[:Defaults.MAX_CHARACTERS_IN_PROMPT]
        
        for name, char in characters_to_include:
            # 获取禁忌行为
            forbidden = state.antigravity_context.character_anchors.get(name, [])
            forbidden_str = f"【禁止行为：{', '.join(forbidden)}】" if forbidden else ""
            
            # 构建角色基础信息
            char_info_parts = [
                f"- {name}: {char.personality_traits.get('role', '')}",
                f"性格:{char.personality_traits.get('personality', '')}",
                f"状态:{char.current_mood}"
            ]
            
            # 添加技能
            if char.skills:
                char_info_parts.append(f"技能:{', '.join(char.skills)}")
            
            # 添加资产
            if char.assets:
                assets_list = [f"{k}: {v}" for k, v in char.assets.items()]
                char_info_parts.append(f"资产:[{', '.join(assets_list)}]")
            
            # 添加物品
            if char.inventory:
                items_list = [item.name for item in char.inventory]
                char_info_parts.append(f"持有物:{', '.join(items_list)}")
            
            # 添加禁忌
            if forbidden_str:
                char_info_parts.append(forbidden_str)
            
            character_lines.append(", ".join(char_info_parts))
            
            # ========== 构建语言风格指导 ==========
            if hasattr(char, 'speech_style') and char.speech_style:
                speech_prompt = char.speech_style.to_prompt_text(name)
                if speech_prompt:
                    speech_style_lines.append(speech_prompt)
            
            # ========== 构建心理状态指导 ==========
            if hasattr(char, 'psychology') and char.psychology:
                psychology_prompt = char.psychology.to_prompt_text(name)
                if psychology_prompt:
                    psychology_lines.append(psychology_prompt)
            
            # ========== 构建价值观约束（新增）==========
            if hasattr(char, 'value_system') and char.value_system:
                value_prompt = char.value_system.to_prompt_text(name)
                if value_prompt:
                    value_lines.append(value_prompt)
                
                # 提取道德底线作为额外禁忌
                if char.value_system.moral_absolutes:
                    moral_forbidden = [f"违背'{a}'" for a in char.value_system.moral_absolutes]
                    if moral_forbidden:
                        value_lines.append(f"【{name}的道德禁忌】：{', '.join(moral_forbidden)}")
                
                # 检查是否有活跃的价值冲突
                if char.value_system.active_conflicts:
                    conflict = char.value_system.active_conflicts[0]
                    conflict_str = f"【{name}当前两难】：{' vs '.join(conflict.values_in_conflict)} - {conflict.situation}"
                    value_lines.append(conflict_str)

            # ========== 构建成长/思想指导（新增）==========
            if hasattr(char, 'growth_system') and char.growth_system:
                gs = char.growth_system
                if gs.current_growth_theme:
                    growth_lines.append(f"【{name}本章成长焦点】：{gs.current_growth_theme}")
                growth_lines.append(f"【{name}当前思想境界】：{gs.mindset.to_prompt_text()}")
        
        # 组合完整的人物上下文
        result_parts = ["\n".join(character_lines)]
        
        # 添加语言风格指导区块
        if speech_style_lines:
            result_parts.append("\n\n【人物语言风格指导】（写对话时必须遵循）")
            result_parts.append("\n".join(speech_style_lines))
        
        # 添加心理描写指导区块
        if psychology_lines:
            result_parts.append("\n\n【人物心理描写指导】（进行心理描写时参考）")
            result_parts.append("\n".join(psychology_lines))
        
        # 添加价值观约束区块
        if value_lines:
            result_parts.append("\n\n【人物价值观约束】（行为决策必须考虑）")
            result_parts.append("\n".join(value_lines))
            
        # 添加成长指导区块
        if growth_lines:
            result_parts.append("\n\n【人物思想与成长】（赋予人物深度）")
            result_parts.append("\n".join(growth_lines))
        
        return "\n".join(result_parts)
    
    def _build_scene_rules(self, state: NGEState) -> str:
        """构建场景约束规则"""
        scene_constraints = state.antigravity_context.scene_constraints
        scene_type = scene_constraints.get("scene_type", SceneType.NORMAL)
        
        cfg_constraints = Config.antigravity.SCENE_CONSTRAINTS.get(scene_type, {})
        if not cfg_constraints:
            return ""
        
        preferred_style = cfg_constraints.get("preferred_style", "")
        forbidden_patterns = ", ".join(cfg_constraints.get("forbidden_patterns", []))
        
        return PromptTemplates.SCENE_CONSTRAINT_TEMPLATE.format(
            scene_type=scene_type,
            preferred_style=preferred_style,
            forbidden_patterns=forbidden_patterns
        )
    
    def _build_context_string(self, state: NGEState) -> str:
        """构建 RAG 上下文字符串"""
        if not state.refined_context:
            return ""
        return "\n【相关背景与细节设定】\n" + "\n".join(state.refined_context) + "\n"
    
    def _build_history_summary(self, state: NGEState) -> str:
        """
        构建历史摘要（优化：限制数量以减少 token 使用）
        
        Args:
            state: 当前状态
            
        Returns:
            历史摘要字符串（最多包含最近 3 条）
        """
        summaries = state.memory_context.recent_summaries
        # 只取最近 N 条摘要，减少 token 使用
        limited_summaries = summaries[-Defaults.MAX_CONTEXT_SUMMARIES:] if len(summaries) > Defaults.MAX_CONTEXT_SUMMARIES else summaries
        return '\n'.join(limited_summaries)
    
    def _build_threads_string(self, state: NGEState) -> str:
        """构建伏笔字符串"""
        active_threads = state.memory_context.global_foreshadowing
        if not active_threads:
            return "无"
        return "\n".join([f"- {t}" for t in active_threads])
    
    def _create_writing_prompt(self, deep_pov: bool = False) -> ChatPromptTemplate:
        """创建写作提示词模板"""
        
        deep_pov_instruction = ""
        if deep_pov:
            deep_pov_instruction = (
                "\n【Deep POV (深层视点) 写作要求】\n"
                "- 必须透过视点人物的感官和心境来描写世界。\n"
                "- 环境描写不是客观的，而是主观的（例如：心情低落时，阳光也是刺眼的）。\n"
                "- 避免“他感到”、“他想”等直接心理动词，直接展示思维流动的过程。\n"
            )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极具天赋的长篇小说作家。擅长细腻的描写和深刻的人物塑造。\n"
                "{style_prompt}\n"
                "当前章节相关人物信息：\n"
                "{character_context}\n"
                "{scene_rules}\n"
                "{refined_context_str}"
                "历史背景摘要：\n"
                "{history_summary}\n"
                "【未解决伏笔/悬念】：\n"
                "{threads_str}\n"
                "\n【核心执行准则】\n"
                "- 绝对禁止让角色做出其【禁止行为】中的动作。\n"
                "- 绝对遵守场景强制约束，这是文风的一致性保证。\n"
                "- 保持角色心境与当前状态一致。\n"
                "- 此前埋下的伏笔若有机会，请自然地推进或回收。\n"
                "{deep_pov_instruction}"
            )),
            ("human", (
                "当前剧情：{current_point_title}\n"
                "核心内容：{current_point_desc}\n"
                "具体指令：{plan_instruction}\n\n"
                "请开始撰写正文。字数建议在 {target_length} 字以上（最少 {min_length} 字），确保情节饱满，文风统一。"
            ))
        ])
        
        return prompt_template.partial(deep_pov_instruction=deep_pov_instruction)
    
    def _process_llm_response(self, response) -> str:
        """处理 LLM 响应"""
        content = normalize_llm_content(response.content)
        content = strip_think_tags(content)  # Rule 4.1: 清除思考标签
        
        # Rule 6.2: 清理验证前缀
        content = re.sub(r'^当前遵循：.*?\n', '', content).strip()
        
        return content
