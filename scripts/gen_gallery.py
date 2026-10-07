# -*- coding: utf-8 -*-
"""生成内置示例场景图库（data/gallery/*.png）

PIL 程序化绘制 6 张校园宣传栏/展板风格示例图，供前端「内置图库」一键选用测试。
画法：背景墙 + 展板框架 + 标题条 + 文字行条 + 主题图标 + 光影。
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GALLERY = ROOT / "data" / "gallery"
GALLERY.mkdir(parents=True, exist_ok=True)

W, H = 1280, 720
FONT = next(
    (c for c in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]
     if os.path.exists(c)),
    None,
)


def font(size: int):
    return ImageFont.truetype(FONT, size)


def wall_bg(d: ImageDraw, c1, c2):
    """背景墙渐变 + 砖缝"""
    for i in range(H):
        t = i / H
        c = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        d.line([(0, i), (W, i)], fill=c)


def board(d: ImageDraw, x0, y0, x1, y1, frame, panel):
    """展板：外框 + 面板 + 内阴影"""
    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=frame)
    d.rounded_rectangle([x0 + 14, y0 + 14, x1 - 14, y1 - 14], radius=10, fill=panel)
    # 面板内顶部渐变（深一点）
    for i in range(90):
        t = 1 - i / 90
        alpha = int(36 * t)
        d.rounded_rectangle([x0 + 14, y0 + 14 + i, x1 - 14, y0 + 16 + i], radius=0,
                            fill=(0, 0, 0, alpha))


def title_bar(d: ImageDraw, x0, y0, x1, y1, fill, text, accent, fs=44):
    """标题条"""
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=fill)
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, outline=accent, width=3)
    tw = d.textlength(text, font=font(fs))
    d.text(((x0 + x1) / 2 - tw / 2, y0 + 12), text, font=font(fs), fill="white")


def text_lines(d: ImageDraw, x0, y0, x1, n, color=(235, 238, 245), h=16, gap=30):
    """模拟正文文字行"""
    y = y0
    for i in range(n):
        w_line = x1 - (i % 3) * 46  # 段落错落
        d.rounded_rectangle([x0, y, x0 + w_line, y + h], radius=6, fill=color + (150,))
        y += gap


def star(d: ImageDraw, cx, cy, r, color):
    pts = []
    import math
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.4
        ang = -90 + k * 36
        pts.append((cx + rr * math.cos(math.radians(ang)), cy + rr * math.sin(math.radians(ang))))
    d.polygon(pts, fill=color)


def shield(d: ImageDraw, cx, cy, s, color):
    d.polygon([(cx, cy - s), (cx + s * 0.85, cy - s * 0.6), (cx + s * 0.85, cy + s * 0.3),
               (cx, cy + s), (cx - s * 0.85, cy + s * 0.3), (cx - s * 0.85, cy - s * 0.6)],
              fill=color)


def build(title, subtitle, panel, accent, frame=(52, 56, 66), icon="star",
          lines=6, ground=(74, 70, 66), wall=(188, 192, 200)):
    img = Image.new("RGB", (W, H), wall)
    d = ImageDraw.Draw(img, "RGBA")
    wall_bg(d, wall, tuple(int(c * 0.72) for c in wall))
    # 顶部横幅
    d.rounded_rectangle([60, 36, W - 60, 120], radius=14, fill=frame)
    d.rounded_rectangle([66, 42, W - 66, 114], radius=10, outline=accent, width=3)
    tw = d.textlength(title, font=font(52))
    d.text(((W - tw) / 2, 50), title, font=font(52), fill="white")
    # 地面
    d.rectangle([0, H - 60, W, H], fill=ground)
    d.line([(0, H - 60), (W, H - 60)], fill=(255, 255, 255, 90), width=4)
    # 展板
    bx0, by0, bx1, by1 = 150, 160, W - 150, H - 120
    board(d, bx0, by0, bx1, by1, frame, panel)
    # 图标（左上）
    if icon == "star":
        star(d, bx0 + 120, by0 + 120, 52, accent)
    elif icon == "shield":
        shield(d, bx0 + 120, by0 + 130, 70, accent)
    elif icon == "gavel":
        d.rounded_rectangle([bx0 + 70, by0 + 130, bx0 + 170, by0 + 176], radius=8, fill=accent)
        d.rounded_rectangle([bx0 + 92, by0 + 96, bx0 + 148, by0 + 130], radius=6, fill=accent)
    # 副标题
    tw2 = d.textlength(subtitle, font=font(40))
    d.text(((bx0 + bx1) / 2 - tw2 / 2, by0 + 90), subtitle, font=font(40), fill=accent)
    # 内容行
    text_lines(d, bx0 + 110, by0 + 190, bx1 - bx0 - 260, lines, color=(236, 240, 248))
    # 底部日期条
    d.rounded_rectangle([bx0 + 110, by1 - 92, bx0 + 420, by1 - 56], radius=8,
                        fill=(0, 0, 0, 70))
    d.text((bx0 + 122, by1 - 84), "学习贯彻进行时 · 校园宣传栏", font=font(26), fill=(220, 226, 238))
    # 右上装饰圆
    d.ellipse([W - 220, 160, W - 100, 280], outline=accent + (120,), width=4)
    d.ellipse([W - 200, 180, W - 120, 260], outline=accent + (80,), width=3)
    return img


def main():
    items = [
        ("学习宣传贯彻党的二十大精神", "高举旗帜 团结奋斗", (196, 26, 34), (255, 214, 92), "star", 7, (88, 82, 78), (196, 200, 208)),
        ("总体国家安全观教育专栏", "国家安全 人人有责", (18, 52, 112), (122, 190, 255), "shield", 6, (70, 76, 84), (186, 196, 206)),
        ("国防教育宣传阵地", "传承红色基因 赓续强军血脉", (52, 68, 44), (216, 172, 84), "star", 6, (80, 76, 70), (200, 200, 190)),
        ("反诈防骗宣传栏", "全民反诈 共建平安校园", (168, 34, 30), (255, 196, 66), "shield", 7, (84, 74, 70), (196, 192, 188)),
        ("行走的思政课 · 青年学习角", "学思践悟 青春担当", (18, 96, 102), (118, 226, 208), "star", 6, (72, 82, 82), (190, 204, 202)),
        ("法治宣传教育专栏", "尊法学法守法用法", (28, 74, 148), (132, 190, 255), "gavel", 6, (72, 76, 86), (188, 196, 206)),
    ]
    for i, (title, subtitle, panel, accent, icon, lines, ground, wall) in enumerate(items, 1):
        img = build(title, subtitle, panel, accent, icon=icon, lines=lines, ground=ground, wall=wall)
        p = GALLERY / f"gallery_campus_{i}.png"
        img.save(p)
        print(p.name, os.path.getsize(p) // 1024, "KB")


if __name__ == "__main__":
    main()
