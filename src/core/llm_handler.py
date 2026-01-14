"""
LLM 响应处理器
统一处理 LLM 响应的解析、清洗和验证
"""
import re
import json
import logging
from typing import Dict, Any, Optional, TypeVar, Type, Union
from pydantic import BaseModel

from .exceptions import LLMParseError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMResponseHandler:
    """
    LLM 响应处理器
    提供统一的响应解析、清洗和验证功能
    
    主要功能：
    1. 标准化响应内容（处理多种格式）
    2. 清除思考标签（DeepSeek-R1 的 <think> 标签）
    3. 提取 JSON 对象（支持多种格式）
    4. 验证并解析为 Pydantic 模型
    """
    
    # 思考标签正则
    THINK_TAG_PATTERN = re.compile(r'<think>.*?</think>', re.DOTALL)
    
    # JSON 提取正则
    JSON_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
    JSON_OBJECT_PATTERN = re.compile(r'(\{.*\})', re.DOTALL)
    JSON_ARRAY_PATTERN = re.compile(r'(\[.*\])', re.DOTALL)
    
    # 验证前缀正则（Rule 6.2）
    VALIDATION_PREFIX_PATTERN = re.compile(r'^当前遵循：.*?\n', re.MULTILINE)
    
    @classmethod
    def normalize(cls, content: Any) -> str:
        """
        标准化 LLM 响应内容
        处理字符串、列表、复杂对象等多种格式
        
        Args:
            content: 原始响应内容
            
        Returns:
            标准化后的字符串
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
    
    @classmethod
    def strip_think_tags(cls, content: str) -> str:
        """
        清除 DeepSeek-R1 的 <think> 标签
        遵循 Antigravity Rule 4.1
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        return cls.THINK_TAG_PATTERN.sub('', content).strip()
    
    @classmethod
    def strip_validation_prefix(cls, content: str) -> str:
        """
        清除验证前缀（Rule 6.2）
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        return cls.VALIDATION_PREFIX_PATTERN.sub('', content).strip()
    
    @classmethod
    def clean(cls, content: Any) -> str:
        """
        完整的响应清洗流程
        包含标准化、清除标签、清除前缀
        
        Args:
            content: 原始响应内容
            
        Returns:
            清洗后的内容
        """
        normalized = cls.normalize(content)
        without_think = cls.strip_think_tags(normalized)
        cleaned = cls.strip_validation_prefix(without_think)
        return cleaned
    
    @classmethod
    def extract_json(
        cls, 
        text: str,
        allow_array: bool = False
    ) -> Optional[Union[Dict[str, Any], list]]:
        """
        从文本中提取 JSON 对象或数组
        支持多种格式：直接 JSON、代码块、内嵌 JSON
        
        Args:
            text: 包含 JSON 的文本
            allow_array: 是否允许返回数组
            
        Returns:
            解析后的 JSON 对象/数组，失败返回 None
        """
        if not text:
            return None
        
        # 1. 直接解析
        try:
            result = json.loads(text.strip())
            if isinstance(result, dict):
                return result
            if allow_array and isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        
        # 2. 提取代码块中的 JSON
        code_block_match = cls.JSON_BLOCK_PATTERN.search(text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. 提取裸 JSON 对象
        json_match = cls.JSON_OBJECT_PATTERN.search(text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 4. 提取 JSON 数组（如果允许）
        if allow_array:
            array_match = cls.JSON_ARRAY_PATTERN.search(text)
            if array_match:
                try:
                    return json.loads(array_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        return None
    
    @classmethod
    def parse_to_model(
        cls,
        text: str,
        model_class: Type[T],
        strict: bool = False
    ) -> Optional[T]:
        """
        解析文本为 Pydantic 模型
        
        Args:
            text: 包含 JSON 的文本
            model_class: Pydantic 模型类
            strict: 是否严格模式（失败时抛出异常）
            
        Returns:
            解析后的模型实例，失败返回 None（非严格模式）
            
        Raises:
            LLMParseError: 严格模式下解析失败时抛出
        """
        json_data = cls.extract_json(text)
        
        if json_data is None:
            if strict:
                raise LLMParseError(
                    message=f"无法从响应中提取 JSON 数据",
                    raw_content=text
                )
            return None
        
        try:
            return model_class.model_validate(json_data)
        except Exception as e:
            if strict:
                raise LLMParseError(
                    message=f"JSON 数据无法转换为 {model_class.__name__}: {str(e)}",
                    raw_content=text
                )
            logger.warning(f"模型验证失败: {e}")
            return None
    
    @classmethod
    def process_response(
        cls,
        response: Any,
        extract_json: bool = True
    ) -> Dict[str, Any]:
        """
        完整处理 LLM 响应
        
        Args:
            response: LLM 响应对象（需要有 .content 属性）
            extract_json: 是否提取 JSON
            
        Returns:
            处理结果字典：
            {
                "raw": 原始响应,
                "cleaned": 清洗后的响应,
                "json": 提取的 JSON（如果启用）,
                "success": 是否成功
            }
        """
        # 获取响应内容
        if hasattr(response, 'content'):
            raw_content = response.content
        else:
            raw_content = str(response)
        
        # 清洗响应
        cleaned = cls.clean(raw_content)
        
        result = {
            "raw": raw_content,
            "cleaned": cleaned,
            "json": None,
            "success": True
        }
        
        # 提取 JSON
        if extract_json:
            json_data = cls.extract_json(cleaned)
            result["json"] = json_data
            if json_data is None:
                result["success"] = False
        
        return result


# ============ 便捷函数（向后兼容）============

def normalize_llm_content(content: Any) -> str:
    """向后兼容的内容标准化函数"""
    return LLMResponseHandler.normalize(content)


def strip_think_tags(content: str) -> str:
    """向后兼容的思考标签清除函数"""
    return LLMResponseHandler.strip_think_tags(content)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """向后兼容的 JSON 提取函数"""
    return LLMResponseHandler.extract_json(text)
