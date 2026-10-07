"""华泰杯 AR 视觉识别智能体 — 后端入口（v2）

运行: python backend/run_server.py 或 start.bat
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR, GALLERY_DIR
from app.db import init_db
from app.routers import scripts, storyboards, scenes, videos, audits, rewrite, assets

init_db()

app = FastAPI(
    title="华泰杯 AR 视觉识别智能体 API",
    version="2.0.0",
    description="理论脚本输入 → 高清 AR 视频成片输出（v2：1080p/H.264/自定义/扩写/图库）",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "stage": "v4"}


app.include_router(scripts.router, prefix="/api/v1")
app.include_router(storyboards.router, prefix="/api/v1")
app.include_router(scenes.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")
app.include_router(audits.router, prefix="/api/v1")
app.include_router(rewrite.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")

# 用户素材池静态访问
user_dir = BASE_DIR / "data" / "assets" / "user"
if user_dir.exists():
    app.mount("/user_assets", StaticFiles(directory=str(user_dir)), name="user_assets")

# AR 素材库静态访问（供前端「素材选择器」展示）
lib_dir = BASE_DIR / "data" / "assets" / "library"
if lib_dir.exists():
    app.mount("/library_assets", StaticFiles(directory=str(lib_dir)), name="library_assets")

# 内置示例图库（供前端「图库」tab 直接选用）
if GALLERY_DIR.exists():
    app.mount("/gallery", StaticFiles(directory=str(GALLERY_DIR)), name="gallery")

# 前端静态页面（必须最后挂载，避免吞掉 API 路由）
frontend_dir = BASE_DIR / "frontend" / "web"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="web")
