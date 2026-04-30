# AGENTS.md — ComfyUI MCP 專案指引

每次進入此目錄，先讀完本檔再讀 `PROGRESS.md`，然後**立刻開始自動執行**。

---

## 自動作業原則

**不等待使用者指示**，每次進入此目錄就按照 PROGRESS.md 的狀態，自動推進下一個未完成的任務。完成後更新 PROGRESS.md 的狀態欄。

執行順序：
1. 讀 PROGRESS.md，找出第一個 `⏳ 待辦` 或 `❌ 阻塞` 的任務
2. 自動執行該任務（安裝套件、clone repo、寫設定檔等）
3. 完成後把狀態改為 `✅ 完成`，記錄執行結果到「更新日誌」
4. 繼續下一個，直到所有任務都 `✅ 完成` 或遇到真正需要人工的阻塞

遇到阻塞時，**絕對不能直接標記放棄**，必須依序嘗試：
1. 分析根本原因（缺套件？路徑錯？權限？網路？版本衝突？）
2. 嘗試替代方案：
   - 下載失敗 → 換 HuggingFace 鏡像、用 Python requests 分段下載、找替代模型
   - 安裝失敗 → 查錯誤訊息、換版本、換替代套件、先裝依賴
   - 路徑不存在 → 自動 mkdir
   - 權限問題 → 找繞過方式或換路徑
   - 網路逾時 → 重試、分段、換工具（curl/wget/python）
3. 窮盡所有方法後才能標記 `❌ 阻塞（需人工）`，且必須在「已知問題」寫清楚：嘗試過什麼、為何失敗、使用者需做什麼。

**永遠不要因為「需要人工」就第一時間放棄——先想盡辦法自己解決。**

---

## 專案目標

建立一個本地 AI 媒體生成系統，透過 MCP 讓 Claude Desktop 能夠：
- 呼叫 ComfyUI 在本機 RTX 5090 (24GB VRAM) 生成圖片
- 呼叫 AudioLDM2 在本機生成音效／音樂片段
- 所有生成物存入 `output/` 資料夾

---

## 架構

```
Claude Desktop
    ↓ MCP (stdio)
mcp_server.py          ← MCP 工具路由器
    ├─→ :8188          ← ComfyUI (圖像)
    └─→ :8189          ← audio_server.py / AudioLDM2 (音效)
                              ↓
                         output/  (PNG / WAV)
```

---

## 檔案職責

| 檔案 | 職責 |
|---|---|
| `mcp_server.py` | MCP Server 主體，定義 3 個 Tools |
| `audio_server.py` | AudioLDM2 FastAPI 包裝，監聽 :8189 |
| `requirements.txt` | Python 依賴套件 |
| `start_servers.bat` | 一鍵啟動 ComfyUI + AudioLDM2 |
| `claude_desktop_config_snippet.json` | 貼入 Claude Desktop config 的片段 |
| `output/` | 所有生成物的輸出目錄 |

---

## MCP 工具清單

| Tool | 參數 | 說明 |
|---|---|---|
| `generate_image` | prompt, width, height, steps | 透過 ComfyUI 生圖，直接回傳圖片 |
| `generate_audio` | prompt, duration, steps | 透過 AudioLDM2 生音效，回傳 WAV 路徑 |
| `list_outputs` | (無) | 列出 output/ 最近 20 個檔案 |

---

## 本機環境

- GPU: RTX 5090 Laptop, 24GB VRAM
- Python: 3.13
- ComfyUI 安裝目標路徑: `C:\ComfyUI`
- 預設模型: SDXL `sd_xl_base_1.0.safetensors`
- OS: Windows 11

---

## 自動執行規則

1. **不要動 `output/`** — 只有程式寫入
2. **workflow 修改** — 換模型只改 `build_image_workflow()`
3. **埠號固定** — ComfyUI :8188，AudioLDM2 :8189
4. **安裝套件** — 直接跑 `pip install`，不詢問
5. **寫設定檔** — 直接寫入 `%APPDATA%\Claude\claude_desktop_config.json`，合併不覆蓋
6. **VRAM 預算** — Flux ~15GB + AudioLDM2 ~5GB = 20GB，超出先啟用 cpu_offload
