@echo off
echo =========================================
echo SUPPLYCHAIN AI SIH 2026 STARTUP SCRIPT
echo =========================================

echo.
echo [1/3] Verifying Ollama...
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not running! Please start Ollama before launching SUPPLYCHAIN AI.
    pause
    exit /b 1
)
echo [OK] Ollama is active.

echo.
echo [2/3] Activating Virtual Environment...
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv!
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

echo.
echo [3/3] Starting Streamlit on Localhost Only...
echo (Keep this window open. Press Ctrl+C to stop the server.)
echo.
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
