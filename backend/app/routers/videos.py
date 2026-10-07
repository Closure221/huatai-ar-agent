"""视频生成与下载路由（v2：支持画质/配音自定义参数）"""
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import db
from app.modules import audio as audio_mod
from app.modules import video as video_mod

router = APIRouter(prefix="/videos", tags=["videos"])

VALID_VOICES = {
    "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunyangNeural",
    "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiaNeural",
}


class RenderIn(BaseModel):
    storyboard_id: str
    scene_id: str
    # 自定义项（前端设置面板传入，全部可选）
    resolution: str = "1080p"      # 720p / 1080p
    fps: int = 24
    crf: int = 20                  # 画质（越小越清晰，18-28）
    subtitle: bool = True          # 是否显示字幕条
    voice: str = "zh-CN-XiaoxiaoNeural"   # AI 配音音色
    rate: str = "+0%"              # 语速：-20% ~ +50%
    assets_map: dict | None = None # 镜头素材多选：{"镜头序号": ["flag","rocket",...]}
    user_assets: list | None = None # 用户素材池（自动配图优先使用）


@router.post("")
def create_video(body: RenderIn):
    sb = db.get_storyboard(body.storyboard_id)
    scene = db.get_scene(body.scene_id)
    if not sb:
        raise HTTPException(404, "分镜不存在")
    if not scene:
        raise HTTPException(404, "场景不存在")
    if body.resolution not in ("720p", "1080p"):
        raise HTTPException(400, "分辨率仅支持 720p / 1080p")
    if body.crf < 14 or body.crf > 32:
        raise HTTPException(400, "画质参数(crf)需在 14-32 之间")
    if body.voice not in VALID_VOICES:
        raise HTTPException(400, f"不支持的配音音色: {body.voice}")
    if body.fps not in (24, 30):
        raise HTTPException(400, "帧率仅支持 24/30")
    record = db.insert_video(body.storyboard_id, body.scene_id)
    vid = record["id"]

    def _render():
        try:
            shots = sb.get("shots") or []
            opts = {
                "resolution": body.resolution,
                "fps": body.fps,
                "crf": body.crf,
                "subtitle": body.subtitle,
            }
            # 1) 自动配图：未手动选素材的镜头按关键词自动配（用户素材池优先 -> 图库 -> 网图）
            from app.modules import assets as assets_mod
            assets_mod.auto_fill_assets(shots, body.user_assets or None)
            # 2) 注入用户手动多选素材（覆盖自动配图）
            if body.assets_map:
                for s in shots:
                    key = str(s.get("index"))
                    if key in body.assets_map:
                        s["assets"] = body.assets_map[key]
            # 2) 渲染高清无音轨成片
            raw_path = video_mod.render(sb, scene, opts)
            # 3) 逐镜头配音（自定义音色/语速），按镜头时间点对齐实现音画同步
            final_path = audio_mod.mux_shot_narration(raw_path, shots,
                                                      voice=body.voice, rate=body.rate)
            db.update_video(vid, path=str(final_path), status="done")
        except Exception as e:  # noqa: BLE001
            db.update_video(vid, status="failed", path="", error=str(e)[:500])

    threading.Thread(target=_render, daemon=True).start()
    return db.get_video(vid)


@router.get("")
def list_videos():
    return db.list_videos()


@router.get("/{vid}")
def get_video(vid: str):
    v = db.get_video(vid)
    if not v:
        raise HTTPException(404, "视频不存在")
    return v


@router.get("/{vid}/download")
def download_video(vid: str):
    v = db.get_video(vid)
    if not v or not v["path"] or not Path(v["path"]).exists():
        raise HTTPException(404, "成片不存在或尚未生成")
    return FileResponse(v["path"], media_type="video/mp4", filename=f"ar_video_{vid}.mp4")
