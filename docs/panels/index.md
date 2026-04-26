# Panel System Overview

NegMAS App features a flexible, VS Code-style panel layout system that allows you to customize your workspace for different tasks. This section covers everything you need to know about the panel system.

## What is the Panel System?

The panel system is a modular UI framework that displays negotiation data in customizable panels. Each panel is responsible for rendering a specific type of visualization or information, such as:

- Utility space plots
- Offer history tables
- Negotiation progress information
- Result summaries

## Key Features

### Flexible Layout

- **Multiple Zones**: Panels can be placed in 5 different zones (left, center, right, bottom-left, bottom-right)
- **Drag & Drop**: Rearrange panels by dragging them between zones
- **Tabbed/Stacked Modes**: Each zone can display panels as tabs or stacked vertically
- **Resizable**: Adjust zone sizes by dragging the borders

### Layout Presets

Choose from built-in layouts optimized for different workflows:

| Layout | Description | Best For |
|--------|-------------|----------|
| **Default** | 2-column with split bottom | General use |
| **Focus** | 3-column with center focus | Detailed analysis |
| **Compact** | 2-column, no bottom panels | Quick overview |
| **Analysis** | All panels visible | Deep analysis |

### Persistence

Your layout preferences are automatically saved to the server at `~/negmas/app/settings/layout.json` and restored when you return.

## Architecture Overview

```
+------------------+     +------------------+     +------------------+
|  Panel Registry  |---->|  Layout Manager  |---->| Layout Renderer  |
|                  |     |                  |     |                  |
| - Panel defs     |     | - State mgmt     |     | - DOM rendering  |
| - Lifecycle      |     | - Presets        |     | - Resize handles |
| - Icons          |     | - Persistence    |     | - Panel picker   |
+------------------+     +------------------+     +------------------+
```

### Components

1. **Panel Registry** (`panel-registry.js`): Defines available panels and their lifecycle methods
2. **Layout Manager** (`layout-manager.js`): Manages layout state, presets, and persistence  
3. **Layout Renderer** (`layout-renderer.js`): Renders the layout to the DOM and handles interactions

## Zone Structure

The layout is organized into 5 zones:

```
+-------------------------------------------------------+
|                     TOP ROW                            |
|  +-------------+  +-------------+  +-------------+    |
|  |    LEFT     |  |   CENTER    |  |    RIGHT    |    |
|  |             |  | (optional)  |  |             |    |
|  +-------------+  +-------------+  +-------------+    |
+-------------------------------------------------------+
|                    BOTTOM ROW                          |
|  +-------------------------+  +---------------------+ |
|  |      BOTTOM-LEFT        |  |    BOTTOM-RIGHT     | |
|  +-------------------------+  +---------------------+ |
+-------------------------------------------------------+
```

- **Two-column mode**: Left and Right zones only in top row
- **Three-column mode**: All three zones in top row
- **Smart bottom row**: Automatically merges when one side is empty

## Next Steps

- [Layout System Details](layout-system.md) - Deep dive into layout configuration
- [Built-in Panels](builtin-panels.md) - Reference for all included panels
- [Creating Custom Panels](creating-panels.md) - Build your own visualization panels
- [Panel API Reference](api-reference.md) - Complete API documentation
