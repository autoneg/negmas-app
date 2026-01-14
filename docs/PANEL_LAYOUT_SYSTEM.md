# Panel Layout System - Complete Design Document

## 1. Executive Summary

A VS Code-style dockable panel system for NegMAS App with:
- **5 zones**: Left, Center (optional), Right, Bottom-Left, Bottom-Right
- **Flexible top row**: 2-column or 3-column modes
- **Smart bottom row**: Auto-merges when one side is empty
- **Tabbed zones**: Multiple panels per zone with tab switching
- **Drag-and-drop**: Move panels between zones
- **Named layouts**: Save/load/switch between layout presets
- **Plugin API**: Simple registration for custom panels

---

## 2. Layout Structure

### 2.1 Default Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOP ROW (2 columns)                          │
│  ┌────────────────────────┐  ┌────────────────────────────────┐ │
│  │         LEFT           │  │            RIGHT               │ │
│  │  ┌────────┬──────────┐ │  │  ┌──────────────────────────┐  │ │
│  │  │History │Histogram │ │  │  │      2D Utility View     │  │ │
│  │  ├────────┴──────────┤ │  │  ├──────────────────────────┤  │ │
│  │  │                   │ │  │  │    Utility Timeline      │  │ │
│  │  │  (active panel)   │ │  │  │                          │  │ │
│  │  │                   │ │  │  └──────────────────────────┘  │ │
│  │  └───────────────────┘ │  └────────────────────────────────┘ │
│  └────────────────────────┘                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    BOTTOM ROW                             │   │
│  │  ┌─────────────────────┐  ┌───────────────────────────┐   │   │
│  │  │    BOTTOM-LEFT      │  │      BOTTOM-RIGHT         │   │   │
│  │  │       Info          │  │        Result             │   │   │
│  │  └─────────────────────┘  └───────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Zone Configuration

| Zone | ID | Default Panels | Display Mode |
|------|----|----------------|--------------|
| Left | `left` | Offer History, Offer Histogram | **Tabbed** |
| Center | `center` | (empty by default) | Tabbed |
| Right | `right` | 2D Utility View, Utility Timeline | **Vertically stacked** |
| Bottom-Left | `bottom-left` | Info | Single panel |
| Bottom-Right | `bottom-right` | Result | Single panel |

### 2.3 Top Row Modes

**Mode A: Two Columns (Default)**
```
┌─────────────────────┐ ┌─────────────────────┐
│        LEFT         │ │        RIGHT        │
└─────────────────────┘ └─────────────────────┘
```

**Mode B: Three Columns**
```
┌──────────┐ ┌────────────────────┐ ┌──────────┐
│   LEFT   │ │       CENTER       │ │  RIGHT   │
└──────────┘ └────────────────────┘ └──────────┘
```

- Toggle via Layout Switcher or by switching to a 3-column layout preset
- Center zone can be collapsed by dragging its resize handle to 0

### 2.4 Bottom Row Behavior

| Scenario | Behavior |
|----------|----------|
| Both zones have panels | Split view with draggable divider |
| Only bottom-left has panels | Bottom-left expands to 100% |
| Only bottom-right has panels | Bottom-right expands to 100% |
| Neither has panels | Bottom row collapses entirely |

---

## 3. Panel Definitions

### 3.1 Core Panels

| Panel ID | Name | Icon | Default Zone | Stack Mode |
|----------|------|------|--------------|------------|
| `offer-history` | Offer History | list | left | tabbed |
| `offer-histogram` | Offer Histogram | bar-chart | left | tabbed |
| `utility-2d` | 2D Utility View | scatter | right | stacked |
| `utility-timeline` | Utility Timeline | line-chart | right | stacked |
| `info` | Info | info | bottom-left | single |
| `result` | Result | check | bottom-right | single |

### 3.2 New Panel: Offer Histogram

**Purpose**: Visualize the distribution of offers across issues/values.

**Features**:
- Bar chart showing frequency of each value per issue
- Color-coded by negotiator
- Updates in real-time as offers come in
- Filterable by negotiator

**Implementation Notes**:
- Uses Plotly.js for rendering
- Shows one histogram per issue (stacked or tabbed within panel)
- X-axis: Issue values, Y-axis: Frequency count

### 3.3 Zone Display Modes

Each zone supports two display modes for multiple panels:

**Tabbed Mode** (default for left, center, bottom zones):
- Only one panel visible at a time
- Tab bar at top shows all panels
- Click tab to switch

**Stacked Mode** (default for right zone):
- All panels visible, stacked vertically
- Each panel has its own header
- Resize handles between panels

Users can toggle mode per-zone via zone menu.

---

## 4. Layout Presets

### 4.1 Built-in Layouts

**"Default"** (2-column + bottom)
```javascript
{
  id: 'default',
  name: 'Default',
  topRowMode: 'two-column',
  zones: {
    left: { 
      panels: ['offer-history', 'offer-histogram'], 
      activePanel: 'offer-history',
      displayMode: 'tabbed'
    },
    center: { panels: [] },
    right: { 
      panels: ['utility-2d', 'utility-timeline'], 
      activePanel: 'utility-2d',
      displayMode: 'stacked'
    },
    bottomLeft: { panels: ['info'], activePanel: 'info' },
    bottomRight: { panels: ['result'], activePanel: 'result' }
  },
  zoneSizes: {
    leftWidth: '35%',
    rightWidth: '65%',
    bottomHeight: '120px',
    bottomSplit: '50%'
  }
}
```

**"Focus"** (3-column, center focus)
```javascript
{
  id: 'focus',
  name: 'Focus',
  topRowMode: 'three-column',
  zones: {
    left: { panels: ['info', 'result'], displayMode: 'tabbed' },
    center: { panels: ['utility-2d'], displayMode: 'stacked' },
    right: { panels: ['offer-history', 'utility-timeline'], displayMode: 'stacked' },
    bottomLeft: { panels: ['offer-histogram'] },
    bottomRight: { panels: [] }
  },
  zoneSizes: {
    leftWidth: '200px',
    centerWidth: '1fr',
    rightWidth: '300px',
    bottomHeight: '180px',
    bottomSplit: '100%'
  }
}
```

**"Compact"** (2-column, no bottom)
```javascript
{
  id: 'compact',
  name: 'Compact',
  topRowMode: 'two-column',
  zones: {
    left: { panels: ['info', 'offer-history', 'result'], displayMode: 'tabbed' },
    right: { panels: ['utility-2d', 'utility-timeline', 'offer-histogram'], displayMode: 'tabbed' },
    bottomLeft: { panels: [] },
    bottomRight: { panels: [] }
  },
  zoneSizes: {
    leftWidth: '40%',
    rightWidth: '60%',
    bottomHeight: '0',
    bottomSplit: '50%'
  }
}
```

**"Analysis"** (all panels visible)
```javascript
{
  id: 'analysis',
  name: 'Analysis',
  topRowMode: 'three-column',
  zones: {
    left: { panels: ['offer-history'], displayMode: 'stacked' },
    center: { panels: ['utility-2d', 'utility-timeline'], displayMode: 'stacked' },
    right: { panels: ['offer-histogram'], displayMode: 'stacked' },
    bottomLeft: { panels: ['info'] },
    bottomRight: { panels: ['result'] }
  },
  zoneSizes: {
    leftWidth: '280px',
    centerWidth: '1fr',
    rightWidth: '280px',
    bottomHeight: '100px',
    bottomSplit: '50%'
  }
}
```

---

## 5. User Interactions

### 5.1 Layout Switching

**Layout Switcher UI** (in header):
```
┌─────────────────────────────┐
│ Layout: [Default    ▼]     │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ ● Default                   │
│   Focus                     │
│   Compact                   │
│   Analysis                  │
│ ─────────────────────────── │
│   My Custom Layout          │
│ ─────────────────────────── │
│ + Save Current Layout       │
│ ⚙ Manage Layouts...         │
└─────────────────────────────┘
```

### 5.2 Tab Operations

| Action | Behavior |
|--------|----------|
| Click tab | Activate that panel |
| Drag tab | Move panel to another zone |
| Right-click tab | Context menu (Close, Move to...) |
| Middle-click tab | Close panel |
| Double-click tab header | Toggle panel zoom |

### 5.3 Zone Operations

| Action | Behavior |
|--------|----------|
| Click "+" in zone | Open panel picker to add panel |
| Drag resize handle | Resize zone |
| Double-click resize handle | Reset to default size |
| Right-click zone header | Zone menu (display mode, collapse) |

### 5.4 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1-5` | Switch to layout 1-5 |
| `Ctrl+Tab` | Next tab in active zone |
| `Ctrl+Shift+Tab` | Previous tab in active zone |
| `Ctrl+W` | Close active panel |
| `Ctrl+Shift+S` | Save current layout |

---

## 6. Implementation Plan

### Phase 1: Infrastructure (2-3 days)
1. Create `panel-registry.js` - Panel definitions and registration
2. Create `layout-manager.js` - Layout state, persistence, switching
3. Define all core panel definitions
4. Create Offer Histogram panel component

### Phase 2: Layout Rendering (2-3 days)
1. Create `layout-renderer.js` - DOM rendering engine
2. Create `layout.css` - All layout styles
3. Implement zone containers with tab/stack modes
4. Implement resize handles between all zones
5. Implement bottom row auto-merge behavior

### Phase 3: Panel Migration (2 days)
1. Extract existing panel code into components
2. Register panels in new registry
3. Migrate Info, Result, Offer History panels
4. Migrate 2D Utility View, Utility Timeline panels
5. Create new Offer Histogram panel

### Phase 4: Drag & Drop (1-2 days)
1. Create `drag-drop-manager.js`
2. Implement tab dragging between zones
3. Implement tab reordering within zones
4. Add visual feedback during drag

### Phase 5: Layout Switcher UI (1-2 days)
1. Create Layout Switcher dropdown component
2. Implement save/load custom layouts
3. Implement layout management modal
4. Add keyboard shortcuts

### Phase 6: Polish & Testing (1-2 days)
1. Test all resize interactions
2. Ensure Plotly charts resize correctly
3. Test server-side persistence
4. Dark mode / color-blind mode compatibility
5. Add feature flag for gradual rollout

### Phase 7: Plugin API (1 day)
1. Create `plugin-api.js` with `NegmasPlugins` global
2. Document plugin API
3. Create example plugin

---

## 7. File Structure

```
negmas_app/
├── static/
│   ├── css/
│   │   ├── styles.css           # Existing (keep)
│   │   └── layout.css           # NEW: Layout system styles
│   └── js/
│       ├── panel-registry.js    # NEW: Panel definitions
│       ├── layout-manager.js    # NEW: Layout state management
│       ├── layout-renderer.js   # NEW: DOM rendering
│       ├── drag-drop-manager.js # NEW: Drag and drop
│       ├── plugin-api.js        # NEW: Plugin system
│       └── panels/              # NEW: Panel components
│           ├── offer-history.js
│           ├── offer-histogram.js
│           ├── utility-2d.js
│           ├── utility-timeline.js
│           ├── info.js
│           └── result.js
├── templates/
│   ├── base.html                # Updated: Include new JS files
│   ├── index.html               # Updated: Use layout container
│   └── components/
│       ├── layout-container.html  # NEW
│       ├── layout-switcher.html   # NEW
│       └── panel-picker.html      # NEW
└── docs/
    └── PANEL_LAYOUT_SYSTEM.md   # This document
```

---

## 8. Technical Details

### 8.1 State Structure

```javascript
// Stored at ~/negmas/app/settings/layout.json
{
  version: 1,
  activeLayoutId: 'default',
  layouts: {
    'default': { /* LayoutDefinition */ },
    'focus': { /* LayoutDefinition */ },
    // ... more layouts
  },
  customLayouts: ['my-layout-1'],
  panelCollapsed: { info: false, history: false, ... },
  leftColumnWidth: '400px'
}
```

### 8.2 Panel Registry Interface

```javascript
// panel-registry.js
const PanelRegistry = {
  panels: new Map(),
  
  register(definition) {
    this.panels.set(definition.id, {
      ...definition,
      // Ensure defaults
      contexts: definition.contexts || ['negotiation'],
      minWidth: definition.minWidth || 200,
      minHeight: definition.minHeight || 100
    });
  },
  
  get(id) { return this.panels.get(id); },
  getAll() { return [...this.panels.values()]; },
  getForContext(context) {
    return this.getAll().filter(p => p.contexts.includes(context));
  }
};
```

### 8.3 Layout Manager Interface

```javascript
// layout-manager.js
const LayoutManager = {
  state: null,
  
  init() {
    this.state = this.loadFromStorage() || this.getDefaultState();
    this.applyLayout(this.state.activeLayoutId);
  },
  
  switchLayout(layoutId) {
    this.state.activeLayoutId = layoutId;
    this.applyLayout(layoutId);
    this.saveToStorage();
    this.emit('layout-changed', layoutId);
  },
  
  saveCurrentAs(name) {
    const id = this.generateId(name);
    const layout = this.captureCurrentLayout();
    layout.id = id;
    layout.name = name;
    this.state.layouts[id] = layout;
    this.state.customLayouts.push(id);
    this.saveToStorage();
    return id;
  },
  
  movePanel(panelId, fromZone, toZone, position) { /* ... */ },
  setZoneDisplayMode(zoneId, mode) { /* ... */ },
  resizeZone(zoneId, size) { /* ... */ }
};
```

---

## 9. Summary

This design provides:
- **Flexible 5-zone layout** with configurable top row (2 or 3 columns)
- **Smart bottom row** that auto-merges when one side is empty
- **Tabbed + Stacked modes** per zone (stacked default for right zone)
- **New Offer Histogram panel** showing value distributions
- **Layout presets** with easy switching via dropdown
- **Drag-and-drop** panel management
- **Plugin API** for custom panels

**Default arrangement**:
- Left (tabbed): Offer History, Offer Histogram
- Right (stacked): 2D Utility View, Utility Timeline
- Bottom-Left: Info
- Bottom-Right: Result

---

## 10. Estimated Timeline

| Phase | Days | Description |
|-------|------|-------------|
| Phase 1 | 2-3 | Infrastructure + Offer Histogram panel |
| Phase 2 | 2-3 | Layout rendering |
| Phase 3 | 2 | Panel migration |
| Phase 4 | 1-2 | Drag & drop |
| Phase 5 | 1-2 | Layout Switcher UI |
| Phase 6 | 1-2 | Polish & testing |
| Phase 7 | 1 | Plugin API |
| **Total** | **10-15** | **Full implementation** |
