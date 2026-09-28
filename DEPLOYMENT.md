# SupplyChain AI - SIH 2026 Production Deployment Guide

## 1. Architecture
SupplyChain AI runs completely locally on the Windows host. External SIH judges will connect via a secure HTTPS Cloudflare Tunnel.
`SIH Judge -> HTTPS -> Cloudflare Tunnel -> Windows Host -> 127.0.0.1:8501 (Streamlit) -> Local Ollama`

## 2. Hardware
- OS: Windows
- CPU: Ryzen 7 7445HS
- RAM: 16 GB
- GPU: RTX 3050 Laptop (4 GB VRAM)

## 3. Prerequisites
- Python 3.10.1
- Git
- Ollama
- cloudflared (Cloudflare Tunnel CLI)

## 4. Python Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5. Ollama Setup
Ensure Ollama is running in the background. It listens on `http://127.0.0.1:11434` by default.

## 6. Model Installation
The following models must be pulled if not already present:
```powershell
ollama pull qwen3.5:4b
ollama pull qwen2.5-coder:3b
ollama pull llama3:8b
ollama pull moondream:1.8b
```

## 7. SupplyChain AI Startup
Launch the application bound strictly to localhost (do NOT use 0.0.0.0):
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

## 8. Local Verification
Open `http://127.0.0.1:8501` in your local browser and verify all workspaces operate properly.

## 9. cloudflared Installation
Download `cloudflared.exe` from the official Cloudflare repository and place it in a folder in your System PATH (e.g., `C:\cloudflared\`).

## 10. Quick Tunnel (Testing)
To generate an immediate temporary URL for testing:
```powershell
cloudflared tunnel --url http://127.0.0.1:8501
```

## 11. Named Tunnel (Production SIH)
For the final SIH presentation, authenticate and create a permanent named tunnel:
```powershell
cloudflared tunnel login
cloudflared tunnel create SupplyChain AI-sih
cloudflared tunnel route dns SupplyChain AI-sih SupplyChain AI.<YOUR_DOMAIN.COM>
cloudflared tunnel run SupplyChain AI-sih
```

## 12. Custom Domain
A custom domain (e.g., via Cloudflare registrar) is required to use a Named Tunnel. If you do not have a domain, use the Quick Tunnel (Step 10) and provide the generated URL to the judges.

## 13. Public Testing
Test the generated public URL from a separate network (e.g., Mobile Hotspot on your phone). Verify File Uploads, Chat routing, and P&ID extraction.

## 14. Security
- **No Cloud AI:** All processing is done locally.
- **Port Security:** Do NOT open Windows Firewall port 8501 or 11434. The Cloudflare tunnel reaches localhost internally.
- **Data Protection:** `.gitignore` blocks uploads and private data from being committed.

## 15. Troubleshooting
- **Ollama Out of Memory:** The 4GB VRAM limit means switching to `llama3:8b` will push inference to CPU. This is expected. If it hangs, restart Ollama.
- **Streamlit Caching Errors:** If an `AttributeError` occurs during hot-reloads, use the UI's "Clear Cache" button or restart the Streamlit server.

## 16. SIH Judge Operation
Laptop must remain powered ON. Disable Windows Sleep/Hibernate. Do not close the Streamlit or Cloudflare terminals.

## 17. Shutdown Procedure
Press `Ctrl+C` in the Streamlit terminal. Press `Ctrl+C` in the Cloudflare terminal. Quit Ollama from the Windows System Tray.
