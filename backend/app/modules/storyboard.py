"""分镜生成模块 v2.1（长脚本全覆盖）

- LLM 优先：短脚本单批生成；长脚本按句分批生成后拼接，保证覆盖全文
- 规则兜底：按全文句子逐镜生成（超长自动合并），不再截断前半段
- max_shots 可自定义总镜头数(3-8)，数量对齐
"""
from __future__ import annotations

import json
import math
import re
import threading
from typing import Optional

# 模型相对路径约定（相对各候选 data 根目录）
MODEL_DIR_HINT = "data/models/models/Qwen--Qwen2.5-0.5B-Instruct/snapshots/master"
# 相对约定路径（覆盖 ModelScope 双层 models 与手动单层放置两种情况）
MODEL_REL_CANDIDATES = [
    "models/models/Qwen--Qwen2.5-0.5B-Instruct/snapshots/master",
    "models/Qwen--Qwen2.5-0.5B-Instruct/snapshots/master",
    "data/models/models/Qwen--Qwen2.5-0.5B-Instruct/snapshots/master",
]

_model = None
_tokenizer = None
_model_lock = threading.Lock()

SYSTEM_PROMPT = """你是校园宣传视频的分镜导演，擅长把宣讲脚本转化为可视化分镜。
请围绕校园宣传栏、理论学习展板、红色文化阵地、国防教育场景、反诈宣传等场景设计画面。
只输出合法 JSON，不要输出任何其他文字。JSON 格式：
{"key_points":["要点1","要点2"],"shots":[{"index":1,"scene_desc":"画面描述","narration":"旁白一句话","ar_overlay":"AR叠加元素描述","duration_sec":6}],"total_duration_sec":30}"""

MAX_SENTENCES = 16  # 规则兜底单镜头句子数安全上限


def _has_weights(snap_dir) -> bool:
    from pathlib import Path
    d = Path(snap_dir)
    return any((d / n).exists() for n in
               ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json"))


def _find_model_dir():
    """按优先级定位模型目录，保证项目整体移动/复制后仍可用。"""
    from pathlib import Path

    from app.core.config import BASE_DIR

    data_roots = [BASE_DIR / "data", BASE_DIR / "backend" / "data"]
    for root in data_roots:
        for rel in MODEL_REL_CANDIDATES:
            cand = root / rel
            if cand.exists() and _has_weights(cand):
                return cand
    for root in data_roots:
        rec = root / "models" / "qwen_path.txt"
        if rec.exists():
            p = Path((rec.read_text(encoding="utf-8") or "").strip())
            if p and p.exists() and _has_weights(p):
                return p
    for root in data_roots:
        mdl = root / "models"
        if mdl.exists():
            snaps = [s for s in sorted(mdl.rglob("snapshots")) if s.is_dir() and _has_weights(s)]
            for s in snaps:
                if s.name == "master":
                    return s
            if snaps:
                return snaps[0]
    raise FileNotFoundError("未找到 Qwen 模型目录，请先运行 backend/download_model.py")


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_dir = _find_model_dir()
        _tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
        _model = AutoModelForCausalLM.from_pretrained(
            str(model_dir), trust_remote_code=True, torch_dtype="auto"
        )
        _model.eval()


# ---------- 文本拆句（全文覆盖） ----------

def _split_sentences(text: str) -> list[str]:
    """把宣讲稿全文拆成完整句子。

    - 按句号/感叹号/问号/分号/换行切分，保留完整句
    - 引号/书名号/括号未配对（奇数个）时不拆，并入下一句，避免把引语拦腰截断
    - 句数不足时再按逗号/顿号拆子句（保证长脚本能覆盖全文）
    """
    text = (text or "").replace("\r", "")
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        paras = [text.strip()]
    sents = []
    for p in paras:
        parts = re.split(r"[。！？；\n]", p)
        parts = [x.strip() for x in parts if x.strip()]
        # 引号/括号配对保护：奇数则与下一段合并
        merged = []
        i = 0
        while i < len(parts):
            cur = parts[i]
            while i + 1 < len(parts) and _unbalanced(cur):
                i += 1
                cur += parts[i]
            merged.append(cur)
            i += 1
        sents += [m for m in merged if len(m) >= 6]
    if len(sents) < 3:
        subs = []
        for s in sents:
            parts = re.split(r"[，,、：:]", s)
            sub = [x.strip() for x in parts if len(x.strip()) >= 5]
            subs.extend(sub if len(sub) > 1 else [s])
        if len(subs) >= len(sents):
            sents = subs
    return sents or [text[:60]]


def _unbalanced(s: str) -> bool:
    """引号/括号/书名号是否未配对（奇数）"""
    pairs = [("“", "”"), ("‘", "’"), ("「", "」"), ("『", "』"), ("（", "）"), ("《", "》")]
    for a, b in pairs:
        if (s.count(a) + s.count(b)) % 2 == 1:
            return True
    return False


def _merge_to(sents: list[str], n: int) -> list[str]:
    """把句子均匀合并成 n 段（相邻合并，保证全文覆盖）"""
    if len(sents) <= n:
        return sents
    out = []
    per = math.ceil(len(sents) / n)
    for i in range(0, len(sents), per):
        chunk = sents[i:i + per]
        out.append("，".join(chunk))
    return out[:n]


# ---------- LLM 生成 ----------

def _llm_generate_once(content: str, title: str, max_shots: int | None = None) -> dict | None:
    """单次 LLM 生成并解析，失败返回 None"""
    import torch

    user = f"脚本标题：{title}\n脚本内容：\n{content}"
    if max_shots:
        user += f"\n\n注意：最多只输出 {max_shots} 个镜头。"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    try:
        text = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:  # noqa: BLE001
        text = f"{SYSTEM_PROMPT}\n用户：{user}\n助手："
    inputs = _tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=640,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
            pad_token_id=_tokenizer.eos_token_id,
        )
    gen = outputs[0][inputs["input_ids"].shape[1]:]
    raw = _tokenizer.decode(gen, skip_special_tokens=True)

    start = raw.find("{")
    if start == -1:
        return None
    for end in range(len(raw) - 1, start - 1, -1):
        if raw[end] == "}":
            try:
                data = json.loads(raw[start:end + 1])
                break
            except Exception:  # noqa: BLE001
                continue
    else:
        return None
    shots = data.get("shots") or []
    if not shots:
        return None
    if max_shots:
        shots = shots[:max_shots]
    norm = []
    for i, s in enumerate(shots, 1):
        norm.append({
            "index": i,
            "scene_desc": str(s.get("scene_desc", "")).strip() or "校园宣传栏前展示主题内容",
            "narration": str(s.get("narration", "")).strip()[:160],
            "ar_overlay": str(s.get("ar_overlay", "")).strip() or "主题文字卡片",
            "duration_sec": min(max(int(s.get("duration_sec", 6)), 3), 12),
            "transition": "fade",
        })
    total = data.get("total_duration_sec") or sum(s["duration_sec"] for s in norm)
    return {
        "key_points": [str(k).strip() for k in (data.get("key_points") or [])][:6],
        "shots": norm,
        "total_duration_sec": int(total),
    }


def _llm_generate(content: str, title: str, max_shots: int | None = None) -> dict | None:
    """LLM 生成：短脚本单批；长脚本（>6 句）分批生成拼接，覆盖全文"""
    try:
        _load_model()
    except Exception:  # noqa: BLE001
        return None

    sents = _split_sentences(content)
    if len(sents) <= 6:
        for _ in range(2):
            try:
                result = _llm_generate_once(content, title, max_shots)
            except Exception:  # noqa: BLE001
                result = None
            if result:
                return result
        return None

    # 长脚本分批：每批 4 句，每批生成 per 镜
    batches = [sents[i:i + 4] for i in range(0, len(sents), 4)]
    per = 3
    if max_shots:
        per = max(2, min(4, max_shots // len(batches)))
    all_shots, kps = [], []
    for b in batches:
        sub = "。".join(b)
        r = None
        for _ in range(2):
            try:
                r = _llm_generate_once(sub, title, per)
            except Exception:  # noqa: BLE001
                r = None
            if r:
                break
        if r:
            all_shots.extend(r["shots"])
            kps.extend(r.get("key_points") or [])
        else:
            rule = _rule_generate(sub, title, per)
            all_shots.extend(rule["shots"])
            kps.extend(rule.get("key_points") or [])
    if not all_shots:
        return None
    for i, s in enumerate(all_shots, 1):
        s["index"] = i
    return {
        "key_points": kps[:6],
        "shots": all_shots,
        "total_duration_sec": sum(s.get("duration_sec", 6) for s in all_shots),
    }


# ---------- 规则兜底（全文覆盖） ----------

_THEME_AR = [
    ("二十大", "金色主题文字卡片：党的二十大精神"),
    ("二十届", "金色主题文字卡片：二十届三中全会"),
    ("中国式现代化", "现代化成就数据图表"),
    ("高质量发展", "高质量发展趋势图表"),
    ("习近平", "红色主题横幅：习近平新时代中国特色社会主义思想"),
    ("党史", "红色飘带 + 党史时间轴"),
    ("社会主义核心价值", "核心价值观 24 字卡片"),
    ("国防", "军绿色军事主题卡片：国防教育"),
    ("军工", "军绿色军工文化徽章 + 兵器剪影"),
    ("兵器", "兵器博物馆主题卡片 + 武器剪影"),
    ("军事", "军绿色军营主题卡片：强军兴军"),
    ("国家安全", "蓝色国家安全主题徽章：总体国家安全观"),
    ("守密", "保密教育主题卡片：守密防谍"),
    ("反谍", "蓝色反间谍警示卡片：国家安全"),
    ("反诈", "红色反诈警示横幅：拒绝诈骗陷阱"),
    ("诈骗", "反诈警示图标 + 共筑反诈长城"),
    ("财产安全", "财产安全守护盾牌图标"),
    ("共筑反诈", "反诈长城主题卡片"),
    ("行走的思政课", "行走的思政课路线卡片"),
    ("思政课", "思政课主题卡片 + 书本图标"),
    ("青年学习社", "青年学习社徽章卡片"),
    ("青年担当", "青年担当主题卡片：青春·责任"),
    ("法治", "蓝色法治主题徽章：法治之光"),
    ("宪法", "宪法主题卡片 + 天平图标"),
    ("廉政", "清廉文化主题卡片：清风廉政"),
    ("交通", "交通安全主题卡片 + 红绿灯图标"),
    ("爱国", "红色爱国主义教育卡片"),
    ("红色", "红色文化主题飘带"),
]

_TRANSITIONS = ["fade", "slide", "zoom", "cut"]


def _rule_generate(content: str, title: str, max_shots: int | None = None) -> dict:
    """规则兜底：全文句子逐镜生成（覆盖到结尾），超长自动合并"""
    sents = _split_sentences(content)
    if max_shots and len(sents) > max_shots:
        sents = _merge_to(sents, max_shots)
    if len(sents) > MAX_SENTENCES:
        sents = _merge_to(sents, MAX_SENTENCES)

    shots, total = [], 0
    for i, s in enumerate(sents, 1):
        ar = "主题文字卡片"
        for kw, label in _THEME_AR:
            if kw in s:
                ar = label
                break
        dur = 6
        total += dur
        shots.append({
            "index": i,
            "scene_desc": f"镜头聚焦校园宣传栏/主题教育展板，呈现：{s[:30]}……",
            "narration": s if len(s) <= 120 else s[:120] + "……",
            "ar_overlay": ar,
            "duration_sec": dur,
            "transition": _TRANSITIONS[i % len(_TRANSITIONS)],
        })
    key_points = [s[:40] for s in sents[:3]]
    return {"key_points": key_points, "shots": shots, "total_duration_sec": total}


def generate(content: str, title: str = "", max_shots: int | None = None) -> dict:
    """主入口：LLM 优先（长脚本分段），失败走规则兜底；max_shots 自定义总镜头数"""
    result = _llm_generate(content, title, max_shots)
    if result is None:
        result = _rule_generate(content, title, max_shots)
    # 镜头数对齐：不足时用规则镜头补足到目标数量
    if max_shots and len(result["shots"]) < max_shots:
        rule = _rule_generate(content, title, max_shots)
        have = {(s.get("narration") or "")[:10] for s in result["shots"]}
        n = len(result["shots"])
        for s in rule["shots"]:
            if n >= max_shots:
                break
            key = (s.get("narration") or "")[:10]
            if key in have:
                continue
            s = dict(s)
            s["index"] = n + 1
            result["shots"].append(s)
            have.add(key)
            n += 1
        result["total_duration_sec"] = sum(x.get("duration_sec", 6) for x in result["shots"])
    # 用脚本原句回填旁白：0.5B 小模型生成分镜时容易把 narration 写成占位描述，
    # 这里按镜头顺序回填脚本完整原句，保证旁白即原文、断句完整
    sents = _split_sentences(content)
    if sents:
        for i, s in enumerate(result["shots"]):
            if i < len(sents):
                s["narration"] = sents[i][:160]
    # 镜头数不足句子数时自动补足：保证脚本每句都有对应镜头（全覆盖）
        while len(result["shots"]) < len(sents):
            k = len(result["shots"])
            sent = sents[k]
            ar = "主题文字卡片"
            for kw, label in _THEME_AR:
                if kw in sent:
                    ar = label
                    break
            result["shots"].append({
                "index": len(result["shots"]) + 1,
                "scene_desc": f"镜头聚焦校园宣传栏/主题教育展板，呈现：{sent[:30]}……",
                "narration": sent[:160],
                "ar_overlay": ar,
                "duration_sec": 6,
                "transition": _TRANSITIONS[len(result["shots"]) % len(_TRANSITIONS)],
            })
        # 重排序号与总时长
        for i, s in enumerate(result["shots"], 1):
            s["index"] = i
    # 每镜时长按旁白字数估计（中文语速约 4.5 字/秒，4-15 秒），保证语音与画面时长匹配、不重叠
    for s in result["shots"]:
        n_txt = len(s.get("narration") or "")
        s["duration_sec"] = min(max(math.ceil(n_txt / 4.5), 4), 15)
    result["total_duration_sec"] = sum(x.get("duration_sec", 6) for x in result["shots"])
    result["title"] = title or "未命名宣讲视频"
    return result
