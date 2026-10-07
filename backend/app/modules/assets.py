"""AR 素材生成模块 v2（高清主题化素材）

对比 v1：画布 2x 高清输出（适配 1080p 成片）、渐变质感、新增「印章/飘带/徽章强化」等
政治宣传常见样式；仍为 PIL 程序化绘制，后续可无缝替换 Stable Diffusion 文生图。
"""
from __future__ import annotations

import os
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.core.config import ASSET_DIR

FONT = next(
    (c for c in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]
     if os.path.exists(c)),
    None,
)


def _font(size: int):
    return ImageFont.truetype(FONT, size)


def _save(img: Image.Image, prefix: str) -> str:
    path = ASSET_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}.png"
    img.save(path)
    return str(path)


# ---------- 主题配色识别 ----------
THEME_STYLES = [
    (("国防", "军工", "兵器", "军事", "军营", "强军"), (58, 74, 48), (210, 168, 70), "国防教育"),
    (("国家安全", "国安", "守密", "反谍", "间谍", "保密"), (22, 62, 132), (96, 168, 255), "国家安全"),
    (("反诈", "诈骗", "财产安全", "防骗", "拒绝诱惑"), (172, 32, 32), (255, 192, 56), "反诈警示"),
    (("二十大", "中国式现代化", "高质量发展", "现代化"), (196, 152, 46), (255, 222, 122), "政治理论"),
    (("党史", "党建", "党支部", "红色", "革命"), (176, 34, 34), (255, 214, 66), "党建党史"),
    (("思政课", "思政", "青年", "学习社", "青年担当", "青春"), (20, 100, 110), (118, 222, 202), "思政青年"),
    (("法治", "宪法", "普法", "民法典", "法律"), (30, 80, 160), (122, 184, 255), "法治教育"),
    (("廉政", "廉洁", "清廉", "反腐"), (30, 128, 118), (160, 232, 210), "清廉廉政"),
    (("社会主义核心价值观", "价值观", "24字"), (168, 58, 40), (255, 214, 118), "核心价值观"),
]


def _style(desc: str) -> tuple:
    if not desc:
        return (139, 26, 44), (255, 215, 0), "主题宣传"
    for keywords, primary, accent, label in THEME_STYLES:
        if any(kw in desc for kw in keywords):
            return primary, accent, label
    if "金" in desc:
        return (196, 152, 46), (255, 222, 122), "金色主题"
    if "红" in desc or "飘带" in desc or "横幅" in desc:
        return (176, 34, 34), (255, 214, 66), "红色主题"
    if "蓝" in desc:
        return (30, 80, 160), (122, 184, 255), "蓝色主题"
    return (139, 26, 44), (255, 215, 0), "主题宣传"


def _topic_text(desc: str) -> str:
    if not desc:
        return "主题宣传"
    topic = desc.split("：")[-1].split("+")[0].strip()
    for prefix in ("金色主题文字卡片：", "红色主题横幅：", "军绿色军事主题卡片：",
                   "蓝色国家安全主题徽章：", "红色反诈警示横幅：", "反诈警示图标 + ",
                   "现代化成就数据图表", "主题文字卡片"):
        if topic.startswith(prefix):
            topic = topic[len(prefix):]
            break
    return topic[:18] or "主题宣传"


def _gradient_bar(img: Image.Image, box, c1, c2, vertical=True):
    """在 box 区域画水平/垂直渐变"""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    steps = max(x1 - x0, 1) if not vertical else max(y1 - y0, 1)
    if not vertical:
        for i in range(steps):
            t = i / steps
            color = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
            d.line([(x0 + i, y0), (x0 + i, y1)], fill=color)
    else:
        for i in range(steps):
            t = i / steps
            color = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
            d.line([(x0, y0 + i), (x1, y0 + i)], fill=color)


def make_card(desc: str) -> Image.Image:
    """高清主题卡片：渐变底 + 徽记 + 主题大字 + 高光条"""
    primary, accent, _label = _style(desc)
    topic = _topic_text(desc)
    w, h = 1040, 240
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _gradient_bar(img, (0, 0, w, h), tuple(int(c * 0.82) for c in primary), primary, vertical=True)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=(0, 0, 0, 60))
    d.rounded_rectangle([8, 8, w - 9, h - 9], radius=22, outline=accent, width=5)
    # 高光
    d.rounded_rectangle([24, 16, w - 24, 44], radius=14, fill=accent + (70,))
    # 徽记（左）
    cx, cy = 76, h // 2
    for r in (44, 32, 20):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=4)
    d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=accent)
    d.line([(cx, cy - 30), (cx, cy + 30)], fill=accent, width=3)
    d.line([(cx - 30, cy), (cx + 30, cy)], fill=accent, width=3)
    # 主题字
    fs = 68 if len(topic) <= 10 else 54
    d.text((150, 78), topic, font=_font(fs), fill="white")
    # 底部装饰点
    for i in range(3):
        d.ellipse([150 + i * 26, 172, 150 + i * 26 + 10, 182], fill=accent + (200,))
    return img


def make_banner(desc: str) -> Image.Image:
    """顶部横幅：渐变丝带 + 双色描边 + 白字"""
    primary, accent, _label = _style(desc)
    topic = _topic_text(desc)
    w, h = 1280, 168
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _gradient_bar(img, (0, 0, w, h), primary, tuple(int(c * 0.72) for c in primary), vertical=True)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=20, fill=(0, 0, 0, 40))
    d.rounded_rectangle([6, 6, w - 7, h - 7], radius=16, outline=accent, width=4)
    # 两侧星标
    for x in (40, w - 104):
        d.polygon([(x + 32, 22), (x + 40, 46), (x + 64, 46), (x + 45, 60),
                   (x + 52, 84), (x + 32, 70), (x + 12, 84), (x + 19, 60),
                   (x, 46), (x + 24, 46)], fill=accent)
    d.text((120, 48), topic, font=_font(72), fill="white")
    return img


def make_chart(desc: str) -> Image.Image:
    """高清数据图表：深色卡片 + 网格 + 渐变柱 + 峰值高亮"""
    primary, accent, _label = _style(desc)
    title = _topic_text(desc)[:14]
    w, h = 900, 560
    img = Image.new("RGBA", (w, h), (14, 18, 30, 235))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=(14, 18, 30, 235))
    d.rounded_rectangle([6, 6, w - 7, h - 7], radius=20, outline=accent, width=3)
    d.text((40, 30), title, font=_font(44), fill=accent)
    # 网格
    gx0, gy0, gx1, gy1 = 70, 110, w - 60, h - 80
    for gy in range(gy0, gy1 + 1, 60):
        d.line([(gx0, gy), (gx1, gy)], fill=(255, 255, 255, 26), width=2)
    # 渐变柱
    vals = [55, 74, 90, 108, 132, 158]
    bw = (gx1 - gx0 - 30) // len(vals) - 18
    for i, v in enumerate(vals):
        x0 = gx0 + 15 + i * (bw + 18)
        y1 = gy1 - int(v / 170 * (gy1 - gy0))
        _gradient_bar(img, (x0, y1, x0 + bw, gy1), primary, accent, vertical=False)
        d.rounded_rectangle([x0, y1, x0 + bw, gy1], radius=10, outline=(255, 255, 255, 90), width=2)
        d.ellipse([x0 + bw // 2 - 5, y1 - 12, x0 + bw // 2 + 5, y1 - 2], fill=accent)
    # 底标签
    for i in range(len(vals)):
        d.text((gx0 + 15 + i * (bw + 18), gy1 + 14), "第%d期" % (i + 1), font=_font(28), fill=(200, 210, 230))
    return img


def make_badge(desc: str) -> Image.Image:
    """高清主题徽章：盾牌 + 星环 + 主题字 + 光晕"""
    primary, accent, label = _style(desc)
    w, h = 520, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 光晕
    cx, cy = w // 2, h // 2
    for r in range(240, 0, -3):
        a = int(60 * (1 - r / 240))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (a,))
    # 外环
    d.ellipse([30, 30, w - 31, h - 31], outline=accent, width=8)
    d.ellipse([56, 56, w - 57, h - 57], outline=primary, width=4)
    # 盾牌
    d.polygon([(cx, 90), (w - 110, 138), (w - 110, 296), (cx, 400), (110, 296), (110, 138)],
              fill=primary + (235,), outline=accent, width=6)
    # 星
    star = [(cx + 0, 150), (cx + 22, 196), (cx + 66, 196), (cx + 30, 224),
            (cx + 44, 268), (cx + 0, 244), (cx - 44, 268), (cx - 30, 224),
            (cx - 66, 196), (cx - 22, 196)]
    d.polygon(star, fill=accent)
    # 主题字（两行）
    t1, t2 = label[:4], label[4:8]
    d.text((cx - len(t1) * 20, 288), t1, font=_font(40), fill="white")
    if t2:
        d.text((cx - len(t2) * 20, 336), t2, font=_font(40), fill="white")
    return img


def make_seal(desc: str) -> Image.Image:
    """红色印章风：圆形印章 + 主题字（政治宣传/审核通过感）"""
    primary, accent, _label = _style(desc)
    topic = _topic_text(desc)[:8]
    w, h = 460, 460
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    red = (192, 32, 28)
    # 双圆环
    d.ellipse([20, 20, w - 21, h - 21], outline=red, width=10)
    d.ellipse([54, 54, w - 55, h - 55], outline=red, width=4)
    # 五角星
    cx, cy = w // 2, 178
    star = []
    for k in range(10):
        r = 62 if k % 2 == 0 else 26
        ang = -90 + k * 36
        import math
        star.append((cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))))
    d.polygon(star, fill=red)
    # 主题字
    if topic:
        d.text((cx - len(topic) * 22, 260), topic, font=_font(44), fill=red)
    d.text((cx - 58, 330), "主题宣传", font=_font(30), fill=red)
    return img


def make_glow(desc: str) -> Image.Image:
    """主题光效背景（透明叠加）"""
    primary, accent, _label = _style(desc)
    w, h = 1280, 900
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    for r in range(430, 0, -3):
        alpha = int(70 * (1 - r / 430))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=primary + (alpha,))
    topic = _topic_text(desc)[:12]
    if topic:
        d.text((cx - len(topic) * 26, cy - 30), topic, font=_font(52), fill=accent)
    return img


def make_ribbon(desc: str) -> Image.Image:
    """飘带：S 形丝带 + 主题字"""
    primary, accent, _label = _style(desc)
    topic = _topic_text(desc)[:10]
    w, h = 760, 420
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 两条丝带
    pts = [(40, 60), (200, 46), (360, 70), (520, 52), (700, 84)]
    for off in (0, 26):
        d.line([(x, y + off) for x, y in pts], fill=primary, width=52)
        d.line([(x, y + off) for x, y in pts], fill=accent, width=8)
    # 尾部三角
    x, y = pts[-1]
    d.polygon([(x, y), (x - 90, y - 60), (x - 90, y + 60)], fill=primary)
    d.text((70, 150), topic, font=_font(64), fill="white")
    return img


def generate_overlay(desc: str) -> str:
    """根据 AR 叠加描述生成素材图，返回文件路径"""
    if not desc:
        desc = "主题文字卡片"
    if "图表" in desc or "数据" in desc or "趋势" in desc or "指标" in desc:
        return _save(make_chart(desc), "ar_chart")
    if "印章" in desc or "审核" in desc or "通过" in desc:
        return _save(make_seal(desc), "ar_seal")
    if "徽章" in desc or "盾牌" in desc or "国家安全" in desc or "法治" in desc or "反诈" in desc:
        return _save(make_badge(desc), "ar_badge")
    if "横幅" in desc or "长城" in desc or "丝带" in desc:
        return _save(make_banner(desc), "ar_banner")
    if "飘带" in desc or "彩带" in desc:
        return _save(make_ribbon(desc), "ar_ribbon")
    if "光效" in desc or "背景" in desc or "路线" in desc:
        return _save(make_glow(desc), "ar_glow")
    return _save(make_card(desc), "ar_card")


# ================= 素材池与自动配图（v3.1） =================

import uuid as _uuid
import requests as _requests
from app.core.config import USER_ASSET_DIR

AUTO_DIR = ASSET_DIR / "auto"   # 网图自动下载缓存
USER_DIR = USER_ASSET_DIR
for _d in (AUTO_DIR, USER_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 镜头关键词 -> 本地图库 slug
_THEME_SLUG = [
    (("国旗", "爱国", "红色", "祖国", "中华", "骄傲"), "flag"),
    (("长城",), "greatwall"),
    (("天安门",), "tiananmen"),
    (("航天", "火箭", "卫星", "科技兴国", "强国"), "rocket"),
    (("科技", "网络", "创新", "信息", "数字"), "technology"),
    (("校园", "青春", "学生", "学子", "青年"), "campus"),
    (("城市", "发展", "成就", "复兴"), "citynight"),
    (("山河", "美丽家园", "大地", "锦绣"), "mountain"),
    (("和平", "和谐", "鸽"), "dove"),
    (("法治", "宪法", "法律", "司法"), "law"),
    (("警察", "安全", "守护", "反诈", "防骗"), "police"),
    (("盾牌", "保护", "防护", "防线"), "shield"),
    (("希望", "未来", "奋进", "新征程"), "sunrise"),
    (("书籍", "学习", "教育", "读书"), "books"),
    (("军人", "国防", "强军", "军队", "征兵"), "soldier"),
    (("宣传", "喇叭", "动员", "传播"), "megaphone"),
]

# slug -> loremflickr 英文标签（网图下载用）
_SLUG_TAGS = {
    "flag": "china,flag", "greatwall": "great,wall,china", "tiananmen": "tiananmen,china",
    "rocket": "rocket,space", "technology": "technology,network", "campus": "university,campus",
    "citynight": "city,night,light", "mountain": "mountain,china", "dove": "dove,bird,peace",
    "law": "law,justice,court", "police": "police,security", "shield": "shield,protection",
    "sunrise": "sunrise,dawn", "books": "books,study", "soldier": "soldier,army",
    "megaphone": "megaphone,loudspeaker",
}


def _theme_slug(text: str) -> str | None:
    for kws, slug in _THEME_SLUG:
        if any(k in text for k in kws):
            return slug
    return None


def net_fetch(slug: str) -> str | None:
    """按 slug 从 loremflickr 下载一张网图缓存到 auto/，返回 slug 或 None"""
    tags = _SLUG_TAGS.get(slug)
    if not tags:
        return None
    out = AUTO_DIR / f"{slug}.jpg"
    if out.exists() and out.stat().st_size > 20000:
        return slug
    try:
        r = _requests.get(f"https://loremflickr.com/1280/720/{tags}",
                          headers=_UA, timeout=45)
        if r.status_code == 200 and len(r.content) > 20000:
            out.write_bytes(r.content)
            return slug
    except Exception:  # noqa: BLE001
        pass
    return None


def user_assets_list() -> list[str]:
    """用户素材池文件名列表"""
    if USER_DIR.exists():
        return sorted(f.stem for f in USER_DIR.glob("*.jpg"))
    return []


def auto_fill_assets(shots: list[dict], user_pool: list[str] | None = None) -> None:
    """自动配图：为每个未指定素材的镜头填充素材（用户素材优先 -> 本地图库 -> 网图下载）

    保证每镜至少有 1 张图、尽量 2 张，且不同镜头尽量用不同图片，避免整片一图到底。
    """
    pool = list(user_pool or user_assets_list())
    lib_slugs = ["flag", "greatwall", "tiananmen", "rocket", "technology", "campus",
                 "citynight", "mountain", "dove", "law", "police", "shield",
                 "sunrise", "books", "soldier", "megaphone"]
    pi = 0
    used: set[str] = set()
    for shot in shots:
        if shot.get("assets"):
            used.update(shot["assets"])
            continue
        text = (shot.get("narration") or "") + (shot.get("scene_desc") or "")
        picked = []
        # 1) 用户素材优先（轮换，避免重复）
        if pool:
            for _ in range(len(pool)):
                cand = pool[pi % len(pool)]
                pi += 1
                if cand not in used:
                    picked.append(cand)
                    break
            else:
                picked.append(pool[(pi - 1) % len(pool)])
        # 2) 主题匹配本地图库
        slug = _theme_slug(text)
        if slug and slug not in picked and slug not in used:
            picked.append(slug)
        elif not slug:
            # 无明确主题：按序轮换通用图库，保证不同镜头不同图
            for s2 in lib_slugs:
                if s2 not in picked and s2 not in used:
                    picked.append(s2)
                    break
        # 3) 网图增强：确保凑足 2 张（主题图 + 网图）
        if len(picked) < 2:
            for s2 in lib_slugs:
                if s2 not in picked and s2 not in used:
                    picked.append(s2)
                    break
        # 4) 网图下载（若主题匹配但库里没下过对应图，则按需下载）
        if slug and slug in _SLUG_TAGS:
            net_fetch(slug)
        shot["assets"] = picked[:2]
        used.update(picked[:2])
