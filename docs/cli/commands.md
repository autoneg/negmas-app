# Command Reference

This page documents all available CLI commands for NegMAS App.

## Main Commands

### negmas-app run / start

Start the NegMAS App (both backend and frontend servers).

```bash
negmas-app run [OPTIONS]
negmas-app start [OPTIONS]  # alias for 'run'
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--port`, `-p` | 5174 | Frontend port |
| `--backend-port` | 8019 | Backend API port |
| `--host` | 127.0.0.1 | Host to bind to |
| `--dev/--no-dev` | --no-dev | Enable auto-reload for development |
| `--log-level` | error | Logging level (debug, info, warning, error) |

### negmas-app kill

Stop all running NegMAS App processes.

```bash
negmas-app kill [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--backend-port` | 8019 | Backend port to kill |
| `--frontend-port` | 5174 | Frontend port to kill |
| `--force`, `-f` | False | Force kill without verification |

### negmas-app restart

Restart the application (kill + start).

```bash
negmas-app restart [OPTIONS]
```

Accepts the same options as `run` and `kill`.

### negmas-app setup

Initial setup - extract bundled scenarios and create user directories.

```bash
negmas-app setup [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--force`, `-f` | False | Overwrite existing files |
| `--skip-cache` | False | Skip copying cache files |

---

## Cache Commands

### negmas-app cache build

Build cache files for scenarios.

```bash
negmas-app cache build scenarios [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--all` | False | Build all cache types |
| `--stats` | False | Build statistics cache only |
| `--info` | False | Build info cache only |
| `--plots` | False | Build plot cache only |
| `--refresh` | False | Rebuild existing caches |
| `--max-pareto-utils` | 20000 | Max utility evaluations for Pareto |
| `--max-pareto-outcomes` | 1000 | Max outcomes in Pareto front |
| `--ensure-finite-reserved-values` | False | Fix invalid reserved values |

### negmas-app cache clear

Clear cache files for scenarios.

```bash
negmas-app cache clear scenarios [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--all` | False | Clear all cache types |
| `--stats` | False | Clear statistics cache only |
| `--info` | False | Clear info cache only |
| `--plots` | False | Clear plot cache only |
| `--force`, `-f` | False | Skip confirmation prompt |

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
