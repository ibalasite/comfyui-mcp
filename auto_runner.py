"""
auto_runner.py — 每 5 分鐘檢查 PROGRESS.md，有未完成任務就叫 Claude Code 來做。
全部完成後自動停用 Windows 工作排程器任務。
"""

import re
import subprocess
import sys
from pathlib import Path

PROGRESS_FILE = Path("C:/comfyuimcp/PROGRESS.md")
TASK_NAME = "ComfyUIMCP-AutoRunner"
CLAUDE_PROMPT = (
    "請讀取 C:/comfyuimcp/AGENTS.md 和 C:/comfyuimcp/PROGRESS.md，"
    "找出所有狀態為「⏳ 待辦」的任務，從第一個開始依序自動執行，"
    "每完成一個立刻把 PROGRESS.md 的狀態改為「✅ 完成」並記錄到更新日誌，"
    "繼續執行下一個，直到所有任務完成或遇到需要人工處理的阻塞為止。"
)


def has_pending_tasks() -> bool:
    if not PROGRESS_FILE.exists():
        print("[ERROR] PROGRESS.md not found")
        return False
    content = PROGRESS_FILE.read_text(encoding="utf-8")
    return bool(re.search(r"⏳ 待辦", content))


def all_done() -> bool:
    if not PROGRESS_FILE.exists():
        return False
    content = PROGRESS_FILE.read_text(encoding="utf-8")
    return not re.search(r"⏳ 待辦", content) and not re.search(r"🔧 進行中", content)


def run_claude():
    print("[INFO] 發現未完成任務，啟動 Claude Code...")
    result = subprocess.run(
        ["claude", "--print", CLAUDE_PROMPT],
        cwd="C:/comfyuimcp",
        capture_output=False,
        text=True,
    )
    print(f"[INFO] Claude Code 結束，return code: {result.returncode}")


def disable_scheduler():
    print("[INFO] 所有任務完成，停用排程...")
    subprocess.run(
        ["schtasks", "/Change", "/TN", TASK_NAME, "/DISABLE"],
        capture_output=False,
    )
    print("[INFO] 排程已停用。")


def main():
    print(f"[CHECK] 檢查 PROGRESS.md...")

    if all_done():
        print("[DONE] 所有任務已完成，停用排程。")
        disable_scheduler()
        return

    if has_pending_tasks():
        run_claude()
        # 執行後再確認一次
        if all_done():
            print("[DONE] 所有任務完成，停用排程。")
            disable_scheduler()
    else:
        print("[OK] 無待辦任務（可能有阻塞，請查看 PROGRESS.md）。")


if __name__ == "__main__":
    main()
