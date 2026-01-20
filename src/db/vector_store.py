"""
NovelGen-Enterprise Vector Store
Unified vector search implementation with pgvector support and local fallback.
"""
from typing import List, Dict, Any, Optional, Type, Union
import numpy as np
from sqlalchemy import text, or_
from sqlalchemy.orm import Session
from .base import SessionLocal
from .models import NovelBible, StyleRef, ReferenceMaterial
from ..utils import get_embedding
from ..core.cache import get_cache_manager
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, db_session: Optional[Session] = None):
        self._db = db_session or SessionLocal()
        self._cache = get_cache_manager()
        self.has_pgvector = self._check_pgvector()

    def close(self):
        """Close the database session."""
        if self._db:
            self._db.close()

    def _check_pgvector(self) -> bool:
        """
        检查 pgvector 扩展是否可用

        Returns:
            是否可用
        """
        try:
            self._db.execute(text("SELECT '[]'::vector"))
            return True
        except Exception:
            self._db.rollback()
            return False

    def check_vector_index(self, table_name: str, column_name: str = "embedding") -> bool:
        """
        检查向量索引是否存在

        Args:
            table_name: 表名
            column_name: 向量列名，默认 "embedding"

        Returns:
            索引是否存在
        """
        try:
            # 查询索引是否存在
            query = text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE tablename = :table_name
                AND indexdef LIKE '%' || :column_name || '%'
                AND indexdef LIKE '%vector%'
            """)
            result = self._db.execute(query, {"table_name": table_name, "column_name": column_name})
            count = result.scalar()
            return count > 0
        except Exception as e:
            logger.warning(f"检查向量索引失败: {e}")
            return False

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        v1 = np.array(v1)
        v2 = np.array(v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return np.dot(v1, v2) / (norm_v1 * norm_v2)

    async def search(
        self,
        query: str,
        model_class: Type[Union[ReferenceMaterial, NovelBible, StyleRef]] = ReferenceMaterial,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        novel_id: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generic search method for any model with an embedding column.

        Args:
            query: The search query text.
            model_class: The SQLAlchemy model class to search (ReferenceMaterial, NovelBible, etc.).
            top_k: Number of results to return.
            filters: Dictionary of exact match filters (e.g., {'category': 'world_setting'}).
            novel_id: Optional novel_id for scoping.
                      For ReferenceMaterial, it searches (novel_id OR global).
                      For others, it typically searches (novel_id only).
            use_cache: 是否使用查询结果缓存，默认 True

        Returns:
            检索结果列表
        """
        # 1. 尝试从缓存获取
        if use_cache:
            try:
                cached_results = await self._cache.get_vector_search_result(
                    query=query,
                    model_class=model_class.__name__,
                    top_k=top_k,
                    novel_id=novel_id
                )
                if cached_results:
                    logger.debug(f"向量检索缓存命中: {model_class.__name__}")
                    return cached_results
            except Exception as e:
                logger.debug(f"缓存查询失败: {e}")

        # 2. 生成查询向量
        query_vector = await get_embedding(query)
        if not query_vector:
            logger.warning("Failed to generate embedding for query.")
            return []

        # 3. 构建查询过滤器
        db_filters = []
        if filters:
            for k, v in filters.items():
                if hasattr(model_class, k):
                    db_filters.append(getattr(model_class, k) == v)

        # Handle novel_id scoping
        if novel_id is not None and hasattr(model_class, 'novel_id'):
            if model_class == ReferenceMaterial:
                # For References: include specific novel items AND global items (novel_id is None)
                db_filters.append(or_(
                    model_class.novel_id == novel_id,
                    model_class.novel_id.is_(None)
                ))
            else:
                # For Bible/Style: strictly scope to the novel
                db_filters.append(model_class.novel_id == novel_id)

        # 4. 执行向量搜索
        try:
            if self.has_pgvector:
                # 使用 pgvector 的高效向量搜索
                results = await self._pgvector_search(
                    model_class, query_vector, db_filters, top_k
                )
            else:
                # 回退到本地相似度计算
                results = await self._fallback_search(
                    model_class, query_vector, db_filters, top_k
                )

            # 5. 保存到缓存
            if use_cache and results:
                try:
                    await self._cache.set_vector_search_result(
                        query=query,
                        model_class=model_class.__name__,
                        results=results,
                        top_k=top_k,
                        novel_id=novel_id
                    )
                except Exception as e:
                    logger.debug(f"保存缓存失败: {e}")

            return results

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    async def _pgvector_search(
        self,
        model_class: Type,
        query_vector: List[float],
        db_filters: List[Any],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用 pgvector 进行向量搜索（异步优化版）"""
        try:
            # 预取更多结果以提高准确性
            fetch_k = top_k * 2

            q = self._db.query(model_class)
            if db_filters:
                q = q.filter(*db_filters)

            # 使用 L2 距离排序（最近邻）
            items = q.order_by(
                model_class.embedding.l2_distance(query_vector)
            ).limit(fetch_k).all()

            # 格式化结果
            results = self._format_results(items, model_class)

            # 如果结果过多，只返回 top_k
            return results[:top_k]

        except Exception as e:
            logger.error(f"pgvector 搜索失败: {e}，回退到本地计算")
            self._db.rollback()
            # 回退到本地计算
            return await self._fallback_search(
                model_class, query_vector, db_filters, top_k
            )

    async def _fallback_search(
        self,
        model_class: Type,
        query_vector: List[float],
        db_filters: List[Any],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """本地余弦相似度计算（优化版）"""
        try:
            from ..config.defaults import Defaults

            q = self._db.query(model_class)
            if db_filters:
                q = q.filter(*db_filters)

            # 限制查询数量，避免加载所有记录
            max_fallback_items = Defaults.MAX_FALLBACK_ITEMS
            all_items = q.limit(max_fallback_items).all()

            # 批量计算相似度
            scored_results = []
            for item in all_items:
                if item.embedding:
                    sim = self._cosine_similarity(query_vector, item.embedding)

                    # 提升小说特定项的优先级
                    priority = 1.0
                    if model_class == ReferenceMaterial and item.novel_id:
                        priority = Defaults.NOVEL_SPECIFIC_PRIORITY_BOOST

                    scored_results.append((sim * priority, item))

            # 排序并返回 top_k
            scored_results.sort(key=lambda x: x[0], reverse=True)
            top_items = [item for _, item in scored_results[:top_k]]

            return self._format_results(top_items, model_class)

        except Exception as e:
            logger.error(f"本地向量搜索失败: {e}")
            return []

    def _format_results(self, items: List[Any], model_class: Type) -> List[Dict[str, Any]]:
        """Format the search results into a standard list of dicts."""
        results = []
        for item in items:
            data = {
                "id": item.id,
                "content": getattr(item, 'content', ''),
                "embedding": getattr(item, 'embedding', [])
            }

            # Add model-specific fields
            if model_class == ReferenceMaterial:
                data.update({
                    "title": getattr(item, 'title', ''),
                    "source": getattr(item, 'source', ''),
                    "category": getattr(item, 'category', ''),
                    "novel_id": getattr(item, 'novel_id', None)
                })
            elif model_class == NovelBible:
                data.update({
                    "key": getattr(item, 'key', ''),
                    "category": getattr(item, 'category', ''),
                    "novel_id": getattr(item, 'novel_id', None)
                })

            results.append(data)
        return results

    async def search_references(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        novel_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Legacy wrapper for backward compatibility."""
        filters = {}
        if category:
            filters['category'] = category

        return await self.search(
            query=query,
            model_class=ReferenceMaterial,
            top_k=top_k,
            filters=filters,
            novel_id=novel_id
        )
