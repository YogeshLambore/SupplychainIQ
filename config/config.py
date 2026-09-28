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

# UI Theme Config (Sovereign Dark Enterprise)
THEME_COLOR_PRIMARY = "#3B82F6"      # Primary Blue
THEME_COLOR_BACKGROUND = "#070B14"   # Deep Navy
THEME_COLOR_SURFACE = "#0D1422"      # Navy Surface
THEME_COLOR_CARD = "#111B2E"         # Card Surface
THEME_COLOR_ELEVATED = "#17233A"     # Elevated Surface
THEME_COLOR_BORDER = "#26344D"       # Border Subtle
THEME_COLOR_TEXT = "#F8FAFC"         # Primary Text
THEME_COLOR_SECONDARY = "#94A3B8"    # Secondary Text
THEME_COLOR_MUTED = "#64748B"        # Muted Text
THEME_COLOR_SUCCESS = "#22C55E"      # Success Green
THEME_COLOR_WARNING = "#F59E0B"      # Warning Amber
THEME_COLOR_ERROR = "#EF4444"        # Critical Red
THEME_COLOR_INFO = "#38BDF8"         # Bright Info Blue

