@echo off
echo ==========================================
echo NegMAS App - Development Setup
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo Error: Must run from project root directory
    exit /b 1
)

echo Step 1: Installing Python dependencies...
echo ------------------------------------------
call uv sync --all-extras --dev

echo.
echo Step 2: Installing local negmas packages...
echo ------------------------------------------
for %%x in (negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl negmas) do (
    if exist "..\%%x" (
        echo Installing ..\%%x
        call uv pip install -e ..\%%x
    ) else (
        echo Warning: ..\%%x not found, skipping
    )
)

echo.
echo Step 3: Installing Vue.js frontend dependencies...
echo ------------------------------------------
if exist "src\frontend" (
    cd src\frontend
    call npm install
    cd ..\..
    echo ✓ Vue.js frontend dependencies installed
) else (
    echo Warning: src\frontend not found, skipping
)

echo.
echo ==========================================
echo ✓ Setup complete!
echo ==========================================
echo.
echo To run the app:
echo.
echo Vue.js version:
echo   python -m src.backend.main dev
echo   → http://127.0.0.1:5174
echo.
echo ==========================================
