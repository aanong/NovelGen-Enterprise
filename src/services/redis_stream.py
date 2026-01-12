import json
import redis.asyncio as redis
from src.config import Config

class RedisStreamService:
    def __init__(self):
        self.redis_url = Config.redis.REDIS_URL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def publish_event(self, task_id: str, event_type: str, data: dict):
        """发布事件到 Redis Channel"""
        channel = f"task:stream:{task_id}"
        message = json.dumps({
            "type": event_type,
            "data": data
        })
        # 设置较短的过期时间，防止垃圾数据堆积（虽然 Pub/Sub 不存储，但如果用 List 做历史记录就需要）
        # 这里仅使用 Pub/Sub
        await self.client.publish(channel, message)

    async def listen_to_task(self, task_id: str):
        """监听指定任务的事件流"""
        channel_name = f"task:stream:{task_id}"
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel_name)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, str):
                        try:
                            yield json.loads(data)
                            continue
                        except json.JSONDecodeError:
                            yield {"type": "message", "data": {"raw": data}}
                            continue
                    yield data
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

    async def close(self):
        if self._client:
            await self._client.close()

# 单例实例
redis_stream = RedisStreamService()
