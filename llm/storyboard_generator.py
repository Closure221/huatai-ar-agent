"""LLM 脚本理解与分镜生成模块（框架占位）

职责：要点提取 + 分镜生成，输出 Storyboard（见 docs/API_CONTRACT.md 1.2）。
"""
from __future__ import annotations


def generate_storyboard(script_text: str, style: str = "political") -> dict:
    """输入理论脚本，输出分镜脚本 Storyboard。

    TODO 实现链路：
      1. 要点提取（核心论点/关键数据/案例）
      2. 叙事结构解析
      3. 分镜生成（JSON Schema 强约束，Few-shot 示例）
      4. AR 元素标注（哪些镜头需 AR、叠加什么）
      5. 输出校验 + 失败自动重试
    """
    raise NotImplementedError


def extract_key_points(script_text: str) -> list[str]:
    """提取脚本要点列表。TODO"""
    raise NotImplementedError


def _build_prompt(script_text: str, schema: dict) -> str:
    """构造分镜生成 Prompt。TODO"""
    raise NotImplementedError
