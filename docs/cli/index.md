# CLI Reference

NegMAS App provides a command-line interface (CLI) for managing the application, scenarios, and caches.

## Installation

The CLI is automatically installed when you install NegMAS App:

```bash
pip install negmas-app
```

Or with uv:

```bash
uv pip install negmas-app
```

## Quick Start

```bash
# First-time setup (extracts bundled scenarios)
negmas-app setup

# Start the application
negmas-app run

# Or equivalently
negmas-app start
```

## Command Groups

### Main Commands

| Command | Description |
|---------|-------------|
| `run` / `start` | Start the NegMAS App (backend + frontend) |
| `restart` | Restart the app (kill existing + start new) |
| `kill` | Stop running NegMAS App processes |
| `setup` | Initial setup - extract scenarios, configure caches |
| `update-scenarios` | Update scenarios from bundled package |

### Cache Management

The `cache` command group manages pre-computed data for faster loading:

| Command | Description |
|---------|-------------|
| `cache build scenarios` | Build cache files for scenarios |
| `cache clear scenarios` | Clear cache files for scenarios |

## Cache Types

NegMAS App uses three types of caches to speed up scenario loading:

| Cache | File | Description | Size |
|-------|------|-------------|------|
| **Info** | `_info.yaml` | Basic scenario metadata (issues, outcomes count) | ~1 KB each |
| **Stats** | `_stats.yaml` | Pre-calculated statistics (Pareto, Nash, Kalai, etc.) | ~1-10 KB each |
| **Plots** | `_plot.webp` | Pre-rendered outcome space visualizations | ~10-50 KB each |

### When to Use Caches

- **Info cache**: Always recommended. Makes scenario browsing instant.
- **Stats cache**: Recommended. Pre-calculates analysis that would otherwise take seconds.
- **Plots cache**: Optional. Trades disk space for instant plot display.

## Common Workflows

### First-Time Setup

```bash
# Extract scenarios and optionally build caches
negmas-app setup
```

The setup wizard will prompt you to choose which caches to build.

### Building Caches Manually

```bash
# Build all caches
negmas-app cache build scenarios --all

# Build only stats (most useful)
negmas-app cache build scenarios --stats

# Build with Pareto frontier limits (saves disk space)
negmas-app cache build scenarios --stats --max-pareto-outcomes 10000

# Rebuild existing caches
negmas-app cache build scenarios --all --refresh
```

### Clearing Caches

```bash
# Clear all caches
negmas-app cache clear scenarios --all

# Clear only plot caches (to save disk space)
negmas-app cache clear scenarios --plots
```

### Managing the Server

```bash
# Start the app
negmas-app run

# Start on custom ports
negmas-app run --port 3000 --backend-port 8000

# Restart after code changes
negmas-app restart

# Stop the app
negmas-app kill
```

## Environment

- **Default scenarios directory**: `~/negmas/app/scenarios/`
- **Default frontend port**: 5174
- **Default backend port**: 8019
- **Configuration file**: `~/negmas/app/settings.yaml`

## See Also

- [Commands Reference](commands.md) - Detailed command documentation
- [Configuration](../getting-started/configuration.md) - Application settings
- [Quick Start](../getting-started/quickstart.md) - Getting started guide
