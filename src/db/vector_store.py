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
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, db_session: Optional[Session] = None):
        self._db = db_session or SessionLocal()
        self.has_pgvector = self._check_pgvector()

    def close(self):
        """Close the database session."""
        if self._db:
            self._db.close()

    def _check_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        try:
            self._db.execute(text("SELECT '[]'::vector"))
            return True
        except Exception:
            self._db.rollback()
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
        novel_id: Optional[int] = None
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
        """
        query_vector = get_embedding(query)
        if not query_vector:
            logger.warning("Failed to generate embedding for query.")
            return []

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
        
        # 1. Try pgvector search
        if self.has_pgvector:
            try:
                q = self._db.query(model_class)
                if db_filters:
                    q = q.filter(*db_filters)
                
                # Use L2 distance for sorting (nearest neighbors)
                items = q.order_by(
                    model_class.embedding.l2_distance(query_vector)
                ).limit(top_k).all()
                
                return self._format_results(items, model_class)
            except Exception as e:
                logger.error(f"Native vector search failed: {e}. Falling back to local.")
                self._db.rollback()

        # 2. Fallback to local cosine similarity
        try:
            q = self._db.query(model_class)
            if db_filters:
                q = q.filter(*db_filters)
            all_items = q.all()
            
            scored_results = []
            for item in all_items:
                if item.embedding:
                    sim = self._cosine_similarity(query_vector, item.embedding)
                    
                    # Boost priority for novel-specific items over global ones
                    priority = 1.0
                    if model_class == ReferenceMaterial and item.novel_id:
                        priority = 1.2 # Give a slight boost to local items
                    
                    scored_results.append((sim * priority, item))
            
            scored_results.sort(key=lambda x: x[0], reverse=True)
            top_items = [item for _, item in scored_results[:top_k]]
            
            return self._format_results(top_items, model_class)
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
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
                    "title": item.title,
                    "source": item.source,
                    "category": item.category,
                    "novel_id": item.novel_id
                })
            elif model_class == NovelBible:
                data.update({
                    "key": item.key,
                    "category": item.category,
                    "novel_id": item.novel_id
                })
            # Add more specific formatting if needed
            
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
