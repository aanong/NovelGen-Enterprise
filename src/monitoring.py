"""
性能监控与分析工具
用于追踪 Agent 执行时间、Token 消耗等指标
"""
import time
import functools
from typing import Dict, Any, Callable
from datetime import datetime
import json
from pathlib import Path


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, log_file: str = ".performance_log.json"):
        self.log_file = Path(log_file)
        self.metrics: Dict[str, Any] = {
            "sessions": []
        }
        self._load_metrics()
    
    def _load_metrics(self):
        """加载历史指标"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.metrics = json.load(f)
            except Exception as e:
                print(f"⚠️ 无法加载性能日志: {e}")
    
    def _save_metrics(self):
        """保存指标到文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 无法保存性能日志: {e}")
    
    def start_session(self, chapter_number: int):
        """开始新的会话"""
        session = {
            "chapter": chapter_number,
            "start_time": datetime.utcnow().isoformat(),
            "agents": {},
            "total_time": 0,
            "retry_count": 0,
            "success": False
        }
        self.metrics["sessions"].append(session)
        return len(self.metrics["sessions"]) - 1
    
    def log_agent_call(
        self,
        session_id: int,
        agent_name: str,
        duration: float,
        token_count: int = 0,
        success: bool = True
    ):
        """记录 Agent 调用"""
        if session_id >= len(self.metrics["sessions"]):
            return
        
        session = self.metrics["sessions"][session_id]
        
        if agent_name not in session["agents"]:
            session["agents"][agent_name] = {
                "calls": 0,
                "total_time": 0,
                "total_tokens": 0,
                "failures": 0
            }
        
        agent_stats = session["agents"][agent_name]
        agent_stats["calls"] += 1
        agent_stats["total_time"] += duration
        agent_stats["total_tokens"] += token_count
        
        if not success:
            agent_stats["failures"] += 1
    
    def end_session(self, session_id: int, success: bool = True, retry_count: int = 0):
        """结束会话"""
        if session_id >= len(self.metrics["sessions"]):
            return
        
        session = self.metrics["sessions"][session_id]
        session["end_time"] = datetime.utcnow().isoformat()
        session["success"] = success
        session["retry_count"] = retry_count
        
        # 计算总时间
        start = datetime.fromisoformat(session["start_time"])
        end = datetime.fromisoformat(session["end_time"])
        session["total_time"] = (end - start).total_seconds()
        
        self._save_metrics()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics["sessions"]:
            return {"message": "暂无数据"}
        
        total_sessions = len(self.metrics["sessions"])
        successful_sessions = sum(1 for s in self.metrics["sessions"] if s.get("success"))
        
        total_time = sum(s.get("total_time", 0) for s in self.metrics["sessions"])
        avg_time = total_time / total_sessions if total_sessions > 0 else 0
        
        total_retries = sum(s.get("retry_count", 0) for s in self.metrics["sessions"])
        avg_retries = total_retries / total_sessions if total_sessions > 0 else 0
        
        # Agent 统计
        agent_stats = {}
        for session in self.metrics["sessions"]:
            for agent_name, stats in session.get("agents", {}).items():
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "total_calls": 0,
                        "total_time": 0,
                        "total_tokens": 0,
                        "total_failures": 0
                    }
                
                agent_stats[agent_name]["total_calls"] += stats.get("calls", 0)
                agent_stats[agent_name]["total_time"] += stats.get("total_time", 0)
                agent_stats[agent_name]["total_tokens"] += stats.get("total_tokens", 0)
                agent_stats[agent_name]["total_failures"] += stats.get("failures", 0)
        
        return {
            "total_chapters": total_sessions,
            "successful_chapters": successful_sessions,
            "success_rate": f"{successful_sessions / total_sessions * 100:.1f}%" if total_sessions > 0 else "N/A",
            "avg_time_per_chapter": f"{avg_time:.2f}s",
            "avg_retries_per_chapter": f"{avg_retries:.2f}",
            "agent_performance": agent_stats
        }
    
    def print_summary(self):
        """打印性能摘要"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 NovelGen-Enterprise 性能报告")
        print("="*60)
        
        if "message" in summary:
            print(summary["message"])
            return
        
        print(f"总章节数: {summary['total_chapters']}")
        print(f"成功章节数: {summary['successful_chapters']}")
        print(f"成功率: {summary['success_rate']}")
        print(f"平均生成时间: {summary['avg_time_per_chapter']}")
        print(f"平均重试次数: {summary['avg_retries_per_chapter']}")
        
        print("\n📈 Agent 性能统计:")
        for agent_name, stats in summary["agent_performance"].items():
            print(f"\n  {agent_name}:")
            print(f"    调用次数: {stats['total_calls']}")
            print(f"    总耗时: {stats['total_time']:.2f}s")
            print(f"    平均耗时: {stats['total_time'] / stats['total_calls']:.2f}s" if stats['total_calls'] > 0 else "    平均耗时: N/A")
            print(f"    Token 消耗: {stats['total_tokens']}")
            print(f"    失败次数: {stats['total_failures']}")
        
        print("="*60)


def monitor_performance(agent_name: str):
    """装饰器：监控函数执行性能"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                duration = time.time() - start_time
                print(f"⏱️ {agent_name} 执行耗时: {duration:.2f}s")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                duration = time.time() - start_time
                print(f"⏱️ {agent_name} 执行耗时: {duration:.2f}s")
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局监控实例
monitor = PerformanceMonitor()


if __name__ == "__main__":
    # 测试
    monitor.print_summary()
