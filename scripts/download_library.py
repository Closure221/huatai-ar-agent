# -*- coding: utf-8 -*-
"""下载主题素材网图到 data/assets/library/

来源：loremflickr（按关键词返回 CC 授权真实照片，1280x720）
用途：AR 素材库，供前端「素材选择器」多选叠加。
"""
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "data" / "assets" / "library"
LIB.mkdir(parents=True, exist_ok=True)

# 主题 -> loremflickr 标签（英文关键词）
THEMES = [
    ("flag", "china,flag"),
    ("greatwall", "great,wall,china"),
    ("tiananmen", "tiananmen,china"),
    ("rocket", "rocket,space"),
    ("technology", "technology,network"),
    ("campus", "university,campus"),
    ("citynight", "city,night,light"),
    ("mountain", "mountain,china"),
    ("dove", "dove,bird,peace"),
    ("law", "law,justice,court"),
    ("police", "police,security"),
    ("shield", "shield,protection"),
    ("sunrise", "sunrise,dawn"),
    ("books", "books,study"),
    ("soldier", "soldier,army"),
    ("megaphone", "megaphone,loudspeaker"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
out = []
for slug, tags in THEMES:
    url = f"https://loremflickr.com/1280/720/{tags}"
    fp = LIB / f"{slug}.jpg"
    if fp.exists() and fp.stat().st_size > 20000:
        out.append(f"{slug}: exists")
        continue
    ok = False
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=60)
            if r.status_code == 200 and len(r.content) > 20000:
                fp.write_bytes(r.content)
                out.append(f"{slug}: OK {len(r.content)//1024}KB")
                ok = True
                break
        except Exception as e:
            out.append(f"{slug}: try{attempt} err {e}")
        time.sleep(1)
    if not ok:
        out.append(f"{slug}: FAIL")
(ROOT / "lib_dl.log").write_text("\n".join(out), encoding="utf-8")
print("done", len(out))
