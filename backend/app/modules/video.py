"""视频合成模块 v4（PPT 幻灯片模式 · 字幕底部）

每镜头一页 PPT：
- 顶部：AR 角标 + 脚本标题 + 页码
- 中部：素材大图区（1-4 张网格，互不遮挡；无素材时显示正文大段）
- 底部：字幕条（旁白文字，半透明深色条居中，最多 3 行）——字幕在底下，不在中间
背景：场景图铺底 + 轻压暗 + 主题色渐变（整体提亮，保证可读性）。
视频 = PPT 翻页（淡入淡出）+ 逐镜头配音（音画同步，时长按旁白字数估计）。
"""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.config import OUTPUT_DIR
from app.modules import assets

DEFAULT_FPS = 24
RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080)}
LIBRARY_DIR = assets.ASSET_DIR / "library"

FONT = next(
    (c for c in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]
     if os.path.exists(c)),
    None,
)


def _font(size: int):
    return ImageFont.truetype(FONT, size)


def _theme_accent(scene: dict) -> tuple:
    attrs = scene.get("culture_attributes") or {}
    theme = (attrs.get("theme") or "") + " " + (attrs.get("category") or "")
    table = [
        (("国防", "军工", "军事", "强军"), (214, 178, 92)),
        (("国家安全", "国安", "保密", "反谍"), (96, 168, 255)),
        (("反诈", "诈骗", "防骗"), (255, 196, 84)),
        (("二十大", "现代化", "政治理论"), (242, 193, 78)),
        (("党史", "党建", "红色"), (255, 190, 84)),
        (("思政", "青年", "学习社"), (96, 220, 200)),
        (("法治", "宪法", "普法"), (122, 184, 255)),
        (("廉政", "清廉"), (140, 226, 200)),
        (("核心价值", "价值观"), (242, 190, 120)),
    ]
    for kws, color in table:
        if any(k in theme for k in kws):
            return color
    return (242, 193, 78)


def _wrap_text(text: str, font, max_w: int, max_lines: int = 6) -> list[str]:
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > max_w:
            if cur:
                lines.append(cur)
                cur = ch
            else:
                cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def _load_bg(scene: dict, W: int, H: int, accent: tuple | None = None) -> Image.Image:
    """PPT 背景（提亮版）：场景图铺底 + 轻压暗 + 主题色渐变蒙层"""
    path = scene.get("source_image", "")
    if path and Path(path).exists():
        img = Image.open(path).convert("RGB")
    else:
        img = Image.new("RGB", (W, H), (34, 40, 60))
    img = img.resize((W, H), Image.LANCZOS)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    # 28% 压暗（可读性），比 v3 的 55% 大幅提亮
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([0, 0, W, H], fill=72)
    img = Image.composite(black, img, mask)
    # 主题色渐变（顶部略亮）
    if accent:
        tint = Image.new("RGB", (W, H), tuple(int(c * 0.55) for c in accent))
        grad = Image.new("L", (W, H), 0)
        dg = ImageDraw.Draw(grad)
        for i in range(H):
            a = int(18 * (1 - i / H))
            dg.line([(0, i), (W, i)], fill=a)
        img = Image.composite(tint, img, grad)
    return img


def _paste_photo(frame: Image.Image, img: Image.Image, x: int, y: int, w: int, h: int,
                 radius: int = 14, border: int = 4) -> None:
    """PPT 图片框：缩放 + 圆角 + 白边 + 阴影"""
    img = img.resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    card = Image.new("RGB", (w + border * 2, h + border * 2), (255, 255, 255))
    card.paste(img, (border, border), mask)
    shadow = Image.new("RGBA", (w + border * 4, h + border * 4), (0, 0, 0, 70))
    frame.paste(shadow, (x - border, y - border + 4), shadow)
    frame.paste(card, (x, y))


def _load_photo(slug: str) -> Image.Image | None:
    """按 slug 从 用户素材池 -> 本地图库 -> 网图缓存 加载图片"""
    for d in (assets.USER_DIR, LIBRARY_DIR, assets.AUTO_DIR):
        ap = d / f"{slug}.jpg"
        if ap.exists():
            try:
                return Image.open(ap).convert("RGB")
            except Exception:  # noqa: BLE001
                return None
    return None


def _compose_ppt_frame(bg: Image.Image, shot: dict, scene: dict,
                       idx: int, total: int, opts: dict, accent: tuple,
                       title: str) -> Image.Image:
    W, H = bg.size
    frame = bg.copy()
    draw = ImageDraw.Draw(frame, "RGBA")
    show_sub = bool(opts.get("subtitle", True))
    user_assets = shot.get("assets") or []
    n = len(user_assets)

    # ---------- 顶部标题栏 ----------
    bar_h = int(H * 0.095)
    r = int(bar_h * 0.30)
    cx, cy = 40, int(bar_h * 0.5) + 20
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
    draw.ellipse([cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3], outline=(255, 255, 255), width=2)
    draw.text((cx - 9, cy - 15), "AR", font=_font(int(r * 1.15)), fill=(255, 255, 255))
    tt = (title or "宣讲视频")[:18]
    draw.text((82, int(bar_h * 0.24) + 18), tt, font=_font(int(H * 0.044)), fill=(255, 255, 255))
    pg = f"{idx} / {total}"
    fp = _font(int(H * 0.038))
    twp = draw.textlength(pg, font=fp)
    draw.text((W - twp - 40, int(bar_h * 0.42) + 14), pg, font=fp, fill=accent)
    draw.line([(28, bar_h + 10), (W - 28, bar_h + 10)], fill=accent + (100,), width=2)

    # ---------- 中部：素材大图区 ----------
    narration = shot.get("narration") or shot.get("scene_desc") or ""
    img_top = bar_h + 34
    sub_h = int(H * 0.16)          # 底部字幕条预留
    img_bottom = H - sub_h - 18
    gx0, gy0 = 74, img_top
    gx1, gy1 = W - 74, img_bottom

    if n == 0:
        # 无素材：正文大段居中
        fs = int(H * 0.052)
        font = _font(fs)
        lines = _wrap_text(narration, font, (gx1 - gx0) - 40, 7)
        y = (gy0 + gy1) // 2 - len(lines) * int(fs * 1.5) // 2
        for line in lines:
            tw2 = draw.textlength(line, font=font)
            draw.text(((W - tw2) / 2, y), line, font=font, fill=(246, 249, 255))
            y += int(fs * 1.6)
        if lines:
            tw2 = draw.textlength(lines[0], font=font)
            draw.line([(W / 2 - tw2 / 2, y), (W / 2 + tw2 / 2, y)], fill=accent, width=3)
    elif n == 1:
        photo = _load_photo(user_assets[0])
        if photo:
            _paste_photo(frame, photo, gx0, gy0, gx1 - gx0, gy1 - gy0)
    elif n == 2:
        gw = (gx1 - gx0 - 16) // 2
        for k in range(2):
            photo = _load_photo(user_assets[k])
            if photo:
                _paste_photo(frame, photo, gx0 + k * (gw + 16), gy0, gw, gy1 - gy0)
    else:
        # 3-4 张：2x2 网格
        gw = (gx1 - gx0 - 16) // 2
        gh = (gy1 - gy0 - 16) // 2
        for k in range(min(n, 4)):
            photo = _load_photo(user_assets[k])
            if photo:
                col, row = k % 2, k // 2
                _paste_photo(frame, photo, gx0 + col * (gw + 16), gy0 + row * (gh + 16), gw, gh)

    # ---------- 底部：字幕条（放底下） ----------
    if show_sub and narration:
        fs = int(H * 0.042)
        font = _font(fs)
        lines = _wrap_text(narration, font, int(W * 0.84), 3)
        bar_h2 = int(fs * 1.55) * len(lines) + 26
        y0 = H - bar_h2 - 16
        draw.rounded_rectangle([int(W * 0.06), y0, int(W * 0.94), H - 10],
                               radius=14, fill=(6, 10, 20, 178),
                               outline=accent + (140,), width=2)
        draw.rounded_rectangle([int(W * 0.06), y0, int(W * 0.06) + 6, H - 10],
                               radius=3, fill=accent + (255,))
        y = y0 + 12
        for line in lines:
            tw2 = draw.textlength(line, font=font)
            draw.text(((W - tw2) / 2, y), line, font=font, fill=(255, 255, 255))
            y += int(fs * 1.55)

    return frame


def _write_with_ffmpeg(frames: list, out_path: Path, W: int, H: int, fps: int, crf: int):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
        "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for arr in frames:
        proc.stdin.write(np.ascontiguousarray(arr).tobytes())
    proc.stdin.close()
    return proc.wait()


def _write_with_cv2(frames: list, out_path: Path, W: int, H: int, fps: int):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (W, H))
    for arr in frames:
        writer.write(arr)
    writer.release()


def _fade_between(prev: np.ndarray, nxt: np.ndarray, n: int) -> list[np.ndarray]:
    out = []
    prev_f = prev.astype(np.float32)
    nxt_f = nxt.astype(np.float32)
    for i in range(1, n + 1):
        a = i / (n + 1)
        out.append((prev_f * (1 - a) + nxt_f * a).astype(np.uint8))
    return out


def render(storyboard: dict, scene: dict, opts: dict | None = None) -> str:
    """渲染成片视频（PPT 模式 v4），返回输出路径"""
    opts = opts or {}
    W, H = RESOLUTIONS.get(opts.get("resolution", "1080p"), RESOLUTIONS["1080p"])
    fps = int(opts.get("fps", DEFAULT_FPS))
    crf = int(opts.get("crf", 20))

    shots = storyboard.get("shots") or []
    if not shots:
        raise ValueError("分镜为空，无法渲染")
    title = storyboard.get("title") or "未命名宣讲视频"

    accent = _theme_accent(scene)
    bg = _load_bg(scene, W, H, accent)
    total = len(shots)

    frames: list[np.ndarray] = []
    prev_frame = None
    fade_n = int(fps * 0.4)
    for idx, shot in enumerate(shots, 1):
        frame_img = _compose_ppt_frame(bg, shot, scene, idx, total, opts, accent, title)
        frame = np.array(frame_img)
        n_frames = max(int(shot.get("duration_sec", 6) * fps), fps)
        if prev_frame is not None:
            frames.extend(_fade_between(prev_frame, frame, fade_n))
        frames.extend([frame] * (n_frames - fade_n))
        prev_frame = frame

    out_path = OUTPUT_DIR / f"ar_video_{storyboard['id']}_{uuid.uuid4().hex[:6]}.mp4"
    try:
        rc = _write_with_ffmpeg(frames, out_path, W, H, fps, crf)
        if rc != 0 or not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError("ffmpeg rc=%s" % rc)
    except Exception:  # noqa: BLE001
        _write_with_cv2(frames, out_path, W, H, fps)
    return str(out_path)
