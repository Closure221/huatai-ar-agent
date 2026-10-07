"""场景识别路由"""
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app import db
from app.core.config import UPLOAD_DIR
from app.modules import vision

router = APIRouter(prefix="/scenes", tags=["scenes"])

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/analyze")
def analyze_scene(file: UploadFile = File(...)):
    """上传场景图片，OCR + 文化属性识别"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"不支持的图片格式: {ext}")
    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "图片过大，最大支持 10MB")
    if not data:
        raise HTTPException(400, "空文件，请上传有效图片")
    fname = f"{uuid.uuid4().hex[:8]}{ext}"
    path = UPLOAD_DIR / fname
    path.write_bytes(data)
    try:
        result = vision.analyze(str(path))
    except Exception as e:  # noqa: BLE001
        # 识别失败时清理已落盘文件，避免残留垃圾
        try:
            path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        # 输入内容非图片（如伪 PNG）与 OCR 前端错误区分处理
        raise HTTPException(422, f"无法从该图片识别内容: {e}")
    scene = db.insert_scene(
        source_image=str(path),
        ocr_text=result["ocr_text"],
        culture_attributes=result["culture_attributes"],
        semantic_summary=result["semantic_summary"],
    )
    return scene


@router.get("")
def list_scenes():
    return db.list_scenes()


@router.get("/{sid}")
def get_scene(sid: str):
    s = db.get_scene(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    return s
