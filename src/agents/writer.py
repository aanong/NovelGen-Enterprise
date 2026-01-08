import os
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from ..config import Config
from ..utils import strip_think_tags
from dotenv import load_dotenv

load_dotenv()

class WriterAgent:
    """
    Writer Agent (Gemini): 负责正文撰写与文风模仿。
    利用 Gemini 的长上下文窗口和文风模仿能力。
    遵循 Rule 1: Gemini 为王（正文生成核心）
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=Config.model.GEMINI_MODEL,
            temperature=Config.model.GEMINI_TEMPERATURE,
            google_api_key=Config.model.GEMINI_API_KEY
        )

    async def write_chapter(self, state: NGEState, plan_instruction: str) -> str:
        """
        撰写章节正文。
        注入文风特征和角色设定。
        遵循 Antigravity Rules: 2.1 (人物锚定), 6.1 (场景约束)
        """
        if state.current_plot_index >= len(state.plot_progress):
            current_point_title = "后续章节"
            current_point_desc = "跟随前文剧情自然发展"
        else:
            current_point = state.plot_progress[state.current_plot_index]
            current_point_title = current_point.title
            current_point_desc = current_point.description

        style = state.novel_bible.style_description
        
        # 构建 System Prompt，动态注入文风特征
        style_prompt = ""
        if style:
            style_prompt = (
                f"文风规范：\n"
                f"- 句式：{style.rhythm_description}，{style.dialogue_narration_ratio} 的对话旁白比。\n"
                f"- 修辞偏好：{', '.join(style.common_rhetoric)}。\n"
                f"- 情绪基调：{style.emotional_tone}。\n"
                f"- 核心词汇：{', '.join(style.vocabulary_preference)}。\n"
            )

        # Rule 2.1: 人物灵魂锚定 - 注入禁忌行为
        character_context = []
        for name, c in state.characters.items():
            forbidden = state.antigravity_context.character_anchors.get(name, [])
            forbidden_str = f"【禁止行为：{', '.join(forbidden)}】" if forbidden else ""
            character_context.append(
                f"- {name}: {c.personality_traits.get('role', '')}, 性格:{c.personality_traits.get('personality', '')}, 状态:{c.current_mood} {forbidden_str}"
            )
        
        # Rule 6.1: 场景化强制约束
        scene_constraints = state.antigravity_context.scene_constraints
        scene_type = scene_constraints.get("scene_type", "Normal")
        scene_rules = ""
        
        cfg_constraints = Config.antigravity.SCENE_CONSTRAINTS.get(scene_type, {})
        if cfg_constraints:
            pref = cfg_constraints.get("preferred_style", "")
            forb = ", ".join(cfg_constraints.get("forbidden_patterns", []))
            scene_rules = f"\n【场景强制约束 - {scene_type}】\n- 风格要求：{pref}\n- 禁忌模式：{forb}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极具天赋的长篇小说作家。擅长细腻的描写和深刻的人物塑造。\n"
                f"{style_prompt}\n"
                "当前章节相关人物信息：\n"
                f"{chr(10).join(character_context)}\n"
                f"{scene_rules}\n"
                "历史背景摘要：\n"
                f"{' | '.join(state.memory_context.recent_summaries[-3:])}\n"
                "\n【核心执行准则】\n"
                "- 绝对禁止让角色做出其【禁止行为】中的动作。\n"
                "- 绝对遵守场景强制约束，这是文风的一致性保证。\n"
                "- 保持角色心境与当前状态一致。\n"
            )),
            ("human", (
                f"当前剧情：{current_point_title}\n"
                f"核心内容：{current_point_desc}\n"
                f"具体指令：{plan_instruction}\n\n"
                "请开始撰写正文。字数建议在 2500 字以上，确保情节饱满，文风统一。"
            ))
        ])

        response = await self.llm.ainvoke(prompt.format())
        content = strip_think_tags(response.content)
        
        return content
