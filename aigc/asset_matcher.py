"""AIGC 素材匹配与生成模块（框架占位）

职责：素材需求解析 → 素材库检索复用 → AIGC 生成 → 质量校验，输出 AssetPack（见 API_CONTRACT 1.4）。
"""
from __future__ import annotations


def match_assets(storyboard: dict) -> dict:
    """输入 Storyboard，输出 AssetPack。

    TODO 实现链路：
      1. 解析每个镜头的素材需求（关键词/风格/尺寸）
      2. 素材库检索（MinIO），命中复用
      3. 未命中 → AIGC 生成（文生图 SDXL / 文生视频 SVD）
      4. 质量校验（分辨率/风格一致性/合规预检）
      5. 镜头-素材绑定
    """
    raise NotImplementedError


def generate_image(prompt: str, style: str, size: tuple[int, int]) -> str:
    """文生图，返回素材路径。TODO"""
    raise NotImplementedError


def generate_video(prompt: str, first_frame: str | None) -> str:
    """文生视频，返回素材路径。TODO"""
    raise NotImplementedError
