import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from dotenv import load_dotenv

load_dotenv()

class WriterAgent:
    """
    Writer Agent (Gemini): 负责正文撰写与文风模仿。
    利用 Gemini 的长上下文窗口和文风模仿能力。
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.8, # 创作时温提高以增加灵活性
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    async def write_chapter(self, state: NGEState, plan_instruction: str) -> str:
        """
        撰写章节正文。
        注入文风特征和角色设定。
        """
        current_point = state.plot_progress[state.current_plot_index]
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

        character_context = "\n".join([
            f"- {c.name}: {c.personality_traits.get('mbti', '')}, 状态:{c.current_mood}" 
            for c in state.characters.values()
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极具天赋的长篇小说作家。擅长细腻的描写和深刻的人物塑造。\n"
                f"{style_prompt}\n"
                "当前章节相关人物信息：\n"
                f"{character_context}\n"
                "历史背景摘要：\n"
                f"{' | '.join(state.memory_context.recent_summaries[-3:])}\n"
            )),
            ("human", (
                f"当前剧情点：{current_point.title}\n"
                f"剧情要求：{current_point.description}\n"
                f"写作指令：{plan_instruction}\n\n"
                "请开始撰写正文，保持字数充足（建议2000字以上），节奏稳健。"
            ))
        ])

        chain = prompt | self.llm
        response = await chain.ainvoke({})
        return response.content
