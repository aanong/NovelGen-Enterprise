"""
NovelGen-Enterprise Vector Store
处理基于 pgvector 的语义检索或本地向量检索 fallback
"""
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import text
from .base import SessionLocal
from .models import NovelBible, StyleRef
from ..utils import get_embedding

class VectorStore:
    def __init__(self, db_session=None):
        self._db = db_session or SessionLocal()
        self.has_pgvector = self._check_pgvector()

    def _check_pgvector(self) -> bool:
        """检查数据库是否支持 pgvector 扩展"""
        try:
            self._db.execute(text("SELECT '[]'::vector"))
            return True
        except Exception:
            return False

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(v1)
        v2 = np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    async def search_bible(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索世界观设定 (Novel Bible) 使用向量相似度"""
        query_vector = get_embedding(query)
        
        # 使用 pgvector 的 L2 距离 (也可改用 Cosine 距离 <->)
        # 注意：这里假设数据库已启用 pgvector 扩展
        try:
            items = self._db.query(NovelBible).order_by(
                NovelBible.embedding.l2_distance(query_vector)
            ).limit(top_k).all()
            
            return [{
                "key": item.key,
                "content": item.content,
                "category": item.category
            } for item in items]
        except Exception as e:
            print(f"Vector search failed (Bible): {e}")
            # Fallback to simple keyword match or return empty
            return []

    async def search_style(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索文风范例 (Style Ref) 使用向量相似度"""
        query_vector = get_embedding(query)
        
        try:
            items = self._db.query(StyleRef).order_by(
                StyleRef.embedding.l2_distance(query_vector)
            ).limit(top_k).all()
            
            return [{
                "content": item.content,
                "metadata": item.style_metadata
            } for item in items]
        except Exception as e:
            print(f"Vector search failed (Style): {e}")
            return []

    def close(self):
        self._db.close()
