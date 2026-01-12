# Layout System

The Layout System provides a flexible, persistent way to organize panels in your workspace. This document covers the technical details of how layouts work and how to configure them.

## Layout Structure

A layout defines how panels are arranged across zones. Each layout consists of:

```javascript
{
    id: 'my-layout',           // Unique identifier
    name: 'My Layout',         // Display name
    builtIn: false,            // Whether this is a built-in preset
    topRowMode: 'two-column',  // 'two-column' or 'three-column'
    zones: {
        left: { ... },
        center: { ... },
        right: { ... },
        bottomLeft: { ... },
        bottomRight: { ... }
    },
    zoneSizes: {
        leftWidth: '35%',
        centerWidth: '0',
        rightWidth: '65%',
        bottomHeight: '120px',
        bottomSplit: '50%'
    }
}
```

## Zone Configuration

Each zone has the following properties:

| Property | Type | Description |
|----------|------|-------------|
| `panels` | `string[]` | Array of panel IDs in this zone |
| `activePanel` | `string \| null` | Currently active panel (for tabbed mode) |
| `displayMode` | `'tabbed' \| 'stacked'` | How panels are displayed |

### Display Modes

#### Tabbed Mode

Panels are shown as tabs - only one is visible at a time:

```
+------------------+
| [Tab1] [Tab2]    |
+------------------+
|                  |
|  Panel Content   |
|                  |
+------------------+
```

Best for: Zones where you want to maximize content area and switch between panels.

#### Stacked Mode

All panels are visible, stacked vertically:

```
+------------------+
| Panel 1          |
+------------------+
| Panel 2          |
+------------------+
| Panel 3          |
+------------------+
```

Best for: Zones where you want to see multiple panels simultaneously.

## Top Row Modes

### Two-Column Mode

The center zone is hidden, giving more space to left and right:

```
+----------------------+----------------------+
|        LEFT          |        RIGHT         |
|                      |                      |
+----------------------+----------------------+
```

### Three-Column Mode

All three zones are visible:

```
+----------+------------------+----------+
|   LEFT   |      CENTER      |  RIGHT   |
|          |                  |          |
+----------+------------------+----------+
```

## Zone Sizes

Control the dimensions of each zone:

| Property | Description | Example Values |
|----------|-------------|----------------|
| `leftWidth` | Width of left zone | `'35%'`, `'300px'`, `'1fr'` |
| `centerWidth` | Width of center zone | `'0'`, `'400px'`, `'1fr'` |
| `rightWidth` | Width of right zone | `'65%'`, `'auto'`, `'1fr'` |
| `bottomHeight` | Height of bottom row | `'120px'`, `'0'`, `'200px'` |
| `bottomSplit` | Split between bottom zones | `'50%'`, `'100%'`, `'0%'` |

!!! tip "Using CSS Grid Units"
    Zone sizes support any valid CSS value. Use `fr` units for flexible layouts:
    
    - `'1fr'` - Takes equal share of available space
    - `'2fr'` - Takes twice the share
    - Mix with fixed sizes: `leftWidth: '300px', rightWidth: '1fr'`

## Built-in Layout Presets

### Default

Balanced 2-column layout suitable for most use cases:

```javascript
{
    topRowMode: 'two-column',
    zones: {
        left: { panels: ['offer-history', 'offer-histogram'], displayMode: 'tabbed' },
        right: { panels: ['utility-2d', 'utility-timeline'], displayMode: 'stacked' },
        bottomLeft: { panels: ['info'], displayMode: 'tabbed' },
        bottomRight: { panels: ['result'], displayMode: 'tabbed' }
    }
}
```

### Focus

3-column layout with large center panel for detailed analysis:

```javascript
{
    topRowMode: 'three-column',
    zones: {
        left: { panels: ['info', 'result'], displayMode: 'tabbed' },
        center: { panels: ['utility-2d'], displayMode: 'stacked' },
        right: { panels: ['offer-history', 'utility-timeline'], displayMode: 'stacked' }
    }
}
```

### Compact

Minimal layout with no bottom row:

```javascript
{
    topRowMode: 'two-column',
    zones: {
        left: { panels: ['info', 'offer-history', 'result'], displayMode: 'tabbed' },
        right: { panels: ['utility-2d', 'utility-timeline', 'offer-histogram'], displayMode: 'tabbed' }
    },
    zoneSizes: { bottomHeight: '0' }
}
```

### Analysis

All panels visible for deep analysis:

```javascript
{
    topRowMode: 'three-column',
    zones: {
        left: { panels: ['offer-history'], displayMode: 'stacked' },
        center: { panels: ['utility-2d', 'utility-timeline'], displayMode: 'stacked' },
        right: { panels: ['offer-histogram'], displayMode: 'stacked' },
        bottomLeft: { panels: ['info'], displayMode: 'tabbed' },
        bottomRight: { panels: ['result'], displayMode: 'tabbed' }
    }
}
```

## Layout Manager API

### Initialization

```javascript
// Initialize the layout manager (called automatically)
LayoutManager.init();
```

### Getting Layout Information

```javascript
// Get the current active layout
const layout = LayoutManager.getActiveLayout();

// Get all available layouts
const layouts = LayoutManager.getAvailableLayouts();

// Get a specific zone's configuration
const zone = LayoutManager.getZone('left');
```

### Switching Layouts

```javascript
// Switch to a different layout
LayoutManager.switchLayout('compact');

// Reset current layout to defaults
LayoutManager.resetCurrentLayout();
```

### Modifying Layouts

```javascript
// Move a panel to a different zone
LayoutManager.movePanel('utility-2d', 'left', 'right');

// Add a panel to a zone
LayoutManager.addPanelToZone('offer-histogram', 'left');

// Remove a panel from its zone
LayoutManager.removePanelFromZone('offer-histogram');

// Set zone display mode
LayoutManager.setZoneDisplayMode('right', 'stacked');

// Set active panel in a zone
LayoutManager.setActivePanel('left', 'offer-history');
```

### Custom Layouts

```javascript
// Save current layout as a custom preset
LayoutManager.saveCustomLayout('my-layout', 'My Custom Layout');

// Delete a custom layout
LayoutManager.deleteCustomLayout('my-layout');
```

### Event Handling

```javascript
// Listen for layout changes
LayoutManager.on('layout-changed', (layoutId) => {
    console.log('Layout changed to:', layoutId);
});

LayoutManager.on('zone-updated', (zoneId, zone) => {
    console.log('Zone updated:', zoneId, zone);
});

LayoutManager.on('panel-moved', (panelId, fromZone, toZone) => {
    console.log('Panel moved:', panelId, fromZone, '->', toZone);
});
```

## Persistence

Layout state is automatically persisted to `localStorage` under the key `negmas-layout-state`. The stored data includes:

- Active layout ID
- Custom layout definitions
- Any runtime modifications to zones

To clear persisted state:

```javascript
localStorage.removeItem('negmas-layout-state');
LayoutManager.init(); // Reinitialize with defaults
```

## CSS Variables

The layout system uses CSS variables for styling:

```css
:root {
    --zone-min-width: 200px;
    --zone-gap: 4px;
    --resize-handle-size: 6px;
    --tab-height: 32px;
    --panel-header-height: 28px;
}
```

Override these in your styles to customize the layout appearance.
