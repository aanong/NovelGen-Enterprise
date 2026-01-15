"""
WritingTechniqueAdvisor Agent 模块
负责写作技法分析与具体写法指导
提供场景化的写作建议和技法推荐
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..schemas.state import NGEState
from ..schemas.style import (
    StyleFeatures, WritingTechnique, AtmosphereControl, 
    AtmosphereType, DescriptionType, SCENE_TEMPLATES
)
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from .base import BaseAgent


class TechniqueRecommendation(BaseModel):
    """写作技法推荐"""
    technique_name: str = Field(description="技法名称")
    priority: int = Field(ge=1, le=5, description="优先级 1-5，5最高")
    reason: str = Field(description="推荐理由")
    application_guide: str = Field(description="具体应用指导")
    example: str = Field(description="示例片段")


class AtmosphereGuide(BaseModel):
    """氛围渲染指导"""
    atmosphere_type: str = Field(description="氛围类型")
    keywords: List[str] = Field(description="渲染关键词")
    forbidden_words: List[str] = Field(description="破坏氛围的词汇")
    sensory_focus: List[str] = Field(description="强调的感官")
    color_hints: List[str] = Field(description="色调提示")
    rhythm_guide: str = Field(description="节奏指导")


class DescriptionGuide(BaseModel):
    """描写指导"""
    description_type: str = Field(description="描写类型")
    proportion: float = Field(ge=0.0, le=1.0, description="建议占比")
    key_points: List[str] = Field(description="描写要点")
    avoid_patterns: List[str] = Field(description="避免的模式")


class WritingAdvice(BaseModel):
    """完整的写作建议"""
    scene_analysis: str = Field(description="场景分析")
    recommended_techniques: List[TechniqueRecommendation] = Field(description="推荐技法")
    atmosphere_guide: AtmosphereGuide = Field(description="氛围指导")
    description_guides: List[DescriptionGuide] = Field(description="描写指导")
    perspective_advice: str = Field(description="视角建议")
    pacing_advice: str = Field(description="节奏建议")
    key_warnings: List[str] = Field(default_factory=list, description="关键警告")


class WritingTechniqueAdvisor(BaseAgent):
    """
    写作技法顾问 Agent
    
    职责：
    1. 分析当前场景特征，推荐适合的写作技法
    2. 提供氛围渲染的具体指导
    3. 给出描写类型的平衡建议
    4. 提供视角和节奏的专业建议
    """
    
    # 写作技法库
    TECHNIQUES = {
        "白描": {
            "description": "用最简练的笔墨，不加渲染烘托，抓住事物特征进行描写",
            "best_for": ["动作场景", "紧张时刻", "人物特写"],
            "avoid_in": ["需要渲染氛围", "情感高潮"],
            "example": "他抬手。剑落。血溅三尺。"
        },
        "细描": {
            "description": "精雕细刻，层层铺垫，细致入微地描写",
            "best_for": ["环境描写", "人物出场", "重要道具"],
            "avoid_in": ["战斗场景", "快节奏段落"],
            "example": "那柄剑静静地悬挂在墙上，剑鞘上雕刻着繁复的云纹..."
        },
        "蒙太奇": {
            "description": "通过镜头组接、画面切换来表现时空转换或内心活动",
            "best_for": ["时间跳跃", "回忆穿插", "对比呈现"],
            "avoid_in": ["需要连贯叙事", "初次场景建立"],
            "example": "十年前的夏天。蝉鸣。少年的笑脸。——眼前，只剩一座孤坟。"
        },
        "意识流": {
            "description": "模仿人的意识流动，打破时空限制，展现内心世界",
            "best_for": ["心理描写", "情感爆发", "迷幻场景"],
            "avoid_in": ["需要清晰叙事", "打斗场面"],
            "example": "为什么……不对，不该是这样……母亲的脸，老师的话，那天的雨……"
        },
        "留白": {
            "description": "故意不说透，留给读者想象空间",
            "best_for": ["悬念制造", "情感含蓄", "结局暗示"],
            "avoid_in": ["需要明确交代", "逻辑关键点"],
            "example": "他没有回答，只是望向远方。很久，很久。"
        },
        "五感描写": {
            "description": "调动视觉、听觉、触觉、嗅觉、味觉进行全方位描写",
            "best_for": ["环境渲染", "氛围营造", "沉浸体验"],
            "avoid_in": ["快节奏场景", "对话密集段落"],
            "example": "空气中弥漫着血腥味。寒风刺骨。远处，钟声沉闷地响起。"
        },
        "对比": {
            "description": "通过事物的对照突出特征或主题",
            "best_for": ["人物塑造", "主题升华", "情感反差"],
            "avoid_in": ["平淡叙事", "单一情绪"],
            "example": "昨日座上宾，今朝阶下囚。"
        },
        "象征": {
            "description": "用具体事物代表抽象概念",
            "best_for": ["主题深化", "情感暗示", "文学性表达"],
            "avoid_in": ["直白叙事", "说明性文字"],
            "example": "那盏灯终于熄灭了，连同他心中最后的希望。"
        },
    }
    
    # 氛围模板
    ATMOSPHERE_TEMPLATES = {
        AtmosphereType.TENSE: {
            "keywords": ["压抑", "窒息", "紧绷", "阴影", "沉默", "凝滞"],
            "forbidden": ["轻松", "愉快", "温暖", "明亮"],
            "sensory": ["听觉（心跳、呼吸）", "触觉（冷汗、僵硬）"],
            "colors": ["黑", "灰", "暗红"],
            "rhythm": "短句为主，句间停顿，如屏息"
        },
        AtmosphereType.HORROR: {
            "keywords": ["阴森", "诡异", "扭曲", "腐烂", "阴冷", "窥视"],
            "forbidden": ["温馨", "美好", "阳光"],
            "sensory": ["听觉（怪声）", "嗅觉（腐臭）", "触觉（阴冷）"],
            "colors": ["惨白", "腐绿", "血红", "漆黑"],
            "rhythm": "长短交替，突然停顿，如心惊"
        },
        AtmosphereType.WARM: {
            "keywords": ["柔和", "温暖", "安心", "宁静", "守护", "归属"],
            "forbidden": ["冷漠", "恐惧", "紧张"],
            "sensory": ["触觉（温暖）", "嗅觉（香气）", "视觉（柔光）"],
            "colors": ["暖黄", "橙红", "米白"],
            "rhythm": "舒缓绵长，如流水"
        },
        AtmosphereType.MELANCHOLY: {
            "keywords": ["萧索", "落寞", "飘零", "遗憾", "褪色", "远去"],
            "forbidden": ["热闹", "欢快", "明艳"],
            "sensory": ["视觉（灰暗）", "听觉（寂静）"],
            "colors": ["灰蓝", "枯黄", "褪色"],
            "rhythm": "悠长低回，如叹息"
        },
        AtmosphereType.EPIC: {
            "keywords": ["壮阔", "磅礴", "震撼", "永恒", "传说", "不朽"],
            "forbidden": ["琐碎", "平庸", "渺小"],
            "sensory": ["视觉（宏大）", "听觉（战鼓）"],
            "colors": ["金", "血红", "苍青"],
            "rhythm": "句式恢弘，气势如虹"
        },
    }
    
    def __init__(self, temperature: Optional[float] = None):
        """初始化写作技法顾问"""
        super().__init__(
            model_name="gemini",
            temperature=temperature or 0.6,
            mock_responses=[
                json.dumps({
                    "scene_analysis": "当前为战斗场景",
                    "recommended_techniques": [
                        {"technique_name": "白描", "priority": 5, "reason": "战斗需要简洁有力", 
                         "application_guide": "用短句描写动作", "example": "剑落。血溅。"}
                    ],
                    "atmosphere_guide": {
                        "atmosphere_type": "tense",
                        "keywords": ["紧张", "压抑"],
                        "forbidden_words": ["轻松"],
                        "sensory_focus": ["听觉"],
                        "color_hints": ["暗红"],
                        "rhythm_guide": "短句急促"
                    },
                    "description_guides": [
                        {"description_type": "action", "proportion": 0.6, 
                         "key_points": ["动作连贯"], "avoid_patterns": ["冗长描写"]}
                    ],
                    "perspective_advice": "保持第三人称限制视角",
                    "pacing_advice": "节奏紧凑",
                    "key_warnings": []
                })
            ]
        )
        self.advice_parser = PydanticOutputParser(pydantic_object=WritingAdvice)
    
    async def process(self, state: NGEState, **kwargs) -> Dict[str, Any]:
        """处理写作技法建议任务"""
        return await self.advise(state)
    
    async def advise(self, state: NGEState) -> Dict[str, Any]:
        """
        分析场景并提供写作建议
        
        Args:
            state: 当前状态
            
        Returns:
            写作建议结果
        """
        # 获取场景类型
        scene_type = state.antigravity_context.scene_constraints.get("scene_type", "Normal")
        
        # 构建场景描述
        scene_description = self._build_scene_description(state)
        
        # 获取预设模板（如果有）
        template_hint = ""
        if scene_type in SCENE_TEMPLATES:
            template = SCENE_TEMPLATES[scene_type]
            template_hint = f"\n参考模板：{template.rhythm_guidance}，技法推荐：{', '.join(template.technique_recommendations)}"
        
        prompt = self._create_advice_prompt()
        
        messages = prompt.format_messages(
            scene_description=scene_description,
            scene_type=scene_type,
            techniques_library=self._format_techniques(),
            template_hint=template_hint,
            format_instructions=self.advice_parser.get_format_instructions()
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            content = strip_think_tags(normalize_llm_content(response.content))
            
            result_json = extract_json_from_text(content)
            if isinstance(result_json, dict):
                return result_json
            
            raise ValueError("无法解析写作建议")
            
        except Exception as e:
            print(f"WritingTechniqueAdvisor Error: {e}")
            return self._get_default_advice(scene_type)
    
    def _build_scene_description(self, state: NGEState) -> str:
        """构建场景描述"""
        parts = []
        
        # 当前剧情点
        if state.current_plot_index < len(state.plot_progress):
            plot = state.plot_progress[state.current_plot_index]
            parts.append(f"剧情：{plot.title} - {plot.description}")
        
        # 涉及人物
        if state.characters:
            chars = []
            for name, char in list(state.characters.items())[:3]:
                mood = char.current_mood
                chars.append(f"{name}({mood})")
            parts.append(f"人物：{', '.join(chars)}")
        
        # 规划指令
        if state.review_feedback:
            parts.append(f"规划：{state.review_feedback[:200]}")
        
        return "\n".join(parts)
    
    def _format_techniques(self) -> str:
        """格式化技法库"""
        lines = []
        for name, info in self.TECHNIQUES.items():
            lines.append(f"- {name}：{info['description']}")
        return "\n".join(lines)
    
    def _create_advice_prompt(self) -> ChatPromptTemplate:
        """创建建议提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "你是一位资深的文学写作导师，精通各种写作技法和文学表现手法。\n"
                "你的任务是根据当前场景，提供专业的写作技法建议。\n\n"
                "【可用技法库】\n{techniques_library}\n\n"
                "【输出要求】\n"
                "1. 分析场景特征，选择最合适的技法\n"
                "2. 提供具体的氛围渲染指导\n"
                "3. 给出描写类型的比例建议\n"
                "4. 指出关键警告（避免的错误）\n\n"
                "输出必须是严格的 JSON 格式。\n"
                "{format_instructions}"
            )),
            ("human", (
                "【场景信息】\n{scene_description}\n\n"
                "【场景类型】{scene_type}{template_hint}\n\n"
                "请提供详细的写作技法建议。"
            ))
        ])
    
    def _get_default_advice(self, scene_type: str) -> Dict[str, Any]:
        """获取默认建议"""
        template = SCENE_TEMPLATES.get(scene_type, SCENE_TEMPLATES.get("Description"))
        
        return {
            "scene_analysis": f"当前为{scene_type}场景",
            "recommended_techniques": [
                {
                    "technique_name": template.technique_recommendations[0] if template.technique_recommendations else "白描",
                    "priority": 4,
                    "reason": "适合当前场景类型",
                    "application_guide": template.rhythm_guidance,
                    "example": template.example_snippet
                }
            ],
            "atmosphere_guide": {
                "atmosphere_type": "neutral",
                "keywords": template.vocabulary_focus[:3] if template.vocabulary_focus else [],
                "forbidden_words": template.taboos[:2] if template.taboos else [],
                "sensory_focus": ["视觉", "听觉"],
                "color_hints": [],
                "rhythm_guide": template.rhythm_guidance
            },
            "description_guides": [],
            "perspective_advice": "保持一致的叙事视角",
            "pacing_advice": template.rhythm_guidance,
            "key_warnings": template.taboos[:2] if template.taboos else []
        }
    
    def generate_technique_prompt(self, advice: Dict[str, Any]) -> str:
        """
        根据建议生成供 Writer 使用的技法提示词
        
        Args:
            advice: 写作建议
            
        Returns:
            格式化的技法提示词
        """
        parts = ["\n【写作技法指导】"]
        
        # 推荐技法
        techniques = advice.get("recommended_techniques", [])
        if techniques:
            tech_names = [t.get("technique_name", "") for t in techniques[:3]]
            parts.append(f"推荐技法：{', '.join(tech_names)}")
            
            # 首要技法的应用指导
            if techniques:
                main_tech = techniques[0]
                parts.append(f"核心应用：{main_tech.get('application_guide', '')}")
        
        # 氛围指导
        atm = advice.get("atmosphere_guide", {})
        if atm:
            keywords = atm.get("keywords", [])
            if keywords:
                parts.append(f"氛围关键词：{', '.join(keywords[:5])}")
            
            forbidden = atm.get("forbidden_words", [])
            if forbidden:
                parts.append(f"氛围禁忌词：{', '.join(forbidden[:3])}")
            
            rhythm = atm.get("rhythm_guide", "")
            if rhythm:
                parts.append(f"节奏：{rhythm}")
        
        # 关键警告
        warnings = advice.get("key_warnings", [])
        if warnings:
            parts.append(f"警告：{'; '.join(warnings[:2])}")
        
        return "\n".join(parts)
    
    def get_atmosphere_control(self, atmosphere_type: AtmosphereType) -> AtmosphereControl:
        """
        获取预定义的氛围控制配置
        
        Args:
            atmosphere_type: 氛围类型
            
        Returns:
            氛围控制配置
        """
        template = self.ATMOSPHERE_TEMPLATES.get(atmosphere_type, {})
        
        return AtmosphereControl(
            target_atmosphere=atmosphere_type,
            atmosphere_keywords=template.get("keywords", []),
            forbidden_words=template.get("forbidden", []),
            sensory_emphasis=template.get("sensory", ["视觉"]),
            color_palette=template.get("colors", []),
            rhythm_hint=template.get("rhythm", "")
        )
