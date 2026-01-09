import asyncio
import json
from src.worker import celery_app
from src.services.state_loader import load_initial_state
from src.graph import NGEGraph
from src.services.redis_stream import redis_stream

@celery_app.task(bind=True, name="generate_chapter")
def generate_chapter_task(self, novel_id: int, branch_id: str = "main"):
    """
    Celery 任务：生成章节 (支持 Redis 流式推送)
    """
    print(f"🚀 [Task {self.request.id}] 开始生成任务: Novel {novel_id}, Branch {branch_id}")
    
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
                    # 过滤掉一些内部链，只关注主要节点
                    if name in ["plan", "write", "review", "evolve", "refine_context", "load_context"]:
                        await redis_stream.publish_event(task_id, "status", {"step": name, "status": "started"})
                
                elif kind == "on_chain_end":
                    name = event["name"]
                    if name in ["plan", "write", "review", "evolve", "refine_context", "load_context"]:
                        await redis_stream.publish_event(task_id, "status", {"step": name, "status": "completed"})
                    
                    # 捕获最终输出 (Graph 的名字通常是 LangGraph)
                    if name == "LangGraph":
                        final_output = event["data"].get("output")

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
            error_msg = str(e)
            print(f"❌ Error in graph execution: {error_msg}")
            await redis_stream.publish_event(task_id, "error", {"message": error_msg})
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
    except Exception as e:
        print(f"❌ [Task {self.request.id}] 任务失败: {e}")
        raise e
