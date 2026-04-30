# ComfyUI MCP — 本地 AI 媒體生成系統

讓 Claude Desktop 透過 MCP 協議，直接調用本機 RTX 5090 生成圖片與音效。無需雲端排隊，秒級回應。

---

## 功能

| 工具 | 說明 |
|---|---|
| `generate_image` | SDXL / Flux.1-schnell 生圖，支援 LoRA、批次、negative prompt |
| `img2img` | 圖片風格轉換，可控制 denoise 強度 |
| `generate_audio` | AudioLDM2 生成音效 / 音樂，支援 negative prompt |
| `list_outputs` | 列出所有生成物 |

## 架構

```
Claude Desktop
    ↓ MCP (stdio)
mcp_server.py
    ├─→ ComfyUI :8188   (SDXL / Flux 圖片)
    └─→ AudioLDM2 :8189 (音效)
              ↓
         output/  (PNG / WAV)
```

## 環境需求

- Windows 11
- NVIDIA RTX 5090（24GB VRAM）
- Python 3.13
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 安裝 ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI C:/ComfyUI
pip install -r C:/ComfyUI/requirements.txt
```

### 3. 模型檔案

| 模型 | 路徑 | 大小 |
|---|---|---|
| [SDXL base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | `C:\ComfyUI\models\checkpoints\` | 6.5 GB |
| [Flux.1-schnell Q4_K_S](https://huggingface.co/city96/FLUX.1-schnell-gguf) | `C:\ComfyUI\models\unet\` | 6.4 GB |
| [clip_l](https://huggingface.co/comfyanonymous/flux_text_encoders) | `C:\ComfyUI\models\clip\` | 235 MB |
| [flux_ae (VAE)](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) | `C:\ComfyUI\models\vae\` | 320 MB |

### 4. 設定 Claude Desktop

將以下內容合併到 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "local-media-gen": {
      "command": "python",
      "args": ["C:/comfyuimcp/mcp_server.py"],
      "env": {
        "COMFYUI_URL": "http://127.0.0.1:8188",
        "AUDIO_URL": "http://127.0.0.1:8189",
        "OUTPUT_DIR": "C:/comfyuimcp/output"
      }
    }
  }
}
```

### 5. 啟動服務

```bat
右鍵 start_all.bat → 以系統管理員身份執行
```

重啟 Claude Desktop 後即可使用。

## 使用範例

在 Claude 對話框直接說：

```
生成一張 512x512 奇幻戰士頭像，SDXL 模型

生成 4 張 slot game 符號，水果風格，batch=4

生成一個 3 秒的老虎機拉桿音效

把這張草圖轉成像素藝術風格
```

## 檔案說明

```
comfyuimcp/
├── mcp_server.py          # MCP 主程式（4 個工具）
├── audio_server.py        # AudioLDM2 FastAPI 服務
├── healthcheck.py         # 健康檢查
├── start_all.bat          # 一鍵啟動
├── requirements.txt       # Python 依賴
├── STARTUP.md             # 啟動指南
├── MANUAL.md              # 使用手冊
├── AGENTS.md              # Claude 自動作業規則
└── PROGRESS.md            # 任務進度追蹤
```

## 技術細節

- **圖片**：ComfyUI API mode，workflow 以 JSON 動態組裝
- **音效**：diffusers `AudioLDM2Pipeline`，已修補 transformers 4.57 相容性問題
- **MCP**：`mcp>=1.0.0` stdio transport
- **自動化**：AGENTS.md + PROGRESS.md 驅動 Claude 自動推進任務

## License

MIT
