"""
剧情支线 API 路由
提供剧情支线的 RESTful API 接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.services.plot_branch_service import PlotBranchService

router = APIRouter()


# ============ 请求/响应模型 ============

class StageSchema(BaseModel):
    """支线阶段定义"""
    name: str
    description: str
    chapter_range: List[int] = Field(default_factory=list, description="[start_chapter, end_chapter]")


class EndingSchema(BaseModel):
    """支线结局定义"""
    key: str
    name: str
    description: str
    conditions: Optional[List[str]] = None


class CreateBranchRequest(BaseModel):
    """创建支线请求"""
    branch_key: str = Field(..., description="支线唯一标识，如 'revenge_arc'")
    name: str = Field(..., description="支线名称")
    description: Optional[str] = None
    branch_type: str = Field(default="side", description="支线类型: main/side/hidden/parallel")
    introduce_at_chapter: Optional[int] = Field(None, description="在第几章引入")
    introduce_condition: Optional[str] = Field(None, description="引入条件描述")
    priority: int = Field(default=5, ge=1, le=10, description="优先级 1-10")
    objectives: Optional[List[str]] = Field(None, description="目标列表")
    possible_endings: Optional[List[Dict]] = Field(None, description="可能的结局")
    stages: Optional[List[Dict]] = Field(None, description="阶段定义")


class CreateBranchWithAssociationsRequest(CreateBranchRequest):
    """创建支线并关联人物道具请求"""
    characters: Optional[List[Dict]] = Field(
        None, 
        description="关联的人物列表 [{'character_id': 1, 'role_in_branch': '...', ...}]"
    )
    items: Optional[List[Dict]] = Field(
        None,
        description="关联的道具列表 [{'item_id': 1, 'role_in_branch': '...', ...}]"
    )


class UpdateBranchRequest(BaseModel):
    """更新支线请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    branch_type: Optional[str] = None
    introduce_at_chapter: Optional[int] = None
    introduce_condition: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    objectives: Optional[List[str]] = None
    possible_endings: Optional[List[Dict]] = None
    stages: Optional[List[Dict]] = None
    status: Optional[str] = None


class UpdateProgressRequest(BaseModel):
    """更新进度请求"""
    progress: float = Field(..., ge=0.0, le=1.0)
    current_stage: Optional[int] = None


class AddCharacterRequest(BaseModel):
    """添加人物到支线请求"""
    character_id: int
    role_in_branch: Optional[str] = Field(None, description="角色定位：主导者/对手/协助者等")
    involvement_level: str = Field(default="major", description="参与程度: core/major/minor/cameo")
    join_at_chapter: Optional[int] = None
    branch_specific_traits: Optional[Dict] = Field(None, description="支线专属特性")
    expected_arc_changes: Optional[Dict] = Field(None, description="预期弧光变化")
    notes: Optional[str] = None


class AddItemRequest(BaseModel):
    """添加道具到支线请求"""
    item_id: int
    role_in_branch: Optional[str] = Field(None, description="道具角色：麦高芬/关键钥匙/奖励等")
    importance: str = Field(default="important", description="重要程度: critical/important/optional")
    appear_at_chapter: Optional[int] = None
    branch_specific_powers: Optional[Dict] = Field(None, description="支线专属能力")
    acquisition_condition: Optional[str] = Field(None, description="获取条件")
    notes: Optional[str] = None


class CompleteBranchRequest(BaseModel):
    """完成支线请求"""
    ending: Optional[str] = Field(None, description="选择的结局")


# ============ 支线管理接口 ============

@router.post("/novels/{novel_id}/branches")
async def create_branch(novel_id: int, request: CreateBranchRequest):
    """
    为小说创建剧情支线
    
    创建一条新的剧情支线，可以指定引入时机、优先级、阶段等信息。
    """
    result = PlotBranchService.create_branch(
        novel_id=novel_id,
        branch_key=request.branch_key,
        name=request.name,
        description=request.description,
        branch_type=request.branch_type,
        introduce_at_chapter=request.introduce_at_chapter,
        introduce_condition=request.introduce_condition,
        priority=request.priority,
        objectives=request.objectives,
        possible_endings=request.possible_endings,
        stages=request.stages
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/novels/{novel_id}/branches/full")
async def create_branch_with_associations(novel_id: int, request: CreateBranchWithAssociationsRequest):
    """
    创建剧情支线并同时关联人物和道具
    
    一次性创建支线及其所有关联，适合批量操作。
    """
    result = PlotBranchService.create_branch_with_associations(
        novel_id=novel_id,
        branch_key=request.branch_key,
        name=request.name,
        description=request.description,
        branch_type=request.branch_type,
        introduce_at_chapter=request.introduce_at_chapter,
        introduce_condition=request.introduce_condition,
        priority=request.priority,
        objectives=request.objectives,
        possible_endings=request.possible_endings,
        stages=request.stages,
        characters=request.characters,
        items=request.items
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/novels/{novel_id}/branches")
async def get_novel_branches(
    novel_id: int,
    status: Optional[str] = Query(None, description="过滤状态: planned/active/completed/abandoned"),
    branch_type: Optional[str] = Query(None, description="过滤类型: main/side/hidden/parallel")
):
    """
    获取小说的所有剧情支线
    
    可选按状态或类型过滤。
    """
    return PlotBranchService.get_novel_branches(novel_id, status, branch_type)


@router.get("/novels/{novel_id}/branches/active")
async def get_active_branches_for_chapter(
    novel_id: int,
    chapter: int = Query(..., description="章节号")
):
    """
    获取在指定章节应激活的支线
    
    返回所有 introduce_at_chapter <= chapter 的支线。
    """
    return PlotBranchService.get_active_branches_for_chapter(novel_id, chapter)


@router.get("/branches/{branch_id}")
async def get_branch(branch_id: int):
    """
    获取支线详情
    
    返回支线完整信息，包括关联的人物和道具。
    """
    branch = PlotBranchService.get_branch(branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="支线不存在")
    return branch


@router.put("/branches/{branch_id}")
async def update_branch(branch_id: int, request: UpdateBranchRequest):
    """
    更新支线信息
    """
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    result = PlotBranchService.update_branch(branch_id, **update_data)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/branches/{branch_id}/activate")
async def activate_branch(branch_id: int):
    """
    激活支线
    
    将支线状态设为 active，记录激活时间。
    """
    result = PlotBranchService.activate_branch(branch_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/branches/{branch_id}/complete")
async def complete_branch(branch_id: int, request: CompleteBranchRequest):
    """
    完成支线
    
    将支线状态设为 completed，可指定最终结局。
    """
    result = PlotBranchService.complete_branch(branch_id, request.ending)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.put("/branches/{branch_id}/progress")
async def update_branch_progress(branch_id: int, request: UpdateProgressRequest):
    """
    更新支线进度
    """
    result = PlotBranchService.update_branch_progress(
        branch_id, 
        request.progress, 
        request.current_stage
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: int):
    """
    删除支线
    
    同时删除所有关联的人物和道具关系。
    """
    result = PlotBranchService.delete_branch(branch_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


# ============ 支线人物关联接口 ============

@router.post("/branches/{branch_id}/characters")
async def add_character_to_branch(branch_id: int, request: AddCharacterRequest):
    """
    将人物添加到支线
    
    定义人物在该支线中的角色和参与程度。
    """
    result = PlotBranchService.add_character_to_branch(
        branch_id=branch_id,
        character_id=request.character_id,
        role_in_branch=request.role_in_branch,
        involvement_level=request.involvement_level,
        join_at_chapter=request.join_at_chapter,
        branch_specific_traits=request.branch_specific_traits,
        expected_arc_changes=request.expected_arc_changes,
        notes=request.notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/branches/{branch_id}/characters")
async def get_branch_characters(branch_id: int):
    """
    获取支线中的所有人物
    """
    return PlotBranchService.get_branch_characters(branch_id)


@router.delete("/branches/{branch_id}/characters/{character_id}")
async def remove_character_from_branch(branch_id: int, character_id: int):
    """
    从支线移除人物
    """
    result = PlotBranchService.remove_character_from_branch(branch_id, character_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/characters/{character_id}/branches")
async def get_character_branches(character_id: int):
    """
    获取人物参与的所有支线
    """
    return PlotBranchService.get_character_branches(character_id)


# ============ 支线道具关联接口 ============

@router.post("/branches/{branch_id}/items")
async def add_item_to_branch(branch_id: int, request: AddItemRequest):
    """
    将道具添加到支线
    
    定义道具在该支线中的角色和重要程度。
    """
    result = PlotBranchService.add_item_to_branch(
        branch_id=branch_id,
        item_id=request.item_id,
        role_in_branch=request.role_in_branch,
        importance=request.importance,
        appear_at_chapter=request.appear_at_chapter,
        branch_specific_powers=request.branch_specific_powers,
        acquisition_condition=request.acquisition_condition,
        notes=request.notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/branches/{branch_id}/items")
async def get_branch_items(branch_id: int):
    """
    获取支线中的所有道具
    """
    return PlotBranchService.get_branch_items(branch_id)


@router.delete("/branches/{branch_id}/items/{item_id}")
async def remove_item_from_branch(branch_id: int, item_id: int):
    """
    从支线移除道具
    """
    result = PlotBranchService.remove_item_from_branch(branch_id, item_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result
