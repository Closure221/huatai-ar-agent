# -*- coding: utf-8 -*-
"""华泰杯 AR 智能体 · 一键自测脚本

自动走通「脚本 → 分镜 → 场景识别 → 视频合成」全链路，
并覆盖若干异常/边界用例。
用法：
    先启动服务（start.bat 或 uvicorn），再运行：
    python scripts/smoke_test.py
"""
import os
import sys
import time

import requests

BASE = os.environ.get("HT_BASE", "http://127.0.0.1:8000")
API = BASE + "/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail and not cond else ""), flush=True)


def main():
    print("== 1. 健康检查 ==", flush=True)
    r = requests.get(API + "/health", timeout=10)
    check("health 200", r.status_code == 200)

    print("== 2. 脚本录入 ==", flush=True)
    script = {
        "title": "总体国家安全观宣传脚本",
        "content": ("国家安全是民族复兴的根基。总体国家安全观强调政治安全、军事安全、国土安全、"
                    "经济安全、金融安全等多个领域的统筹协调。青年一代要增强国家安全意识，筑牢网络安全防线，"
                    "自觉维护国家主权和领土完整。反诈宣传进校园，共筑安全长城。"),
        "source": "smoke_test",
    }
    r = requests.post(API + "/scripts", json=script, timeout=10)
    check("创建脚本 200", r.status_code == 200)
    sid = r.json().get("id") if r.status_code == 200 else None
    check("脚本返回 id", bool(sid))

    r = requests.get(API + "/scripts", timeout=10)
    check("脚本列表 200", r.status_code == 200)

    print("== 3. 分镜生成 ==", flush=True)
    if sid:
        r = requests.post(API + "/storyboards", json={"script_id": sid}, timeout=240)
        check("生成分镜 200", r.status_code == 200)
        if r.status_code == 200:
            sb = r.json()
            shots = sb.get("shots") or []
            check("分镜有镜头(3-6)", 3 <= len(shots) <= 6, "shots=%d" % len(shots))
            check("分镜字段完整", bool(sb.get("key_points")) and all(
                {"index", "scene_desc", "narration", "ar_overlay", "duration_sec"} <= set(s)
                for s in shots))
            sb_id = sb["id"]
        else:
            check("分镜错误信息", "detail" in r.text)
            sb_id = None
    else:
        sb_id = None

    print("== 4. 场景识别 ==", flush=True)
    test_img = None
    up = os.path.join(ROOT, "data", "uploads")
    if os.path.isdir(up):
        for f in sorted(os.listdir(up)):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                test_img = os.path.join(up, f)
                break
    scene_id = None
    if test_img:
        with open(test_img, "rb") as fh:
            r = requests.post(API + "/scenes/analyze", files={"file": (os.path.basename(test_img), fh)},
                              timeout=120)
        check("上传识别 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            scene_id = d.get("id")
            check("识别含 OCR 文本", bool(d.get("ocr_text")))
            check("识别含文化属性", bool(d.get("culture_attributes")))
            check("识别含语义摘要", bool(d.get("semantic_summary")))
    else:
        print("  [SKIP] 无测试图片", flush=True)

    print("== 5. 视频合成 ==", flush=True)
    if sid and sb_id and scene_id:
        r = requests.post(API + "/videos", json={"storyboard_id": sb_id, "scene_id": scene_id}, timeout=20)
        check("发起合成 200", r.status_code == 200)
        vid = r.json().get("id")
        final, waited = None, 0
        while waited < 240:
            time.sleep(3)
            waited += 3
            v = requests.get(API + "/videos/%s" % vid, timeout=10).json()
            if v["status"] == "done":
                final = v
                break
            if v["status"] == "failed":
                check("合成失败且有原因", bool(v.get("error")), "error=" + str(v.get("error")))
                break
        check("合成成功(done)", final is not None, "waited=%ds" % waited)
        if final:
            p = final.get("path", "")
            check("成片文件存在", bool(p) and os.path.exists(p), p)
            if p and os.path.exists(p):
                check("成片大小>0", os.path.getsize(p) > 1000)
            r = requests.get(API + "/videos/%s/download" % vid, timeout=20)
            check("下载 200 & mp4", r.status_code == 200 and "video/mp4" in r.headers.get("content-type", ""))
    else:
        print("  [SKIP] 前置步骤未完成，跳过合成", flush=True)

    print("== 6. 异常/边界用例 ==", flush=True)
    # 6.1 空脚本
    r = requests.post(API + "/scripts", json={"title": "x", "content": "   "}, timeout=10)
    check("空脚本 400", r.status_code == 400)
    # 6.2 不存在的分镜
    r = requests.post(API + "/videos", json={"storyboard_id": "nope", "scene_id": "nope"}, timeout=10)
    check("不存在分镜 404", r.status_code == 404)
    # 6.3 不存在的脚本生成分镜
    r = requests.post(API + "/storyboards", json={"script_id": "nope"}, timeout=10)
    check("不存在脚本 404", r.status_code == 404)
    # 6.4 非法图片类型
    r = requests.post(API + "/scenes/analyze",
                      files={"file": ("t.txt", b"not image")}, timeout=10)
    check("非法类型 400", r.status_code == 400)
    # 6.5 超出大小（伪造 >10MB）
    big = b"\x89PNG\r\n" + b"0" * (10 * 1024 * 1024 + 1)
    try:
        r = requests.post(API + "/scenes/analyze",
                          files={"file": ("big.png", big)}, timeout=120)
        check("超大文件 413", r.status_code == 413)
    except Exception as e:
        check("超大文件 413", False, str(e))
    # 6.6 审核
    r = requests.post(API + "/audits", json={
        "target_type": "script", "target_id": sid or "x",
        "content": script["content"], "title": script["title"]}, timeout=60)
    check("审核 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("审核含结论", "final_status" in d and "auto_check" in d)

    print("\n==== 结果汇总 ====", flush=True)
    print("PASS: %d, FAIL: %d" % (len(PASS), len(FAIL)), flush=True)
    for name, detail in FAIL:
        print("  FAILED: %s | %s" % (name, detail), flush=True)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
