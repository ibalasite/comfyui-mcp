@echo off
:: 建立 Windows 工作排程器任務，每 5 分鐘執行 auto_runner.py
:: 需以「系統管理員」身份執行

set TASK_NAME=ComfyUIMCP-AutoRunner
set PYTHON=python
set SCRIPT=C:\comfyuimcp\auto_runner.py
set LOG=C:\comfyuimcp\runner.log

echo [*] 建立排程任務: %TASK_NAME%

schtasks /Create /F /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON%\" \"%SCRIPT%\" >> \"%LOG%\" 2>&1" ^
  /SC MINUTE /MO 5 ^
  /RL HIGHEST ^
  /RU "%USERNAME%"

if %ERRORLEVEL% EQU 0 (
    echo [OK] 排程建立成功！每 5 分鐘自動檢查 PROGRESS.md
    echo [*] 立刻執行一次...
    schtasks /Run /TN "%TASK_NAME%"
) else (
    echo [ERROR] 排程建立失敗，請用系統管理員身份重新執行此 bat 檔
)

pause
