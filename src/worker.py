from celery import Celery
from src.config import Config

celery_app = Celery(
    "novelgen_worker",
    broker=Config.redis.REDIS_URL,
    backend=Config.redis.REDIS_URL,
    include=["src.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # 任务超时设置，防止任务卡死
    task_time_limit=3600, # 1小时硬超时
    task_soft_time_limit=3000, # 50分钟软超时
)

if __name__ == "__main__":
    celery_app.start()
