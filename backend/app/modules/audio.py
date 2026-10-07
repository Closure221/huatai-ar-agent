"""AI 配音合成模块（MVP：edge-tts 微软在线 TTS + ffmpeg 混流）

流程：把分镜全部旁白合成一段 mp3 语音 → 与已渲染的无音轨成片混流。
输出写独立路径（禁止覆盖输入文件，避免 Windows 文件锁导致静默失败），
并校验输出确含 Audio 流；失败则返回原路径兜底。
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import cv2
import imageio_ffmpeg

VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓：自然清晰女声
RATE = "+0%"

_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _norm_rate(rate: str) -> str:
    """edge-tts rate 参数规范化：'0%' -> '+0%'（edge-tts 不接受无符号百分数）"""
    rate = (rate or "").strip()
    if not rate:
        return "+0%"
    if rate.endswith("%") and rate[0].isdigit():
        return "+" + rate
    return rate


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # errors="replace"：避免 ffmpeg 输出在 GBK 控制台下解码崩溃
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


async def _synth_async(text: str, out: str | Path, voice: str = VOICE, rate: str = RATE) -> None:
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=_norm_rate(rate))
    await com.save(str(out))


def synth_mp3(text: str, out: str | Path, voice: str = VOICE, rate: str = RATE, retries: int = 2) -> bool:
    """合成一段语音 mp3，成功返回 True；网络波动自动重试"""
    for attempt in range(retries + 1):
        try:
            asyncio.run(_synth_async(text, out, voice, rate))
            if Path(out).exists() and Path(out).stat().st_size > 0:
                return True
        except Exception as e:  # noqa: BLE001
            if attempt >= retries:
                print("[audio] tts error: %s" % e, flush=True)
    return False


def video_duration_sec(path: str | Path) -> float:
    """用 OpenCV 读取视频总时长（秒）"""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return frames / fps if frames and fps else 0.0


def _has_audio_stream(video_path: str | Path) -> bool:
    """用 ffmpeg 探测文件是否含音轨"""
    r = _run([_FFMPEG, "-i", str(video_path)])
    return "Audio:" in r.stderr


def mux_narration(video_path: str | Path,
                  narration_text: str,
                  out_path: str | Path | None = None,
                  voice: str = VOICE, rate: str = RATE) -> str:
    """给无音轨成片加上 AI 旁白，返回最终路径（成功则带音轨，失败返回原路径）"""
    src = Path(video_path)
    if out_path is None:
        out_path = src.with_name(src.stem + "_voiced" + src.suffix)
    dst = Path(out_path)

    text = (narration_text or "").strip()
    if not text:
        print("[audio] mux: empty narration, fallback raw", flush=True)
        # 无旁白内容：直接兜底原片
        if dst != src and dst.exists():
            try:
                dst.unlink()
            except Exception:  # noqa: BLE001
                pass
        return str(src)

    tmpdir = tempfile.mkdtemp(prefix="ht_audio_")
    mp3 = Path(tmpdir) / "narration.mp3"
    try:
        if not synth_mp3(text, mp3, voice, rate):
            print("[audio] mux: tts fail, fallback raw", flush=True)
            return str(src)
        dur = video_duration_sec(src)
        if dur <= 0:
            print("[audio] mux: dur<=0 (%.2f), fallback raw" % dur, flush=True)
            return str(src)
        dur_s = int(dur)
        r = _run([
            _FFMPEG, "-y",
            "-i", str(src),
            "-i", str(mp3),
            "-filter_complex", "[1:a]apad[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(dur_s),
            "-shortest",
            str(dst),
        ])
        # 只有输出文件存在、有大小、且探测出音轨才算成功
        if (r.returncode == 0 and dst.exists() and dst.stat().st_size > 0
                and _has_audio_stream(dst)):
            return str(dst)
        print("[audio] mux: ffmpeg fail rc=%s size=%s hasaudio=%s" % (
            r.returncode, dst.stat().st_size if dst.exists() else -1,
            _has_audio_stream(dst) if dst.exists() else "na"), flush=True)
        if dst.exists():
            try:
                dst.unlink()
            except Exception:  # noqa: BLE001
                pass
        return str(src)
    except Exception:  # noqa: BLE001
        if dst.exists():
            try:
                dst.unlink()
            except Exception:  # noqa: BLE001
                pass
        return str(src)


def build_narration_text(shots: list[dict]) -> str:
    """把每个镜头的旁白拼接成整段朗读文本"""
    parts = []
    for s in shots or []:
        n = (s.get("narration") or "").strip()
        if n:
            parts.append(n)
    return "。\n".join(parts)


def mux_shot_narration(video_path: str | Path,
                       shots: list[dict],
                       out_path: str | Path | None = None,
                       voice: str = VOICE, rate: str = RATE) -> str:
    """逐镜头配音（音画同步）：每镜旁白单独 TTS，按镜头累计时间点 adelay 对齐混流。

    相比整段配音，每个镜头的旁白从该镜头开始时间播放，语音与画面内容同步。
    失败时回退整段配音（mux_narration），再失败返回原片。
    """
    src = Path(video_path)
    if out_path is None:
        out_path = src.with_name(src.stem + "_voiced" + src.suffix)
    dst = Path(out_path)

    if not shots:
        return mux_narration(video_path, "", out_path, voice, rate)

    tmpdir = tempfile.mkdtemp(prefix="ht_audio_")
    try:
        # 1) 逐镜 TTS，记录 (mp3, 起始毫秒)
        inputs = []
        t_ms = 0
        for i, s in enumerate(shots):
            text = (s.get("narration") or "").strip()
            dur_ms = max(int(s.get("duration_sec", 6) * 1000), 3000)
            if text:
                mp3 = Path(tmpdir) / f"shot_{i}.mp3"
                if synth_mp3(text, mp3, voice, rate):
                    inputs.append((mp3, t_ms))
            t_ms += dur_ms
        if not inputs:
            print("[audio] mux_shot: no tts segments, fallback raw", flush=True)
            return str(src)

        # 2) ffmpeg：逐段 adelay 到镜头起始时间，amix 合并
        cmd = [_FFMPEG, "-y", "-loglevel", "error", "-i", str(src)]
        for mp3, _ in inputs:
            cmd += ["-i", str(mp3)]
        filters = []
        for i, (mp3, start_ms) in enumerate(inputs):
            filters.append(f"[{i + 1}:a]adelay={start_ms}|{start_ms}[a{i}]")
        mix_in = "".join(f"[a{i}]" for i in range(len(inputs)))
        # duration=longest：输出持续到最后一个语音段结束（first 会把后续镜头语音全裁掉）；
        # normalize=0：保持各段原始音量，不做归一化（各镜头时段不重叠，安全）
        filters.append(f"{mix_in}amix=inputs={len(inputs)}:duration=longest:dropout_transition=0:normalize=0[aout]")
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(dst)]
        r = _run(cmd)
        if (r.returncode == 0 and dst.exists() and dst.stat().st_size > 0
                and _has_audio_stream(dst)):
            return str(dst)
        print("[audio] mux_shot ffmpeg fail rc=%s size=%s" % (
            r.returncode, dst.stat().st_size if dst.exists() else -1), flush=True)
        if dst.exists():
            try:
                dst.unlink()
            except Exception:  # noqa: BLE001
                pass
        # 3) fallback：整段配音
        text = build_narration_text(shots)
        if text:
            return mux_narration(video_path, text, out_path, voice, rate)
        return str(src)
    except Exception as e:  # noqa: BLE001
        print("[audio] mux_shot err: %s" % e, flush=True)
        if dst.exists():
            try:
                dst.unlink()
            except Exception:  # noqa: BLE001
                pass
        return str(src)
