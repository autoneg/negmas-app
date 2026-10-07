#!/usr/bin/env bash
set -e

echo "=========================================="
echo "NegMAS App - Development Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

echo "Step 1: Installing Python dependencies (incl. negmas* from PyPI)..."
echo "------------------------------------------"
# All negmas* packages come from PyPI as normal dependencies. The app must work
# without local checkouts, so we do NOT install editable packages from ../ here.
uv sync --all-extras --dev

echo ""
echo "Step 2: Installing Vue.js frontend dependencies..."
echo "------------------------------------------"
if [ -d "src/frontend" ]; then
    cd src/frontend
    npm install
    cd ../..
    echo "✓ Vue.js frontend dependencies installed"
else
    echo "Warning: src/frontend not found, skipping"
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "To run the app:"
echo ""
echo "Vue.js version (default):"
echo "  negmas-app run          # Start both backend + frontend"
echo "  → http://127.0.0.1:5174"
echo ""
echo "  Options:"
echo "    --port 5174           # Frontend port (default)"
echo "    --backend-port 8019   # Backend port (default)"
echo "    --no-dev              # Disable auto-reload"
echo ""
echo "Alpine.js version (legacy):"
echo "  negmas-legacy run"
echo "  → http://127.0.0.1:8019"
echo ""
echo "Commands:"
echo "  negmas-app run        # Start app"
echo "  negmas-app kill       # Stop app"
echo "  negmas-app restart    # Restart app"
echo ""
echo "=========================================="
