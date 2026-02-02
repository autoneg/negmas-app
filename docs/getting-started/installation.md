# Installation

This guide covers how to install NegMAS App on your system.

## Requirements

- **Python 3.11+** (3.12+ recommended)
- **Node.js 18+** (for development only)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

## Installation Methods

### Using pip (Recommended)

```bash
pip install negmas-app
```

### Using uv (Faster)

```bash
uv pip install negmas-app
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Run the setup script
./setup-dev.sh   # Linux/macOS
setup-dev.bat    # Windows

# Or manually install dependencies
uv sync --all-extras --dev
cd src/frontend && npm install && cd ../..
```

## First-Time Setup

After installation, you **must run the setup command** to extract bundled scenarios:

```bash
negmas-app setup
```

This command will:

1. Extract 279 ANAC scenarios to `~/negmas/app/scenarios/`
2. Optionally build cache files for faster loading
3. Check for Genius Bridge (required for ANAC/Genius agents)

### Setup Options

```bash
# Basic setup with all caches
negmas-app setup

# Skip cache files (faster setup, slower runtime)
negmas-app setup --skip-cache

# Force overwrite existing files
negmas-app setup --force
```

### Cache Types

During setup, you'll be asked about building caches:

| Cache Type | Description | Size | Benefit |
|------------|-------------|------|---------|
| **Info** | Basic scenario metadata | ~1 MB | Fast scenario browsing |
| **Stats** | Pre-calculated statistics | ~1-5 MB | Instant stats display |
| **Plots** | Pre-rendered visualizations | ~10-20 MB | Instant plot display |

**Recommendation**: Build info and stats caches. Plots are optional.

## Verifying Installation

```bash
# Start the application
negmas-app start

# This should:
# 1. Start the backend server on port 8019
# 2. Start the frontend server on port 5174
# 3. Open your browser to http://127.0.0.1:5174
```

If the browser doesn't open automatically, navigate to `http://127.0.0.1:5174`.

## Optional Dependencies

### Genius Bridge (for ANAC Agents)

Genius agents require Java and the Genius Bridge:

```bash
# macOS
brew install openjdk

# Ubuntu/Debian
sudo apt install default-jdk
```

The Genius Bridge will be downloaded automatically during setup if needed.

### Development Tools

```bash
# Install development dependencies
uv pip install negmas-app[dev]

# Or with pip
pip install negmas-app[dev]
```

### Documentation

```bash
# Install documentation dependencies
uv pip install negmas-app[docs]
```

## Troubleshooting

### Port Already in Use

```bash
# Kill existing servers
negmas-app kill

# Then start again
negmas-app start

# Or use custom ports
negmas-app start --port 5175 --backend-port 8020
```

### Scenarios Not Found

```bash
# Re-run setup
negmas-app setup --force
```

### Frontend Not Loading

Make sure you're accessing the correct URL: `http://127.0.0.1:5174` (not 8019).

The backend runs on port 8019, but the frontend (Vue.js) runs on port 5174.

## Updating

```bash
# Using uv
uv pip install --upgrade negmas-app

# Using pip
pip install --upgrade negmas-app

# Update scenarios after upgrade
negmas-app update-scenarios
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first negotiation
- [Configuration](configuration.md) - Customize the application
