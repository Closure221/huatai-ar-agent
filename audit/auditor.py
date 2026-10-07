"""内容审核模块（框架占位）

职责：文本合规 + 图像安全 + 人工审核流转 + 审计日志，输出 AuditResult（见 API_CONTRACT 1.5）。
"""
from __future__ import annotations


def audit(content: str | dict, target_type: str) -> dict:
    """审核任意内容（script/storyboard/asset/video），返回 AuditResult。

    TODO 实现链路：
      1. 文本：敏感词库命中 + LLM 语义审查（政治表述准确性）
      2. 图像：NSFW 检测 + 违规内容识别
      3. 视频：抽帧检测
      4. 汇总 → 自动通过 or 转人工
      5. 审计日志全量留存（追加式，不可篡改）
    """
    raise NotImplementedError


def submit_human_review(audit_id: str, conclusion: str, comment: str, reviewer: str) -> dict:
    """人工审核结论回填。TODO"""
    raise NotImplementedError


def _sensitive_word_check(text: str) -> list[str]:
    """敏感词命中检测。TODO"""
    raise NotImplementedError


def _llm_semantic_check(text: str) -> dict:
    """LLM 语义合规审查。TODO"""
    raise NotImplementedError
