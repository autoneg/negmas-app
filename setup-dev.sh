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

echo "Step 1: Installing Python dependencies..."
echo "------------------------------------------"
uv sync --all-extras --dev

echo ""
echo "Step 2: Installing local negmas packages..."
echo "------------------------------------------"
for x in negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl negmas; do
    if [ -d "../$x" ]; then
        echo "Installing ../$x"
        uv pip install -e ../$x
    else
        echo "Warning: ../$x not found, skipping"
    fi
done

echo ""
echo "Step 3: Installing Vue.js frontend dependencies..."
echo "------------------------------------------"
if [ -d "negmas_vue/frontend" ]; then
    cd negmas_vue/frontend
    npm install
    cd ../..
    echo "✓ Vue.js frontend dependencies installed"
else
    echo "Warning: negmas_vue/frontend not found, skipping"
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "To run the apps:"
echo ""
echo "Alpine.js version (stable):"
echo "  negmas-app run"
echo "  → http://127.0.0.1:8019"
echo ""
echo "Vue.js version (in development):"
echo "  python -m negmas_vue.backend.main dev"
echo "  → http://127.0.0.1:5174"
echo ""
echo "=========================================="
