"""分镜生成路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.modules import storyboard as sb_mod

router = APIRouter(prefix="/storyboards", tags=["storyboards"])


class GenIn(BaseModel):
    script_id: str
    max_shots: int | None = None   # 自定义镜头数量(3-8)，缺省由 LLM 决定


@router.post("")
def generate_storyboard(body: GenIn):
    """由脚本生成分镜（同步执行，耗时可能较长）"""
    script = db.get_script(body.script_id)
    if not script:
        raise HTTPException(404, "脚本不存在")
    if body.max_shots is not None and not (3 <= body.max_shots <= 8):
        raise HTTPException(400, "镜头数量需在 3-8 之间")
    try:
        result = sb_mod.generate(
            script["content"], script["title"],
            max_shots=body.max_shots,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"分镜生成失败: {e}")
    sb = db.insert_storyboard(
        script_id=script["id"],
        title=result["title"],
        key_points=result["key_points"],
        shots=result["shots"],
        duration=result["total_duration_sec"],
    )
    db.update_script_status(script["id"], "storyboarded")
    return sb


@router.get("")
def list_storyboards():
    return db.list_storyboards()


@router.get("/{sid}")
def get_storyboard(sid: str):
    sb = db.get_storyboard(sid)
    if not sb:
        raise HTTPException(404, "分镜不存在")
    return sb
