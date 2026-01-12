# Configuration

NegMAS App can be configured through settings files and the web interface.

## Settings Files

Settings are stored in YAML format. The app looks for settings in:

1. `~/negmas/app/settings.yaml` - Global settings
2. `./negmas_app/settings.yaml` - Local project settings (overrides global)

### Example Settings

```yaml
# ~/negmas/app/settings.yaml

# Server settings
server:
  host: "127.0.0.1"
  port: 8019

# Default negotiation settings
negotiation:
  default_steps: 100
  default_delay: 100  # ms between steps in real-time mode
  auto_save: true

# Genius Bridge
genius:
  auto_start: false
  port: 25337

# UI settings
ui:
  dark_mode: false
  color_blind_mode: false
  sidebar_collapsed: false

# Custom paths
paths:
  scenarios: []      # Additional scenario directories
  negotiators: []    # Additional negotiator modules

# Negotiator sources
sources:
  disabled: []       # List of disabled source IDs
```

## Web Interface Settings

Access settings through the **Settings** button in the header.

### General Tab

- **Dark Mode**: Toggle dark color scheme
- **Color Blind Mode**: Use accessible colors and line styles
- **Save Negotiations**: Persist results to disk

### Negotiation Tab

- **Default Max Steps**: Default deadline for new negotiations
- **Default Step Delay**: Animation speed for real-time mode

### Negotiator Sources Tab

Enable/disable negotiator sources:

- **negmas**: Built-in NegMAS negotiators
- **genius**: Genius Bridge negotiators (requires Java)
- **llm**: LLM-based negotiators

### Genius Bridge Tab

- **Auto-start**: Start bridge automatically when needed
- **Status**: View and control bridge status

### Custom Paths Tab

Add additional paths for:
- Scenario files
- Custom negotiator modules

## Environment Variables

Some settings can be set via environment variables:

```bash
# Server port
export NEGMAS_APP_PORT=8080

# Storage directory
export NEGMAS_APP_DATA_DIR=~/my-negmas-data
```

## Command Line Options

Override settings when starting the server:

```bash
# Custom port
negmas-app --port 8080

# Custom host (expose to network)
negmas-app --host 0.0.0.0

# Debug mode
negmas-app --debug

# Custom data directory
negmas-app --data-dir ~/my-data
```

## Storage Locations

NegMAS App stores data in:

| Data | Location |
|------|----------|
| Settings | `~/negmas/app/settings.yaml` |
| Saved negotiations | `~/negmas/app/negotiations/` |
| Session presets | `~/negmas/app/presets/` |
| Tournament results | `~/negmas/app/tournaments/` |
| Parameter cache | `~/negmas/app/cache/` |

## Resetting Configuration

To reset to defaults:

```bash
# Remove settings file
rm ~/negmas/app/settings.yaml

# Clear browser localStorage
# (In browser console)
localStorage.clear()
```
