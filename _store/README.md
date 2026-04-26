# Archived Code - DO NOT USE IN PRODUCTION

This directory contains archived code that has been superseded by newer implementations.

## Contents

### alpine_version/

**Status**: ⚠️ DEPRECATED - Replaced by Vue.js version

The original Alpine.js implementation of NegMAS App. This version has been completely replaced by the modern Vue.js implementation located in `src/frontend/`.

**Archived on**: January 22, 2026

**Why archived**:
- Replaced by Vue.js version with better architecture
- Vue.js version has all features from Alpine.js plus enhancements
- Kept temporarily for reference during transition period
- Will be deleted once Vue.js version is confirmed stable in production

**Contents**:
- `frontend/` - Alpine.js HTML/CSS/JS files
- `static/` - Static assets (CSS, images)
- `templates/` - Jinja2 templates for Alpine.js version
- `legacy_main.py` - CLI entry point for Alpine.js version

**To run the legacy version** (for comparison only):
```bash
negmas-legacy run
```

## Migration Status

✅ **All features migrated to Vue.js**:
- Negotiation views with 8 panels
- Tournament views with grid/leaderboard/negotiations
- Tournament → Negotiation navigation
- Real-time SSE streaming
- Save/load functionality
- Configuration system
- Scenario browser
- All modals and wizards

## Deletion Timeline

This archived code will be kept for approximately **1-2 months** after Vue.js version goes into production, then permanently deleted.

**Do not develop new features in the Alpine.js version.**

---

*Last updated: January 22, 2026*
