# STARTUP.md — 服務啟動指南

每次開機或重啟後，必須依序啟動以下服務，Claude Desktop 才能使用 MCP 工具。

---

## 快速啟動（推薦）

以**系統管理員**身份執行：

```
右鍵 C:\comfyuimcp\start_all.bat → 以系統管理員身份執行
```

等待兩個視窗出現「Ready」訊息後即可使用。

---

## 服務說明

| 服務 | 埠號 | 用途 | 啟動時間 |
|---|---|---|---|
| ComfyUI | :8188 | 圖片生成（SDXL / Flux） | 約 20–40 秒 |
| AudioLDM2 | :8189 | 音效生成 | 約 40–60 秒 |

---

## 完整啟動步驟

### 步驟 1：啟動 ComfyUI

開啟一個新的命令提示字元，執行：

```bat
cd C:\ComfyUI
python main.py --listen 127.0.0.1 --port 8188 --preview-method auto
```

**等待看到此訊息才代表就緒：**
```
To see the GUI go to: http://127.0.0.1:8188
```

### 步驟 2：啟動 AudioLDM2

開啟另一個命令提示字元，執行：

```bat
cd C:\comfyuimcp
python audio_server.py
```

**等待看到此訊息才代表就緒：**
```
AudioLDM2 ready on cuda
INFO: Application startup complete.
```

### 步驟 3：確認服務正常

執行健康檢查：

```bat
cd C:\comfyuimcp
python healthcheck.py
```

預期輸出：
```
[OK]  ComfyUI   :8188 → 200
[OK]  AudioLDM2 :8189 → 200
✅ 兩個服務都正常，可以使用 MCP 工具
```

### 步驟 4：重啟 Claude Desktop

每次更換 MCP 設定後需重啟。一般使用不需要。

---

## 一鍵啟動腳本（start_all.bat）

`C:\comfyuimcp\start_all.bat` 會自動完成步驟 1–2，並在啟動後執行健康檢查。

---

## VRAM 使用量參考

| 模式 | 佔用 VRAM |
|---|---|
| ComfyUI 閒置 | ~1 GB |
| 生成 SDXL 圖片時 | ~8–10 GB |
| 生成 Flux 圖片時 | ~12–15 GB |
| AudioLDM2（CUDA 模式） | ~4–6 GB |
| 同時生圖 + 音效 | ~16–20 GB |

RTX 5090 有 24GB，可同時運行，留有約 4GB 餘量。

---

## 停止服務

關閉對應的命令提示字元視窗即可，或在視窗中按 `Ctrl+C`。

---

## 常見問題

### ComfyUI 啟動失敗：`Address already in use`
埠 8188 被佔用，執行：
```bat
netstat -ano | findstr :8188
taskkill /PID <找到的PID> /F
```

### AudioLDM2 啟動失敗：`Address already in use`
```bat
netstat -ano | findstr :8189
taskkill /PID <找到的PID> /F
```

### Claude Desktop 看不到 MCP 工具
1. 確認 `%APPDATA%\Claude\claude_desktop_config.json` 有 `local-media-gen` 區塊
2. 重啟 Claude Desktop
3. 在 Claude 介面左下角確認出現 🔨 工具圖示
