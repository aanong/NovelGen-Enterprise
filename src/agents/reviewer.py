import os
import re
import json
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState, CharacterState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, validate_character_consistency, normalize_llm_content
from .base import BaseAgent
from ..core.types import NodeAction, ReviewDecision
from ..config.defaults import Defaults
from ..config.prompts import PromptTemplates
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from ..core.registry import register_agent
from ..db.models import NovelBible
import json
import logging

logger = logging.getLogger(__name__)

@register_agent("reviewer")
class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent (Gemini): 负责逻辑审查、人物OOC检查及状态演化。
    作为【王】进行最后的裁决。
    遵循 Rule 1.1 / 2.2: 逻辑与一致性守门人
    """
    def __init__(self, temperature: float = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or Config.model.DEEPSEEK_REVIEWER_TEMP,
            mock_responses=[
                # Response for review_draft
                json.dumps({"passed": True, "score": 0.9, "feedback": "Good job", "logical_errors": []}),
            ]
        )

    async def process(self, state: NGEState, draft: str) -> Dict[str, Any]:
        """
        BaseAgent required method.
        Delegates to review_draft.
        """
        return await self.review_draft(state, draft)

    async def review_draft(self, state: NGEState, draft: str, outline_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        检查生成的正文是否有逻辑漏洞或人物 OOC。
        遵循 Rule 3.3: 剧情防崩与连贯
        增强：集成世界观一致性检查
        """
        # 提取当前所有角色禁忌
        character_rules = ""
        for name, char in state.characters.items():
            anchors = state.antigravity_context.character_anchors.get(name, [])
            if anchors:
                character_rules += f"- {name}: 禁止 {', '.join(anchors)}\n"

        # 提取全局伏笔
        active_threads = state.memory_context.global_foreshadowing
        threads_str = "\n".join([f"- {t}" for t in active_threads]) if active_threads else "无"

        # 大纲遵循度参考
        outline_context = ""
        if outline_info:
            outline_context = (
                f"\n【本章规划要求】\n"
                f"场景设定：{outline_info.get('scene', '无')}\n"
                f"核心冲突：{outline_info.get('conflict', '无')}\n"
            )

        # 世界观规则检查 (集成 WorldGuard 逻辑)
        world_rules = await self._get_world_rules(state)
        world_rules_str = self._format_world_rules(world_rules)
        character_limits = self._get_character_limits(state)

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极其敏锐的小说评论家和逻辑学家。你的任务是发现草稿中的任何微小漏洞。\n"
                f"{PromptTemplates.ANTIGRAVITY_WARNING}\n"
                "当前人物灵魂锚定：\n{character_rules}\n"
                "【需关注的未回收伏笔】：\n{threads_str}\n"
                "{outline_context}\n"
                "【世界观规则】\n{world_rules}\n"
                "【角色能力限制】\n{character_limits}\n"
                "【审核重点】：\n"
                "1. 逻辑自洽性：是否存在前后矛盾或时空错误？\n"
                "2. 人物一致性：角色行为是否符合性格锚定？是否 OOC？\n"
                "3. 大纲遵循度：是否完成了规划要求的场景和核心冲突？\n"
                "4. 伏笔处理：是否按计划推进或回收了指定的伏笔？\n"
                "5. 世界观一致性：是否违背能力体系、地理设定、技术水平等规则？\n"
                "6. **剧情生硬度检测**：是否存在“为了推进剧情而强行扭曲人物逻辑”（Forced Plotting）的情况？\n"
                "7. **文风一致性**：叙事语调是否与设定（NovelBible）中的基调保持一致？\n"
                "输出格式必须为 JSON。"
            )),
            ("human", (
                "请审查以下小说章节草稿，并给出详细反馈。\n"
                "剧情背景：{summary}\n"
                "草稿内容：\n{draft}\n\n"
                "必须包含以下字段：passed (bool), score (0.0-1.0), feedback (str), logical_errors (list), world_violations (list), forced_plotting_score (0.0-1.0, 越高越生硬), style_consistency_score (0.0-1.0)"
            ))
        ])

        last_summary = state.memory_context.recent_summaries[-1] if state.memory_context.recent_summaries else "开篇"
        
        # Use format_messages instead of format
        messages = prompt.format_messages(
            draft=draft, 
            summary=last_summary,
            character_rules=character_rules,
            threads_str=threads_str,
            outline_context=outline_context,
            world_rules=world_rules_str,
            character_limits=character_limits
        )
        response = await self.llm.ainvoke(messages)
        
        content_str = normalize_llm_content(response.content)
        content_str = strip_think_tags(content_str)
        result = extract_json_from_text(content_str)
        
        if not result:
            return {
                "passed": False, 
                "score": 0.0, 
                "feedback": "审核系统解析失败，请检查模型输出格式", 
                "logical_errors": ["Parse Error"],
                "world_violations": []
            }
            
        return result

    async def _get_world_rules(self, state: NGEState) -> List[Dict]:
        """获取世界观规则 (简化版 WorldGuard 逻辑)"""
        from ..db.vector_store import VectorStore
        novel_id = state.current_novel_id
        rules = []
        
        # 从 NovelBible 中提取规则
        try:
            vector_store = VectorStore()
            bible_results = await vector_store.search(
                "世界观 规则 设定 体系 法则",
                model_class=NovelBible,
                top_k=5,
                novel_id=novel_id
            )
            
            for bible in bible_results:
                category = bible.get("category", "general")
                key = bible.get("key", "")
                content = bible.get("content", "")
                
                rule_type = self._categorize_world_rule(category, key)
                
                rules.append({
                    "rule_type": rule_type,
                    "rule_name": key,
                    "rule_content": content,
                    "is_absolute": category in ["core", "power_system", "magic", "fundamental"]
                })
                
        except Exception as e:
            logger.warning(f"获取世界规则失败: {e}")
        
        # 从 state.novel_bible 中补充
        if state.novel_bible and state.novel_bible.world_view:
            rules.append({
                "rule_type": "general",
                "rule_name": "世界观概述",
                "rule_content": state.novel_bible.world_view,
                "is_absolute": True
            })
            
        return rules
    
    def _categorize_world_rule(self, category: str, key: str) -> str:
        """分类世界规则"""
        key_lower = key.lower()
        
        if any(kw in key_lower for kw in ["修炼", "境界", "功法", "武功", "能力"]):
            return "power_system"
        if any(kw in key_lower for kw in ["地理", "地图", "地区", "城市"]):
            return "geography"
        if any(kw in key_lower for kw in ["科技", "技术", "机械", "装备"]):
            return "technology"
        if any(kw in key_lower for kw in ["魔法", "法术", "咒语", "阵法"]):
            return "magic"
        
        return "general"
    
    def _get_character_limits(self, state: NGEState) -> str:
        """获取角色能力限制"""
        limits = []
        
        for name, char in state.characters.items():
            limit_parts = [f"【{name}】"]
            
            # 技能限制
            if char.skills:
                limit_parts.append(f"已掌握技能：{', '.join(char.skills)}")
            else:
                limit_parts.append("暂无特殊技能")
            
            # 能力等级
            if hasattr(char, 'ability_levels') and char.ability_levels:
                abilities = []
                for skill, level in char.ability_levels.items():
                    if hasattr(level, 'level'):
                        abilities.append(f"{skill}(Lv{level.level})")
                if abilities:
                    limit_parts.append(f"能力等级：{', '.join(abilities)}")
            
            # 禁忌行为
            forbidden = state.antigravity_context.character_anchors.get(name, [])
            if forbidden:
                limit_parts.append(f"禁止：{', '.join(forbidden)}")
            
            limits.append("；".join(limit_parts))
        
        return "\n".join(limits) if limits else "无特殊限制"
    
    def _format_world_rules(self, rules: List[Dict]) -> str:
        """格式化世界规则"""
        if not rules:
            return "（无明确规则，请根据常识判断）"
        
        # 按类型分组
        grouped = {}
        for rule in rules:
            rule_type = rule["rule_type"]
            if rule_type not in grouped:
                grouped[rule_type] = []
            grouped[rule_type].append(rule)
        
        type_names = {
            "power_system": "能力体系",
            "geography": "地理设定",
            "technology": "科技水平",
            "magic": "魔法规则",
            "general": "通用设定",
        }
        
        formatted = []
        for rule_type, type_rules in grouped.items():
            type_name = type_names.get(rule_type, rule_type)
            formatted.append(f"\n【{type_name}】")
            
            for rule in type_rules[:2]:  # 每类最多2条
                absolute = "【绝对规则】" if rule.get("is_absolute") else ""
                formatted.append(f"- {rule['rule_name']}{absolute}：{rule['rule_content'][:150]}")
        
        return "\n".join(formatted)
