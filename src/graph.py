from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from .schemas.state import NGEState, WorldItemSchema
from .agents.architect import ArchitectAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .agents.style_analyzer import StyleAnalyzer
from .db.base import SessionLocal
from .db.models import NovelBible, Character, CharacterRelationship, PlotOutline, LogicAudit, Chapter as DBChapter
from .db.vector_store import VectorStore
from .monitoring import monitor
import json
from datetime import datetime

class NGEGraph:
    def __init__(self):
        self.architect = ArchitectAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        self.analyzer = StyleAnalyzer()
        
        self.workflow = StateGraph(NGEState)
        self._build_graph()

    def _build_graph(self):
        # 节点定义
        self.workflow.add_node("load_context", self.load_context_node) 
        self.workflow.add_node("plan", self.plan_node)
        self.workflow.add_node("refine_context", self.refine_context_node) 
        self.workflow.add_node("write", self.write_node)
        self.workflow.add_node("review", self.review_node)
        self.workflow.add_node("evolve", self.evolve_node)
        
        # 连线
        self.workflow.add_node("repair", self.repair_node) 
        
        # 连线
        self.workflow.set_entry_point("load_context")
        self.workflow.add_edge("load_context", "plan")
        self.workflow.add_edge("plan", "refine_context")
        self.workflow.add_edge("refine_context", "write")
        self.workflow.add_edge("write", "review")
        
        # 条件分支
        self.workflow.add_conditional_edges(
            "review",
            self.should_continue,
            {
                "continue": "evolve",
                "revise": "write",
                "repair": "repair"
            }
        )
        
        self.workflow.add_edge("repair", "evolve")
        self.workflow.add_edge("evolve", END)
        
        self.app = self.workflow.compile()

    async def load_context_node(self, state: NGEState):
        """从数据库加载/刷新当前的 State（如人物状态、世界观、历史摘要）"""
        current_ch = state.current_plot_index + 1
        print(f"--- LOADING CONTEXT (Chapter {current_ch}, Branch: {state.current_branch}) ---")
        
        # 启动性能会话
        monitor.start_session(current_ch)
        
        db = SessionLocal()
        try:
            # 1. 同步角色状态
            db_chars = db.query(Character).all()
            for c in db_chars:
                if c.name in state.characters:
                    char = state.characters[c.name]
                    char.current_mood = c.current_mood
                    char.personality_traits = c.personality_traits or {}
                    char.skills = c.skills or []
                    char.assets = c.assets or {}
                    
                    # 同步背包
                    char.inventory = [
                        WorldItemSchema(
                            name=item.name,
                            description=item.description,
                            rarity=item.rarity,
                            powers=item.powers or {},
                            location=item.location
                        ) for item in c.inventory
                    ]
            
            # 2. 同步全球物品
            from .db.models import WorldItem
            db_items = db.query(WorldItem).all()
            state.world_items = [
                WorldItemSchema(
                    name=item.name,
                    description=item.description,
                    rarity=item.rarity,
                    powers=item.powers or {},
                    location=item.location
                ) for item in db_items
            ]
            
            # 3. Rule 3.1: 加载历史摘要 (链表回溯)
            summaries = []
            
            # 确定回溯起点
            start_chapter_id = state.last_chapter_id
            if not start_chapter_id:
                # 如果没有指定起点，尝试查找当前分支的最新章节
                latest_chapter = db.query(DBChapter).filter(
                    DBChapter.novel_id == 1,
                    DBChapter.branch_id == state.current_branch,
                    DBChapter.chapter_number < current_ch
                ).order_by(DBChapter.chapter_number.desc()).first()
                if latest_chapter:
                    start_chapter_id = latest_chapter.id
            
            # 开始回溯
            curr_id = start_chapter_id
            for _ in range(3): # 回溯 3 章
                if not curr_id:
                    break
                ch = db.query(DBChapter).filter(DBChapter.id == curr_id).first()
                if ch:
                    if ch.summary:
                        summaries.insert(0, ch.summary) # 插入到开头，保持时间顺序
                    curr_id = ch.previous_chapter_id
                else:
                    break
            
            state.memory_context.recent_summaries = summaries
            print(f"✅ 已加载 {len(summaries)} 条历史摘要 (Branch: {state.current_branch})。")
            
            return {"next_action": "plan"}
        except Exception as e:
            print(f"Error loading context: {e}")
            return {"next_action": "plan"}
        finally:
            db.close()

    async def plan_node(self, state: NGEState):
        print(f"--- PLANNING CHAPTER (Branch: {state.current_branch}) ---")
        db = SessionLocal()
        try:
            current_chapter_num = state.current_plot_index + 1
            
            # 1. 检查 DB 是否已有大纲 (匹配 branch_id)
            outline = db.query(PlotOutline).filter_by(
                novel_id=1, 
                chapter_number=current_chapter_num,
                branch_id=state.current_branch
            ).first()
            
            if outline:
                # 如果已有大纲（不管是 pending 还是 completed），直接复用
                print(f"✅ 发现现有大纲 (Ch.{current_chapter_num}, Branch: {state.current_branch}, Status: {outline.status})")
                
                # 如果是 pending 且内容为空，则可以调用 Agent 补充，但这里我们假设 import 已有内容
                if not outline.scene_description or not outline.key_conflict:
                    plan_data = await self.architect.plan_next_chapter(state)
                    outline.scene_description = plan_data.get("scene", outline.scene_description)
                    outline.key_conflict = plan_data.get("conflict", outline.key_conflict)
                    db.commit()
                    instruction = plan_data["instruction"]
                else:
                    instruction = f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                
                return {"next_action": "refine_context", "review_feedback": instruction}

            # 2. 调用 Architect Agent 生成
            plan_data = await self.architect.plan_next_chapter(state)
            
            # 3. 存入 DB
            new_outline = PlotOutline(
                novel_id=1,
                chapter_number=current_chapter_num,
                branch_id=state.current_branch,
                scene_description=plan_data.get("scene", "Generated Scene"),
                key_conflict=plan_data.get("conflict", "Generated Conflict"),
                status="pending"
            )
            db.add(new_outline)
            db.commit()
            
            return {"next_action": "refine_context", "review_feedback": plan_data["instruction"]}
        except Exception as e:
            print(f"Planning Error: {e}")
            return {"next_action": "refine_context", "review_feedback": "Error in planning."}
        finally:
            db.close()

    async def refine_context_node(self, state: NGEState):
        """上下文精炼 (Real RAG Implementation)"""
        print("--- REFINING CONTEXT VIA RAG ---")
        
        # 1. 获取当前规划的场景描述作为 Query
        query = state.review_feedback # 在 plan 节点中，instruction 或 plan_data 被存入 review_feedback
        
        vs = VectorStore()
        try:
            # 2. 检索相关世界观
            bible_results = await vs.search_bible(query, top_k=3)
            bible_context = "\n".join([f"[{b['key']}]: {b['content']}" for b in bible_results])
            
            # 3. 检索相关文风范例
            style_results = await vs.search_style(query, top_k=1)
            style_context = style_results[0]['content'] if style_results else "常规文风"
            
            print(f"✅ RAG 检索完成。找到 {len(bible_results)} 条相关设定。")
            
            # 4. 更新 State 中的提示词
            # 将检索到的内容注入到 review_feedback 中，供 Writer 使用
            enhanced_instruction = (
                f"{state.review_feedback}\n\n"
                f"【参考世界观设定】\n{bible_context}\n\n"
                f"【文风参考范例】\n{style_context}"
            )
            
            return {
                "next_action": "write",
                "review_feedback": enhanced_instruction
            }
        except Exception as e:
            print(f"RAG Error: {e}")
            return {"next_action": "write"}
        finally:
            vs.close()

    async def write_node(self, state: NGEState):
        print("--- WRITING CHAPTER ---")
        draft = await self.writer.write_chapter(state, state.review_feedback)
        return {"current_draft": draft, "next_action": "review"}

    async def review_node(self, state: NGEState):
        print("--- REVIEWING DRAFT ---")
        db = SessionLocal()
        try:
            review_result = await self.reviewer.review_draft(state, state.current_draft)
            
            audit = LogicAudit(
                reviewer_role="Deepseek-Critic",
                is_passed=review_result.get("passed", False),
                feedback=review_result.get("feedback", "No feedback"),
                logic_score=review_result.get("score", 0.0),
                created_at=datetime.utcnow()
            )
            db.add(audit)
            db.commit()

            if review_result.get("passed"):
                return {"next_action": "evolve", "review_feedback": "Passed"}
            else:
                return {
                    "next_action": "write", 
                    "review_feedback": f"修正建议：{review_result.get('feedback')}",
                    "retry_count": state.retry_count + 1
                }
        finally:
            db.close()

    async def evolve_node(self, state: NGEState):
        print("--- EVOLVING CHARACTERS & SAVING ---")
        db = SessionLocal()
        try:
            evolution_data = await self.reviewer.evolve_characters(state, state.current_draft)
            
            # 1. 更新内存和 DB 中的角色状态
            for name, changes in evolution_data.items():
                if name == "summary":
                    continue # Skip general summary field during character iteration
                
                if name in state.characters and isinstance(changes, dict):
                    char = state.characters[name]
                    # 更新基本状态
                    char.current_mood = changes.get("new_mood", char.current_mood)
                    evol_log = f"Ch.{state.current_plot_index + 1}: {changes.get('evolution_summary', '')}"
                    char.evolution_log.append(evol_log)
                    
                    # 更新技能与资产 (如果有变化)
                    if "new_skills" in changes and isinstance(changes["new_skills"], list):
                        char.skills = list(set(char.skills + changes["new_skills"]))
                    if "asset_changes" in changes and isinstance(changes["asset_changes"], dict):
                        char.assets.update(changes["asset_changes"])
                    
                    # 同步到 DB
                    db_char = db.query(Character).filter_by(name=name).first()
                    if db_char:
                        db_char.current_mood = char.current_mood
                        db_char.evolution_log = char.evolution_log
                        db_char.skills = char.skills
                        db_char.assets = char.assets
                        
                        # 处理物品所有权变更 (例如：如果是 {"acquired_items": ["神源之心"]})
                        if "acquired_items" in changes:
                            from .db.models import WorldItem
                            for item_name in changes["acquired_items"]:
                                db_item = db.query(WorldItem).filter_by(name=item_name).first()
                                if db_item:
                                    db_item.owner_id = db_char.id
                                    db_item.location = f"Character: {name}"
                        
                        # 处理物品丢失/消耗
                        if "lost_items" in changes:
                            from .db.models import WorldItem
                            for item_name in changes["lost_items"]:
                                db_item = db.query(WorldItem).filter_by(name=item_name).first()
                                if db_item and db_item.owner_id == db_char.id:
                                    db_item.owner_id = None
                                    db_item.location = "Lost/Consumed"

                        # 处理关系变更
                        if "relationship_changes" in changes:
                            for rel_change in changes["relationship_changes"]:
                                target_name = rel_change.get("target")
                                change_type = rel_change.get("change_type")
                                value = rel_change.get("value", 0.0)
                                
                                target_char = db.query(Character).filter_by(name=target_name).first()
                                if target_char:
                                    # 查找现有关系 (A-B 或 B-A)
                                    rel = db.query(CharacterRelationship).filter(
                                        ((CharacterRelationship.char_a_id == db_char.id) & (CharacterRelationship.char_b_id == target_char.id)) |
                                        ((CharacterRelationship.char_a_id == target_char.id) & (CharacterRelationship.char_b_id == db_char.id))
                                    ).first()
                                    
                                    if not rel:
                                        rel = CharacterRelationship(
                                            char_a_id=db_char.id,
                                            char_b_id=target_char.id,
                                            relation_type="Neutral",
                                            intimacy=0.0,
                                            history=[]
                                        )
                                        db.add(rel)
                                    
                                    # 更新亲密度
                                    rel.intimacy = max(-1.0, min(1.0, rel.intimacy + value))
                                    # 记录历史
                                    if not rel.history: rel.history = []
                                    # 确保 history 是列表
                                    if isinstance(rel.history, str):
                                        try:
                                            rel.history = json.loads(rel.history)
                                        except:
                                            rel.history = []
                                    
                                    # 使用 list.append 而不是重新赋值，以确保 SQLAlchemy 追踪变更 (对于 JSON 类型有时需要 flag_modified，但这里重新赋值给 rel.history 应该可以)
                                    new_history = list(rel.history)
                                    new_history.append({
                                        "chapter": state.current_plot_index + 1,
                                        "event": change_type,
                                        "change": value
                                    })
                                    rel.history = new_history
                                    
                                    # 更新关系类型 (简单逻辑)
                                    if rel.intimacy > 0.6: rel.relation_type = "Ally"
                                    elif rel.intimacy > 0.2: rel.relation_type = "Friendly"
                                    elif rel.intimacy < -0.6: rel.relation_type = "Enemy"
                                    elif rel.intimacy < -0.2: rel.relation_type = "Hostile"
            
            # 2. 保存章节 (Upsert)
            chapter_num = state.current_plot_index + 1
            existing_chapter = db.query(DBChapter).filter_by(
                novel_id=1, 
                chapter_number=chapter_num,
                branch_id=state.current_branch
            ).first()
            
            if existing_chapter:
                existing_chapter.title = f"第 {chapter_num} 章"
                existing_chapter.content = state.current_draft
                existing_chapter.summary = evolution_data.get("summary", "")
                existing_chapter.logic_checked = True
                # 更新 last_chapter_id
                state.last_chapter_id = existing_chapter.id
            else:
                new_chapter = DBChapter(
                    novel_id=1,
                    chapter_number=chapter_num,
                    branch_id=state.current_branch,
                    previous_chapter_id=state.last_chapter_id, # 链接到上一章
                    title=f"第 {chapter_num} 章",
                    content=state.current_draft,
                    summary=evolution_data.get("summary", ""),
                    created_at=datetime.utcnow(),
                    logic_checked=True
                )
                db.add(new_chapter)
                db.flush() # 获取 ID
                state.last_chapter_id = new_chapter.id
            
            db.commit()
            
            # 3. 结束性能会话
            monitor.end_session(state.current_plot_index, success=True, retry_count=state.retry_count)
            monitor.print_summary()

            return {
                "current_plot_index": state.current_plot_index + 1,
                "last_chapter_id": state.last_chapter_id, # 更新状态中的 last_chapter_id
                "next_action": "finalize",
                "retry_count": 0 # 重置章节重试计数
            }
        except Exception as e:
            print(f"Save & Evolve Error: {e}")
            db.rollback()
            return {"next_action": "finalize"}
        finally:
            db.close()

    async def repair_node(self, state: NGEState):
        """Rule 5.2: Gemini 介入重写修复"""
        print("🔴 触发 Rule 5.2：Gemini 执行强制修复...")
        
        # 利用 ReviewerAgent (现在是 Gemini) 进行修复
        # 这里我们可以调用一个新的方法或者复用 review 方法的 logic，
        # 但为了清晰，我们假设 ReviewerAgent 有一个 fix_draft 方法。
        # 如果没有，我们就原位实现一个简单的 Prompt。
        
        prompt = (
            f"你作为一个小说主编，现在需要对一份经过多次修改仍不合格的草稿进行最终修复。\n"
            f"修改意见：{state.review_feedback}\n"
            f"原始草稿：\n{state.current_draft}\n\n"
            f"请直接给出修复后的完整正文，确保逻辑通顺，不再有之前的错误。"
        )
        
        # 这里直接调用 reviewer 的 llm (Gemini)
        response = await self.reviewer.llm.ainvoke(prompt)
        fixed_draft = strip_think_tags(response.content)
        
        return {
            "current_draft": fixed_draft,
            "next_action": "evolve",
            "review_feedback": "Fixed by Gemini (Rule 5.2)"
        }

    def should_continue(self, state: NGEState):
        """Rule 5.1 & 5.2: 循环熔断机制"""
        if state.next_action == "evolve":
            print("🟢 审核通过。")
            return "continue"
        
        if state.retry_count >= state.max_retry_limit:
            print(f"🔴 熔断保护：已重试 {state.retry_count} 次，进入 Gemini 分级修复。")
            return "repair"
            
        print(f"🔄 准备第 {state.retry_count + 1} 次生成...")
        return "revise"
