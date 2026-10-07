# -*- coding: utf-8 -*-
"""华泰杯 AR 后端启动器（供 start.bat / 手动调用）

用法：.venv\\Scripts\\python.exe backend\\run_server.py
使用 --app-dir 显式指定 backend 为应用根目录，避免 cd 带来的相对路径问题。
"""
import sys
from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        app_dir=str(BACKEND_DIR),
        log_level="info",
    )
