# MANUAL.md — 使用手冊

本系統讓 Claude Desktop 能夠在你的本機 RTX 5090 上生成圖片與音效，不需要雲端服務。

---

## 系統需求

| 項目 | 需求 |
|---|---|
| GPU | NVIDIA RTX 5090（24GB VRAM） |
| OS | Windows 11 |
| Python | 3.13 |
| 服務 A | ComfyUI（圖片）|
| 服務 B | AudioLDM2（音效）|

---

## 第一次使用前

1. 執行 `start_all.bat`（系統管理員身份）
2. 等待兩個服務視窗都出現就緒訊息（約 60 秒）
3. 打開 Claude Desktop，左下角出現 🔨 圖示代表 MCP 連線成功

之後每次開機重複步驟 1–2 即可。

---

## Claude Desktop 可用工具

### 1. `generate_image` — 生成圖片

在 Claude 對話中要求生成圖片，Claude 會自動呼叫此工具，圖片直接顯示在對話框。

**可用參數：**

| 參數 | 說明 | 預設值 | 範圍 |
|---|---|---|---|
| `prompt` | 圖片描述（英文效果最佳）| 必填 | — |
| `negative` | 不想要的元素 | ugly, blurry... | — |
| `model` | 使用的模型 | `sdxl` | `sdxl` / `flux` |
| `width` | 圖片寬度（像素）| 1024 | 256–2048 |
| `height` | 圖片高度（像素）| 1024 | 256–2048 |
| `steps` | 生成步數（越高越精細）| 20 | 5–50 |
| `batch` | 一次生成幾張 | 1 | 1–4 |
| `lora` | LoRA 模型檔名（SDXL only）| 無 | — |

**對話範例：**

```
幫我生成一張 512x512 的遊戲角色頭像，奇幻戰士風格，使用 SDXL

幫我批次生成 4 張 slot game 符號小圖，一次出，水果風格

生成一張 Flux 模型的賽博龐克城市風景，1920x1080
```

---

### 2. `img2img` — 圖片轉換

提供一張底圖，描述想要的變化，系統會在保留構圖的前提下改變風格。

**可用參數：**

| 參數 | 說明 | 預設值 |
|---|---|---|
| `prompt` | 目標描述 | 必填 |
| `image_b64` | 來源圖片（Base64 編碼）| 必填 |
| `negative` | 不想要的元素 | ugly, blurry... |
| `denoise` | 改變強度（0=完全不動，1=完全重生成）| 0.75 |
| `steps` | 步數 | 20 |

**對話範例：**

```
把這張草稿圖轉成像素藝術風格，保留構圖，denoise 設 0.6
```

---

### 3. `generate_audio` — 生成音效

生成遊戲音效、環境音、音樂片段，回傳 WAV 檔案路徑。

**可用參數：**

| 參數 | 說明 | 預設值 | 範圍 |
|---|---|---|---|
| `prompt` | 音效描述（英文）| 必填 | — |
| `negative` | 不想要的音質 | low quality, noise... | — |
| `duration` | 長度（秒）| 3.0 | 1–10 |
| `steps` | 生成步數 | 25 | 5–50 |

**對話範例：**

```
生成一個 3 秒的 slot machine 拉桿聲音效

生成 5 秒的遊戲背景環境音，森林風格，帶有鳥鳴

生成一個 2 秒的 UI 點擊音效，清脆乾淨
```

---

### 4. `list_outputs` — 查看輸出目錄

列出最近生成的 20 個檔案。

**對話範例：**

```
列出最近生成了哪些圖片和音效
```

---

## 模型對照表

### 圖片模型

| 模型 | 用途 | 速度 | 特色 |
|---|---|---|---|
| SDXL | 通用圖片、角色、場景 | 中 | 品質穩定，支援 LoRA |
| Flux.1-schnell | 高品質圖片 | 快 | 細節豐富，不支援 LoRA |

### 音效模型

| 模型 | 用途 |
|---|---|
| AudioLDM2 | 通用音效、環境音、音樂片段 |

---

## 輸出目錄

所有生成物存放於：

```
C:\comfyuimcp\output\
├── img_xxxxxxxx.png     ← generate_image 輸出
├── sfx_xxxxxxxx.wav     ← generate_audio 輸出
└── test\               ← 驗收測試輸出
```

---

## 生成速度參考（RTX 5090）

| 任務 | 時間 |
|---|---|
| SDXL 512×512，steps=20 | 約 5–10 秒 |
| SDXL 1024×1024，steps=20 | 約 10–20 秒 |
| Flux 1024×1024，steps=20 | 約 8–15 秒 |
| 音效 3 秒，steps=25（CUDA）| 約 10–20 秒 |

---

## LoRA 使用方式

1. 將 `.safetensors` LoRA 檔案放到 `C:\ComfyUI\models\loras\`
2. 在對話中指定 `lora` 參數：

```
生成一張日式動漫風格角色頭像，使用 lora: anime_style.safetensors
```

---

## 常見問題

**Q：Claude 說工具不可用？**
→ 確認 ComfyUI 和 AudioLDM2 都已啟動，執行 `python healthcheck.py` 確認。

**Q：圖片生成到一半就失敗？**
→ VRAM 不足。縮小尺寸（512×512）或減少 steps，或先關掉音效服務。

**Q：音效聽起來很模糊？**
→ 增加 `steps` 到 30–40，或在 `negative` 加入 `"muffled, low quality"`。

**Q：想要固定風格每次都一樣？**
→ 目前每次使用隨機 seed，如需固定風格可透過 LoRA 實現。

**Q：生成的圖片在哪裡？**
→ `C:\comfyuimcp\output\`，或請 Claude 執行 `list_outputs`。

---

## 專案目錄結構

```
C:\comfyuimcp\
├── AGENTS.md                    ← Claude 自動作業規則
├── PROGRESS.md                  ← 任務進度追蹤
├── STARTUP.md                   ← 啟動指南
├── MANUAL.md                    ← 本使用手冊
├── mcp_server.py                ← MCP 主程式
├── audio_server.py              ← 音效服務
├── healthcheck.py               ← 健康檢查
├── start_all.bat                ← 一鍵啟動
├── requirements.txt             ← Python 依賴
├── test_report.md               ← 驗收報告
└── output\                      ← 所有生成物

C:\ComfyUI\
├── models\
│   ├── checkpoints\
│   │   └── sd_xl_base_1.0.safetensors   (6.5GB)
│   ├── unet\
│   │   └── flux1-schnell-Q4_K_S.gguf   (6.4GB)
│   ├── clip\
│   │   └── clip_l.safetensors           (235MB)
│   ├── vae\
│   │   └── flux_ae.safetensors          (320MB)
│   └── loras\                           ← 放 LoRA 檔案
```
