"""
主支线交织管理仓储模块
提供主线与支线交织点的数据库操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .models import PlotInterweaving, PlotBranch
import datetime


class PlotInterweavingRepository:
    """
    主支线交织仓储类
    实现交织点的 CRUD 和查询操作
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ============ 基础 CRUD 操作 ============
    
    def create(
        self,
        novel_id: int,
        main_plot_chapter: int,
        branch_id: int,
        chapter_number: int,
        interweave_type: str,
        main_plot_description: Optional[str] = None,
        impact_description: Optional[str] = None,
        main_plot_impact: float = 0.5,
        branch_impact: float = 0.5,
        character_changes: Optional[Dict[str, str]] = None
    ) -> PlotInterweaving:
        """
        创建交织点
        
        Args:
            novel_id: 小说 ID
            main_plot_chapter: 主线剧情点章节
            branch_id: 支线 ID
            chapter_number: 交织发生章节
            interweave_type: 交织类型（converge/diverge/parallel/cross/merge）
            main_plot_description: 主线剧情点描述
            impact_description: 交织影响描述
            main_plot_impact: 对主线的影响程度
            branch_impact: 对支线的影响程度
            character_changes: 涉及的角色变化
            
        Returns:
            创建的交织点对象
        """
        interweaving = PlotInterweaving(
            novel_id=novel_id,
            main_plot_chapter=main_plot_chapter,
            main_plot_description=main_plot_description,
            branch_id=branch_id,
            interweave_type=interweave_type,
            chapter_number=chapter_number,
            impact_description=impact_description,
            main_plot_impact=main_plot_impact,
            branch_impact=branch_impact,
            character_changes=character_changes or {},
            status="planned"
        )
        self.session.add(interweaving)
        self.session.commit()
        self.session.refresh(interweaving)
        return interweaving
    
    def get_by_id(self, interweaving_id: int) -> Optional[PlotInterweaving]:
        """根据 ID 获取交织点"""
        return self.session.query(PlotInterweaving).filter(
            PlotInterweaving.id == interweaving_id
        ).first()
    
    def get_by_novel(
        self,
        novel_id: int,
        status: Optional[str] = None
    ) -> List[PlotInterweaving]:
        """
        获取小说的所有交织点
        
        Args:
            novel_id: 小说 ID
            status: 可选，按状态筛选
            
        Returns:
            交织点列表
        """
        query = self.session.query(PlotInterweaving).filter(
            PlotInterweaving.novel_id == novel_id
        )
        if status:
            query = query.filter(PlotInterweaving.status == status)
        return query.order_by(PlotInterweaving.chapter_number).all()
    
    def get_by_chapter(
        self,
        novel_id: int,
        chapter_number: int
    ) -> List[PlotInterweaving]:
        """
        获取特定章节的交织点
        
        Args:
            novel_id: 小说 ID
            chapter_number: 章节号
            
        Returns:
            该章节的交织点列表
        """
        return self.session.query(PlotInterweaving).filter(
            and_(
                PlotInterweaving.novel_id == novel_id,
                PlotInterweaving.chapter_number == chapter_number
            )
        ).all()
    
    def get_by_branch(
        self,
        branch_id: int
    ) -> List[PlotInterweaving]:
        """
        获取特定支线的所有交织点
        
        Args:
            branch_id: 支线 ID
            
        Returns:
            该支线的交织点列表
        """
        return self.session.query(PlotInterweaving).filter(
            PlotInterweaving.branch_id == branch_id
        ).order_by(PlotInterweaving.chapter_number).all()
    
    def update(
        self,
        interweaving_id: int,
        **kwargs
    ) -> Optional[PlotInterweaving]:
        """更新交织点信息"""
        interweaving = self.get_by_id(interweaving_id)
        if not interweaving:
            return None
        for key, value in kwargs.items():
            if hasattr(interweaving, key):
                setattr(interweaving, key, value)
        self.session.commit()
        self.session.refresh(interweaving)
        return interweaving
    
    def delete(self, interweaving_id: int) -> bool:
        """删除交织点"""
        interweaving = self.get_by_id(interweaving_id)
        if not interweaving:
            return False
        self.session.delete(interweaving)
        self.session.commit()
        return True
    
    # ============ 状态管理操作 ============
    
    def activate(self, interweaving_id: int) -> Optional[PlotInterweaving]:
        """
        激活交织点（从 planned 变为 active）
        
        Args:
            interweaving_id: 交织点 ID
            
        Returns:
            更新后的交织点对象
        """
        return self.update(interweaving_id, status="active")
    
    def complete(self, interweaving_id: int) -> Optional[PlotInterweaving]:
        """
        完成交织点
        
        Args:
            interweaving_id: 交织点 ID
            
        Returns:
            更新后的交织点对象
        """
        return self.update(interweaving_id, status="completed")
    
    # ============ 查询操作 ============
    
    def get_upcoming(
        self,
        novel_id: int,
        current_chapter: int,
        lookahead: int = 5
    ) -> List[PlotInterweaving]:
        """
        获取即将发生的交织点
        
        Args:
            novel_id: 小说 ID
            current_chapter: 当前章节
            lookahead: 向前查看的章节数
            
        Returns:
            即将发生的交织点列表
        """
        return self.session.query(PlotInterweaving).filter(
            and_(
                PlotInterweaving.novel_id == novel_id,
                PlotInterweaving.status == "planned",
                PlotInterweaving.chapter_number >= current_chapter,
                PlotInterweaving.chapter_number <= current_chapter + lookahead
            )
        ).order_by(PlotInterweaving.chapter_number).all()
    
    def get_active(self, novel_id: int) -> List[PlotInterweaving]:
        """
        获取当前活跃的交织点
        
        Args:
            novel_id: 小说 ID
            
        Returns:
            活跃的交织点列表
        """
        return self.session.query(PlotInterweaving).filter(
            and_(
                PlotInterweaving.novel_id == novel_id,
                PlotInterweaving.status == "active"
            )
        ).all()
    
    def get_by_type(
        self,
        novel_id: int,
        interweave_type: str
    ) -> List[PlotInterweaving]:
        """
        按交织类型获取交织点
        
        Args:
            novel_id: 小说 ID
            interweave_type: 交织类型
            
        Returns:
            该类型的交织点列表
        """
        return self.session.query(PlotInterweaving).filter(
            and_(
                PlotInterweaving.novel_id == novel_id,
                PlotInterweaving.interweave_type == interweave_type
            )
        ).order_by(PlotInterweaving.chapter_number).all()
    
    def get_statistics(self, novel_id: int) -> Dict[str, Any]:
        """
        获取交织点统计信息
        
        Args:
            novel_id: 小说 ID
            
        Returns:
            统计信息字典
        """
        all_interweavings = self.get_by_novel(novel_id)
        
        status_counts = {"planned": 0, "active": 0, "completed": 0}
        type_counts = {}
        branch_counts = {}
        
        for i in all_interweavings:
            status_counts[i.status] = status_counts.get(i.status, 0) + 1
            type_counts[i.interweave_type] = type_counts.get(i.interweave_type, 0) + 1
            branch_counts[i.branch_id] = branch_counts.get(i.branch_id, 0) + 1
        
        return {
            "total": len(all_interweavings),
            "by_status": status_counts,
            "by_type": type_counts,
            "by_branch": branch_counts,
            "completion_rate": status_counts["completed"] / len(all_interweavings) if all_interweavings else 0
        }
    
    def get_branch_integration_score(self, branch_id: int) -> float:
        """
        计算支线与主线的整合度分数
        基于交织点的数量、类型和影响程度
        
        Args:
            branch_id: 支线 ID
            
        Returns:
            整合度分数 0.0-1.0
        """
        interweavings = self.get_by_branch(branch_id)
        
        if not interweavings:
            return 0.0
        
        # 计算加权分数
        type_weights = {
            "merge": 1.0,      # 融合最高
            "converge": 0.8,   # 汇合次之
            "cross": 0.6,      # 交叉中等
            "parallel": 0.4,   # 平行较低
            "diverge": 0.3     # 分离最低
        }
        
        total_score = 0.0
        for i in interweavings:
            type_weight = type_weights.get(i.interweave_type, 0.5)
            impact_avg = (i.main_plot_impact + i.branch_impact) / 2
            total_score += type_weight * impact_avg
        
        # 归一化到 0-1
        max_possible = len(interweavings) * 1.0  # 全部是 merge 且满影响
        return min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0
