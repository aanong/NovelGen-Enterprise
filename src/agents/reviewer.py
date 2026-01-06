import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState, character_state
from dotenv import load_dotenv

load_dotenv()

class ReviewerAgent:
    """
    Reviewer Agent (Deepseek): 负责逻辑审查、人物OOC检查及状态演化。
    """
    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-r1:7b",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="http://localhost:11434/v1",
            temperature=0.1 # 审查时需要高精度
        )

    async def review_draft(self, state: NGEState, draft: str) -> dict:
        """
        检查生成的正文是否有逻辑漏洞或人物 OOC。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个极其敏锐的小说评论家和逻辑学家。"),
            ("human", (
                "请审查以下小说章节草稿，并给出详细反馈。\n"
                "审查标准：\n1. 剧情是否符合当前大纲？\n2. 人物言行是否符合既定性格 (MBTI/背景)？\n3. 是否有前后矛盾的逻辑硬伤？\n\n"
                f"草稿内容：\n{draft}\n\n"
                "请以 JSON 格式输出：{'passed': bool, 'feedback': str, 'logical_errors': List[str]}"
            ))
        ])
        
        response = await self.llm.ainvoke(prompt.format())
        # 简单解析 JSON 字符串 (实际生产中应使用 OutputParser)
        try:
            return json.loads(response.content)
        except:
            return {"passed": False, "feedback": "解析反馈失败", "logical_errors": ["JSON 解析错误"]}

    async def evolve_characters(self, state: NGEState, draft: str):
        """
        CharacterEvolver: 分析该章节发生的事件是否改变了人物的心境或关系。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个心理分析专家和人物塑造师。"),
            ("human", (
                f"这是新完成的章节：\n{draft}\n\n"
                "请分析文中每个角色的心理变化、关系变动，并生成更新日志。\n"
                "输出格式：{'character_name': {'new_mood': str, 'evolution_summary': str, 'relationship_changes': str}}"
            ))
        ])
        
        response = await self.llm.ainvoke(prompt.format())
        # 返回演化建议
        return response.content
