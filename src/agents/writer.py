import os
import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from ..config import Config
from ..utils import strip_think_tags, normalize_llm_content
from dotenv import load_dotenv

load_dotenv()

class WriterAgent:
    """
    Writer Agent (DeepSeek -> Gemini): 负责正文撰写与文风模仿。
    Switching to Gemini for stability in this environment.
    """
    def __init__(self):
        if Config.model.GEMINI_MODEL == "mock":
            from ..utils import MockChatModel
            self.llm = MockChatModel(responses=[
                "当前遵循：Normal 场景\n这是一个用于测试的章节正文。主角李青云站在青云山巅，俯瞰着云海。"
            ])
        elif "localhost" in Config.model.DEEPSEEK_API_BASE or Config.model.DEEPSEEK_API_KEY == "ollama":
            self.llm = ChatGoogleGenerativeAI(
                model=Config.model.GEMINI_MODEL,
                google_api_key=Config.model.GEMINI_API_KEY,
                temperature=Config.model.GEMINI_TEMPERATURE
            )
        else:
            self.llm = ChatOpenAI(
                model=Config.model.DEEPSEEK_MODEL,
                openai_api_key=Config.model.DEEPSEEK_API_KEY,
                openai_api_base=Config.model.DEEPSEEK_API_BASE,
                temperature=Config.model.GEMINI_TEMPERATURE
            )

    async def write_chapter(self, state: NGEState, plan_instruction: str) -> str:
        """
        撰写章节正文。
        注入文风特征和角色设定。
        遵循 Antigravity Rules: 2.1 (人物锚定), 6.1 (场景约束), 6.2 (验证前缀)
        """
        if state.current_plot_index >= len(state.plot_progress):
            current_point_title = "后续章节"
            current_point_desc = "跟随前文剧情自然发展"
        else:
            current_point = state.plot_progress[state.current_plot_index]
            current_point_title = current_point.title
            current_point_desc = current_point.description

        style = state.novel_bible.style_description
        
        # 1. 构建 System Prompt
        style_prompt = ""
        if style:
            style_prompt = (
                f"文风规范：\n"
                f"- 句式：{style.rhythm_description}，{style.dialogue_narration_ratio} 的对话旁白比。\n"
                f"- 修辞偏好：{', '.join(style.common_rhetoric)}。\n"
                f"- 情绪基调：{style.emotional_tone}。\n"
                f"- 核心词汇：{', '.join(style.vocabulary_preference)}。\n"
            )

        # 2. Rule 2.1: 人物灵魂锚定
        character_context = []
        for name, c in state.characters.items():
            forbidden = state.antigravity_context.character_anchors.get(name, [])
            forbidden_str = f"【禁止行为：{', '.join(forbidden)}】" if forbidden else ""
            
            skills_str = f"技能:{', '.join(c.skills)}" if c.skills else ""
            assets_list = [f"{k}: {v}" for k, v in c.assets.items()]
            assets_str = f"资产:[{', '.join(assets_list)}]" if assets_list else ""
            items_str = f"持有物:{', '.join([i.name for i in c.inventory])}" if c.inventory else ""
            
            char_info = [
                f"- {name}: {c.personality_traits.get('role', '')}",
                f"性格:{c.personality_traits.get('personality', '')}",
                f"状态:{c.current_mood}"
            ]
            if skills_str: char_info.append(skills_str)
            if assets_str: char_info.append(assets_str)
            if items_str: char_info.append(items_str)
            if forbidden_str: char_info.append(forbidden_str)
            
            character_context.append(", ".join(char_info))
        
        # 3. Rule 6.1: 场景化强制约束
        scene_constraints = state.antigravity_context.scene_constraints
        scene_type = scene_constraints.get("scene_type", "Normal")
        scene_rules = ""
        
        cfg_constraints = Config.antigravity.SCENE_CONSTRAINTS.get(scene_type, {})
        if cfg_constraints:
            pref = cfg_constraints.get("preferred_style", "")
            forb = ", ".join(cfg_constraints.get("forbidden_patterns", []))
            scene_rules = f"\n【场景强制约束 - {scene_type}】\n- 风格要求：{pref}\n- 禁忌模式：{forb}"

        # 4. RAG & History
        refined_context_str = ""
        if state.refined_context:
            refined_context_str = "\n【相关背景与细节设定】\n" + "\n".join(state.refined_context) + "\n"

        # 提取全局伏笔
        active_threads = state.memory_context.global_foreshadowing
        threads_str = "\n".join([f"- {t}" for t in active_threads]) if active_threads else "无"

        history_summary = '\n'.join(state.memory_context.recent_summaries)

        prompt = ChatPromptTemplate.from_messages([
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
                "- Rule 6.2: 在回复的开头必须以“当前遵循：[场景准则]”作为验证（如：当前遵循：Action 场景，短促动词，禁用长句）。\n"
                "- 绝对禁止让角色做出其【禁止行为】中的动作。\n"
                "- 绝对遵守场景强制约束，这是文风的一致性保证。\n"
                "- 保持角色心境与当前状态一致。\n"
                "- 此前埋下的伏笔若有机会，请自然地推进或回收。\n"
            )),
            ("human", (
                "当前剧情：{current_point_title}\n"
                "核心内容：{current_point_desc}\n"
                "具体指令：{plan_instruction}\n\n"
                "请开始撰写正文。字数建议在 2500 字以上，确保情节饱满，文风统一。"
            ))
        ])

        messages = prompt.format_messages(
            style_prompt=style_prompt,
            character_context=chr(10).join(character_context),
            scene_rules=scene_rules,
            refined_context_str=refined_context_str,
            history_summary=history_summary,
            threads_str=threads_str,
            current_point_title=current_point_title,
            current_point_desc=current_point_desc,
            plan_instruction=plan_instruction
        )
        response = await self.llm.ainvoke(messages)
        content = normalize_llm_content(response.content)
        content = strip_think_tags(content)
        
        # Rule 6.2 & 4.1: 清理验证前缀和思考标签
        content = re.sub(r'^当前遵循：.*?\n', '', content).strip()
        
        return content
