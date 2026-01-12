# Panel API Reference

Complete API reference for the NegMAS App panel system.

## PanelRegistry

The global panel registry manages panel definitions.

### Methods

#### `register(id, definition)`

Register a new panel.

```javascript
PanelRegistry.register(id: string, definition: PanelDefinition): void
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `string` | Unique panel identifier |
| `definition` | `PanelDefinition` | Panel definition object |

**Example:**

```javascript
PanelRegistry.register('my-panel', {
    name: 'My Panel',
    render(state) { return '<div>Hello</div>'; }
});
```

#### `get(id)`

Get a panel definition by ID.

```javascript
PanelRegistry.get(id: string): PanelDefinition | undefined
```

#### `getAll()`

Get all registered panels.

```javascript
PanelRegistry.getAll(): Record<string, PanelDefinition>
```

#### `has(id)`

Check if a panel is registered.

```javascript
PanelRegistry.has(id: string): boolean
```

#### `unregister(id)`

Remove a panel from the registry.

```javascript
PanelRegistry.unregister(id: string): boolean
```

---

## PanelDefinition

Interface for panel definitions.

```typescript
interface PanelDefinition {
    // Required
    name: string;
    render(state: AppState): string;
    
    // Optional
    description?: string;
    icon?: string;
    category?: string;
    defaultZone?: ZoneId;
    minWidth?: number;
    minHeight?: number;
    
    // Lifecycle methods
    init?(element: HTMLElement, state: AppState): void;
    update?(element: HTMLElement, state: AppState): void;
    destroy?(element: HTMLElement): void;
}
```

### Properties

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `name` | `string` | Yes | - | Display name |
| `description` | `string` | No | `''` | Tooltip text |
| `icon` | `string` | No | `'default'` | Icon identifier |
| `category` | `string` | No | `'custom'` | Grouping category |
| `defaultZone` | `ZoneId` | No | `'right'` | Initial zone placement |
| `minWidth` | `number` | No | `200` | Min width (px) |
| `minHeight` | `number` | No | `100` | Min height (px) |

### Lifecycle Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `render` | `(state) => string` | Generate HTML content |
| `init` | `(element, state) => void` | Post-mount initialization |
| `update` | `(element, state) => void` | State change handler |
| `destroy` | `(element) => void` | Cleanup before removal |

---

## LayoutManager

Manages layout state, persistence, and switching.

### Initialization

#### `init()`

Initialize the layout manager. Called automatically.

```javascript
LayoutManager.init(): LayoutManager
```

### Layout Operations

#### `getActiveLayout()`

Get the current active layout.

```javascript
LayoutManager.getActiveLayout(): Layout
```

#### `getAvailableLayouts()`

Get all available layouts (built-in + custom).

```javascript
LayoutManager.getAvailableLayouts(): Layout[]
```

#### `switchLayout(layoutId)`

Switch to a different layout.

```javascript
LayoutManager.switchLayout(layoutId: string): void
```

#### `resetCurrentLayout()`

Reset the current layout to its default state.

```javascript
LayoutManager.resetCurrentLayout(): void
```

### Zone Operations

#### `getZone(zoneId)`

Get a zone's configuration.

```javascript
LayoutManager.getZone(zoneId: ZoneId): ZoneConfig
```

#### `setZoneDisplayMode(zoneId, mode)`

Set how panels are displayed in a zone.

```javascript
LayoutManager.setZoneDisplayMode(
    zoneId: ZoneId, 
    mode: 'tabbed' | 'stacked'
): void
```

#### `setActivePanel(zoneId, panelId)`

Set the active panel in a tabbed zone.

```javascript
LayoutManager.setActivePanel(zoneId: ZoneId, panelId: string): void
```

### Panel Operations

#### `movePanel(panelId, fromZone, toZone)`

Move a panel between zones.

```javascript
LayoutManager.movePanel(
    panelId: string, 
    fromZone: ZoneId, 
    toZone: ZoneId
): void
```

#### `addPanelToZone(panelId, zoneId)`

Add a panel to a zone.

```javascript
LayoutManager.addPanelToZone(panelId: string, zoneId: ZoneId): void
```

#### `removePanelFromZone(panelId)`

Remove a panel from its current zone.

```javascript
LayoutManager.removePanelFromZone(panelId: string): void
```

### Custom Layouts

#### `saveCustomLayout(id, name)`

Save the current layout as a custom preset.

```javascript
LayoutManager.saveCustomLayout(id: string, name: string): void
```

#### `deleteCustomLayout(id)`

Delete a custom layout.

```javascript
LayoutManager.deleteCustomLayout(id: string): void
```

### Events

#### `on(event, callback)`

Subscribe to layout events.

```javascript
LayoutManager.on(event: string, callback: Function): void
```

**Events:**

| Event | Payload | Description |
|-------|---------|-------------|
| `layout-changed` | `layoutId` | Layout switched |
| `zone-updated` | `zoneId, zone` | Zone configuration changed |
| `panel-moved` | `panelId, from, to` | Panel moved between zones |
| `panel-added` | `panelId, zoneId` | Panel added to zone |
| `panel-removed` | `panelId, zoneId` | Panel removed from zone |

#### `off(event, callback)`

Unsubscribe from events.

```javascript
LayoutManager.off(event: string, callback: Function): void
```

#### `emit(event, ...args)`

Emit an event (internal use).

```javascript
LayoutManager.emit(event: string, ...args: any[]): void
```

---

## LayoutRenderer

Renders layouts to the DOM and handles user interactions.

### Initialization

#### `init(container, state)`

Initialize the renderer with a container element.

```javascript
LayoutRenderer.init(container: HTMLElement, state: AppState): void
```

### State Management

#### `setState(state)`

Update the application state and re-render panels.

```javascript
LayoutRenderer.setState(state: AppState): void
```

#### `getState()`

Get the current state.

```javascript
LayoutRenderer.getState(): AppState
```

### Rendering

#### `render()`

Force a full re-render of the layout.

```javascript
LayoutRenderer.render(): void
```

#### `updatePanel(panelId)`

Update a specific panel.

```javascript
LayoutRenderer.updatePanel(panelId: string): void
```

### Cleanup

#### `destroy()`

Clean up the renderer and all panels.

```javascript
LayoutRenderer.destroy(): void
```

---

## Type Definitions

### ZoneId

```typescript
type ZoneId = 'left' | 'center' | 'right' | 'bottomLeft' | 'bottomRight';
```

### Layout

```typescript
interface Layout {
    id: string;
    name: string;
    builtIn: boolean;
    topRowMode: 'two-column' | 'three-column';
    zones: Record<ZoneId, ZoneConfig>;
    zoneSizes: ZoneSizes;
}
```

### ZoneConfig

```typescript
interface ZoneConfig {
    panels: string[];
    activePanel: string | null;
    displayMode: 'tabbed' | 'stacked';
}
```

### ZoneSizes

```typescript
interface ZoneSizes {
    leftWidth: string;
    centerWidth: string;
    rightWidth: string;
    bottomHeight: string;
    bottomSplit: string;
}
```

### AppState

```typescript
interface AppState {
    currentNegotiation: NegotiationState | null;
    // ... other app state
}
```

### NegotiationState

```typescript
interface NegotiationState {
    id: string;
    status: 'running' | 'completed' | 'failed';
    scenario: string;
    step: number;
    max_steps: number | null;
    time_elapsed: number;
    time_limit: number | null;
    negotiators: Negotiator[];
    issues: Issue[];
    offers: Offer[];
    agreement: Agreement | null;
    pareto_frontier: [number, number][] | null;
}
```

---

## PanelIcons

Global object containing SVG icons for panels.

### Built-in Icons

| Key | Description |
|-----|-------------|
| `default` | Generic panel icon |
| `info` | Information circle |
| `list` | List view |
| `chart` | Line chart |
| `bar-chart` | Bar chart |
| `scatter` | Scatter plot |
| `timeline` | Timeline |
| `grid` | Grid layout |
| `settings` | Settings gear |
| `result` | Checkmark/result |

### Adding Custom Icons

```javascript
PanelIcons['my-icon'] = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <!-- SVG content -->
    </svg>
`;
```

### Using Icons

```javascript
// In panel definition
{
    icon: 'my-icon'
}

// Programmatically
const iconHtml = PanelIcons['my-icon'];
```
