"""
资料库管理 API
支持为小说添加、查询、删除资料库
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.deps import get_db
from src.db.models import Novel, ReferenceMaterial
from src.utils import get_embedding
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class ReferenceMaterialCreate(BaseModel):
    """创建资料库条目"""
    title: str
    content: str
    source: Optional[str] = None
    category: Optional[str] = None  # world_setting, plot_trope, character_archetype, style
    tags: Optional[List[str]] = None


class ReferenceMaterialResponse(BaseModel):
    """资料库条目响应"""
    id: int
    title: str
    content: str
    source: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    novel_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class ReferenceMaterialUpdate(BaseModel):
    """更新资料库条目"""
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/novels/{novel_id}/references", response_model=ReferenceMaterialResponse)
def add_reference_to_novel(
    novel_id: int,
    reference: ReferenceMaterialCreate,
    db: Session = Depends(get_db)
):
    """
    为指定小说添加资料库条目
    """
    # 验证小说存在
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail=f"Novel with ID {novel_id} not found")
    
    # 检查是否已存在相同标题的资料
    existing = db.query(ReferenceMaterial).filter(
        ReferenceMaterial.novel_id == novel_id,
        ReferenceMaterial.title == reference.title
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Reference material with title '{reference.title}' already exists for this novel"
        )
    
    # 生成 embedding
    try:
        embedding = get_embedding(reference.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")
    
    # 创建资料库条目
    ref_material = ReferenceMaterial(
        title=reference.title,
        content=reference.content,
        source=reference.source,
        category=reference.category,
        tags=reference.tags or [],
        novel_id=novel_id,
        embedding=embedding
    )
    
    db.add(ref_material)
    db.commit()
    db.refresh(ref_material)
    
    return ref_material


@router.get("/novels/{novel_id}/references", response_model=List[ReferenceMaterialResponse])
def get_novel_references(
    novel_id: int,
    category: Optional[str] = Query(None, description="过滤分类"),
    db: Session = Depends(get_db)
):
    """
    获取指定小说的资料库列表
    """
    # 验证小说存在
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail=f"Novel with ID {novel_id} not found")
    
    query = db.query(ReferenceMaterial).filter(ReferenceMaterial.novel_id == novel_id)
    
    if category:
        query = query.filter(ReferenceMaterial.category == category)
    
    references = query.order_by(ReferenceMaterial.created_at.desc()).all()
    return references


@router.get("/references/{reference_id}", response_model=ReferenceMaterialResponse)
def get_reference(
    reference_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个资料库条目
    """
    reference = db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()
    if not reference:
        raise HTTPException(status_code=404, detail="Reference material not found")
    return reference


@router.put("/references/{reference_id}", response_model=ReferenceMaterialResponse)
def update_reference(
    reference_id: int,
    reference_update: ReferenceMaterialUpdate,
    db: Session = Depends(get_db)
):
    """
    更新资料库条目
    """
    reference = db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()
    if not reference:
        raise HTTPException(status_code=404, detail="Reference material not found")
    
    # 更新字段
    update_data = reference_update.dict(exclude_unset=True)
    
    # 如果内容更新，需要重新生成 embedding
    if "content" in update_data:
        try:
            update_data["embedding"] = get_embedding(update_data["content"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")
    
    for key, value in update_data.items():
        setattr(reference, key, value)
    
    db.commit()
    db.refresh(reference)
    return reference


@router.delete("/references/{reference_id}")
def delete_reference(
    reference_id: int,
    db: Session = Depends(get_db)
):
    """
    删除资料库条目
    """
    reference = db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()
    if not reference:
        raise HTTPException(status_code=404, detail="Reference material not found")
    
    db.delete(reference)
    db.commit()
    return {"message": "Reference material deleted successfully"}


@router.post("/novels/{novel_id}/references/batch", response_model=List[ReferenceMaterialResponse])
def batch_add_references_to_novel(
    novel_id: int,
    references: List[ReferenceMaterialCreate],
    db: Session = Depends(get_db)
):
    """
    批量为小说添加资料库条目
    """
    # 验证小说存在
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail=f"Novel with ID {novel_id} not found")
    
    created_refs = []
    errors = []
    
    for ref_data in references:
        # 检查是否已存在
        existing = db.query(ReferenceMaterial).filter(
            ReferenceMaterial.novel_id == novel_id,
            ReferenceMaterial.title == ref_data.title
        ).first()
        
        if existing:
            errors.append(f"'{ref_data.title}' already exists")
            continue
        
        try:
            # 生成 embedding
            embedding = get_embedding(ref_data.content)
            
            # 创建资料库条目
            ref_material = ReferenceMaterial(
                title=ref_data.title,
                content=ref_data.content,
                source=ref_data.source,
                category=ref_data.category,
                tags=ref_data.tags or [],
                novel_id=novel_id,
                embedding=embedding
            )
            
            db.add(ref_material)
            created_refs.append(ref_material)
        except Exception as e:
            errors.append(f"Failed to create '{ref_data.title}': {str(e)}")
    
    db.commit()
    
    # 刷新所有创建的对象
    for ref in created_refs:
        db.refresh(ref)
    
    if errors:
        return {
            "created": created_refs,
            "errors": errors,
            "message": f"Created {len(created_refs)} references, {len(errors)} errors"
        }
    
    return created_refs


@router.get("/references/global", response_model=List[ReferenceMaterialResponse])
def get_global_references(
    category: Optional[str] = Query(None, description="过滤分类"),
    db: Session = Depends(get_db)
):
    """
    获取全局资料库（未关联特定小说的资料）
    """
    query = db.query(ReferenceMaterial).filter(ReferenceMaterial.novel_id.is_(None))
    
    if category:
        query = query.filter(ReferenceMaterial.category == category)
    
    references = query.order_by(ReferenceMaterial.created_at.desc()).all()
    return references
