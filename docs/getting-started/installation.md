# Installation

## Requirements

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Install from PyPI

```bash
# Using uv (recommended)
uv pip install negmas-app

# Using pip
pip install negmas-app
```

## Install from Source

```bash
# Clone the repository
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Optional Dependencies

### Development Tools

```bash
# Install development dependencies
uv pip install negmas-app[dev]

# Or with pip
pip install negmas-app[dev]
```

This includes:
- pytest for testing
- pyright for type checking
- Coverage tools

### Documentation

```bash
# Install documentation dependencies
uv pip install negmas-app[docs]
```

This includes:
- MkDocs
- Material theme
- API documentation generators

## Verify Installation

```bash
# Check the installation
negmas-app --version

# Start the server
negmas-app

# Or specify a port
negmas-app --port 8080
```

The app will be available at http://127.0.0.1:8019 (default).

## Updating

```bash
# Using uv
uv pip install --upgrade negmas-app

# Using pip
pip install --upgrade negmas-app
```

## Troubleshooting

### Port Already in Use

If port 8019 is already in use:

```bash
# Use a different port
negmas-app --port 8080

# Or kill the existing process
lsof -ti:8019 | xargs kill -9
```

### Missing Dependencies

If you encounter import errors, ensure all dependencies are installed:

```bash
uv pip install negmas negmas-genius-agents negmas-llm
```

### Genius Bridge Issues

The Genius Bridge requires Java. Install it with:

```bash
# macOS
brew install openjdk

# Ubuntu/Debian
sudo apt install default-jdk
```
