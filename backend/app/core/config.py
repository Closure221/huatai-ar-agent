"""全局配置（v2）

所有路径基于项目根目录，无硬编码密钥。
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # 项目根
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"      # 用户上传的场景图
ASSET_DIR = DATA_DIR / "assets"        # 素材库 / AIGC 生成物
OUTPUT_DIR = DATA_DIR / "outputs"      # 成片视频
MODEL_DIR = DATA_DIR / "models"        # 下载的模型权重
GALLERY_DIR = DATA_DIR / "gallery"     # 内置示例图库（供前端选用）
USER_ASSET_DIR = DATA_DIR / "assets" / "user"   # 用户上传素材池（多图）
DB_PATH = DATA_DIR / "huatai_ar.db"

for d in (UPLOAD_DIR, ASSET_DIR, OUTPUT_DIR, MODEL_DIR, GALLERY_DIR, USER_ASSET_DIR):
    d.mkdir(parents=True, exist_ok=True)
