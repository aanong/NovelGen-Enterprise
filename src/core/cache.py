"""
缓存管理模块
提供 Redis + 内存双层缓存支持，支持 LLM 响应、embedding 和向量检索结果缓存
"""
import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timedelta
from functools import wraps
import pickle

logger = logging.getLogger(__name__)


class MemoryCache:
    """内存缓存 - 单节点快速访问"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化内存缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL（秒）
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl

    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """检查缓存是否过期"""
        if "expires_at" not in entry:
            return False
        return datetime.utcnow() > entry["expires_at"]

    def _evict_if_needed(self):
        """当缓存满时，移除最老的条目"""
        if len(self._cache) < self._max_size:
            return
        # 移除最老的条目
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].get("created_at", datetime.min)
        )
        del self._cache[oldest_key]

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if self._is_expired(entry):
            del self._cache[key]
            return None

        return entry.get("value")

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        self._evict_if_needed()

        expires_at = datetime.utcnow() + timedelta(seconds=ttl or self._default_ttl)
        self._cache[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """批量设置"""
        for key, value in mapping.items():
            self.set(key, value, ttl)

    def delete_many(self, keys: List[str]) -> None:
        """批量删除"""
        for key in keys:
            self.delete(key)

    def cleanup(self) -> int:
        """清理过期缓存，返回清理数量"""
        expired_keys = [k for k, v in self._cache.items() if self._is_expired(v)]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    @property
    def size(self) -> int:
        """返回当前缓存大小"""
        return len(self._cache)


class RedisCache:
    """Redis 缓存 - 分布式缓存支持"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        初始化 Redis 缓存

        Args:
            redis_url: Redis 连接 URL
        """
        self._redis_url = redis_url
        self._client = None
        self._connected = False

    async def _ensure_connection(self):
        """确保 Redis 连接可用"""
        if self._connected and self._client:
            return

        try:
            import redis.asyncio as redis
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis 缓存连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败，将使用内存缓存: {e}")
            self._connected = False
            self._client = None

    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return f"nge:cache:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        await self._ensure_connection()

        if not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return pickle.loads(bytes.fromhex(value))
            return None
        except Exception as e:
            logger.warning(f"Redis get 失败: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        await self._ensure_connection()

        if not self._client:
            return

        try:
            serialized = pickle.dumps(value).hex()
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
        except Exception as e:
            logger.warning(f"Redis set 失败: {e}")

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        await self._ensure_connection()

        if not self._client:
            return False

        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis delete 失败: {e}")
            return False

    async def clear(self) -> None:
        """清空缓存（仅清除 NGE 相关前缀）"""
        await self._ensure_connection()

        if not self._client:
            return

        try:
            keys = await self._client.keys("nge:cache:*")
            if keys:
                await self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear 失败: {e}")

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        await self._ensure_connection()

        if not self._client:
            return {}

        try:
            values = await self._client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = pickle.loads(bytes.fromhex(value))
            return result
        except Exception as e:
            logger.warning(f"Redis get_many 失败: {e}")
            return {}

    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """批量设置（使用 pipeline）"""
        await self._ensure_connection()

        if not self._client:
            return

        try:
            async with self._client.pipeline(transaction=True) as pipe:
                for key, value in mapping.items():
                    serialized = pickle.dumps(value).hex()
                    if ttl:
                        pipe.setex(key, ttl, serialized)
                    else:
                        pipe.set(key, serialized)
                await pipe.execute()
        except Exception as e:
            logger.warning(f"Redis set_many 失败: {e}")

    async def delete_many(self, keys: List[str]) -> None:
        """批量删除"""
        await self._ensure_connection()

        if not self._client:
            return

        try:
            await self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis delete_many 失败: {e}")

    @property
    def client(self):
        """返回原始 Redis 客户端"""
        return self._client


class CacheManager:
    """
    缓存管理器
    提供 Redis + 内存双层缓存，支持 LLM 响应、embedding 和向量检索结果缓存
    """

    _instance: Optional["CacheManager"] = None
    _memory_cache: MemoryCache
    _redis_cache: RedisCache

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化缓存管理器"""
        if self._initialized:
            return

        from src.config import Config

        # 初始化内存缓存（容量 1000，TTL 5 分钟）
        self._memory_cache = MemoryCache(max_size=1000, default_ttl=300)

        # 初始化 Redis 缓存
        redis_url = getattr(Config.redis, "REDIS_URL", "redis://localhost:6379/0")
        self._redis_cache = RedisCache(redis_url)

        self._initialized = True
        logger.info("缓存管理器初始化完成")

    def _generate_cache_key(
        self,
        category: str,
        *args,
        **kwargs
    ) -> str:
        """
        生成缓存键

        Args:
            category: 缓存类别（如 'llm_response', 'embedding', 'vector_search'）
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键
        """
        key_data = {
            "category": category,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return f"nge:{category}:{hashlib.md5(key_str.encode()).hexdigest()}"

    # ============ LLM 响应缓存 ============

    async def get_llm_response(
        self,
        prompt_hash: str,
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取 LLM 响应缓存

        Args:
            prompt_hash: 提示词哈希
            model_name: 模型名称

        Returns:
            缓存的响应，失败返回 None
        """
        key = self._generate_cache_key("llm", prompt_hash, model_name)

        # 先查内存缓存
        value = self._memory_cache.get(key)
        if value:
            logger.debug(f"LLM 响应缓存命中（内存）: {key[:16]}...")
            return value

        # 再查 Redis 缓存
        value = await self._redis_cache.get(key)
        if value:
            logger.debug(f"LLM 响应缓存命中（Redis）: {key[:16]}...")
            # 回填内存缓存
            self._memory_cache.set(key, value, ttl=3600)
            return value

        return None

    async def set_llm_response(
        self,
        prompt_hash: str,
        model_name: str,
        response: Dict[str, Any]
    ) -> None:
        """
        设置 LLM 响应缓存

        Args:
            prompt_hash: 提示词哈希
            model_name: 模型名称
            response: LLM 响应
        """
        key = self._generate_cache_key("llm", prompt_hash, model_name)
        ttl = 3600  # 1 小时

        # 同时写入内存和 Redis
        self._memory_cache.set(key, response, ttl)
        await self._redis_cache.set(key, response, ttl)

    # ============ Embedding 缓存 ============

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取 Embedding 缓存

        Args:
            text: 文本

        Returns:
            Embedding 向量，失败返回 None
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()
        key = self._generate_cache_key("embedding", text_hash)

        # 先查内存
        value = self._memory_cache.get(key)
        if value:
            logger.debug(f"Embedding 缓存命中（内存）: {text_hash[:16]}...")
            return value

        # 再查 Redis
        value = await self._redis_cache.get(key)
        if value:
            logger.debug(f"Embedding 缓存命中（Redis）: {text_hash[:16]}...")
            self._memory_cache.set(key, value, ttl=86400)
            return value

        return None

    async def set_embedding(
        self,
        text: str,
        embedding: List[float]
    ) -> None:
        """
        设置 Embedding 缓存

        Args:
            text: 文本
            embedding: Embedding 向量
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()
        key = self._generate_cache_key("embedding", text_hash)
        ttl = 86400  # 24 小时

        self._memory_cache.set(key, embedding, ttl)
        await self._redis_cache.set(key, embedding, ttl)

    # ============ 向量检索缓存 ============

    async def get_vector_search_result(
        self,
        query: str,
        model_class: str,
        top_k: int,
        novel_id: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取向量检索结果缓存

        Args:
            query: 查询文本
            model_class: 模型类名
            top_k: 返回数量
            novel_id: 小说 ID

        Returns:
            检索结果，失败返回 None
        """
        key = self._generate_cache_key(
            "vector_search",
            query[:100],  # 限制 query 长度
            model_class,
            top_k,
            novel_id
        )

        # 先查内存
        value = self._memory_cache.get(key)
        if value:
            logger.debug(f"向量检索缓存命中（内存）: {key[:16]}...")
            return value

        # 再查 Redis
        value = await self._redis_cache.get(key)
        if value:
            logger.debug(f"向量检索缓存命中（Redis）: {key[:16]}...")
            self._memory_cache.set(key, value, ttl=300)
            return value

        return None

    async def set_vector_search_result(
        self,
        query: str,
        model_class: str,
        results: List[Dict[str, Any]],
        top_k: int,
        novel_id: Optional[int] = None
    ) -> None:
        """
        设置向量检索结果缓存

        Args:
            query: 查询文本
            model_class: 模型类名
            results: 检索结果
            top_k: 返回数量
            novel_id: 小说 ID
        """
        key = self._generate_cache_key(
            "vector_search",
            query[:100],
            model_class,
            top_k,
            novel_id
        )
        ttl = 300  # 5 分钟

        self._memory_cache.set(key, results, ttl)
        await self._redis_cache.set(key, results, ttl)

    # ============ 规划结果缓存 ============

    async def get_plan_result(
        self,
        novel_id: int,
        chapter_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取章节规划结果缓存

        Args:
            novel_id: 小说 ID
            chapter_number: 章节号

        Returns:
            规划结果，失败返回 None
        """
        key = self._generate_cache_key("plan", novel_id, chapter_number)

        value = self._memory_cache.get(key)
        if value:
            return value

        value = await self._redis_cache.get(key)
        if value:
            self._memory_cache.set(key, value, ttl=86400)
            return value

        return None

    async def set_plan_result(
        self,
        novel_id: int,
        chapter_number: int,
        result: Dict[str, Any]
    ) -> None:
        """
        设置章节规划结果缓存

        Args:
            novel_id: 小说 ID
            chapter_number: 章节号
            result: 规划结果
        """
        key = self._generate_cache_key("plan", novel_id, chapter_number)
        ttl = 86400  # 24 小时

        self._memory_cache.set(key, result, ttl)
        await self._redis_cache.set(key, result, ttl)

    # ============ 通用缓存方法 ============

    async def get(
        self,
        category: str,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        通用获取缓存

        Args:
            category: 缓存类别
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存值，失败返回 None
        """
        key = self._generate_cache_key(category, *args, **kwargs)

        value = self._memory_cache.get(key)
        if value:
            return value

        value = await self._redis_cache.get(key)
        if value:
            self._memory_cache.set(key, value, ttl=300)
            return value

        return None

    async def set(
        self,
        category: str,
        value: Any,
        ttl: int = 300,
        *args,
        **kwargs
    ) -> None:
        """
        通用设置缓存

        Args:
            category: 缓存类别
            value: 缓存值
            ttl: TTL（秒）
            *args: 位置参数
            **kwargs: 关键字参数
        """
        key = self._generate_cache_key(category, *args, **kwargs)

        self._memory_cache.set(key, value, ttl)
        await self._redis_cache.set(key, value, ttl)

    async def delete(
        self,
        category: str,
        *args,
        **kwargs
    ) -> bool:
        """
        删除缓存

        Args:
            category: 缓存类别
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            是否删除成功
        """
        key = self._generate_cache_key(category, *args, **kwargs)

        self._memory_cache.delete(key)
        return await self._redis_cache.delete(key)

    def clear_category(self, category: str) -> None:
        """清除指定类别的内存缓存"""
        keys_to_delete = [
            k for k in self._memory_cache._cache.keys()
            if k.startswith(f"nge:{category}:")
        ]
        for key in keys_to_delete:
            del self._memory_cache._cache[key]

    async def clear_all(self) -> None:
        """清除所有缓存"""
        self._memory_cache.clear()
        await self._redis_cache.clear()

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存缓存统计"""
        return {
            "size": self._memory_cache.size,
            "max_size": self._memory_cache._max_size
        }


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# ============ 便捷函数 ============

def cached_llm_response(ttl: int = 3600):
    """装饰器：缓存 LLM 响应"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()

            # 生成 prompt hash
            prompt_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
            prompt_hash = hashlib.md5(prompt_data.encode()).hexdigest()

            # 检查缓存
            model_name = kwargs.get("model_name", "default")
            cached = await cache.get_llm_response(prompt_hash, model_name)
            if cached:
                return cached

            # 调用函数
            result = await func(*args, **kwargs)

            # 缓存结果
            await cache.set_llm_response(prompt_hash, model_name, result)
            return result

        return wrapper
    return decorator


def cached_embedding(ttl: int = 86400):
    """装饰器：缓存 Embedding"""
    def decorator(func):
        @wraps(func)
        async def wrapper(text: str, *args, **kwargs):
            cache = get_cache_manager()

            # 检查缓存
            cached = await cache.get_embedding(text)
            if cached is not None:
                return cached

            # 调用函数
            result = await func(text, *args, **kwargs)

            # 缓存结果
            if result:
                await cache.set_embedding(text, result)
            return result

        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试缓存管理器
    async def test():
        cache = CacheManager()

        # 测试 LLM 响应缓存
        await cache.set_llm_response(
            prompt_hash="test_prompt_hash",
            model_name="gemini",
            response={"content": "测试响应"}
        )
        result = await cache.get_llm_response("test_prompt_hash", "gemini")
        print(f"LLM 响应测试: {result}")

        # 测试 Embedding 缓存
        await cache.set_embedding("测试文本", [0.1, 0.2, 0.3])
        result = await cache.get_embedding("测试文本")
        print(f"Embedding 测试: {result}")

        # 测试向量检索缓存
        await cache.set_vector_search_result(
            query="测试查询",
            model_class="ReferenceMaterial",
            results=[{"id": 1, "content": "测试内容"}],
            top_k=3,
            novel_id=1
        )
        result = await cache.get_vector_search_result(
            query="测试查询",
            model_class="ReferenceMaterial",
            top_k=3,
            novel_id=1
        )
        print(f"向量检索测试: {result}")

        # 打印统计
        print(f"\n缓存统计: {cache.get_memory_stats()}")

    asyncio.run(test())
