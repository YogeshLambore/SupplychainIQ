import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
DEMO_DIR = DATA_DIR / "demo"
MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure directories exist
for _dir in [DATA_DIR, DEMO_DIR, MODELS_DIR, OUTPUTS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# Application Config
APP_NAME = "NEXORA"
APP_SUBTITLE = "SOVEREIGN AI WORKBENCH"
APP_VERSION = "0.1.0-prototype"

# Model paths (Expected locations for local models)
LLAMA_MODEL_PATH = MODELS_DIR / "llama-3-8b-instruct.gguf"
MOONDREAM_MODEL_PATH = MODELS_DIR / "moondream2.safetensors"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Security & Limits
MAX_UPLOAD_SIZE_MB = 50
SANDBOX_TIMEOUT_SEC = 15

# UI Theme Config (Enterprise Dark)
THEME_COLOR_PRIMARY = "#10b981" # Emerald Green
THEME_COLOR_BACKGROUND = "#0f1115"
THEME_COLOR_CARD = "#1e2128"
THEME_COLOR_TEXT = "#e2e8f0"
THEME_COLOR_MUTED = "#64748b"
THEME_COLOR_WARNING = "#f59e0b"
THEME_COLOR_ERROR = "#ef4444"
