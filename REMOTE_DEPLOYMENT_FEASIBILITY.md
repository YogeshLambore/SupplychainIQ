# SupplyChain AI - Remote SIH Deployment Feasibility Audit

## EXECUTIVE SUMMARY
Deploying SupplyChain AI to a remote server so your laptop can remain OFF is **technically feasible but requires a paid cloud server**. The primary blocker for "free" hosting is the substantial RAM (16GB) and Disk (30GB) requirement needed to host Ollama and its models. Current free-tier cloud platforms (like AWS Free Tier, Render, Railway) do not offer sufficient memory. A low-cost GPU cloud instance (like RunPod or DigitalOcean) is the recommended path for a lag-free demonstration.

## CURRENT ARCHITECTURE
- **Streamlit entry point:** `app.py`
- **Python version:** 3.10+
- **Ollama Dependency:** Hard requirement via HTTP API (`OLLAMA_HOST` configurable).
- **RapidOCR Dependencies:** Uses `rapidocr-onnxruntime` and `opencv-python-headless` (compatible with Linux/Cloud environments).
- **Storage:** Uses relative local paths (`./data/chroma`, `./data/uploads`), meaning persistent block storage is required on the remote host to maintain session history.
- **External Network:** Air-gapped. 0 external API dependencies.
- **Windows Specifics:** None. The codebase is purely Python and entirely cross-platform.

## MODEL RESOURCE REQUIREMENTS
The application currently orchestrates four local models via Ollama. 
- `llama3:8b` (4.7 GB) - Deep Reasoning
- `qwen3.5:4b` (3.4 GB) - Fast Chat
- `qwen2.5-coder:3b` (1.9 GB) - Coding
- `moondream:1.8b` (1.7 GB) - Engineering Vision
**Total Model Disk Size:** ~11.7 GB

- **RAM Requirement:** Ollama dynamically swaps models into memory. To run `llama3:8b` and the Streamlit backend simultaneously without crashing, a strict minimum of **8 GB RAM** is required, though **16 GB RAM** is highly recommended.
- **VRAM / CPU Fallback:** If deployed to a CPU-only server, Ollama will gracefully fallback to CPU inference. However, generating responses with `llama3:8b` on a standard cloud CPU will be sluggish (~3-6 tokens/sec). A GPU is required for a snappy SIH demo experience.

## REMOTE SERVER REQUIREMENTS

### A. Minimum Technically Possible (CPU-Only, Slow)
- **CPU:** 4-Core
- **RAM:** 8 GB
- **GPU:** None
- **Disk:** 30 GB SSD

### B. Recommended SIH Demo (Budget GPU)
- **CPU:** 4-Core
- **RAM:** 16 GB
- **GPU:** NVIDIA T4 or RTX 3060 (8 GB VRAM)
- **Disk:** 40 GB SSD

### C. Comfortable Production-like Demo
- **CPU:** 8-Core
- **RAM:** 16+ GB
- **GPU:** NVIDIA A10G, RTX 3090, or A4000 (16+ GB VRAM)
- **Disk:** 50 GB SSD

## DEPLOYMENT OPTIONS

**OPTION A: Streamlit-only cloud hosting (e.g., Streamlit Community Cloud)**
- **Can current SupplyChain AI run?** NO.
- **Why?** It cannot host Ollama. You would have to expose your laptop's Ollama publicly using Ngrok and point the cloud app to it, meaning your laptop must stay ON.

**OPTION B: Cloud VM + Streamlit + Ollama (CPU Only)**
- **Can current SupplyChain AI run?** YES.
- **Trade-offs:** Cheapest standalone option (e.g., DigitalOcean $12-$24/mo droplet). However, LLM inference will be noticeably slow because it lacks a GPU.

**OPTION C: Cloud GPU VM + Streamlit + Ollama**
- **Can current SupplyChain AI run?** YES.
- **Trade-offs:** Requires a provider like RunPod, AWS EC2, or vast.ai. Extremely fast, perfect SIH experience. Laptop can be OFF. Costs roughly ~$0.20 to $0.50 per hour while running.

**OPTION D: Containerized SupplyChain AI + Remote Inference**
- **Can current SupplyChain AI run?** YES (with `Dockerfile`).
- **Trade-offs:** Highest complexity. Requires packaging SupplyChain AI into a Docker image and writing a `docker-compose.yml` to spin up both Streamlit and Ollama containers simultaneously.

## FREE/LOW-COST OPTIONS
- **Hugging Face Spaces (Docker):** FREE BUT INSUFFICIENT. (Free tier is CPU-only, installing Ollama + Streamlit inside a single HF Docker container is fragile and slow).
- **Vercel / Render / Railway Free Tiers:** FREE BUT INSUFFICIENT. (RAM limits are usually 512MB, completely incapable of running a 4.7GB LLM).
- **GitHub Codespaces:** FREE BUT INSUFFICIENT. (Goes to sleep when you close your browser; not a permanent URL).
- **RunPod / Vast.ai:** PAID (~$0.30/hr). Excellent GPU instances for a live demo, but requires a credit card.
- **DigitalOcean / Hetzner:** PAID (~$15/mo). Standard CPU VMs. 

## SECURITY REQUIREMENTS
If hosted remotely, anyone with the URL can access SupplyChain AI. 
- **Authentication:** Currently absent. Anyone can upload files.
- **Ollama API:** Must be bound to `localhost` inside the cloud VM so the public cannot hijack your inference engine.

## CLOUDFLARE REQUIREMENTS
The current URL (`https://treated-ampland-sized-affecting.trycloudflare.com`) is a **Quick Tunnel pointing to your local machine**. It will immediately break the moment your laptop goes to sleep or changes networks.
To achieve laptop independence, you must install `cloudflared` on the **remote Cloud VM** (Options B or C) and route the tunnel from the cloud server instead.

## RISKS & BLOCKERS
- **BLOCKER:** No `Dockerfile` currently exists to easily migrate the complex Python environment to a cloud server.
- **BLOCKER:** `OLLAMA_HOST` requires exact configuration in a cloud environment if Streamlit and Ollama are separated.
- **RISK:** No authentication means SIH judges (or anyone else) can view other judges' chat histories or uploaded P&IDs if they visit the URL simultaneously.

## RECOMMENDED NEXT IMPLEMENTATION STEP
If you commit to a laptop-independent deployment, the exact next step is: **Create a `Dockerfile` and `docker-compose.yml`**. This will containerize Streamlit and Ollama together, allowing you to easily deploy the entire stack to a paid GPU host like RunPod with a single command.

==================================================
REMOTE_DEPLOYMENT_STATUS:
FEASIBLE_WITH_CHANGES

LAPTOP_INDEPENDENT_DEPLOYMENT:
YES

GPU_REQUIRED:
DEPENDS (Technically no, but strongly recommended for SIH demo latency)

FREE_OPTION:
NOT_AVAILABLE (No free tier exists with 16GB RAM for local LLMs)

CODE_CHANGES_REQUIRED:
MINOR (Requires adding Dockerfiles; Python code is fine)
