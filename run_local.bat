@echo off
rem H3 Shot Studio against your own ComfyUI (start ComfyUI on port 8188 first).
cd /d %~dp0
.venv\Scripts\comfy-api-proxy.exe status >nul 2>&1 || .venv\Scripts\comfy-api-proxy.exe start --state-dir outputs\proxy-state
set COMFY_BASE_URL=http://127.0.0.1:8189
start "" http://127.0.0.1:7860
.venv\Scripts\python.exe -m shotstudio.server
