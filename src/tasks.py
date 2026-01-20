import asyncio
import json
import logging
from src.worker import celery_app
from src.services.state_loader import load_initial_state
from src.graph import NGEGraph
from src.services.redis_stream import redis_stream
from src.core.error_handler import ErrorHandler, ErrorType, get_llm_circuit_breaker

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="generate_chapter")
def generate_chapter_task(self, novel_id: int, branch_id: str = "main"):
    """
    Celery 任务：生成章节 (支持 Redis 流式推送)
    包含熔断器保护和增强的错误处理
    """
    print(f"🚀 [Task {self.request.id}] 开始生成任务: Novel {novel_id}, Branch {branch_id}")

    # 获取熔断器
    circuit_breaker = get_llm_circuit_breaker()

    # 检查熔断器状态
    if not circuit_breaker.allow_request():
        error_msg = "LLM 服务熔断中，请稍后重试"
        print(f"⚠️ [Task {self.request.id}] {error_msg}")

        # 发布熔断事件
        async def _publish_circuit_open():
            await redis_stream.publish_event(
                self.request.id,
                "error",
                {
                    "message": error_msg,
                    "error_type": "circuit_breaker_open",
                    "technical_details": "LLM service circuit breaker is open"
                }
            )
            await redis_stream.close()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(_publish_circuit_open())
        except Exception:
            pass

        # 临时错误，让 Celery 重试
        raise celery_app.TaskRetry(
            exc=Exception(error_msg),
            delay=30  # 30 秒后重试
        )

    async def _run():
        task_id = self.request.id
        initial_state = await load_initial_state(novel_id, branch_id)

        if not initial_state:
            await redis_stream.publish_event(task_id, "error", {"message": "Failed to load initial state"})
            return {"status": "failed", "reason": "Failed to load initial state"}

        graph = NGEGraph()
        final_output = None

        try:
            # 使用 astream_events 获取详细事件流
            async for event in graph.app.astream_events(initial_state, version="v1"):
                kind = event["event"]

                # 1. 捕获 LLM 生成的 Token (流式输出)
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        await redis_stream.publish_event(task_id, "token", {"content": content})

                # 2. 捕获节点状态变化 (进度更新)
                elif kind == "on_chain_start":
                    name = event["name"]
                    if name in ["plan", "write", "review", "evolve", "refine_context", "load_context"]:
                        await redis_stream.publish_event(task_id, "status", {"step": name, "status": "started"})

                elif kind == "on_chain_end":
                    name = event["name"]
                    if name in ["plan", "write", "review", "evolve", "refine_context", "load_context"]:
                        await redis_stream.publish_event(task_id, "status", {"step": name, "status": "completed"})

                    # 捕获最终输出
                    if name == "LangGraph":
                        final_output = event["data"].get("output")

            # 记录成功，关闭熔断器
            circuit_breaker.record_success()

            await redis_stream.publish_event(task_id, "done", {"message": "Generation completed"})

            result = {
                "status": "success",
                "novel_id": novel_id,
                "task_id": task_id
            }

            if final_output:
                result["chapter_index"] = final_output.get('current_plot_index', 0)
                result["draft_preview"] = final_output.get('current_draft', "")[:200]

            return result

        except Exception as e:
            # 分类错误
            error_type, error_msg = ErrorHandler.classify_error(e)
            friendly_msg = ErrorHandler.get_friendly_error_message(e)

            # 记录错误日志
            ErrorHandler.log_error(e, context={"novel_id": novel_id, "task_id": task_id})

            # 记录熔断器失败
            circuit_breaker.record_failure()

            logger.error(f"任务执行失败: {error_msg}", exc_info=True)
            print(f"❌ Error in graph execution: {error_msg}")

            # 发送错误事件
            await redis_stream.publish_event(task_id, "error", {
                "message": friendly_msg,
                "error_type": error_type.value,
                "technical_details": error_msg
            })

            # 根据错误类型决定是否重试
            if error_type in {
                ErrorType.RATE_LIMIT,
                ErrorType.TIMEOUT,
                ErrorType.NETWORK_ERROR,
                ErrorType.SERVICE_UNAVAILABLE,
                ErrorType.DATABASE_ERROR
            }:
                # 临时错误，抛出让 Celery 重试
                should_retry, delay = ErrorHandler.should_retry(e, self.request.retries)
                if should_retry:
                    raise celery_app.TaskRetry(
                        exc=e,
                        delay=delay
                    )

            # 永久错误，直接抛出
            raise e
        finally:
            await redis_stream.close()

    try:
        # 在同步的 Celery Worker 中运行异步代码
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_run())
        print(f"✅ [Task {self.request.id}] 任务完成")
        return result

    except celery_app.TaskRetry as e:
        # 重新抛出重试异常
        print(f"🔄 [Task {self.request.id}] 任务将重试: {e}")
        raise

    except Exception as e:
        print(f"❌ [Task {self.request.id}] 任务失败: {e}")
        raise
