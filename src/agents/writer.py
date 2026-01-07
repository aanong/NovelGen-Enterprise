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
            model="models/gemini-3-pro-preview",
            temperature=0.8,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    async def write_chapter(self, state: NGEState, plan_instruction: str) -> str:
        """
        撰写章节正文。
        注入文风特征和角色设定。
        遵循 Antigravity Rules: 2.1 (人物锚定), 6.1 (场景约束)
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

        # Rule 2.1: 人物灵魂锚定 - 注入禁忌行为
        character_context = []
        for c in state.characters.values():
            forbidden = state.antigravity_context.character_anchors.get(c.name, [])
            forbidden_str = f"【禁忌行为】{', '.join(forbidden)}" if forbidden else ""
            character_context.append(
                f"- {c.name}: {c.personality_traits.get('mbti', '')}, 状态:{c.current_mood} {forbidden_str}"
            )
        
        # Rule 6.1: 场景化强制约束
        scene_constraints = state.antigravity_context.scene_constraints
        scene_type = scene_constraints.get("scene_type", "Normal")
        scene_rules = ""
        
        if scene_type == "Action":
            scene_rules = "\n【场景约束】动作场景：禁用超过20字的长句，多用短促动词。"
        elif scene_type == "Emotional":
            scene_rules = "\n【场景约束】情感场景：禁用连续动词堆叠，注重心理描写。"
        elif scene_type == "Dialogue":
            scene_rules = "\n【场景约束】对话场景：对话占比需达到60%以上，符合人物语气。"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极具天赋的长篇小说作家。擅长细腻的描写和深刻的人物塑造。\n"
                f"{style_prompt}\n"
                "当前章节相关人物信息：\n"
                f"{chr(10).join(character_context)}\n"
                f"{scene_rules}\n"
                "历史背景摘要：\n"
                f"{' | '.join(state.memory_context.recent_summaries[-3:])}\n"
                "\n【反重力规则警告】\n"
                "- 严禁让角色做出【禁忌行为】中列出的动作\n"
                "- 严禁自行改变人物性格，性格转变需由 Architect 决策\n"
                "- 必须遵守场景约束规则\n"
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
        
        # Rule 4.1: 过滤 <think> 标签（如果使用 DeepSeek）
        import re
        content = response.content
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        return content
