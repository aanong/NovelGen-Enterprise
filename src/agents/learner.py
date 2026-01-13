import os
import re
import json

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

from dotenv import load_dotenv
from ..db.base import SessionLocal
from ..db.models import NovelBible as DBBible, Character as DBCharacter, PlotOutline as DBOutline, StyleRef as DBStyle
from sqlalchemy.orm import Session

# --- Defines the schemas for parsing ---

class ExtractedCharacter(BaseModel):
    name: str = Field(description="角色姓名")
    role: str = Field(description="角色定位，如主角、反派、配角")
    personality: str = Field(description="性格特征描述")
    background: str = Field(description="背景故事或设定")
    skills: List[str] = Field(default_factory=list, description="角色掌握的技能、功法或特殊能力")
    assets: Dict[str, str] = Field(default_factory=dict, description="角色拥有的非实物资产，如灵石、地盘、声望、权力等")
    relationship_summary: str = Field(description="与其他角色的关系简述")

class ExtractedItem(BaseModel):
    name: str = Field(description="物品/法宝名称")
    description: str = Field(description="物品功能和外观描述")
    rarity: str = Field(description="稀有度，如：凡、灵、宝、仙、神")
    powers: Dict[str, str] = Field(description="物品的特殊能力或数值描述")
    owner_name: Optional[str] = Field(None, description="物品当前的拥有者（姓名），如果是在野则填 None")
    location: Optional[str] = Field(None, description="物品所在地理位置")

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
    items: List[ExtractedItem] = Field(default_factory=list, description="重要物品或法宝列表")
    outlines: List[ExtractedChapterOutline]
    style: ExtractedStyle

# --- Learner Agent Implementation ---

class LearnerAgent(BaseAgent):
    """
    LearnerAgent: 负责从非结构化文本中提取结构化的小说设定。
    使用 Deepseek (逻辑推理强) 来进行理解和拆解。
    """
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or Config.model.DEEPSEEK_REVIEWER_TEMP,
            mock_responses=[
                json.dumps({
                    "world_view_items": [{"category": "World", "key": "System", "content": "Magic"}], 
                    "characters": [{"name": "MockChar", "role": "Protagonist", "personality": "Brave", "background": "None", "relationship_summary": "None", "skills": [], "assets": {}}], 
                    "items": [], 
                    "outlines": [{"chapter_number": 1, "title": "Ch1", "scene_description": "Scene 1", "key_conflict": "Conflict 1", "instruction": "Write Ch1"}], 
                    "style": {"tone": "Mock", "rhetoric": [], "keywords": [], "example_sentence": "Mock"}
                })
            ]
        )
        self.parser = PydanticOutputParser(pydantic_object=NovelSetupData)
        self.db: Session = SessionLocal()

    async def process(self, *args, **kwargs) -> Any:
        """
        BaseAgent required method.
        Not primarily used in current flow, but required for consistency.
        """
        pass # LearnerAgent usually called via specific methods

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def _get_agent_setting(self, key: str, default: str) -> str:
        """从数据库获取 Agent 配置 (category='agent_config')"""
        try:
            setting = self.db.query(DBBible).filter(
                DBBible.category == 'agent_config',
                DBBible.key == key
            ).first()
            return setting.content if setting else default
        except Exception:
            return default

    async def parse_document(self, content: str) -> NovelSetupData:
        """
        全量解析文档内容。
        """
        from ..utils import strip_think_tags, extract_json_from_text
        
        system_prompt = self._get_agent_setting("learner_system_prompt", (
            "你是一个专业的文学数据分析师。你的任务是读取用户提供的小说设定文档，"
            "并将其拆解为用于生成的结构化数据。\n\n"
            "文档可能包含：大纲、人物小传（含功法技能、资产）、关键物品/法宝、世界观设定、文风描述。\n"
            "你需要智能地识别这些部分，即使它们没有清晰的标题。\n"
            "对于角色，请特别关注他们的【技能/功法】和【资产/财富】。\n"
            "对于重要物品，请记录其【稀有度】和【所有权】。\n"
            "如果某个字段文档未提供，请根据上下文合理推断或填入'未定义'。\n\n"
            "{format_instructions}"
        ))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
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
        if isinstance(content_str, list):
            # Handle case where content is a list of parts
            parts = []
            for part in content_str:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif hasattr(part, "text"):
                    parts.append(part.text)
                else:
                    parts.append(str(part))
            content_str = "".join(parts)
        
        # Rule 4.1: Strip <think> tags using utility
        content_str = strip_think_tags(content_str)
        print(f"DEBUG: Learner Raw Content: {content_str[:500]}...") # Debug print
        
        try:
            # Try standard parsing first
            return self.parser.parse(content_str)
        except Exception as e:
            print(f"⚠️ 初始解析失败，尝试深度修复 JSON 格式...")
            
            # Using utility to extract JSON
            raw_json = extract_json_from_text(content_str)
            
            if not raw_json:
                print(f"❌ 无法从文本中提取 JSON 内容")
                raise e

            try:
                # 1. Remap common mismatches (Fuzzy remapping to match NovelSetupData)
                # Some LLMs might wrap lists in objects with the same name as the model class
                for k in list(raw_json.keys()):
                    val = raw_json[k]
                    k_low = k.lower()
                    
                    # Target key detection
                    target_key = None
                    if ("chapter" in k_low or "outline" in k_low or "章节" in k_low):
                        target_key = "outlines"
                    elif ("style" in k_low or k_low == "text"):
                        target_key = "style"
                    elif ("world" in k_low or "view" in k_low):
                        target_key = "world_view_items"
                    elif ("character" in k_low):
                        target_key = "characters"
                    elif ("item" in k_low or "treasure" in k_low or "artifact" in k_low or "物品" in k_low or "法宝" in k_low):
                        target_key = "items"
                    
                    if target_key:
                        # Unwrap if the LLM nested it (e.g. {"ExtractedWorldView": {"world_view_items": [...]}})
                        if isinstance(val, dict):
                            # Check if the nested dict has the key we want or a similar one
                            inner_found = False
                            for ik, iv in val.items():
                                if ik.lower() in [target_key, k_low] or any(x in ik.lower() for x in ["items", "list", "data"]):
                                    raw_json[target_key] = iv
                                    inner_found = True
                                    break
                            if not inner_found:
                                # If it's just a dict representing a single item but expects a list, wrap it
                                if target_key in ["world_view_items", "characters", "outlines"]:
                                    raw_json[target_key] = [val]
                                else:
                                    raw_json[target_key] = val
                        else:
                            raw_json[target_key] = val
                        
                        if target_key != k:
                            raw_json.pop(k, None)

                # 2. Fix characters
                if "characters" in raw_json:
                    if not isinstance(raw_json["characters"], list):
                        raw_json["characters"] = [raw_json["characters"]]
                    for char in raw_json["characters"]:
                        if "relationship_summary" not in char:
                            char["relationship_summary"] = "暂无明确关系说明"
                        if "skills" not in char:
                            char["skills"] = []
                        if "assets" not in char:
                            char["assets"] = {}
                else:
                    raw_json["characters"] = []
                
                # 2.5 Fix items
                if "items" not in raw_json:
                    raw_json["items"] = []
                elif not isinstance(raw_json["items"], list):
                    raw_json["items"] = [raw_json["items"]]
                
                # 3. Fix outlines
                if "outlines" in raw_json:
                    if not isinstance(raw_json["outlines"], list):
                        raw_json["outlines"] = [raw_json["outlines"]]
                    for outline in raw_json["outlines"]:
                        # Inner remapping
                        for ok in list(outline.keys()):
                            ok_low = ok.lower()
                            if "desc" in ok_low and "scene_description" not in outline:
                                outline["scene_description"] = outline.pop(ok)
                            elif "conflict" in ok_low and "key_conflict" not in outline:
                                outline["key_conflict"] = outline.pop(ok)
                        
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
                    if not isinstance(s, dict): s = {"tone": "常规", "content": str(s)}
                    
                    # Inner remapping
                    for sk in list(s.keys()):
                        sk_low = sk.lower()
                        if "tone" in sk_low and "tone" not in s: s["tone"] = s.pop(sk)
                        elif "rhetoric" in sk_low and "rhetoric" not in s: s["rhetoric"] = s.pop(sk)
                        elif ("keyword" in sk_low or "vocab" in sk_low) and "keywords" not in s: s["keywords"] = s.pop(sk)
                        elif ("example" in sk_low or "features" in sk_low or "sentence" in sk_low) and "example_sentence" not in s: s["example_sentence"] = s.pop(sk)

                    if "example_sentence" not in s: s["example_sentence"] = "暂无风格范例"
                    if "rhetoric" not in s: s["rhetoric"] = ["暂无修辞设定"]
                    if "keywords" not in s: s["keywords"] = ["暂无关键词"]
                    if "tone" not in s: s["tone"] = "常规"
                    raw_json["style"] = s
                else:
                    raw_json["style"] = {"tone": "常规", "rhetoric": [], "keywords": [], "example_sentence": "未定义"}

                if "world_view_items" not in raw_json:
                    raw_json["world_view_items"] = []
                elif not isinstance(raw_json["world_view_items"], list):
                    raw_json["world_view_items"] = [raw_json["world_view_items"]]

                return NovelSetupData.model_validate(raw_json)
            except Exception as parse_error:
                print(f"❌ 深度解析仍然失败: {parse_error}")
                print(f"原始响应内容: {content_str[:500]}...")
                raise parse_error

    async def load_setup_from_db(self) -> NovelSetupData:
        """
        从数据库加载当前所有小说设定，并封装为 NovelSetupData。
        遵守 Rule 1.1 & 2.1: 数据库中的设定具有最高优先级。
        """
        # 1. 加载世界观
        db_bible = self.db.query(DBBible).filter(DBBible.category != 'agent_config').all()
        world_view_items = [
            ExtractedWorldView(
                category=b.category,
                key=b.key,
                content=b.content
            ) for b in db_bible
        ]

        # 2. 加载角色
        db_chars = self.db.query(DBCharacter).all()
        characters = [
            ExtractedCharacter(
                name=c.name,
                role=c.role or "配角",
                personality=c.personality_traits.get("personality", "未知"),
                background=c.personality_traits.get("background", "无"),
                relationship_summary="通过关系表查询" # 可选：进一步查询 CharacterRelationship
            ) for c in db_chars
        ]

        # 3. 加载大纲
        db_outlines = self.db.query(DBOutline).order_by(DBOutline.chapter_number).all()
        outlines = [
            ExtractedChapterOutline(
                chapter_number=o.chapter_number,
                title=f"第 {o.chapter_number} 章",
                scene_description=o.scene_description or "",
                key_conflict=o.key_conflict or "",
                instruction="从数据库加载"
            ) for o in db_outlines
        ]

        # 4. 加载文风
        db_style = self.db.query(DBStyle).order_by(DBStyle.id.desc()).first()
        if db_style:
            meta = db_style.style_metadata or {}
            style = ExtractedStyle(
                tone=meta.get("tone", "常规"),
                rhetoric=meta.get("rhetoric", []),
                keywords=meta.get("keywords", []),
                example_sentence=db_style.content.split("\n范例: ")[-1] if "\n范例: " in db_style.content else "无"
            )
        else:
            style = ExtractedStyle(tone="常规", rhetoric=[], keywords=[], example_sentence="未定义")

        return NovelSetupData(
            world_view_items=world_view_items,
            characters=characters,
            items=[], # 可选：从 WorldItem 表加载
            outlines=outlines,
            style=style
        )


