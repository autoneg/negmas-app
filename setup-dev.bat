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

echo Step 1: Installing Python dependencies (incl. negmas* from PyPI)...
echo ------------------------------------------
REM All negmas* packages come from PyPI as normal dependencies. The app must work
REM without local checkouts, so we do NOT install editable packages from ..\ here.
call uv sync --all-extras --dev

echo.
echo Step 2: Installing Vue.js frontend dependencies...
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
