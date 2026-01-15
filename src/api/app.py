from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any
import os
import asyncio
from src.api.routes import chapters, characters, generation, outlines, novels, relationships, world, references, plot_branches
from src.db.base import SessionLocal, engine
from src.config import Config
from src.core.cache import get_cache_manager

app = FastAPI(
    title="NovelGen-Enterprise API",
    description="API for the NovelGen-Enterprise system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(novels.router, prefix="/api/novels", tags=["novels"])
app.include_router(chapters.router, prefix="/api/chapters", tags=["chapters"])
app.include_router(characters.router, prefix="/api/characters", tags=["characters"])
app.include_router(outlines.router, prefix="/api/outlines", tags=["outlines"])
app.include_router(generation.router, prefix="/api/generate", tags=["generation"])
app.include_router(relationships.router, prefix="/api/relationships", tags=["relationships"])
app.include_router(world.router, prefix="/api/world", tags=["world"])
app.include_router(references.router, prefix="/api", tags=["references"])
app.include_router(plot_branches.router, prefix="/api", tags=["plot_branches"])

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    检查数据库、Redis 和 LLM API 的可用性
    
    Returns:
        包含各组件健康状态的字典
    """
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "checks": {}
    }
    
    # 1. 检查数据库连接
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "连接正常"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"连接失败: {str(e)}"
        }
    
    # 2. 检查 Redis 连接
    try:
        cache_manager = get_cache_manager()
        client = await cache_manager.client
        if client:
            await client.ping()
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "连接正常"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "degraded",
                "message": "Redis 不可用，将使用内存缓存"
            }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "degraded",
            "message": f"Redis 连接失败: {str(e)}，将使用内存缓存"
        }
    
    # 3. 检查 LLM API 配置
    try:
        gemini_configured = bool(Config.model.GEMINI_API_KEY)
        deepseek_configured = bool(
            Config.model.DEEPSEEK_API_KEY and 
            Config.model.DEEPSEEK_API_BASE
        )
        
        if gemini_configured or deepseek_configured:
            health_status["checks"]["llm"] = {
                "status": "healthy",
                "message": "LLM API 已配置",
                "gemini_configured": gemini_configured,
                "deepseek_configured": deepseek_configured
            }
        else:
            health_status["status"] = "unhealthy"
            health_status["checks"]["llm"] = {
                "status": "unhealthy",
                "message": "未配置 LLM API"
            }
    except Exception as e:
        health_status["checks"]["llm"] = {
            "status": "unknown",
            "message": f"检查失败: {str(e)}"
        }
    
    # 4. 检查连接池状态
    try:
        from src.db.base import get_pool_stats
        pool_stats = get_pool_stats()
        health_status["checks"]["connection_pool"] = {
            "status": "healthy",
            "stats": pool_stats
        }
    except Exception as e:
        health_status["checks"]["connection_pool"] = {
            "status": "unknown",
            "message": f"无法获取连接池状态: {str(e)}"
        }
    
    # 如果任何关键组件不健康，返回 503
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
