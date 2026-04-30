@echo off
chcp 65001 >nul
title ComfyUI MCP — 啟動中

echo ==========================================
echo   ComfyUI MCP 服務啟動器
echo ==========================================
echo.

:: 檢查 ComfyUI 是否存在
if not exist "C:\ComfyUI\main.py" (
    echo [ERROR] 找不到 C:\ComfyUI\main.py
    echo         請先安裝 ComfyUI 到 C:\ComfyUI
    pause & exit /b 1
)

:: 檢查 audio_server.py 是否存在
if not exist "C:\comfyuimcp\audio_server.py" (
    echo [ERROR] 找不到 C:\comfyuimcp\audio_server.py
    pause & exit /b 1
)

echo [1/2] 啟動 ComfyUI (:8188) ...
start "ComfyUI :8188" cmd /k "cd /d C:\ComfyUI && python main.py --listen 127.0.0.1 --port 8188 --preview-method auto"

echo [2/2] 啟動 AudioLDM2 (:8189) ...
start "AudioLDM2 :8189" cmd /k "cd /d C:\comfyuimcp && python audio_server.py"

echo.
echo 兩個服務已在獨立視窗中啟動。
echo.
echo 等待 60 秒後自動執行健康檢查...
timeout /t 60 /nobreak >nul

echo.
echo [健康檢查]
cd /d C:\comfyuimcp
python healthcheck.py

echo.
echo 完成！可以開始使用 Claude Desktop MCP 工具。
echo 關閉此視窗不會影響服務運行。
pause
