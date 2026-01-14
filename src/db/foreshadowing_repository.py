"""
伏笔管理仓储模块
提供伏笔生命周期管理的数据库操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .models import Foreshadowing, ForeshadowingLink
import datetime


class ForeshadowingRepository:
    """
    伏笔仓储类
    实现伏笔的 CRUD 和生命周期管理
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ============ 基础 CRUD 操作 ============
    
    def create(
        self,
        novel_id: int,
        content: str,
        created_at_chapter: int,
        branch_id: str = "main",
        hint_text: Optional[str] = None,
        expected_resolve_chapter: Optional[int] = None,
        importance: int = 5,
        foreshadowing_type: str = "plot",
        related_characters: Optional[List[str]] = None,
        related_items: Optional[List[str]] = None,
        resolve_condition: Optional[str] = None
    ) -> Foreshadowing:
        """
        创建新伏笔
        
        Args:
            novel_id: 小说 ID
            content: 伏笔内容描述
            created_at_chapter: 埋设章节
            branch_id: 分支 ID
            hint_text: 暗示文本
            expected_resolve_chapter: 预期回收章节
            importance: 重要性 1-10
            foreshadowing_type: 伏笔类型
            related_characters: 相关角色
            related_items: 相关道具
            resolve_condition: 回收条件
            
        Returns:
            创建的伏笔对象
        """
        foreshadowing = Foreshadowing(
            novel_id=novel_id,
            branch_id=branch_id,
            content=content,
            hint_text=hint_text,
            created_at_chapter=created_at_chapter,
            expected_resolve_chapter=expected_resolve_chapter,
            importance=importance,
            foreshadowing_type=foreshadowing_type,
            related_characters=related_characters or [],
            related_items=related_items or [],
            resolve_condition=resolve_condition,
            status="planted",
            advancement_log=[]
        )
        self.session.add(foreshadowing)
        self.session.commit()
        self.session.refresh(foreshadowing)
        return foreshadowing
    
    def get_by_id(self, foreshadowing_id: int) -> Optional[Foreshadowing]:
        """根据 ID 获取伏笔"""
        return self.session.query(Foreshadowing).filter(
            Foreshadowing.id == foreshadowing_id
        ).first()
    
    def get_by_novel(
        self,
        novel_id: int,
        branch_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Foreshadowing]:
        """
        获取小说的伏笔列表
        
        Args:
            novel_id: 小说 ID
            branch_id: 可选，按分支筛选
            status: 可选，按状态筛选
            
        Returns:
            伏笔列表
        """
        query = self.session.query(Foreshadowing).filter(
            Foreshadowing.novel_id == novel_id
        )
        if branch_id:
            query = query.filter(Foreshadowing.branch_id == branch_id)
        if status:
            query = query.filter(Foreshadowing.status == status)
        return query.order_by(Foreshadowing.created_at_chapter).all()
    
    def update(
        self,
        foreshadowing_id: int,
        **kwargs
    ) -> Optional[Foreshadowing]:
        """更新伏笔信息"""
        foreshadowing = self.get_by_id(foreshadowing_id)
        if not foreshadowing:
            return None
        for key, value in kwargs.items():
            if hasattr(foreshadowing, key):
                setattr(foreshadowing, key, value)
        self.session.commit()
        self.session.refresh(foreshadowing)
        return foreshadowing
    
    def delete(self, foreshadowing_id: int) -> bool:
        """删除伏笔"""
        foreshadowing = self.get_by_id(foreshadowing_id)
        if not foreshadowing:
            return False
        self.session.delete(foreshadowing)
        self.session.commit()
        return True
    
    # ============ 生命周期管理操作 ============
    
    def advance(
        self,
        foreshadowing_id: int,
        chapter: int,
        description: str
    ) -> Optional[Foreshadowing]:
        """
        推进伏笔
        记录伏笔在某章节的推进情况
        
        Args:
            foreshadowing_id: 伏笔 ID
            chapter: 推进章节
            description: 推进描述
            
        Returns:
            更新后的伏笔对象
        """
        foreshadowing = self.get_by_id(foreshadowing_id)
        if not foreshadowing:
            return None
        
        # 更新状态为已推进
        foreshadowing.status = "advanced"
        
        # 添加推进记录
        log = foreshadowing.advancement_log or []
        log.append({
            "chapter": chapter,
            "description": description,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        foreshadowing.advancement_log = log
        
        self.session.commit()
        self.session.refresh(foreshadowing)
        return foreshadowing
    
    def resolve(
        self,
        foreshadowing_id: int,
        chapter: int,
        quality_score: Optional[float] = None,
        feedback: Optional[str] = None
    ) -> Optional[Foreshadowing]:
        """
        回收伏笔
        
        Args:
            foreshadowing_id: 伏笔 ID
            chapter: 回收章节
            quality_score: 回收质量评分 0.0-1.0
            feedback: 回收反馈
            
        Returns:
            更新后的伏笔对象
        """
        foreshadowing = self.get_by_id(foreshadowing_id)
        if not foreshadowing:
            return None
        
        foreshadowing.status = "resolved"
        foreshadowing.actual_resolve_chapter = chapter
        foreshadowing.resolved_at = datetime.datetime.utcnow()
        
        if quality_score is not None:
            foreshadowing.resolve_quality_score = quality_score
        if feedback:
            foreshadowing.resolve_feedback = feedback
        
        self.session.commit()
        self.session.refresh(foreshadowing)
        return foreshadowing
    
    def abandon(
        self,
        foreshadowing_id: int,
        reason: Optional[str] = None
    ) -> Optional[Foreshadowing]:
        """
        放弃伏笔
        
        Args:
            foreshadowing_id: 伏笔 ID
            reason: 放弃原因
            
        Returns:
            更新后的伏笔对象
        """
        foreshadowing = self.get_by_id(foreshadowing_id)
        if not foreshadowing:
            return None
        
        foreshadowing.status = "abandoned"
        if reason:
            foreshadowing.resolve_feedback = f"放弃原因：{reason}"
        
        self.session.commit()
        self.session.refresh(foreshadowing)
        return foreshadowing
    
    # ============ 查询操作 ============
    
    def get_active(
        self,
        novel_id: int,
        branch_id: str = "main"
    ) -> List[Foreshadowing]:
        """
        获取活跃的伏笔（已埋设或已推进，未回收）
        
        Args:
            novel_id: 小说 ID
            branch_id: 分支 ID
            
        Returns:
            活跃伏笔列表
        """
        return self.session.query(Foreshadowing).filter(
            and_(
                Foreshadowing.novel_id == novel_id,
                Foreshadowing.branch_id == branch_id,
                Foreshadowing.status.in_(["planted", "advanced"])
            )
        ).order_by(Foreshadowing.importance.desc()).all()
    
    def get_overdue(
        self,
        novel_id: int,
        current_chapter: int,
        branch_id: str = "main"
    ) -> List[Foreshadowing]:
        """
        获取过期未回收的伏笔
        
        Args:
            novel_id: 小说 ID
            current_chapter: 当前章节
            branch_id: 分支 ID
            
        Returns:
            过期伏笔列表
        """
        return self.session.query(Foreshadowing).filter(
            and_(
                Foreshadowing.novel_id == novel_id,
                Foreshadowing.branch_id == branch_id,
                Foreshadowing.status.in_(["planted", "advanced"]),
                Foreshadowing.expected_resolve_chapter.isnot(None),
                Foreshadowing.expected_resolve_chapter < current_chapter
            )
        ).order_by(Foreshadowing.importance.desc()).all()
    
    def get_due_soon(
        self,
        novel_id: int,
        current_chapter: int,
        lookahead: int = 3,
        branch_id: str = "main"
    ) -> List[Foreshadowing]:
        """
        获取即将到期的伏笔
        
        Args:
            novel_id: 小说 ID
            current_chapter: 当前章节
            lookahead: 向前查看的章节数
            branch_id: 分支 ID
            
        Returns:
            即将到期的伏笔列表
        """
        return self.session.query(Foreshadowing).filter(
            and_(
                Foreshadowing.novel_id == novel_id,
                Foreshadowing.branch_id == branch_id,
                Foreshadowing.status.in_(["planted", "advanced"]),
                Foreshadowing.expected_resolve_chapter.isnot(None),
                Foreshadowing.expected_resolve_chapter >= current_chapter,
                Foreshadowing.expected_resolve_chapter <= current_chapter + lookahead
            )
        ).order_by(Foreshadowing.expected_resolve_chapter).all()
    
    def get_by_character(
        self,
        novel_id: int,
        character_name: str
    ) -> List[Foreshadowing]:
        """获取与特定角色相关的伏笔"""
        # 注意：JSON 查询方式可能因数据库而异
        all_foreshadowings = self.session.query(Foreshadowing).filter(
            Foreshadowing.novel_id == novel_id
        ).all()
        
        return [
            f for f in all_foreshadowings
            if f.related_characters and character_name in f.related_characters
        ]
    
    def get_statistics(
        self,
        novel_id: int,
        branch_id: str = "main"
    ) -> Dict[str, Any]:
        """
        获取伏笔统计信息
        
        Args:
            novel_id: 小说 ID
            branch_id: 分支 ID
            
        Returns:
            统计信息字典
        """
        all_foreshadowings = self.get_by_novel(novel_id, branch_id)
        
        status_counts = {"planted": 0, "advanced": 0, "resolved": 0, "abandoned": 0}
        type_counts = {}
        total_importance = 0
        resolved_quality = []
        
        for f in all_foreshadowings:
            status_counts[f.status] = status_counts.get(f.status, 0) + 1
            type_counts[f.foreshadowing_type] = type_counts.get(f.foreshadowing_type, 0) + 1
            total_importance += f.importance or 0
            if f.resolve_quality_score is not None:
                resolved_quality.append(f.resolve_quality_score)
        
        return {
            "total": len(all_foreshadowings),
            "by_status": status_counts,
            "by_type": type_counts,
            "avg_importance": total_importance / len(all_foreshadowings) if all_foreshadowings else 0,
            "avg_resolve_quality": sum(resolved_quality) / len(resolved_quality) if resolved_quality else None,
            "active_count": status_counts["planted"] + status_counts["advanced"],
            "resolution_rate": status_counts["resolved"] / len(all_foreshadowings) if all_foreshadowings else 0
        }


class ForeshadowingLinkRepository:
    """
    伏笔链条仓储类
    管理伏笔之间的关联关系
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        parent_id: int,
        child_id: int,
        link_type: str,
        notes: Optional[str] = None
    ) -> ForeshadowingLink:
        """
        创建伏笔链接
        
        Args:
            parent_id: 父伏笔 ID
            child_id: 子伏笔 ID
            link_type: 链接类型（derives_from/requires/blocks/parallel/contradicts）
            notes: 备注
            
        Returns:
            创建的链接对象
        """
        link = ForeshadowingLink(
            parent_id=parent_id,
            child_id=child_id,
            link_type=link_type,
            notes=notes
        )
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link
    
    def get_children(self, parent_id: int) -> List[ForeshadowingLink]:
        """获取父伏笔的所有子伏笔链接"""
        return self.session.query(ForeshadowingLink).filter(
            ForeshadowingLink.parent_id == parent_id
        ).all()
    
    def get_parents(self, child_id: int) -> List[ForeshadowingLink]:
        """获取子伏笔的所有父伏笔链接"""
        return self.session.query(ForeshadowingLink).filter(
            ForeshadowingLink.child_id == child_id
        ).all()
    
    def get_blocking_dependencies(
        self,
        foreshadowing_id: int,
        foreshadowing_repo: ForeshadowingRepository
    ) -> List[Foreshadowing]:
        """
        获取阻止回收的依赖伏笔
        检查是否有 requires 类型的父伏笔尚未回收
        
        Args:
            foreshadowing_id: 要回收的伏笔 ID
            foreshadowing_repo: 伏笔仓储实例
            
        Returns:
            阻止回收的伏笔列表
        """
        parent_links = self.session.query(ForeshadowingLink).filter(
            and_(
                ForeshadowingLink.child_id == foreshadowing_id,
                ForeshadowingLink.link_type == "requires"
            )
        ).all()
        
        blocking = []
        for link in parent_links:
            parent = foreshadowing_repo.get_by_id(link.parent_id)
            if parent and parent.status not in ["resolved", "abandoned"]:
                blocking.append(parent)
        
        return blocking
    
    def delete(self, link_id: int) -> bool:
        """删除链接"""
        link = self.session.query(ForeshadowingLink).filter(
            ForeshadowingLink.id == link_id
        ).first()
        if not link:
            return False
        self.session.delete(link)
        self.session.commit()
        return True
