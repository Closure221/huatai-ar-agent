"""AR 素材库路由（v2.1 新增）

GET /api/v1/assets/library：列出内置素材（data/assets/library/*.jpg）
"""
import uuid
from pathlib import Path

from fastapi import APIRouter

from app.core.config import ASSET_DIR

router = APIRouter(prefix="/assets", tags=["assets"])

LIBRARY_DIR = ASSET_DIR / "library"

# slug -> (显示名, 标签)
LIB_META = {
    "flag": ("国旗", "爱国·红色"),
    "greatwall": ("长城", "山河·中华"),
    "tiananmen": ("天安门", "山河·中华"),
    "rocket": ("航天火箭", "科技·强国"),
    "technology": ("科技网络", "科技·强国"),
    "campus": ("校园", "青春·校园"),
    "citynight": ("城市夜景", "发展·成就"),
    "mountain": ("壮美山河", "山河·中华"),
    "dove": ("和平鸽", "和平·和谐"),
    "law": ("法治", "法治·公平"),
    "police": ("警察", "安全·守护"),
    "shield": ("盾牌", "安全·守护"),
    "sunrise": ("日出", "希望·奋进"),
    "books": ("书籍", "学习·成长"),
    "soldier": ("军人", "国防·强军"),
    "megaphone": ("宣传喇叭", "宣传·动员"),
}


@router.get("/library")
def list_library() -> list[dict]:
    """返回素材列表（名称/标签/缩略图 URL）"""
    items = []
    if LIBRARY_DIR.exists():
        for f in sorted(LIBRARY_DIR.glob("*.jpg")):
            slug = f.stem
            label, tag = LIB_META.get(slug, (slug, "素材"))
            items.append({
                "name": slug,
                "label": label,
                "tag": tag,
                "url": f"/library_assets/{f.name}",
            })
    return items


# ---------- 用户素材池 ----------

from fastapi import UploadFile, File
from app.modules import assets as assets_mod

ALLOWED_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@router.post("/upload")
def upload_user_assets(files: list[UploadFile] = File(...)):
    """上传用户素材（多张图片，统一转 jpg 进素材池）"""
    import io
    from PIL import Image as PILImage
    saved = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in ALLOWED_IMG:
            continue
        data = f.file.read()
        if not data or len(data) > 15 * 1024 * 1024:
            continue
        try:
            img = PILImage.open(io.BytesIO(data)).convert("RGB")
            name = "user_" + uuid.uuid4().hex[:10] + ".jpg"
            img.save(assets_mod.USER_DIR / name, "JPEG", quality=90)
            saved.append(name.rsplit(".", 1)[0])
        except Exception:  # noqa: BLE001
            continue
    return {"saved": saved, "total": len(saved)}


@router.get("/user")
def list_user_assets() -> list[dict]:
    """用户素材池列表"""
    out = []
    if assets_mod.USER_DIR.exists():
        for f in sorted(assets_mod.USER_DIR.glob("*.jpg")):
            out.append({"name": f.stem, "label": "我的素材", "tag": "我的上传",
                        "url": "/user_assets/" + f.name})
    return out
