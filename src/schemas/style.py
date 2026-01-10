from pydantic import BaseModel, Field
from typing import List, Dict

class StyleFeatures(BaseModel):
    sentence_length_distribution: Dict[str, float] = Field(description="句式长度分布情况，例如：{'short': 0.3, 'medium': 0.5, 'long': 0.2}")
    common_rhetoric: List[str] = Field(description="经常使用的修辞手法，如：隐喻、拟人、留白等")
    dialogue_narration_ratio: str = Field(description="对话与旁白的比例描述，如：'3:7'")
    emotional_tone: str = Field(description="整体的情绪色调，如：'忧郁'、'热血'、'清冷'")
    vocabulary_preference: List[str] = Field(description="偏好使用的词汇类型或特定词汇")
    rhythm_description: str = Field(description="文字节奏的描述")
    example_sentences: List[str] = Field(default_factory=list, description="风格示例句子")
