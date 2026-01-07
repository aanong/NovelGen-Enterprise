import os
import re
import json

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

        # We manually process the response to handle R1's <think> tags and potential parsing issues
        input_data = {
            "content": content,
            "format_instructions": self.parser.get_format_instructions()
        }
        
        prompt_value = prompt.format_prompt(**input_data)
        response = await self.llm.ainvoke(prompt_value.to_messages())
        content_str = response.content
        
        # Rule 4.1: Strip <think> tags
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
        
        try:
            # Try standard parsing first
            result = self.parser.parse(content_str)
            return result
        except Exception as e:
            print(f"⚠️ 初始解析失败，尝试深度修复 JSON 格式...")
            # Try to find JSON block
            json_match = re.search(r'(\{.*\})', content_str, re.DOTALL)
            if json_match:
                try:
                    # langgraph/langchain might have already partially cleaned it, 
                    # but let's be sure we get the JSON part
                    json_text = json_match.group(1)
                    raw_json = json.loads(json_text)
                    
                    # 1. Remap common mismatches (Fuzzy)
                    for k in list(raw_json.keys()):
                        k_low = k.lower()
                        if ("chapter" in k_low or "outline" in k_low or "章节" in k_low) and "outlines" not in raw_json:
                            raw_json["outlines"] = raw_json.pop(k)
                        elif ("style" in k_low or k_low == "text") and "style" not in raw_json:
                            raw_json["style"] = raw_json.pop(k)
                        elif ("world" in k_low or "view" in k_low) and "world_view_items" not in raw_json:
                            raw_json["world_view_items"] = raw_json.pop(k)
                        elif ("character" in k_low) and "characters" not in raw_json:
                            raw_json["characters"] = raw_json.pop(k)
                    
                    # 2. Fix characters
                    if "characters" in raw_json:
                        for char in raw_json["characters"]:
                            if "relationship_summary" not in char:
                                char["relationship_summary"] = "暂无明确关系说明"
                    else:
                        raw_json["characters"] = []
                    
                    # 3. Fix outlines
                    if "outlines" in raw_json:
                        for outline in raw_json["outlines"]:
                            # Inner remapping
                            for ok in list(outline.keys()):
                                ok_low = ok.lower()
                                if "desc" in ok_low and "scene_description" not in outline:
                                    outline["scene_description"] = outline.pop(ok)
                                elif "conflict" in ok_low and "key_conflict" not in outline:
                                    outline["key_conflict"] = outline.pop(ok)
                                elif "instruction" in ok_low and "instruction" not in outline:
                                    pass # already good
                            
                            if "instruction" not in outline:
                                outline["instruction"] = "请按照情节大纲进行创作，注意角色性格的一致性。"
                            if "key_conflict" not in outline:
                                outline["key_conflict"] = "核心冲突待展开"
                            if "title" not in outline:
                                outline["title"] = f"第 {outline.get('chapter_number', '?')} 章"
                            if "scene_description" not in outline:
                                outline["scene_description"] = "描述待补充"
                            if "chapter_number" not in outline:
                                outline["chapter_number"] = 0
                    else:
                        raw_json["outlines"] = []
                    
                    # 4. Fix style
                    if "style" in raw_json:
                        s = raw_json["style"]
                        if not isinstance(s, dict): s = {"content": str(s)}
                        
                        # Inner remapping
                        for sk in list(s.keys()):
                            sk_low = sk.lower()
                            if "tone" in sk_low and "tone" not in s: s["tone"] = s.pop(sk)
                            elif "rhetoric" in sk_low and "rhetoric" not in s: s["rhetoric"] = s.pop(sk)
                            elif "keyword" in sk_low and "keywords" not in s: s["keywords"] = s.pop(sk)
                            elif ("example" in sk_low or "features" in sk_low) and "example_sentence" not in s: s["example_sentence"] = s.pop(sk)

                        if "example_sentence" not in s: s["example_sentence"] = "暂无风格范例"
                        if "rhetoric" not in s: s.setdefault("rhetoric", ["暂无修辞设定"])
                        if "keywords" not in s: s.setdefault("keywords", ["暂无关键词"])
                        if "tone" not in s: s["tone"] = "常规"
                        raw_json["style"] = s
                    else:
                        raw_json["style"] = {"tone": "常规", "rhetoric": [], "keywords": [], "example_sentence": "未定义"}

                    if "world_view_items" not in raw_json:
                        raw_json["world_view_items"] = []

                    return NovelSetupData.model_validate(raw_json)
                except Exception as parse_error:
                    print(f"❌ 深度解析仍然失败: {parse_error}")
            
            raise e

