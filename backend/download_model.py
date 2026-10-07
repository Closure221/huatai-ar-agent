# -*- coding: utf-8 -*-
"""下载 Qwen2.5-0.5B-Instruct 到本地 models 目录（ModelScope 国内源）"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import MODEL_DIR

os.environ.setdefault("MODELSCOPE_CACHE", str(MODEL_DIR))

from modelscope import snapshot_download  # noqa: E402

model_id = "Qwen/Qwen2.5-0.5B-Instruct"
print(f"开始下载 {model_id} -> {MODEL_DIR}")
path = snapshot_download(model_id, cache_dir=str(MODEL_DIR))
print("下载完成:", path)

# 记录本地路径供 storyboard 模块读取
with open(MODEL_DIR / "qwen_path.txt", "w", encoding="utf-8") as f:
    f.write(str(path))
print("路径已记录")
