"""业务服务层（框架占位）

各服务仅声明接口签名，实现待各模块就绪后填充。
调用关系见 docs/ARCHITECTURE.md 第 2 节。
"""
from __future__ import annotations

# ---------- 脚本与分镜 ----------

def create_script(title: str, content: str, source: str) -> dict:
    """录入理论脚本。TODO: 实现入库 + 触发解析。"""
    raise NotImplementedError


def generate_storyboard(script_id: str) -> dict:
    """调用 llm 模块生成分镜。TODO"""
    raise NotImplementedError


def edit_shot(storyboard_id: str, shot_id: str, patch: dict) -> dict:
    """人工编辑分镜镜头。TODO"""
    raise NotImplementedError


# ---------- 场景识别 ----------

def analyze_scene(image_path: str) -> dict:
    """调用 vision 模块识别场景。TODO"""
    raise NotImplementedError


# ---------- 素材匹配 ----------

def match_assets(storyboard_id: str) -> dict:
    """调用 aigc 模块匹配/生成素材。TODO"""
    raise NotImplementedError


# ---------- 渲染 ----------

def submit_render_job(storyboard_id: str, scene_ids: list[str]) -> dict:
    """提交渲染任务（异步）。TODO"""
    raise NotImplementedError


def get_render_progress(job_id: str) -> dict:
    """查询渲染进度。TODO"""
    raise NotImplementedError


# ---------- 审核 ----------

def audit_content(target_type: str, target_id: str) -> dict:
    """调用 audit 模块审核。TODO"""
    raise NotImplementedError
