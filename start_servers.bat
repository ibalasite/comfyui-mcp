@echo off
title Local Media Gen Stack

echo [1/2] Starting AudioLDM2 server on :8189 ...
start "AudioLDM2" cmd /k "cd /d C:\Projects\comfyuimcp && python audio_server.py"

echo [2/2] Starting ComfyUI on :8188 ...
echo NOTE: Edit the path below to match your ComfyUI install location.
start "ComfyUI" cmd /k "cd /d C:\Projects\ComfyUI && python main.py --listen 127.0.0.1 --port 8188 --preview-method auto"

echo.
echo Both servers launched. Wait ~30s for models to load before using Claude.
pause
