# Command Reference

This page documents all available CLI commands for NegMAS App.

## Main Application

### negmas-app

::: mkdocs-click
    :module: negmas_app.main
    :command: cli
    :prog_name: negmas-app
    :depth: 2

---

## Examples

### Starting the App

```bash
# Start with default settings
negmas-app run

# Start on custom ports
negmas-app run --port 3000 --backend-port 8000

# Start without development mode (no auto-reload)
negmas-app run --no-dev

# Start with debug logging
negmas-app run --log-level debug
```

### Managing Processes

```bash
# Stop all negmas-app processes
negmas-app kill

# Force kill (doesn't verify it's negmas-app)
negmas-app kill --force

# Restart the application
negmas-app restart
```

### Initial Setup

```bash
# Run interactive setup
negmas-app setup

# Force overwrite existing files
negmas-app setup --force

# Skip cache files
negmas-app setup --skip-cache
```

### Cache Management

```bash
# Build all caches for scenarios
negmas-app cache build scenarios --all

# Build only statistics cache
negmas-app cache build scenarios --stats

# Build with Pareto frontier limits
negmas-app cache build scenarios --stats --max-pareto-outcomes 10000

# Rebuild existing caches
negmas-app cache build scenarios --all --refresh

# Fix invalid reserved values while building
negmas-app cache build scenarios --stats --ensure-finite-reserved-values

# Clear all caches
negmas-app cache clear scenarios --all

# Clear only plot caches
negmas-app cache clear scenarios --plots

# Clear without confirmation
negmas-app cache clear scenarios --all --force
```

### Updating Scenarios

```bash
# Update scenarios from bundled package
negmas-app update-scenarios

# Force overwrite existing
negmas-app update-scenarios --force
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (check output for details) |

## Environment Variables

Currently, NegMAS App does not use environment variables for configuration. All settings are managed through:

- Command-line arguments
- Settings file at `~/negmas/app/settings.yaml`
- In-app settings dialog
