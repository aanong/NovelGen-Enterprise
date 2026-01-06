import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

load_dotenv()

# --- Defines the schemas for parsing ---

class ExtractedCharacter(BaseModel):
    name: str = Field(description="角色姓名")
    role: str = Field(description="角色定位，如主角、反派、配角")
    personality: str = Field(description="性格特征描述")
    background: str = Field(description="背景故事或设定")
    relationship_summary: str = Field(description="与其他角色的关系简述")

class ExtractedChapterOutline(BaseModel):
    chapter_number: int
    title: str = Field(description="章节标题，如果没有则自拟")
    scene_description: str = Field(description="核心场面和环境描述")
    key_conflict: str = Field(description="本章的核心冲突或事件")
    instruction: str = Field(description="给AI的写作指导，包含伏笔")

class ExtractedWorldView(BaseModel):
    category: str = Field(description="设定类别，如：修炼体系、地理环境、历史背景")
    key: str = Field(description="设定的特定名词，如：魂力、天斗帝国")
    content: str = Field(description="具体的设定规则内容")

class ExtractedStyle(BaseModel):
    tone: str = Field(description="整体基调，如：阴郁、热血、轻松")
    rhetoric: List[str] = Field(description="常用修辞或写作手法")
    keywords: List[str] = Field(description="关键词或高频词")
    example_sentence: str = Field(description="风格代表句")

class NovelSetupData(BaseModel):
    world_view_items: List[ExtractedWorldView]
    characters: List[ExtractedCharacter]
    outlines: List[ExtractedChapterOutline]
    style: ExtractedStyle

# --- Learner Agent Implementation ---

class LearnerAgent:
    """
    LearnerAgent: 负责从非结构化文本中提取结构化的小说设定。
    使用 Deepseek (逻辑推理强) 来进行理解和拆解。
    """
    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-r1:7b",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="http://localhost:11434/v1",
            temperature=0.1 # 提取任务需要低随机性
        )
        self.parser = PydanticOutputParser(pydantic_object=NovelSetupData)

    async def parse_document(self, content: str) -> NovelSetupData:
        """
        全量解析文档内容。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的文学数据分析师。你的任务是读取用户提供的小说设定文档，"
                "并将其拆解为用于生成的结构化数据。\n\n"
                "文档可能包含：大纲、人物小传、世界观设定、文风描述。\n"
                "你需要智能地识别这些部分，即使它们没有清晰的标题。\n"
                "如果某个字段文档未提供，请根据上下文合理推断或填入'未定义'。\n\n"
                "{format_instructions}"
            )),
            ("human", "请解析以下文档：\n\n{content}")
        ])

        chain = prompt | self.llm | self.parser
        
        try:
            # 对于非常长的文档，可能需要分块处理。这里暂定为直接处理(Deepseek V3 context window is large enough)
            result = await chain.ainvoke({
                "content": content,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"❌ 解析文档失败: {e}")
            raise e
