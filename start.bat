@echo off
chcp 65001 >nul
title Huatai AR Agent
cd /d "%~dp0"

REM 优先使用项目 .venv（绝对路径，避免 cd 后相对路径失效）
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

echo Starting Huatai AR Agent...
echo Python: %PYTHON_EXE%
echo URL: http://127.0.0.1:8000

start "HuataiAR" "%PYTHON_EXE%" "%~dp0backend\run_server.py"
timeout /t 6 /nobreak >nul
start http://127.0.0.1:8000
echo.
echo Service started. Browser will open automatically.
pause
