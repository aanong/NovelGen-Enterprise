from celery import Celery
from src.config import Config

celery_app = Celery(
    "novelgen_worker",
    broker=Config.redis.REDIS_URL,
    backend=Config.redis.REDIS_URL,
    include=["src.tasks"]
)

celery_app.conf.update(
    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区配置
    timezone="UTC",
    enable_utc=True,

    # ========== 性能优化配置 ==========

    # 并发配置
    worker_concurrency=10,  # 默认并发 worker 数量，可根据 CPU 核心数调整

    # 任务预取配置 - 提高吞吐量
    worker_prefetch_multiplier=4,  # 每个 worker 预取 4 个任务

    # ========== 超时保护配置 ==========

    # 任务超时设置（防止任务卡死）
    task_time_limit=1800,  # 30 分钟硬超时
    task_soft_time_limit=1500,  # 25 分钟软超时（发出警告）

    # ========== 重试策略配置 ==========

    # 自动重试配置
    task_default_retry_delay=60,  # 默认重试延迟 60 秒
    max_retries=3,  # 最大重试次数

    # 重试指数退避（可选）
    task_acks_late=True,  # 任务完成后才确认，避免重试时丢失

    # ========== 资源限制配置 ==========

    # 内存保护
    worker_disable_rate_limits=True,  # 禁用速率限制以提高性能
    worker_max_tasks_per_child=1000,  # 每个 worker 处理 1000 个任务后重启，防止内存泄漏

    # 结果过期时间
    result_expires=3600,  # 结果 1 小时后过期

    # 任务路由（可选，用于将任务路由到特定队列）
    task_routes={
        "src.tasks.generate_chapter_task": {"queue": "chapter_generation"},
    },

    # 任务默认队列
    task_default_queue="default",

    # 任务跟踪
    task_track_started=True,  # 跟踪任务开始时间

    # 任务时间限制检查周期
    task_time_limit_check=60,  # 每 60 秒检查一次超时

    # 数据库连接复用（如果使用数据库作为结果后端）
    database_db_reuse=True,
)

# 生产环境推荐配置（可通过环境变量覆盖）
import os

# 从环境变量读取配置，允许灵活调整
if os.getenv("CELERY_CONCURRENCY"):
    celery_app.conf.worker_concurrency = int(os.getenv("CELERY_CONCURRENCY"))

if os.getenv("CELERY_PREFETCH_MULTIPLIER"):
    celery_app.conf.worker_prefetch_multiplier = int(os.getenv("CELERY_PREFETCH_MULTIPLIER"))

if os.getenv("CELERY_TASK_TIME_LIMIT"):
    celery_app.conf.task_time_limit = int(os.getenv("CELERY_TASK_TIME_LIMIT"))

if __name__ == "__main__":
    celery_app.start()
