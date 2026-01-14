"""
剧情支线仓储模块
提供剧情支线的 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from .models import PlotBranch, PlotBranchCharacter, PlotBranchItem, Character, WorldItem
import datetime
import logging

logger = logging.getLogger(__name__)


class PlotBranchRepository:
    """剧情支线仓储类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ============ 支线基本操作 ============
    
    def create_branch(
        self,
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
    ) -> PlotBranch:
        """
        创建剧情支线
        
        Args:
            novel_id: 小说 ID
            branch_key: 支线唯一标识
            name: 支线名称
            description: 支线描述
            branch_type: 支线类型 (main/side/hidden/parallel)
            introduce_at_chapter: 引入章节
            introduce_condition: 引入条件
            priority: 优先级 1-10
            objectives: 目标列表
            possible_endings: 可能的结局
            stages: 支线阶段定义
            
        Returns:
            创建的 PlotBranch 对象
        """
        branch = PlotBranch(
            novel_id=novel_id,
            branch_key=branch_key,
            name=name,
            description=description,
            branch_type=branch_type,
            introduce_at_chapter=introduce_at_chapter,
            introduce_condition=introduce_condition,
            priority=priority,
            objectives=objectives or [],
            possible_endings=possible_endings or [],
            stages=stages or []
        )
        self.session.add(branch)
        self.session.commit()
        self.session.refresh(branch)
        return branch
    
    def get_branch_by_id(self, branch_id: int) -> Optional[PlotBranch]:
        """根据 ID 获取支线"""
        return self.session.query(PlotBranch).filter(
            PlotBranch.id == branch_id
        ).options(
            joinedload(PlotBranch.character_associations).joinedload(PlotBranchCharacter.character),
            joinedload(PlotBranch.item_associations).joinedload(PlotBranchItem.item)
        ).first()
    
    def get_branch_by_key(self, novel_id: int, branch_key: str) -> Optional[PlotBranch]:
        """根据小说 ID 和支线 key 获取支线"""
        return self.session.query(PlotBranch).filter(
            and_(PlotBranch.novel_id == novel_id, PlotBranch.branch_key == branch_key)
        ).options(
            joinedload(PlotBranch.character_associations).joinedload(PlotBranchCharacter.character),
            joinedload(PlotBranch.item_associations).joinedload(PlotBranchItem.item)
        ).first()
    
    def get_branches_by_novel(
        self,
        novel_id: int,
        status: str = None,
        branch_type: str = None
    ) -> List[PlotBranch]:
        """
        获取小说的所有支线
        
        Args:
            novel_id: 小说 ID
            status: 可选状态过滤
            branch_type: 可选类型过滤
            
        Returns:
            支线列表
        """
        query = self.session.query(PlotBranch).filter(PlotBranch.novel_id == novel_id)
        
        if status:
            query = query.filter(PlotBranch.status == status)
        if branch_type:
            query = query.filter(PlotBranch.branch_type == branch_type)
        
        return query.order_by(PlotBranch.priority.desc(), PlotBranch.introduce_at_chapter).all()
    
    def get_branches_for_chapter(self, novel_id: int, chapter_number: int) -> List[PlotBranch]:
        """
        获取在指定章节应该激活的支线
        
        Args:
            novel_id: 小说 ID
            chapter_number: 章节号
            
        Returns:
            应激活的支线列表
        """
        return self.session.query(PlotBranch).filter(
            and_(
                PlotBranch.novel_id == novel_id,
                PlotBranch.introduce_at_chapter <= chapter_number,
                PlotBranch.status.in_(["planned", "active"])
            )
        ).order_by(PlotBranch.priority.desc()).all()
    
    def update_branch(self, branch_id: int, **kwargs) -> Optional[PlotBranch]:
        """更新支线信息"""
        branch = self.session.query(PlotBranch).filter(PlotBranch.id == branch_id).first()
        if not branch:
            return None
        
        for key, value in kwargs.items():
            if hasattr(branch, key):
                setattr(branch, key, value)
        
        branch.updated_at = datetime.datetime.utcnow()
        self.session.commit()
        self.session.refresh(branch)
        return branch
    
    def activate_branch(self, branch_id: int) -> Optional[PlotBranch]:
        """激活支线"""
        return self.update_branch(
            branch_id,
            status="active",
            activated_at=datetime.datetime.utcnow()
        )
    
    def complete_branch(self, branch_id: int, ending: str = None) -> Optional[PlotBranch]:
        """完成支线"""
        return self.update_branch(
            branch_id,
            status="completed",
            current_ending=ending,
            progress=1.0,
            completed_at=datetime.datetime.utcnow()
        )
    
    def update_branch_progress(
        self,
        branch_id: int,
        progress: float,
        current_stage: int = None
    ) -> Optional[PlotBranch]:
        """更新支线进度"""
        kwargs = {"progress": min(1.0, max(0.0, progress))}
        if current_stage is not None:
            kwargs["current_stage"] = current_stage
        return self.update_branch(branch_id, **kwargs)
    
    def delete_branch(self, branch_id: int) -> bool:
        """删除支线"""
        branch = self.session.query(PlotBranch).filter(PlotBranch.id == branch_id).first()
        if not branch:
            return False
        self.session.delete(branch)
        self.session.commit()
        return True
    
    # ============ 支线人物关联操作 ============
    
    def add_character_to_branch(
        self,
        branch_id: int,
        character_id: int,
        role_in_branch: str = None,
        involvement_level: str = "major",
        join_at_chapter: int = None,
        branch_specific_traits: Dict = None,
        expected_arc_changes: Dict = None,
        notes: str = None
    ) -> PlotBranchCharacter:
        """
        将人物添加到支线
        
        Args:
            branch_id: 支线 ID
            character_id: 人物 ID
            role_in_branch: 角色在支线中的定位
            involvement_level: 参与程度 (core/major/minor/cameo)
            join_at_chapter: 加入章节
            branch_specific_traits: 支线专属特性
            expected_arc_changes: 预期弧光变化
            notes: 备注
            
        Returns:
            创建的关联对象
        """
        # 检查是否已存在
        existing = self.session.query(PlotBranchCharacter).filter(
            and_(
                PlotBranchCharacter.branch_id == branch_id,
                PlotBranchCharacter.character_id == character_id
            )
        ).first()
        
        if existing:
            # 更新现有关联
            existing.role_in_branch = role_in_branch or existing.role_in_branch
            existing.involvement_level = involvement_level
            existing.join_at_chapter = join_at_chapter
            existing.branch_specific_traits = branch_specific_traits or existing.branch_specific_traits
            existing.expected_arc_changes = expected_arc_changes or existing.expected_arc_changes
            existing.notes = notes or existing.notes
            self.session.commit()
            self.session.refresh(existing)
            return existing
        
        association = PlotBranchCharacter(
            branch_id=branch_id,
            character_id=character_id,
            role_in_branch=role_in_branch,
            involvement_level=involvement_level,
            join_at_chapter=join_at_chapter,
            branch_specific_traits=branch_specific_traits or {},
            expected_arc_changes=expected_arc_changes or {},
            notes=notes
        )
        self.session.add(association)
        self.session.commit()
        self.session.refresh(association)
        return association
    
    def remove_character_from_branch(self, branch_id: int, character_id: int) -> bool:
        """从支线移除人物"""
        association = self.session.query(PlotBranchCharacter).filter(
            and_(
                PlotBranchCharacter.branch_id == branch_id,
                PlotBranchCharacter.character_id == character_id
            )
        ).first()
        
        if not association:
            return False
        
        self.session.delete(association)
        self.session.commit()
        return True
    
    def get_characters_in_branch(self, branch_id: int) -> List[PlotBranchCharacter]:
        """获取支线中的所有人物"""
        return self.session.query(PlotBranchCharacter).filter(
            PlotBranchCharacter.branch_id == branch_id
        ).options(
            joinedload(PlotBranchCharacter.character)
        ).all()
    
    def get_branches_for_character(self, character_id: int) -> List[PlotBranchCharacter]:
        """获取人物参与的所有支线"""
        return self.session.query(PlotBranchCharacter).filter(
            PlotBranchCharacter.character_id == character_id
        ).options(
            joinedload(PlotBranchCharacter.branch)
        ).all()
    
    # ============ 支线道具关联操作 ============
    
    def add_item_to_branch(
        self,
        branch_id: int,
        item_id: int,
        role_in_branch: str = None,
        importance: str = "important",
        appear_at_chapter: int = None,
        branch_specific_powers: Dict = None,
        acquisition_condition: str = None,
        notes: str = None
    ) -> PlotBranchItem:
        """
        将道具添加到支线
        
        Args:
            branch_id: 支线 ID
            item_id: 道具 ID
            role_in_branch: 道具在支线中的角色
            importance: 重要程度 (critical/important/optional)
            appear_at_chapter: 出现章节
            branch_specific_powers: 支线专属能力
            acquisition_condition: 获取条件
            notes: 备注
            
        Returns:
            创建的关联对象
        """
        # 检查是否已存在
        existing = self.session.query(PlotBranchItem).filter(
            and_(
                PlotBranchItem.branch_id == branch_id,
                PlotBranchItem.item_id == item_id
            )
        ).first()
        
        if existing:
            # 更新现有关联
            existing.role_in_branch = role_in_branch or existing.role_in_branch
            existing.importance = importance
            existing.appear_at_chapter = appear_at_chapter
            existing.branch_specific_powers = branch_specific_powers or existing.branch_specific_powers
            existing.acquisition_condition = acquisition_condition or existing.acquisition_condition
            existing.notes = notes or existing.notes
            self.session.commit()
            self.session.refresh(existing)
            return existing
        
        association = PlotBranchItem(
            branch_id=branch_id,
            item_id=item_id,
            role_in_branch=role_in_branch,
            importance=importance,
            appear_at_chapter=appear_at_chapter,
            branch_specific_powers=branch_specific_powers or {},
            acquisition_condition=acquisition_condition,
            notes=notes
        )
        self.session.add(association)
        self.session.commit()
        self.session.refresh(association)
        return association
    
    def remove_item_from_branch(self, branch_id: int, item_id: int) -> bool:
        """从支线移除道具"""
        association = self.session.query(PlotBranchItem).filter(
            and_(
                PlotBranchItem.branch_id == branch_id,
                PlotBranchItem.item_id == item_id
            )
        ).first()
        
        if not association:
            return False
        
        self.session.delete(association)
        self.session.commit()
        return True
    
    def get_items_in_branch(self, branch_id: int) -> List[PlotBranchItem]:
        """获取支线中的所有道具"""
        return self.session.query(PlotBranchItem).filter(
            PlotBranchItem.branch_id == branch_id
        ).options(
            joinedload(PlotBranchItem.item)
        ).all()
    
    def get_branches_for_item(self, item_id: int) -> List[PlotBranchItem]:
        """获取道具关联的所有支线"""
        return self.session.query(PlotBranchItem).filter(
            PlotBranchItem.item_id == item_id
        ).options(
            joinedload(PlotBranchItem.branch)
        ).all()
