"""场景视觉识别模块（框架占位）

职责：OCR + 目标检测 + 多模态语义理解，输出 SceneInfo（见 docs/API_CONTRACT.md 1.3）。
"""
from __future__ import annotations


def scene_analyze(image_path: str) -> dict:
    """分析一张场景图片，返回 SceneInfo。

    TODO 实现链路：
      1. 图像预处理（矫正/增强）
      2. PaddleOCR 文字检测与识别 → ocr_text / ocr_blocks
      3. YOLO 目标检测（展板/红色标识）→ detected_objects
      4. 多模态模型语义理解 → semantic_summary / culture_attributes
      5. 合并输出 SceneInfo
    """
    raise NotImplementedError


def batch_analyze(image_paths: list[str]) -> list[dict]:
    """批量分析多张场景图片。TODO"""
    raise NotImplementedError


def _preprocess(image_path: str) -> str:
    """图像预处理。TODO 内部函数。"""
    raise NotImplementedError
