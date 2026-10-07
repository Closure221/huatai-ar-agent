"""审核路由（MVP：自动审核 + 人工结论）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.modules import audit as audit_mod

router = APIRouter(prefix="/audits", tags=["audits"])


class AuditIn(BaseModel):
    target_type: str  # script / storyboard / video
    target_id: str
    content: str      # 待审文本（脚本/分镜描述/字幕）
    title: str = ""


@router.post("")
def run_audit(body: AuditIn):
    """对文本内容跑自动审核（敏感词 + LLM 语义）"""
    try:
        result = audit_mod.audit_text(body.content)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"审核失败: {e}")
    record = db.insert_audit(body.target_type, body.target_id, result,
                             "passed" if result["passed"] else "rejected")
    return record


@router.get("")
def list_audits():
    return db.list_audits()
