"""
NovelGen-Enterprise 工具函数库
提供通用的辅助函数
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from .config import Config

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None

if genai is not None:
    try:
        genai.configure(api_key=Config.model.GEMINI_API_KEY)
    except Exception:
        pass


def get_embedding(text: str) -> List[float]:
    """
    使用 Gemini 模型获取文本的 Embedding 向量
    """
    try:
        if genai is None:
            return [0.1] * 768
        result = genai.embed_content(
            model=Config.model.EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception:
        # Fallback for mock/test
        return [0.1] * 768


def normalize_llm_content(content: Any) -> str:
    """
    Normalize LLM content which might be a string or a list of parts.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(part.text)
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


def strip_think_tags(content: str) -> str:
    """
    Rule 4.1: 清除 DeepSeek-R1 的 <think> 标签
    
    Args:
        content: 原始内容
    
    Returns:
        清理后的内容
    """
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    从文本中提取 JSON 对象（容错处理）
    
    Args:
        text: 包含 JSON 的文本
    
    Returns:
        解析后的 JSON 对象，失败返回 None
    """
    # 先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 块
    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试提取代码块中的 JSON
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    return None


def validate_character_consistency(
    character_name: str,
    action: str,
    forbidden_actions: List[str]
) -> Dict[str, Any]:
    """
    Rule 2.1: 验证人物行为是否违反禁忌
    
    Args:
        character_name: 角色名
        action: 角色的行为描述
        forbidden_actions: 禁忌行为列表
    
    Returns:
        {
            "valid": bool,
            "violations": List[str]
        }
    """
    violations = []
    
    for forbidden in forbidden_actions:
        if forbidden.lower() in action.lower():
            violations.append(f"{character_name} 违反禁忌: {forbidden}")
    
    return {
        "valid": len(violations) == 0,
        "violations": violations
    }


def analyze_sentence_length(text: str) -> Dict[str, float]:
    """
    分析文本的句式长度分布
    
    Args:
        text: 待分析文本
    
    Returns:
        {
            "short": 比例,
            "medium": 比例,
            "long": 比例
        }
    """
    # 按标点符号分句
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {"short": 0.0, "medium": 0.0, "long": 0.0}
    
    short_count = sum(1 for s in sentences if len(s) <= 15)
    medium_count = sum(1 for s in sentences if 15 < len(s) <= 30)
    long_count = sum(1 for s in sentences if len(s) > 30)
    
    total = len(sentences)
    
    return {
        "short": round(short_count / total, 2),
        "medium": round(medium_count / total, 2),
        "long": round(long_count / total, 2)
    }


def check_scene_constraints(
    content: str,
    scene_type: str,
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Rule 6.1: 检查内容是否符合场景约束
    
    Args:
        content: 章节内容
        scene_type: 场景类型
        constraints: 场景约束配置
    
    Returns:
        {
            "passed": bool,
            "issues": List[str]
        }
    """
    issues = []
    
    if scene_type == "Action":
        # 检查是否有超长句
        sentences = re.split(r'[。！？]', content)
        long_sentences = [s for s in sentences if len(s.strip()) > 20]
        if long_sentences:
            issues.append(f"发现 {len(long_sentences)} 个超过20字的长句（动作场景禁止）")
    
    elif scene_type == "Dialogue":
        # 检查对话占比
        dialogue_pattern = r'[「『""].*?[」』""]'
        dialogues = re.findall(dialogue_pattern, content)
        dialogue_chars = sum(len(d) for d in dialogues)
        total_chars = len(content)
        
        if total_chars > 0:
            dialogue_ratio = dialogue_chars / total_chars
            min_ratio = constraints.get("min_dialogue_ratio", 0.6)
            if dialogue_ratio < min_ratio:
                issues.append(f"对话占比 {dialogue_ratio:.1%} 低于要求的 {min_ratio:.1%}")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def generate_chapter_summary(content: str, max_length: int = 200) -> str:
    """
    生成章节摘要（简单版本，可用 LLM 替代）
    
    Args:
        content: 章节内容
        max_length: 摘要最大长度
    
    Returns:
        摘要文本
    """
    # 简单截取前 N 个字符
    summary = content[:max_length]
    if len(content) > max_length:
        summary += "..."
    
    return summary


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳
    
    Args:
        dt: datetime 对象，默认为当前时间
    
    Returns:
        格式化的时间字符串
    """
    if dt is None:
        dt = datetime.utcnow()
    
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def calculate_intimacy_change(
    event_type: str,
    base_intimacy: float
) -> float:
    """
    计算人物关系亲密度变化
    
    Args:
        event_type: 事件类型（如 "合作", "冲突", "背叛"）
        base_intimacy: 当前亲密度
    
    Returns:
        新的亲密度值（-1.0 到 1.0）
    """
    changes = {
        "合作": 0.1,
        "救命": 0.3,
        "冲突": -0.2,
        "背叛": -0.5,
        "和解": 0.2
    }
    
    change = changes.get(event_type, 0.0)
    new_intimacy = max(-1.0, min(1.0, base_intimacy + change))
    
    return round(new_intimacy, 2)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

class MockChatModel:
    """
    Mock Chat Model for testing flows without API access.
    """
    def __init__(self, responses: List[str] = None):
        self.responses = responses or [
            '{"tone": "Dark", "rhetoric": ["Metaphor"], "keywords": ["Shadow"], "example_sentence": "Darkness fell."}',
            '{"world_view_items": [], "characters": [{"name": "MockChar", "role": "Protagonist", "personality": "Brave", "background": "None", "relationship_summary": "None"}], "items": [], "outlines": [{"chapter_number": 1, "title": "Ch1", "scene_description": "Scene 1", "key_conflict": "Conflict 1", "instruction": "Write Ch1"}], "style": {"tone": "Mock", "rhetoric": [], "keywords": [], "example_sentence": "Mock"}}',
            '{"chapters": [{"chapter_number": 1, "title": "Ch1", "scene_description": "Scene 1", "key_conflict": "Conflict 1", "foreshadowing": []}, {"chapter_number": 2, "title": "Ch2", "scene_description": "Scene 2", "key_conflict": "Conflict 2", "foreshadowing": []}, {"chapter_number": 3, "title": "Ch3", "scene_description": "Scene 3", "key_conflict": "Conflict 3", "foreshadowing": []}]}',
             '{"expanded_points": [{"id": "1", "title": "Point 1", "description": "Desc 1", "key_events": ["Event 1"], "chapter_index": 1}]}',
             '{"thinking": "Mock Think", "scene_description": "Mock Scene", "key_conflict": "Mock Conflict", "instruction": "Mock Instruction"}'
        ]
        self.call_count = 0

    async def ainvoke(self, input: Any) -> Any:
        # Return a mock response object with .content
        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        
        class MockResponse:
            def __init__(self, content):
                self.content = content
        
        return MockResponse(response_text)

    def bind_tools(self, tools):
        return self

if __name__ == "__main__":
    # 测试函数
    test_text = """
    <think>这是思考内容</think>
    这是正文内容。这是一个短句。这是一个稍微长一点的句子，用来测试句式分析功能。
    这是一个非常非常非常非常非常非常非常非常非常非常长的句子，用来测试长句检测。
    """
    
    print("测试 strip_think_tags:")
    print(strip_think_tags(test_text))
    
    print("\n测试 analyze_sentence_length:")
    print(analyze_sentence_length(test_text))
