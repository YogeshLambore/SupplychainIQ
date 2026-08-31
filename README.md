# NEXORA

**Sovereign on-premise agentic AI workbench for confidential industrial work.**

NEXORA is a fully local, offline AI intelligence workbench designed for engineering, finance, and document analysis. It successfully bridges the gap between natural language AI interactions and deterministic data analysis without relying on any external cloud APIs.

## Key Features
* **Document Intelligence:** Local RAG (Retrieval-Augmented Generation) over PDFs with source citations and visual page previews.
* **Finance Analytics:** Natural language queries powered by a deterministic, local Pandas/Matplotlib chart engine (Zero Hallucination).
* **Engineering Vision:** Multi-modal analysis of P&ID diagrams combined with sensor CSV data.
* **Sovereignty & Security:** Operates 100% locally. No API keys, no data leaving the host machine.
* **Resilient Fallback Engine:** Will never crash. Automatically falls back to secondary models or offline deterministic logic if the primary LLM is unavailable.

## Architecture & Technology Stack
* **Frontend:** Streamlit (Python)
* **Local Inference:** Ollama 
* **Primary LLM:** Llama 3 8B (`llama3:8b`)
* **Document Processor:** PyMuPDF (`fitz`)
* **RAG Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`)
* **Data & Math Engine:** Pandas & NumPy
* **Visualization Engine:** Matplotlib

## Local Setup

### 1. Install Dependencies
Ensure you have Python 3.10+ installed.
```bash
pip install -r requirements.txt
```

### 2. Ollama Setup
NEXORA requires a local instance of [Ollama](https://ollama.com/) to run the Llama 3 model.
1. Download and install Ollama.
2. Pull the required model:
```bash
ollama run llama3:8b
```
3. Ensure Ollama is running in the background (default port `11434`).

### 3. Run NEXORA
```bash
streamlit run app.py
```

## Cloud Deployment Limitations

**IMPORTANT: Vercel / Cloud Serverless Limitations**
NEXORA is designed as an *on-premise* AI workbench. It relies on a local instance of Ollama and heavily stateful Python data analysis libraries.

If you attempt to deploy this Streamlit application directly to serverless platforms like **Vercel**, you will face structural limitations:
1. Vercel serverless functions have hard timeouts that interrupt Streamlit's WebSocket connections.
2. Vercel cannot host a 4.7 GB Llama 3 8B model natively.
3. `localhost:11434` on Vercel is the serverless container, *not* your computer, so the cloud app will not be able to talk to your local Ollama instance unless you expose it publicly (e.g., via Ngrok).

**Recommended Production Demo Architecture:**
For demonstrating the UI in the cloud without re-architecting, use **Streamlit Community Cloud**. 
To enable the AI capabilities in the cloud, you must:
1. Expose your local Ollama server securely (e.g. using Ngrok) and set the `OLLAMA_HOST` environment variable on Streamlit Cloud to point to your secure tunnel URL.
2. OR, replace the Ollama integration with a cloud API for demonstration purposes.

If `OLLAMA_HOST` is unreachable, NEXORA will gracefully degrade to its **Fallback Behavior**, utilizing deterministic text extraction and Pandas math without LLM explanations, ensuring the app remains usable.
