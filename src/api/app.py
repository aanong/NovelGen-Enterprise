from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from src.api.routes import chapters, characters, generation, outlines, novels, relationships, world, references, plot_branches

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
