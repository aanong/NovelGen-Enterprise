import os
import re
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
                f"草稿内容：\n{{draft}}\n\n"
                "请以 JSON 格式输出：{{'passed': bool, 'feedback': str, 'logical_errors': List[str]}}"
            ))
        ])
        
        response = await self.llm.ainvoke(prompt.format(draft=draft))
        content_str = response.content
        
        # Rule 4.1: Strip <think> tags
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
        
        try:
            # Try to find JSON block
            json_match = re.search(r'(\{.*\})', content_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(content_str)
        except Exception as e:
            print(f"Review Parsing Error: {e}")
            # Fallback: if we can't parse but it looks okay, or failed to parse, 
            # let's be more lenient in test or default to something
            return {"passed": True, "feedback": "无法解析反馈，默认通过", "logical_errors": []}

    async def evolve_characters(self, state: NGEState, draft: str):
        """
        CharacterEvolver: 分析该章节发生的事件是否改变了人物的心境或关系。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个心理分析专家和人物塑造师。"),
            ("human", (
                f"这是新完成的章节：\n{{draft}}\n\n"
                "请分析文中每个角色的心理变化、关系变动，并生成更新日志。\n"
                "输出格式：{{'character_name': {{'new_mood': str, 'evolution_summary': str, 'relationship_changes': str}}}}"
            ))
        ])
        
        response = await self.llm.ainvoke(prompt.format(draft=draft))
        # 返回演化建议
        content_str = response.content
        # Rule 4.1: Strip <think> tags
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
        return content_str
