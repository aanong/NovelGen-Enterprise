import logging
from typing import Dict, Any
from ..schemas.state import NGEState, WorldItemSchema
from ..db.base import SessionLocal
from ..db.models import Character, CharacterBranchStatus, WorldItem, Chapter as DBChapter
from ..monitoring import monitor
from ..config import Config
from .base import BaseNode
from ..core.registry import register_node

logger = logging.getLogger(__name__)

@register_node("load_context")
class LoadContextNode(BaseNode):
    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """从数据库加载/刷新当前的 State（如人物状态、世界观、历史摘要）"""
        current_ch = state.current_plot_index + 1
        print(f"--- LOADING CONTEXT (Chapter {current_ch}, Branch: {state.current_branch}) ---")
        
        # 启动性能会话
        monitor.start_session(current_ch)
        
        db = SessionLocal()
        try:
            # 1. 同步角色状态 (支持分支快照)
            db_chars = db.query(Character).filter(Character.novel_id == state.current_novel_id).all()
            for c in db_chars:
                if c.name in state.characters:
                    char_state = state.characters[c.name]
                    
                    # 默认使用全局最新状态
                    target_mood = c.current_mood
                    target_skills = c.skills or []
                    target_assets = c.assets or {}
                    target_status = c.status or {}
                    
                    # 尝试查找分支快照
                    # 查找条件：当前分支，章节号 < 当前章节，按章节号倒序取第一个
                    snapshot = db.query(CharacterBranchStatus).filter(
                        CharacterBranchStatus.character_id == c.id,
                        CharacterBranchStatus.branch_id == state.current_branch,
                        CharacterBranchStatus.chapter_number < current_ch
                    ).order_by(CharacterBranchStatus.chapter_number.desc()).first()
                    
                    if snapshot:
                        print(f"  - Loaded snapshot for {c.name} from Branch {state.current_branch} Ch.{snapshot.chapter_number}")
                        target_mood = snapshot.current_mood
                        target_skills = snapshot.skills or []
                        target_assets = snapshot.assets or {}
                        target_status = snapshot.status or {}
                    
                    # 更新 State
                    char_state.current_mood = target_mood
                    char_state.skills = target_skills
                    char_state.assets = target_assets
                    char_state.status = target_status
                    
                    # 同步背包
                    char_state.inventory = [
                        WorldItemSchema(
                            name=item.name,
                            description=item.description or "",
                            rarity=item.rarity or "Common",
                            powers=item.powers or {},
                            location=item.location
                        ) for item in c.inventory
                    ]
            
            # 2. 同步全球物品
            db_items = db.query(WorldItem).filter(WorldItem.novel_id == state.current_novel_id).all()
            state.world_items = [
                WorldItemSchema(
                    name=item.name,
                    description=item.description or "",
                    rarity=item.rarity or "Common",
                    powers=item.powers or {},
                    location=item.location
                ) for item in db_items
            ]
            
            # 3. Rule 3.1: 加载历史摘要 (链表回溯)
            summaries = []
            key_events = []
            
            # 确定回溯起点
            start_chapter_id = state.last_chapter_id
            if not start_chapter_id:
                # 如果没有指定起点，尝试查找当前分支的最新章节
                latest_chapter = db.query(DBChapter).filter(
                    DBChapter.novel_id == state.current_novel_id,
                    DBChapter.branch_id == state.current_branch,
                    DBChapter.chapter_number < current_ch
                ).order_by(DBChapter.chapter_number.desc()).first()
                if latest_chapter:
                    start_chapter_id = latest_chapter.id
            
            # 开始回溯（使用配置中的最大上下文章节数）
            max_context_chapters = Config.antigravity.MAX_CONTEXT_CHAPTERS
            curr_id = start_chapter_id
            for _ in range(max_context_chapters): # 回溯章节数可配置，增加上下文窗口防止剧情漂移
                if not curr_id:
                    break
                ch = db.query(DBChapter).filter(DBChapter.id == curr_id).first()
                if ch:
                    if ch.summary:
                        # 尝试解析结构化摘要
                        try:
                            import json
                            summary_data = json.loads(ch.summary)
                            if isinstance(summary_data, dict):
                                summaries.insert(0, summary_data.get("summary", ""))
                                if "key_events" in summary_data:
                                    key_events.extend(summary_data["key_events"])
                            else:
                                summaries.insert(0, str(ch.summary))
                        except:
                            summaries.insert(0, ch.summary) # 插入到开头，保持时间顺序
                    curr_id = ch.previous_chapter_id
                else:
                    break
            
            state.memory_context.recent_summaries = summaries
            # 将关键事件也放入上下文（如果 state 结构支持，或者合并到摘要中）
            if key_events:
                # 简单处理：将最近的关键事件合并到 summaries 的最后一条
                events_str = "\n前文关键事件回顾：\n- " + "\n- ".join(key_events[-5:])
                if state.memory_context.recent_summaries:
                    state.memory_context.recent_summaries[-1] += events_str

            print(f"✅ 已加载 {len(summaries)} 条历史摘要 (Branch: {state.current_branch})。")
            
            return {"next_action": "plan"}
        except Exception as e:
            logger.error(f"Error loading context for chapter {current_ch}: {e}", exc_info=True)
            print(f"Error loading context: {e}")
            return {"next_action": "plan"}
        finally:
            db.close()
