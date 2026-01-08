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
            self._db.rollback() # Important: clean up the aborted transaction
            return False

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(v1)
        v2 = np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    async def search_bible(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索世界观设定 (Novel Bible) 使用向量相似度"""
        query_vector = get_embedding(query)
        
        if self.has_pgvector:
            try:
                # 使用 pgvector 的 L2 距离
                items = self._db.query(NovelBible).order_by(
                    NovelBible.embedding.l2_distance(query_vector)
                ).limit(top_k).all()
                
                return [{
                    "key": item.key,
                    "content": item.content,
                    "category": item.category
                } for item in items]
            except Exception as e:
                print(f"Native vector search failed (Bible): {e}")
        
        # Fallback to Python-side cosine similarity
        try:
            all_items = self._db.query(NovelBible).all()
            if not all_items:
                return []
            
            # Calculate similarities
            results = []
            for item in all_items:
                if item.embedding:
                    sim = self._cosine_similarity(query_vector, item.embedding)
                    results.append((sim, item))
            
            # Sort by similarity descending
            results.sort(key=lambda x: x[0], reverse=True)
            
            return [{
                "key": item.key,
                "content": item.content,
                "category": item.category,
                "score": float(score)
            } for score, item in results[:top_k]]
        except Exception as e:
            print(f"Fallback vector search failed (Bible): {e}")
            return []

    async def search_style(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索文风范例 (Style Ref) 使用向量相似度"""
        query_vector = get_embedding(query)
        
        if self.has_pgvector:
            try:
                items = self._db.query(StyleRef).order_by(
                    StyleRef.embedding.l2_distance(query_vector)
                ).limit(top_k).all()
                
                return [{
                    "content": item.content,
                    "metadata": item.style_metadata
                } for item in items]
            except Exception as e:
                print(f"Native vector search failed (Style): {e}")
        
        # Fallback
        try:
            all_items = self._db.query(StyleRef).all()
            results = []
            for item in all_items:
                if item.embedding:
                    sim = self._cosine_similarity(query_vector, item.embedding)
                    results.append((sim, item))
            
            results.sort(key=lambda x: x[0], reverse=True)
            
            return [{
                "content": item.content,
                "metadata": item.style_metadata,
                "score": float(score)
            } for score, item in results[:top_k]]
        except Exception as e:
            print(f"Fallback vector search failed (Style): {e}")
            return []

    def close(self):
        self._db.close()
