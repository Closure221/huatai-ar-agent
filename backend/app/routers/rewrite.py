"""文案扩写路由（v2 新增）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules import rewrite as rewrite_mod

router = APIRouter(prefix="/scripts", tags=["scripts"])


class ExpandIn(BaseModel):
    content: str
    title: str = ""
    mode: str = "expand"          # expand / polish / keypoints
    length: str = "medium"        # short / medium / long


@router.post("/expand")
def expand_script(body: ExpandIn):
    """文案自动扩写/润色/要点提取（LLM 优先，规则兜底）"""
    if not body.content.strip():
        raise HTTPException(400, "内容不能为空")
    try:
        result = rewrite_mod.expand(
            content=body.content,
            title=body.title,
            mode=body.mode,
            length=body.length,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"扩写失败: {e}")
    if not result["text"]:
        raise HTTPException(500, "扩写结果为空")
    return result
