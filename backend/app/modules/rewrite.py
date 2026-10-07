"""文案自动扩写模块 v2

expand(content, title, mode, length)：
- mode=expand   将简短要点/一句话扩写为完整宣讲稿（分段展开 + 引语 + 升华）
- mode=polish   对已有稿件润色（保持结构、优化表达）
- mode=keypoints 提取要点（复用 storyboard 能力）

LLM（Qwen2.5-0.5B 本地）优先；模型不可用/超时自动降级规则扩写，保证可用。
规则扩写基于主题词库 + 通用宣讲句式模板，输出结构完整的宣讲稿。
"""
from __future__ import annotations

import re
import threading

from app.modules import storyboard as sb_mod

# 主题词 -> 意义句模板
_THEME_MEANING = [
    ("国家安全", "国家安全是民族复兴的根基，社会稳定是国家强盛的前提。"),
    ("反诈", "反诈宣传是守护师生财产安全、共建平安校园的重要防线。"),
    ("国防", "国防教育是增强民族凝聚力、提高全民国防素质的基础工程。"),
    ("党史", "党的历史是最生动、最有说服力的教科书。"),
    ("二十大", "党的二十大精神为新时代新征程党和国家事业发展指明了前进方向。"),
    ("中国式现代化", "中国式现代化是中国共产党领导的社会主义现代化，既有各国现代化的共同特征，更有基于自己国情的中国特色。"),
    ("青年", "青年强则国家强，新时代青年生逢其时，施展才干的舞台无比广阔。"),
    ("法治", "全面依法治国是坚持和发展中国特色社会主义的本质要求和重要保障。"),
    ("核心价值观", "社会主义核心价值观是凝聚人心、汇聚民力的强大力量。"),
    ("廉政", "廉洁文化是社会主义先进文化的重要组成部分。"),
    ("思政", "思想政治理论课是落实立德树人根本任务的关键课程。"),
]

_GENERIC_MEANING = "这一主题与我们的学习生活紧密相关，需要我们学深悟透、落到实处。"
_ACTION = ("作为新时代青年学生，我们应当主动学习、深入领会、积极践行，"
           "把思想认识转化为日常行动，在学思践悟中坚定信念，为强国建设、民族复兴贡献青春力量。")

_LLM_LOCK = threading.Lock()

_SYSTEM_PROMPT = """你是高校校园政治理论学习宣讲稿的写作助手，擅长把要点扩写成条理清晰、语言庄重的宣讲稿。
要求：分段展开，先提出观点再展开说明，语言准确严谨、积极向上，结尾给出号召。
只输出正文文本，不要输出标题和 JSON。"""


# ---------- LLM 扩写 ----------

def _llm(content: str, mode: str, length: str) -> str | None:
    try:
        import torch
        sb_mod._load_model()
    except Exception:  # noqa: BLE001
        return None
    if mode == "polish":
        instruction = "请对下面的宣讲稿进行润色：保持原有结构和论点，优化表达，使语言更流畅庄重。\n\n"
    elif mode == "keypoints":
        instruction = "请提取下面内容的核心要点，输出为 3-5 条短句，每条一行。\n\n"
    else:
        length_note = {"short": "约150字", "medium": "约300字", "long": "约500字"}.get(length, "约300字")
        instruction = f"请把下面的要点扩写成一则完整的校园宣讲稿（{length_note}），分3段：开头引入、主体展开、结尾号召。\n\n"
    user = instruction + content
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    try:
        text = sb_mod._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:  # noqa: BLE001
        text = f"{_SYSTEM_PROMPT}\n用户：{user}\n助手："
    inputs = sb_mod._tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = sb_mod._model.generate(
            **inputs, max_new_tokens=512, do_sample=True, temperature=0.7, top_p=0.9,
            pad_token_id=sb_mod._tokenizer.eos_token_id,
        )
    gen = outputs[0][inputs["input_ids"].shape[1]:]
    raw = sb_mod._tokenizer.decode(gen, skip_special_tokens=True).strip()
    if len(raw) < 30:
        return None
    return raw


# ---------- 规则扩写 ----------

def _find_theme(content: str) -> str | None:
    for kw, meaning in _THEME_MEANING:
        if kw in content:
            return meaning
    return None


def _rule_expand(content: str, mode: str) -> str:
    text = content.strip().replace("\r", "")
    if mode == "keypoints":
        sents = [s for s in re.split(r"[。！？；\n]", text) if len(s.strip()) >= 4]
        return "\n".join("1. " + s.strip()[:60] for s in sents[:6]) or text[:200]
    if mode == "polish":
        return text  # 规则无法润色，原样返回（LLM 不可用时）
    # expand：分段展开
    sents = [s for s in re.split(r"[。！？；\n]", text) if len(s.strip()) >= 3]
    if not sents:
        sents = [text[:40]]
    meaning = _find_theme(text) or _GENERIC_MEANING
    paras = []
    paras.append(f"{sents[0].strip()}。{meaning}")
    for s in sents[1:]:
        paras.append(f"{s.strip()}。这要求我们提高思想认识，在学习和生活中自觉践行，把理论要求转化为日常行动。")
    paras.append(_ACTION)
    return "\n\n".join(paras)


# ---------- 对外接口 ----------

def expand(content: str, title: str = "", mode: str = "expand",
           length: str = "medium") -> dict:
    """文案扩写/润色/要点，返回 {text, method, length}"""
    if not content or not content.strip():
        return {"text": "", "method": "empty", "length": length}
    method = "rule"
    text = None
    if mode in ("expand", "polish", "keypoints"):
        try:
            text = _llm(content, mode, length)
            if text:
                method = "llm"
        except Exception:  # noqa: BLE001
            text = None
    if text is None:
        text = _rule_expand(content, mode)
        method = "rule" if mode != "keypoints" else "rule-keypoints"
    return {"text": text, "method": method, "length": length}
