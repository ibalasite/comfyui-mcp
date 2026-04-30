"""
healthcheck.py — 確認 ComfyUI :8188 和 AudioLDM2 :8189 是否正常回應
"""
import httpx

def check(name, url):
    try:
        r = httpx.get(url, timeout=5)
        print(f"[OK]  {name} → {r.status_code}")
        return True
    except Exception as e:
        print(f"[ERR] {name} → {e}")
        return False

if __name__ == "__main__":
    ok1 = check("ComfyUI  :8188", "http://127.0.0.1:8188/system_stats")
    ok2 = check("AudioLDM2 :8189", "http://127.0.0.1:8189/health")
    print()
    if ok1 and ok2:
        print("✅ 兩個服務都正常，可以使用 MCP 工具")
    else:
        print("❌ 有服務未啟動，請先執行 start_servers.bat")
