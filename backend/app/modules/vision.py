"""场景视觉识别模块（MVP：RapidOCR + 文化属性关键词解析）

输入：场景图片路径
输出：{ocr_text, ocr_blocks, culture_attributes, semantic_summary}
"""
from __future__ import annotations

import threading
from typing import Optional

# 主题词库（按主题归类，覆盖常见校园政治/社会宣传场景）
# 后续可继续扩充，保持「主题名 -> [触发关键词]」结构
THEME_KEYWORDS = {
    # --- 政治理论类 ---
    "党的二十大精神": ["二十大", "党的二十大", "二十届三中全会", "二十届"],
    "习近平新时代中国特色社会主义思想": ["习近平", "新时代中国特色社会主义思想", "新时代", "中国梦", "中国梦·我的梦"],
    "百年党史": ["党史", "建党", "百年", "红船", "长征", "革命", "建党精神", "红色精神"],
    "社会主义核心价值观": ["社会主义核心价值观", "富强", "民主", "文明", "和谐", "爱国", "敬业", "诚信", "友善", "24字价值观"],
    "全国两会": ["两会", "人大", "政协", "政府工作报告"],
    "主题教育": ["主题教育", "党纪学习教育", "三会一课", "党课", "专题学习"],
    "中国式现代化": ["中国式现代化", "高质量发展", "现代化", "共同富裕", "新发展理念"],

    # --- 国防与安全教育类（本次三张图核心主题）---
    "国防教育": ["国防", "军工", "兵器", "军事", "强军", "国防科技", "军工文化", "军营", "军威", "军魂", "国防教育", "军事博物馆"],
    "国家安全": ["国家安全", "国安", "总体国家安全观", "谍报", "反间", "间谍", "保密", "守密", "反谍", "国家安全日", "总体安全"],
    "反诈骗": ["反诈", "诈骗", "诈骗", "高利贷", "电信诈骗", "刷单", "兼职陷阱", "钓鱼", "电信诈骗", "反诈中心", "诈骗手法", "防骗", "反诈宣传"],
    "反诈宣传": ["共筑反诈", "反诈长城", "反电信网络诈骗", "财产安全", "拒绝诱惑", "警惕高薪", "高薪兼职"],
    "保密教育": ["保密", "密级", "涉密", "防谍", "反间谍", "国家秘密", "保密法", "守密防谍"],

    # --- 思政与红色文化类 ---
    "爱国主义教育": ["爱国主义", "红色文化", "红色基因", "革命精神", "英雄", "先烈", "烈士", "爱国精神"],
    "行走的思政课": ["思政课", "行走的思政课", "实践思政课", "思政", "社会实践", "行走课堂"],
    "青年担当": ["青年担当", "青年学习社", "青年使命", "青年责任", "青年学习社", "青春", "青年担当"],

    # --- 法治与社会类 ---
    "法治教育": ["法治", "宪法", "民法典", "普法", "法治宣传", "守法", "法律"],
    "廉政教育": ["廉政", "反腐", "廉洁", "清廉", "廉政文化"],
    "环保与安全": ["环保", "节能", "绿色低碳", "生态", "安全用电", "消防"],
    "交通安全": ["交通", "红绿灯", "礼让行人", "交通安全", "出行安全"],
}

CATEGORY_RULES = [
    # 按优先级排列，命中即归类
    ("国防教育阵地", ["国防", "军工", "兵器", "军事", "军工文化", "军事博物馆", "国防科技"]),
    ("国家安全宣传", ["国家安全", "反间谍", "反谍", "守密", "国安", "保密"]),
    ("反诈骗宣传", ["反诈", "诈骗", "防骗", "电信诈骗", "反诈中心", "财产安全"]),
    ("党建阵地", ["党建", "党支部", "党员", "先锋", "三会一课"]),
    ("理论学习展板", ["理论学习", "学习宣传", "宣讲", "专题学习", "学习社", "青年学习社"]),
    ("思政课宣传", ["思政课", "行走的思政课", "思政", "社会实践"]),
    ("红色文化阵地", ["红色", "党史", "革命", "纪念馆", "烈士", "爱国主义"]),
    ("法治宣传", ["法治", "普法", "宪法", "民法典", "廉政"]),
    ("宣传栏", ["宣传栏", "公告栏", "展板", "海报"]),
]


_engine: Optional[object] = None
_engine_lock = threading.Lock()


def _get_engine():
    """懒加载 RapidOCR（首次调用自动下载模型）"""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
    return _engine


def _flatten_box(box) -> list[float]:
    """兼容嵌套坐标 [[x,y],[x,y]...] 与扁平坐标 [x1,y1,x2,y2...]"""
    flat = []
    for pt in box:
        if isinstance(pt, (list, tuple)):
            flat.extend(pt)
        else:
            flat.append(pt)
    return [float(x) for x in flat]


def _match_theme(text: str) -> dict:
    """从 OCR 文本中匹配政治/社会主题与文化属性（支持多主题命中，按首个为 primary）"""
    themes = []
    for theme, kws in THEME_KEYWORDS.items():
        if any(kw in text for kw in kws):
            themes.append(theme)
    categories = []
    for cat, kws in CATEGORY_RULES:
        if any(kw in text for kw in kws):
            categories.append(cat)
    return {
        "theme": themes[0] if themes else "未识别",
        "themes": themes,
        "category": categories[0] if categories else "校园宣传场景",
        "categories": categories,
    }


def analyze(image_path: str) -> dict:
    """识别场景图片：OCR 文字 + 文化属性标注"""
    engine = _get_engine()
    result, _ = engine(str(image_path))

    blocks, texts = [], []
    if result:
        for box, text, score in result:
            blocks.append({
                "text": text,
                "score": round(float(score), 3),
                "bbox": _flatten_box(box),
            })
            texts.append(text)

    ocr_text = "\n".join(texts)
    attrs = _match_theme(ocr_text)

    # 语义摘要：拼接主题 + 类别 + 首段文字
    summary_parts = []
    if attrs["themes"]:
        summary_parts.append(f"该场景呈现「{'、'.join(attrs['themes'])}」主题内容")
    if attrs["categories"]:
        summary_parts.append(f"属于{'、'.join(attrs['categories'])}")
    if texts:
        summary_parts.append(f"识别到 {len(texts)} 处文字，如「{texts[0][:30]}」")
    semantic_summary = "；".join(summary_parts) if summary_parts else "未识别到明显文字内容"

    return {
        "ocr_text": ocr_text,
        "ocr_blocks": blocks,
        "culture_attributes": attrs,
        "semantic_summary": semantic_summary,
    }
