"""
WorldConsistencyGuard Agent 模块
负责世界观一致性检查和违规检测
确保生成内容不违背既定的世界观设定
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..schemas.state import NGEState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from ..db.vector_store import VectorStore
from ..db.models import NovelBible
from .base import BaseAgent


class WorldRuleType(BaseModel):
    """世界规则类型"""
    rule_type: str = Field(description="规则类型：power_system/geography/history/society/technology/magic")
    rule_name: str = Field(description="规则名称")
    rule_content: str = Field(description="规则内容")
    is_absolute: bool = Field(default=True, description="是否为绝对规则（不可违背）")
    exceptions: List[str] = Field(default_factory=list, description="例外情况")


class ViolationDetail(BaseModel):
    """违规详情"""
    violation_type: str = Field(description="违规类型")
    rule_violated: str = Field(description="违反的规则")
    content_excerpt: str = Field(description="违规内容摘录")
    severity: str = Field(description="严重程度：critical/major/minor")
    explanation: str = Field(description="违规说明")
    suggestion: str = Field(description="修正建议")


class ConsistencyCheckResult(BaseModel):
    """一致性检查结果"""
    is_consistent: bool = Field(description="是否一致")
    violations: List[ViolationDetail] = Field(default_factory=list, description="违规列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    overall_score: float = Field(ge=0.0, le=1.0, description="一致性评分")
    critical_count: int = Field(default=0, description="严重违规数量")
    needs_revision: bool = Field(default=False, description="是否需要修订")


class WorldConsistencyGuard(BaseAgent):
    """
    世界观一致性守护 Agent
    
    职责：
    1. 检查生成内容是否违背世界观设定
    2. 验证能力系统/魔法体系的使用是否合规
    3. 检测时间线和地理位置的逻辑错误
    4. 确保科技/社会背景的一致性
    """
    
    # 常见违规类型
    VIOLATION_TYPES = {
        "power_violation": "能力体系违规",
        "geography_violation": "地理设定违规",
        "timeline_violation": "时间线违规",
        "technology_violation": "科技设定违规",
        "society_violation": "社会制度违规",
        "magic_violation": "魔法规则违规",
        "character_capability": "角色能力越界",
        "item_misuse": "道具设定违规",
    }
    
    def __init__(self, temperature: Optional[float] = None):
        """初始化世界观一致性守护 Agent"""
        super().__init__(
            model_name="deepseek",  # 使用逻辑能力强的模型
            temperature=temperature or 0.2,  # 低温度保证准确性
            mock_responses=[
                json.dumps({
                    "is_consistent": True,
                    "violations": [],
                    "warnings": [],
                    "overall_score": 0.95,
                    "critical_count": 0,
                    "needs_revision": False
                })
            ]
        )
        self.result_parser = PydanticOutputParser(pydantic_object=ConsistencyCheckResult)
        self.vector_store = VectorStore()
        
        # 缓存世界规则
        self._rules_cache: Dict[int, List[WorldRuleType]] = {}
    
    async def process(self, state: NGEState, content: str = None, **kwargs) -> Dict[str, Any]:
        """处理一致性检查任务"""
        content = content or state.current_draft
        return await self.check_consistency(state, content)
    
    async def check_consistency(
        self,
        state: NGEState,
        content: str
    ) -> Dict[str, Any]:
        """
        检查内容的世界观一致性
        
        Args:
            state: 当前状态
            content: 待检查的内容
            
        Returns:
            检查结果
        """
        # 1. 获取世界观规则
        world_rules = await self._get_world_rules(state)
        
        # 2. 获取角色能力限制
        character_limits = self._get_character_limits(state)
        
        # 3. 构建检查提示词
        prompt = self._create_check_prompt()
        
        messages = prompt.format_messages(
            content=content[:6000],  # 限制长度
            world_rules=self._format_rules(world_rules),
            character_limits=character_limits,
            format_instructions=self.result_parser.get_format_instructions()
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            result_content = strip_think_tags(normalize_llm_content(response.content))
            
            result_json = extract_json_from_text(result_content)
            if isinstance(result_json, dict):
                # 计算严重违规数量
                violations = result_json.get("violations", [])
                critical_count = sum(
                    1 for v in violations 
                    if v.get("severity") == "critical"
                )
                result_json["critical_count"] = critical_count
                result_json["needs_revision"] = critical_count > 0
                
                return result_json
            
            return self._get_default_result()
            
        except Exception as e:
            print(f"WorldConsistencyGuard Error: {e}")
            return self._get_default_result()
    
    async def _get_world_rules(self, state: NGEState) -> List[WorldRuleType]:
        """获取世界观规则"""
        novel_id = state.current_novel_id
        
        # 检查缓存
        if novel_id in self._rules_cache:
            return self._rules_cache[novel_id]
        
        rules = []
        
        # 从 NovelBible 中提取规则
        try:
            bible_results = await self.vector_store.search(
                "世界观 规则 设定 体系 法则",
                model_class=NovelBible,
                top_k=10,
                novel_id=novel_id
            )
            
            for bible in bible_results:
                category = bible.get("category", "general")
                key = bible.get("key", "")
                content = bible.get("content", "")
                
                rule_type = self._categorize_rule(category, key)
                
                rules.append(WorldRuleType(
                    rule_type=rule_type,
                    rule_name=key,
                    rule_content=content,
                    is_absolute=self._is_absolute_rule(category)
                ))
                
        except Exception as e:
            print(f"获取世界规则失败: {e}")
        
        # 从 state.novel_bible 中补充
        if state.novel_bible:
            if state.novel_bible.world_view:
                rules.append(WorldRuleType(
                    rule_type="general",
                    rule_name="世界观概述",
                    rule_content=state.novel_bible.world_view,
                    is_absolute=True
                ))
            
            for key, value in state.novel_bible.core_settings.items():
                rules.append(WorldRuleType(
                    rule_type=self._categorize_rule("core", key),
                    rule_name=key,
                    rule_content=value,
                    is_absolute=True
                ))
        
        # 缓存结果
        self._rules_cache[novel_id] = rules
        
        return rules
    
    def _categorize_rule(self, category: str, key: str) -> str:
        """根据类别和关键词分类规则"""
        key_lower = key.lower()
        category_lower = category.lower()
        
        if any(kw in key_lower for kw in ["修炼", "境界", "功法", "武功", "能力"]):
            return "power_system"
        if any(kw in key_lower for kw in ["地理", "地图", "地区", "城市"]):
            return "geography"
        if any(kw in key_lower for kw in ["历史", "年代", "纪年", "朝代"]):
            return "history"
        if any(kw in key_lower for kw in ["社会", "阶级", "制度", "律法"]):
            return "society"
        if any(kw in key_lower for kw in ["科技", "技术", "机械", "装备"]):
            return "technology"
        if any(kw in key_lower for kw in ["魔法", "法术", "咒语", "阵法"]):
            return "magic"
        
        return "general"
    
    def _is_absolute_rule(self, category: str) -> bool:
        """判断是否为绝对规则"""
        absolute_categories = ["core", "power_system", "magic", "fundamental"]
        return category.lower() in absolute_categories
    
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
            if char.ability_levels:
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
    
    def _format_rules(self, rules: List[WorldRuleType]) -> str:
        """格式化规则列表"""
        if not rules:
            return "（无明确规则，请根据常识判断）"
        
        formatted = []
        
        # 按类型分组
        grouped = {}
        for rule in rules:
            if rule.rule_type not in grouped:
                grouped[rule.rule_type] = []
            grouped[rule.rule_type].append(rule)
        
        type_names = {
            "power_system": "能力体系",
            "geography": "地理设定",
            "history": "历史背景",
            "society": "社会制度",
            "technology": "科技水平",
            "magic": "魔法规则",
            "general": "通用设定",
        }
        
        for rule_type, type_rules in grouped.items():
            type_name = type_names.get(rule_type, rule_type)
            formatted.append(f"\n【{type_name}】")
            
            for rule in type_rules[:3]:  # 每类最多3条
                absolute = "【绝对规则】" if rule.is_absolute else ""
                formatted.append(f"- {rule.rule_name}{absolute}：{rule.rule_content[:200]}")
        
        return "\n".join(formatted)
    
    def _create_check_prompt(self) -> ChatPromptTemplate:
        """创建检查提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个严谨的世界观一致性审查员。\n"
                "你的任务是检查小说内容是否违背了既定的世界观设定。\n\n"
                "【检查维度】\n"
                "1. 能力体系：角色使用的能力是否超出其应有水平\n"
                "2. 地理设定：地点描述是否与设定一致\n"
                "3. 时间线：事件顺序是否合理\n"
                "4. 科技/魔法：使用的技术/魔法是否符合世界观\n"
                "5. 社会规则：人物行为是否符合社会背景\n\n"
                "【严重程度判定】\n"
                "- critical：严重违规，直接颠覆设定，必须修改\n"
                "- major：较大违规，影响可信度，建议修改\n"
                "- minor：轻微违规，可以接受但最好调整\n\n"
                "输出必须是严格的 JSON 格式。\n"
                "{format_instructions}"
            )),
            ("human", (
                "【世界观规则】\n{world_rules}\n\n"
                "【角色能力限制】\n{character_limits}\n\n"
                "【待检查内容】\n{content}\n\n"
                "请检查内容的世界观一致性。"
            ))
        ])
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            "is_consistent": True,
            "violations": [],
            "warnings": ["一致性检查未完成，请人工复核"],
            "overall_score": 0.8,
            "critical_count": 0,
            "needs_revision": False
        }
    
    def generate_revision_guide(self, result: Dict[str, Any]) -> str:
        """
        根据检查结果生成修订指南
        
        Args:
            result: 检查结果
            
        Returns:
            修订指南文本
        """
        if result.get("is_consistent", True):
            return ""
        
        parts = ["\n【世界观一致性修订要求】"]
        
        violations = result.get("violations", [])
        critical_violations = [v for v in violations if v.get("severity") == "critical"]
        major_violations = [v for v in violations if v.get("severity") == "major"]
        
        if critical_violations:
            parts.append("\n必须修正（严重违规）：")
            for v in critical_violations:
                parts.append(f"- {v.get('rule_violated', '未知规则')}：{v.get('suggestion', '请修正')}")
        
        if major_violations:
            parts.append("\n建议修正（较大违规）：")
            for v in major_violations[:3]:
                parts.append(f"- {v.get('rule_violated', '未知规则')}：{v.get('suggestion', '请调整')}")
        
        return "\n".join(parts)
    
    def clear_cache(self, novel_id: Optional[int] = None):
        """清除规则缓存"""
        if novel_id:
            self._rules_cache.pop(novel_id, None)
        else:
            self._rules_cache.clear()
