"""脚本管理路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db

router = APIRouter(prefix="/scripts", tags=["scripts"])


class ScriptIn(BaseModel):
    title: str
    content: str
    source: str = "manual"


@router.post("")
def create_script(body: ScriptIn):
    if not body.content.strip():
        raise HTTPException(400, "脚本内容不能为空")
    return db.insert_script(body.title.strip() or "未命名脚本", body.content, body.source)


@router.get("")
def list_scripts():
    return db.list_scripts()


@router.get("/{sid}")
def get_script(sid: str):
    s = db.get_script(sid)
    if not s:
        raise HTTPException(404, "脚本不存在")
    return s
