"""内容审核模块（MVP：敏感词规则 + LLM 语义复核）

audit_text(content) -> {passed, sensitive_words, reasons, detail}
注意：自动审核仅作辅助，最终政治内容合规责任由人工终审承担（前端提供审核记录）。
"""
from __future__ import annotations

import re
import threading
from typing import Optional

# 基础不当表述词库（谨慎维护：只放明显违规/错误表述，不放正常政治术语）
SENSITIVE_WORDS = [
    # 错误表述 / 不当称谓（示例，可按需扩充）
    "邪恶的社会主义", "共产党是错的", "否定党的领导",
    # 违规内容
    "颠覆国家政权", "分裂国家", "邪教",
    # 低俗不当
    "色情", "赌博", "毒品交易",
]

_model = None
_tokenizer = None
_lock = threading.Lock()

LLM_PROMPT = """你是内容审核员。判断下面的政治理论宣讲文本是否存在政治表述错误、不当内容或敏感违规信息。
只回答两个词：合规 或 不合规。
文本：
{text}"""


def _sensitive_word_check(text: str) -> list[str]:
    return [w for w in SENSITIVE_WORDS if w in text]


def _llm_check(text: str) -> dict:
    """LLM 语义复核：文本被截断到 400 字，返回 {flagged, reason}"""
    try:
        from app.modules.storyboard import _load_model, _model, _tokenizer

        _load_model()
        prompt = LLM_PROMPT.format(text=text[:400])
        inputs = _tokenizer(prompt, return_tensors="pt")
        import torch

        with torch.no_grad():
            outputs = _model.generate(
                **inputs, max_new_tokens=16, do_sample=False,
                pad_token_id=_tokenizer.eos_token_id,
            )
        raw = _tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        flagged = "不合规" in raw
        return {"flagged": flagged, "reason": raw.strip()[:60]}
    except Exception:  # noqa: BLE001
        return {"flagged": False, "reason": "LLM 复核不可用，跳过"}


def audit_text(content: str) -> dict:
    """审核文本，返回结构化结果"""
    if not content:
        return {
            "passed": True, "sensitive_words": [], "reasons": ["内容为空"],
            "detail": {}, "mode": "rule",
        }
    hits = _sensitive_word_check(content)
    llm = _llm_check(content)

    reasons = []
    if hits:
        reasons.append(f"命中敏感词: {', '.join(hits)}")
    if llm["flagged"]:
        reasons.append(f"LLM 语义复核提示: {llm['reason']}")
    if not reasons:
        reasons.append("未命中敏感词，LLM 语义复核未发现异常")

    passed = not hits and not llm["flagged"]
    return {
        "passed": passed,
        "sensitive_words": hits,
        "reasons": reasons,
        "detail": {"llm": llm},
        "mode": "rule+llm",
    }
