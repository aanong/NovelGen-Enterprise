"""
剧情支线服务模块
提供剧情支线的业务逻辑处理
"""
from typing import List, Optional, Dict, Any
from src.db.base import SessionLocal
from src.db.plot_branch_repository import PlotBranchRepository
from src.db.models import PlotBranch, PlotBranchCharacter, PlotBranchItem, Character, WorldItem
import logging

logger = logging.getLogger(__name__)


class PlotBranchService:
    """剧情支线服务类"""
    
    # ============ 支线管理 ============
    
    @staticmethod
    def create_branch(
        novel_id: int,
        branch_key: str,
        name: str,
        description: str = None,
        branch_type: str = "side",
        introduce_at_chapter: int = None,
        introduce_condition: str = None,
        priority: int = 5,
        objectives: List[str] = None,
        possible_endings: List[Dict] = None,
        stages: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        为小说创建剧情支线
        
        Args:
            novel_id: 小说 ID
            branch_key: 支线唯一标识（如 "revenge_arc"）
            name: 支线名称（如 "复仇之路"）
            description: 支线描述
            branch_type: 类型 (main/side/hidden/parallel)
            introduce_at_chapter: 在第几章引入
            introduce_condition: 引入条件描述
            priority: 优先级 1-10
            objectives: 目标列表
            possible_endings: 可能的结局
            stages: 阶段定义
            
        Returns:
            创建结果
        """
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            
            # 检查是否已存在
            existing = repo.get_branch_by_key(novel_id, branch_key)
            if existing:
                return {
                    "success": False,
                    "error": f"支线 '{branch_key}' 已存在于该小说中"
                }
            
            branch = repo.create_branch(
                novel_id=novel_id,
                branch_key=branch_key,
                name=name,
                description=description,
                branch_type=branch_type,
                introduce_at_chapter=introduce_at_chapter,
                introduce_condition=introduce_condition,
                priority=priority,
                objectives=objectives,
                possible_endings=possible_endings,
                stages=stages
            )
            
            return {
                "success": True,
                "branch": PlotBranchService._serialize_branch(branch)
            }
        except Exception as e:
            logger.error(f"创建支线失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def get_branch(branch_id: int) -> Optional[Dict[str, Any]]:
        """获取支线详情（含关联的人物和道具）"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branch = repo.get_branch_by_id(branch_id)
            if not branch:
                return None
            return PlotBranchService._serialize_branch_full(branch)
        finally:
            db.close()
    
    @staticmethod
    def get_novel_branches(
        novel_id: int,
        status: str = None,
        branch_type: str = None
    ) -> List[Dict[str, Any]]:
        """获取小说的所有支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branches = repo.get_branches_by_novel(novel_id, status, branch_type)
            return [PlotBranchService._serialize_branch(b) for b in branches]
        finally:
            db.close()
    
    @staticmethod
    def get_active_branches_for_chapter(novel_id: int, chapter_number: int) -> List[Dict[str, Any]]:
        """获取在指定章节应该激活的支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branches = repo.get_branches_for_chapter(novel_id, chapter_number)
            return [PlotBranchService._serialize_branch(b) for b in branches]
        finally:
            db.close()
    
    @staticmethod
    def update_branch(branch_id: int, **kwargs) -> Dict[str, Any]:
        """更新支线信息"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branch = repo.update_branch(branch_id, **kwargs)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            return {
                "success": True,
                "branch": PlotBranchService._serialize_branch(branch)
            }
        except Exception as e:
            logger.error(f"更新支线失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def activate_branch(branch_id: int) -> Dict[str, Any]:
        """激活支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branch = repo.activate_branch(branch_id)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            return {
                "success": True,
                "message": f"支线 '{branch.name}' 已激活",
                "branch": PlotBranchService._serialize_branch(branch)
            }
        finally:
            db.close()
    
    @staticmethod
    def complete_branch(branch_id: int, ending: str = None) -> Dict[str, Any]:
        """完成支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branch = repo.complete_branch(branch_id, ending)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            return {
                "success": True,
                "message": f"支线 '{branch.name}' 已完成",
                "branch": PlotBranchService._serialize_branch(branch)
            }
        finally:
            db.close()
    
    @staticmethod
    def update_branch_progress(
        branch_id: int,
        progress: float,
        current_stage: int = None
    ) -> Dict[str, Any]:
        """更新支线进度"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            branch = repo.update_branch_progress(branch_id, progress, current_stage)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            return {
                "success": True,
                "branch": PlotBranchService._serialize_branch(branch)
            }
        finally:
            db.close()
    
    @staticmethod
    def delete_branch(branch_id: int) -> Dict[str, Any]:
        """删除支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            success = repo.delete_branch(branch_id)
            return {
                "success": success,
                "message": "支线已删除" if success else "支线不存在"
            }
        finally:
            db.close()
    
    # ============ 支线人物管理 ============
    
    @staticmethod
    def add_character_to_branch(
        branch_id: int,
        character_id: int,
        role_in_branch: str = None,
        involvement_level: str = "major",
        join_at_chapter: int = None,
        branch_specific_traits: Dict = None,
        expected_arc_changes: Dict = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        将人物添加到支线
        
        Args:
            branch_id: 支线 ID
            character_id: 人物 ID
            role_in_branch: 在支线中的角色（主导者/对手/协助者等）
            involvement_level: 参与程度 (core/major/minor/cameo)
            join_at_chapter: 加入章节
            branch_specific_traits: 支线专属特性
            expected_arc_changes: 预期弧光变化
            notes: 备注
        """
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            
            # 验证支线存在
            branch = repo.get_branch_by_id(branch_id)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            
            # 验证人物存在
            character = db.query(Character).filter(Character.id == character_id).first()
            if not character:
                return {"success": False, "error": "人物不存在"}
            
            association = repo.add_character_to_branch(
                branch_id=branch_id,
                character_id=character_id,
                role_in_branch=role_in_branch,
                involvement_level=involvement_level,
                join_at_chapter=join_at_chapter,
                branch_specific_traits=branch_specific_traits,
                expected_arc_changes=expected_arc_changes,
                notes=notes
            )
            
            return {
                "success": True,
                "message": f"人物 '{character.name}' 已添加到支线 '{branch.name}'",
                "association": PlotBranchService._serialize_branch_character(association)
            }
        except Exception as e:
            logger.error(f"添加人物到支线失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def remove_character_from_branch(branch_id: int, character_id: int) -> Dict[str, Any]:
        """从支线移除人物"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            success = repo.remove_character_from_branch(branch_id, character_id)
            return {
                "success": success,
                "message": "人物已从支线移除" if success else "关联不存在"
            }
        finally:
            db.close()
    
    @staticmethod
    def get_branch_characters(branch_id: int) -> List[Dict[str, Any]]:
        """获取支线中的所有人物"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            associations = repo.get_characters_in_branch(branch_id)
            return [PlotBranchService._serialize_branch_character(a) for a in associations]
        finally:
            db.close()
    
    @staticmethod
    def get_character_branches(character_id: int) -> List[Dict[str, Any]]:
        """获取人物参与的所有支线"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            associations = repo.get_branches_for_character(character_id)
            return [
                {
                    "branch": PlotBranchService._serialize_branch(a.branch),
                    "role_in_branch": a.role_in_branch,
                    "involvement_level": a.involvement_level,
                    "join_at_chapter": a.join_at_chapter
                }
                for a in associations
            ]
        finally:
            db.close()
    
    # ============ 支线道具管理 ============
    
    @staticmethod
    def add_item_to_branch(
        branch_id: int,
        item_id: int,
        role_in_branch: str = None,
        importance: str = "important",
        appear_at_chapter: int = None,
        branch_specific_powers: Dict = None,
        acquisition_condition: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        将道具添加到支线
        
        Args:
            branch_id: 支线 ID
            item_id: 道具 ID
            role_in_branch: 道具角色（麦高芬/关键钥匙/奖励等）
            importance: 重要程度 (critical/important/optional)
            appear_at_chapter: 出现章节
            branch_specific_powers: 支线专属能力
            acquisition_condition: 获取条件
            notes: 备注
        """
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            
            # 验证支线存在
            branch = repo.get_branch_by_id(branch_id)
            if not branch:
                return {"success": False, "error": "支线不存在"}
            
            # 验证道具存在
            item = db.query(WorldItem).filter(WorldItem.id == item_id).first()
            if not item:
                return {"success": False, "error": "道具不存在"}
            
            association = repo.add_item_to_branch(
                branch_id=branch_id,
                item_id=item_id,
                role_in_branch=role_in_branch,
                importance=importance,
                appear_at_chapter=appear_at_chapter,
                branch_specific_powers=branch_specific_powers,
                acquisition_condition=acquisition_condition,
                notes=notes
            )
            
            return {
                "success": True,
                "message": f"道具 '{item.name}' 已添加到支线 '{branch.name}'",
                "association": PlotBranchService._serialize_branch_item(association)
            }
        except Exception as e:
            logger.error(f"添加道具到支线失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def remove_item_from_branch(branch_id: int, item_id: int) -> Dict[str, Any]:
        """从支线移除道具"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            success = repo.remove_item_from_branch(branch_id, item_id)
            return {
                "success": success,
                "message": "道具已从支线移除" if success else "关联不存在"
            }
        finally:
            db.close()
    
    @staticmethod
    def get_branch_items(branch_id: int) -> List[Dict[str, Any]]:
        """获取支线中的所有道具"""
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            associations = repo.get_items_in_branch(branch_id)
            return [PlotBranchService._serialize_branch_item(a) for a in associations]
        finally:
            db.close()
    
    # ============ 批量操作 ============
    
    @staticmethod
    def create_branch_with_associations(
        novel_id: int,
        branch_key: str,
        name: str,
        description: str = None,
        branch_type: str = "side",
        introduce_at_chapter: int = None,
        introduce_condition: str = None,
        priority: int = 5,
        objectives: List[str] = None,
        possible_endings: List[Dict] = None,
        stages: List[Dict] = None,
        characters: List[Dict] = None,  # [{"character_id": 1, "role": "...", ...}]
        items: List[Dict] = None        # [{"item_id": 1, "role": "...", ...}]
    ) -> Dict[str, Any]:
        """
        创建支线并同时关联人物和道具（事务性操作）
        
        Args:
            ... (同 create_branch)
            characters: 要关联的人物列表
            items: 要关联的道具列表
        """
        db = SessionLocal()
        try:
            repo = PlotBranchRepository(db)
            
            # 检查是否已存在
            existing = repo.get_branch_by_key(novel_id, branch_key)
            if existing:
                return {
                    "success": False,
                    "error": f"支线 '{branch_key}' 已存在于该小说中"
                }
            
            # 创建支线
            branch = repo.create_branch(
                novel_id=novel_id,
                branch_key=branch_key,
                name=name,
                description=description,
                branch_type=branch_type,
                introduce_at_chapter=introduce_at_chapter,
                introduce_condition=introduce_condition,
                priority=priority,
                objectives=objectives,
                possible_endings=possible_endings,
                stages=stages
            )
            
            # 关联人物
            added_characters = []
            if characters:
                for char_data in characters:
                    try:
                        assoc = repo.add_character_to_branch(
                            branch_id=branch.id,
                            character_id=char_data.get("character_id"),
                            role_in_branch=char_data.get("role_in_branch"),
                            involvement_level=char_data.get("involvement_level", "major"),
                            join_at_chapter=char_data.get("join_at_chapter"),
                            branch_specific_traits=char_data.get("branch_specific_traits"),
                            expected_arc_changes=char_data.get("expected_arc_changes"),
                            notes=char_data.get("notes")
                        )
                        added_characters.append(assoc.character_id)
                    except Exception as e:
                        logger.warning(f"关联人物失败: {e}")
            
            # 关联道具
            added_items = []
            if items:
                for item_data in items:
                    try:
                        assoc = repo.add_item_to_branch(
                            branch_id=branch.id,
                            item_id=item_data.get("item_id"),
                            role_in_branch=item_data.get("role_in_branch"),
                            importance=item_data.get("importance", "important"),
                            appear_at_chapter=item_data.get("appear_at_chapter"),
                            branch_specific_powers=item_data.get("branch_specific_powers"),
                            acquisition_condition=item_data.get("acquisition_condition"),
                            notes=item_data.get("notes")
                        )
                        added_items.append(assoc.item_id)
                    except Exception as e:
                        logger.warning(f"关联道具失败: {e}")
            
            # 重新获取完整数据
            branch = repo.get_branch_by_id(branch.id)
            
            return {
                "success": True,
                "branch": PlotBranchService._serialize_branch_full(branch),
                "added_characters": added_characters,
                "added_items": added_items
            }
        except Exception as e:
            db.rollback()
            logger.error(f"创建支线失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    # ============ 序列化辅助方法 ============
    
    @staticmethod
    def _serialize_branch(branch: PlotBranch) -> Dict[str, Any]:
        """序列化支线基本信息"""
        return {
            "id": branch.id,
            "novel_id": branch.novel_id,
            "branch_key": branch.branch_key,
            "name": branch.name,
            "description": branch.description,
            "branch_type": branch.branch_type,
            "introduce_at_chapter": branch.introduce_at_chapter,
            "introduce_condition": branch.introduce_condition,
            "status": branch.status,
            "priority": branch.priority,
            "objectives": branch.objectives,
            "possible_endings": branch.possible_endings,
            "current_ending": branch.current_ending,
            "progress": branch.progress,
            "current_stage": branch.current_stage,
            "stages": branch.stages,
            "created_at": branch.created_at.isoformat() if branch.created_at else None,
            "updated_at": branch.updated_at.isoformat() if branch.updated_at else None,
            "activated_at": branch.activated_at.isoformat() if branch.activated_at else None,
            "completed_at": branch.completed_at.isoformat() if branch.completed_at else None
        }
    
    @staticmethod
    def _serialize_branch_full(branch: PlotBranch) -> Dict[str, Any]:
        """序列化支线完整信息（含关联）"""
        result = PlotBranchService._serialize_branch(branch)
        
        # 添加关联的人物
        result["characters"] = [
            PlotBranchService._serialize_branch_character(a)
            for a in branch.character_associations
        ]
        
        # 添加关联的道具
        result["items"] = [
            PlotBranchService._serialize_branch_item(a)
            for a in branch.item_associations
        ]
        
        return result
    
    @staticmethod
    def _serialize_branch_character(assoc: PlotBranchCharacter) -> Dict[str, Any]:
        """序列化支线人物关联"""
        return {
            "id": assoc.id,
            "character_id": assoc.character_id,
            "character_name": assoc.character.name if assoc.character else None,
            "role_in_branch": assoc.role_in_branch,
            "involvement_level": assoc.involvement_level,
            "join_at_chapter": assoc.join_at_chapter,
            "leave_at_chapter": assoc.leave_at_chapter,
            "branch_specific_traits": assoc.branch_specific_traits,
            "expected_arc_changes": assoc.expected_arc_changes,
            "notes": assoc.notes
        }
    
    @staticmethod
    def _serialize_branch_item(assoc: PlotBranchItem) -> Dict[str, Any]:
        """序列化支线道具关联"""
        return {
            "id": assoc.id,
            "item_id": assoc.item_id,
            "item_name": assoc.item.name if assoc.item else None,
            "role_in_branch": assoc.role_in_branch,
            "importance": assoc.importance,
            "appear_at_chapter": assoc.appear_at_chapter,
            "branch_specific_powers": assoc.branch_specific_powers,
            "acquisition_condition": assoc.acquisition_condition,
            "notes": assoc.notes
        }
