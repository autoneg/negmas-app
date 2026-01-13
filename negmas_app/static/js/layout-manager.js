/**
 * Layout Manager - Manages layout state, persistence, and switching
 * 
 * This module provides:
 * - Layout definitions and presets
 * - Layout state management
 * - Persistence to localStorage
 * - Layout switching
 * - Zone configuration (2-col / 3-col modes)
 */

/**
 * Built-in layout presets
 */
const BuiltInLayouts = {
    // Default: 2-column + bottom split
    default: {
        id: 'default',
        name: 'Default',
        builtIn: true,
        topRowMode: 'two-column',
        zones: {
            left: {
                panels: ['offer-history', 'offer-histogram'],
                activePanel: 'offer-history',
                displayMode: 'tabbed'
            },
            center: {
                panels: [],
                activePanel: null,
                displayMode: 'tabbed'
            },
            right: {
                panels: ['utility-2d', 'utility-timeline'],
                activePanel: 'utility-2d',
                displayMode: 'stacked'
            },
            bottomLeft: {
                panels: ['info'],
                activePanel: 'info',
                displayMode: 'tabbed'
            },
            bottomRight: {
                panels: ['result'],
                activePanel: 'result',
                displayMode: 'tabbed'
            }
        },
        zoneSizes: {
            leftWidth: '35%',
            centerWidth: '0',
            rightWidth: '65%',
            bottomHeight: '120px',
            bottomSplit: '50%'
        }
    },
    
    // Focus: 3-column with center focus
    focus: {
        id: 'focus',
        name: 'Focus',
        builtIn: true,
        topRowMode: 'three-column',
        zones: {
            left: {
                panels: ['info', 'result'],
                activePanel: 'info',
                displayMode: 'tabbed'
            },
            center: {
                panels: ['utility-2d'],
                activePanel: 'utility-2d',
                displayMode: 'stacked'
            },
            right: {
                panels: ['offer-history', 'utility-timeline'],
                activePanel: 'offer-history',
                displayMode: 'stacked'
            },
            bottomLeft: {
                panels: ['offer-histogram'],
                activePanel: 'offer-histogram',
                displayMode: 'tabbed'
            },
            bottomRight: {
                panels: [],
                activePanel: null,
                displayMode: 'tabbed'
            }
        },
        zoneSizes: {
            leftWidth: '200px',
            centerWidth: '1fr',
            rightWidth: '300px',
            bottomHeight: '180px',
            bottomSplit: '100%'
        }
    },
    
    // Compact: 2-column, no bottom
    compact: {
        id: 'compact',
        name: 'Compact',
        builtIn: true,
        topRowMode: 'two-column',
        zones: {
            left: {
                panels: ['info', 'offer-history', 'result'],
                activePanel: 'offer-history',
                displayMode: 'tabbed'
            },
            center: {
                panels: [],
                activePanel: null,
                displayMode: 'tabbed'
            },
            right: {
                panels: ['utility-2d', 'utility-timeline', 'offer-histogram'],
                activePanel: 'utility-2d',
                displayMode: 'tabbed'
            },
            bottomLeft: {
                panels: [],
                activePanel: null,
                displayMode: 'tabbed'
            },
            bottomRight: {
                panels: [],
                activePanel: null,
                displayMode: 'tabbed'
            }
        },
        zoneSizes: {
            leftWidth: '40%',
            centerWidth: '0',
            rightWidth: '60%',
            bottomHeight: '0',
            bottomSplit: '50%'
        }
    },
    
    // Analysis: All panels visible
    analysis: {
        id: 'analysis',
        name: 'Analysis',
        builtIn: true,
        topRowMode: 'three-column',
        zones: {
            left: {
                panels: ['offer-history'],
                activePanel: 'offer-history',
                displayMode: 'stacked'
            },
            center: {
                panels: ['utility-2d', 'utility-timeline'],
                activePanel: 'utility-2d',
                displayMode: 'stacked'
            },
            right: {
                panels: ['offer-histogram'],
                activePanel: 'offer-histogram',
                displayMode: 'stacked'
            },
            bottomLeft: {
                panels: ['info'],
                activePanel: 'info',
                displayMode: 'tabbed'
            },
            bottomRight: {
                panels: ['result'],
                activePanel: 'result',
                displayMode: 'tabbed'
            }
        },
        zoneSizes: {
            leftWidth: '280px',
            centerWidth: '1fr',
            rightWidth: '280px',
            bottomHeight: '100px',
            bottomSplit: '50%'
        }
    }
};

/**
 * Zone IDs
 */
const ZoneIds = ['left', 'center', 'right', 'bottomLeft', 'bottomRight'];

/**
 * Layout Manager - Central controller for layout state
 */
const LayoutManager = {
    _state: null,
    _listeners: new Map(),
    _storageKey: 'negmas-layout-state',
    _initialized: false,
    
    /**
     * Initialize the layout manager
     */
    init() {
        if (this._initialized) return;
        
        // Load state from storage or use defaults
        this._state = this._loadFromStorage() || this._getDefaultState();
        
        // Ensure all built-in layouts are present
        Object.entries(BuiltInLayouts).forEach(([id, layout]) => {
            this._state.layouts[id] = layout;
        });
        
        this._initialized = true;
        console.log('[LayoutManager] Initialized with layout:', this._state.activeLayoutId);
        
        return this;
    },
    
    /**
     * Get the default state
     */
    _getDefaultState() {
        return {
            version: 1,
            activeLayoutId: 'default',
            layouts: { ...BuiltInLayouts },
            customLayouts: [],
            zoneState: {}
        };
    },
    
    /**
     * Load state from localStorage
     */
    _loadFromStorage() {
        try {
            const stored = localStorage.getItem(this._storageKey);
            if (stored) {
                const state = JSON.parse(stored);
                // Migration: ensure version compatibility
                if (state.version === 1) {
                    return state;
                }
            }
        } catch (e) {
            console.warn('[LayoutManager] Failed to load state from storage:', e);
        }
        return null;
    },
    
    /**
     * Save state to localStorage
     */
    _saveToStorage() {
        try {
            localStorage.setItem(this._storageKey, JSON.stringify(this._state));
        } catch (e) {
            console.warn('[LayoutManager] Failed to save state to storage:', e);
        }
    },
    
    /**
     * Get the current state
     */
    getState() {
        return this._state;
    },
    
    /**
     * Get the active layout
     */
    getActiveLayout() {
        if (!this._state) {
            this.init();
        }
        return this._state.layouts[this._state.activeLayoutId] || this._state.layouts.default;
    },
    
    /**
     * Get a specific layout by ID
     */
    getLayout(layoutId) {
        return this._state.layouts[layoutId];
    },
    
    /**
     * Get all layouts
     */
    getAllLayouts() {
        if (!this._state) {
            this.init();
        }
        return Object.values(this._state.layouts);
    },
    
    /**
     * Get available layouts (alias for getAllLayouts)
     */
    getAvailableLayouts() {
        return this.getAllLayouts();
    },
    
    /**
     * Get built-in layouts
     */
    getBuiltInLayouts() {
        return this.getAllLayouts().filter(l => l.builtIn);
    },
    
    /**
     * Get custom layouts
     */
    getCustomLayouts() {
        return this.getAllLayouts().filter(l => !l.builtIn);
    },
    
    /**
     * Switch to a different layout
     */
    switchLayout(layoutId) {
        if (!this._state.layouts[layoutId]) {
            console.warn('[LayoutManager] Layout not found:', layoutId);
            return false;
        }
        
        this._state.activeLayoutId = layoutId;
        this._saveToStorage();
        this._emit('layout-changed', { layoutId, layout: this.getActiveLayout() });
        
        return true;
    },
    
    /**
     * Save current layout as a new custom layout
     */
    saveCurrentAs(name) {
        const id = 'custom-' + Date.now();
        const currentLayout = this.getActiveLayout();
        
        const newLayout = {
            ...JSON.parse(JSON.stringify(currentLayout)), // Deep clone
            id,
            name,
            builtIn: false
        };
        
        this._state.layouts[id] = newLayout;
        this._state.customLayouts.push(id);
        this._state.activeLayoutId = id;
        this._saveToStorage();
        
        this._emit('layout-saved', { layoutId: id, layout: newLayout });
        
        return id;
    },
    
    /**
     * Update current layout (for built-in layouts, creates a modified copy)
     */
    updateCurrentLayout(updates) {
        const current = this.getActiveLayout();
        
        if (current.builtIn) {
            // For built-in layouts, save modifications to a custom layout
            const id = 'custom-' + Date.now();
            const modified = {
                ...JSON.parse(JSON.stringify(current)),
                ...updates,
                id,
                name: current.name + ' (Modified)',
                builtIn: false
            };
            
            this._state.layouts[id] = modified;
            this._state.customLayouts.push(id);
            this._state.activeLayoutId = id;
        } else {
            // Update existing custom layout
            Object.assign(current, updates);
        }
        
        this._saveToStorage();
        this._emit('layout-updated', { layout: this.getActiveLayout() });
    },
    
    /**
     * Delete a custom layout
     */
    deleteLayout(layoutId) {
        const layout = this._state.layouts[layoutId];
        if (!layout || layout.builtIn) {
            console.warn('[LayoutManager] Cannot delete layout:', layoutId);
            return false;
        }
        
        delete this._state.layouts[layoutId];
        this._state.customLayouts = this._state.customLayouts.filter(id => id !== layoutId);
        
        // Switch to default if deleted layout was active
        if (this._state.activeLayoutId === layoutId) {
            this._state.activeLayoutId = 'default';
        }
        
        this._saveToStorage();
        this._emit('layout-deleted', { layoutId });
        
        return true;
    },
    
    /**
     * Rename a custom layout
     */
    renameLayout(layoutId, newName) {
        const layout = this._state.layouts[layoutId];
        if (!layout || layout.builtIn) {
            return false;
        }
        
        layout.name = newName;
        this._saveToStorage();
        this._emit('layout-renamed', { layoutId, name: newName });
        
        return true;
    },
    
    // ========== Zone Operations ==========
    
    /**
     * Get zone configuration
     */
    getZone(zoneId) {
        const layout = this.getActiveLayout();
        return layout.zones[zoneId];
    },
    
    /**
     * Set active panel in a zone
     */
    setActivePanel(zoneId, panelId) {
        const zone = this.getZone(zoneId);
        if (!zone || !zone.panels.includes(panelId)) return false;
        
        zone.activePanel = panelId;
        this._saveToStorage();
        this._emit('panel-activated', { zoneId, panelId });
        
        return true;
    },
    
    /**
     * Add a panel to a zone
     */
    addPanelToZone(panelId, zoneId, position = -1) {
        const zone = this.getZone(zoneId);
        if (!zone) return false;
        
        // Check if panel is already in any zone
        this._removePanelFromAllZones(panelId);
        
        // Add to target zone
        if (position < 0 || position >= zone.panels.length) {
            zone.panels.push(panelId);
        } else {
            zone.panels.splice(position, 0, panelId);
        }
        
        // Make it active if it's the only panel or zone was empty
        if (zone.panels.length === 1 || !zone.activePanel) {
            zone.activePanel = panelId;
        }
        
        this._saveToStorage();
        this._emit('panel-added', { zoneId, panelId, position });
        
        return true;
    },
    
    /**
     * Remove a panel from a zone
     */
    removePanelFromZone(panelId, zoneId) {
        const zone = this.getZone(zoneId);
        if (!zone) return false;
        
        const idx = zone.panels.indexOf(panelId);
        if (idx < 0) return false;
        
        zone.panels.splice(idx, 1);
        
        // Update active panel if needed
        if (zone.activePanel === panelId) {
            zone.activePanel = zone.panels[0] || null;
        }
        
        this._saveToStorage();
        this._emit('panel-removed', { zoneId, panelId });
        
        return true;
    },
    
    /**
     * Move a panel from one zone to another
     */
    movePanel(panelId, fromZone, toZone, position = -1) {
        this.removePanelFromZone(panelId, fromZone);
        this.addPanelToZone(panelId, toZone, position);
        
        this._emit('panel-moved', { panelId, fromZone, toZone, position });
        
        return true;
    },
    
    /**
     * Reorder panels within a zone
     */
    reorderPanels(zoneId, panelIds) {
        const zone = this.getZone(zoneId);
        if (!zone) return false;
        
        zone.panels = panelIds;
        this._saveToStorage();
        this._emit('panels-reordered', { zoneId, panelIds });
        
        return true;
    },
    
    /**
     * Set zone display mode (tabbed or stacked)
     */
    setZoneDisplayMode(zoneId, mode) {
        const zone = this.getZone(zoneId);
        if (!zone) return false;
        
        zone.displayMode = mode;
        this._saveToStorage();
        this._emit('zone-mode-changed', { zoneId, mode });
        
        return true;
    },
    
    /**
     * Remove panel from all zones (helper)
     */
    _removePanelFromAllZones(panelId) {
        const layout = this.getActiveLayout();
        ZoneIds.forEach(zoneId => {
            const zone = layout.zones[zoneId];
            const idx = zone.panels.indexOf(panelId);
            if (idx >= 0) {
                zone.panels.splice(idx, 1);
                if (zone.activePanel === panelId) {
                    zone.activePanel = zone.panels[0] || null;
                }
            }
        });
    },
    
    // ========== Zone Sizes ==========
    
    /**
     * Get zone sizes
     */
    getZoneSizes() {
        return this.getActiveLayout().zoneSizes;
    },
    
    /**
     * Update zone size
     */
    setZoneSize(sizeKey, value) {
        const sizes = this.getZoneSizes();
        sizes[sizeKey] = value;
        this._saveToStorage();
        this._emit('zone-resized', { sizeKey, value });
    },
    
    /**
     * Toggle between 2-column and 3-column modes
     */
    toggleTopRowMode() {
        const layout = this.getActiveLayout();
        const newMode = layout.topRowMode === 'two-column' ? 'three-column' : 'two-column';
        
        layout.topRowMode = newMode;
        
        // Adjust sizes based on mode
        if (newMode === 'two-column') {
            // Move center panels to right zone
            const centerPanels = layout.zones.center.panels;
            centerPanels.forEach(p => {
                if (!layout.zones.right.panels.includes(p)) {
                    layout.zones.right.panels.push(p);
                }
            });
            layout.zones.center.panels = [];
            layout.zones.center.activePanel = null;
            layout.zoneSizes.centerWidth = '0';
        } else {
            // Set default center width
            layout.zoneSizes.centerWidth = '1fr';
            layout.zoneSizes.leftWidth = '280px';
            layout.zoneSizes.rightWidth = '280px';
        }
        
        this._saveToStorage();
        this._emit('top-row-mode-changed', { mode: newMode });
        
        return newMode;
    },
    
    /**
     * Get top row mode
     */
    getTopRowMode() {
        return this.getActiveLayout().topRowMode;
    },
    
    // ========== Bottom Row Helpers ==========
    
    /**
     * Check if bottom row should be visible
     */
    isBottomRowVisible() {
        const layout = this.getActiveLayout();
        return layout.zones.bottomLeft.panels.length > 0 || 
               layout.zones.bottomRight.panels.length > 0;
    },
    
    /**
     * Get bottom row merge state
     * Returns: 'split' | 'merged-left' | 'merged-right' | 'hidden'
     */
    getBottomRowState() {
        const layout = this.getActiveLayout();
        const hasLeft = layout.zones.bottomLeft.panels.length > 0;
        const hasRight = layout.zones.bottomRight.panels.length > 0;
        
        if (!hasLeft && !hasRight) return 'hidden';
        if (hasLeft && hasRight) return 'split';
        if (hasLeft) return 'merged-left';
        return 'merged-right';
    },
    
    // ========== Event System ==========
    
    /**
     * Subscribe to layout events
     */
    on(event, callback) {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, new Set());
        }
        this._listeners.get(event).add(callback);
        
        return () => this.off(event, callback);
    },
    
    /**
     * Unsubscribe from layout events
     */
    off(event, callback) {
        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.delete(callback);
        }
    },
    
    /**
     * Emit an event
     */
    _emit(event, data) {
        // Notify internal listeners
        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.forEach(cb => {
                try {
                    cb(data);
                } catch (e) {
                    console.error('[LayoutManager] Event handler error:', e);
                }
            });
        }
        
        // Also emit as DOM event for external listeners
        window.dispatchEvent(new CustomEvent(`negmas:${event}`, { detail: data }));
    },
    
    // ========== Utility Methods ==========
    
    /**
     * Reset to default layout
     */
    resetToDefault() {
        this._state.activeLayoutId = 'default';
        this._saveToStorage();
        this._emit('layout-changed', { layoutId: 'default', layout: this.getActiveLayout() });
    },
    
    /**
     * Reset current layout to its default state
     */
    resetCurrentLayout() {
        const currentId = this._state.activeLayoutId;
        
        // If it's a built-in layout, restore from BuiltInLayouts
        if (BuiltInLayouts[currentId]) {
            this._state.layouts[currentId] = JSON.parse(JSON.stringify(BuiltInLayouts[currentId]));
            this._saveToStorage();
            this._emit('layout-changed', { layoutId: currentId, layout: this.getActiveLayout() });
        } else {
            // For custom layouts, just switch to default
            this.resetToDefault();
        }
    },
    
    /**
     * Export current state as JSON
     */
    exportState() {
        return JSON.stringify(this._state, null, 2);
    },
    
    /**
     * Import state from JSON
     */
    importState(json) {
        try {
            const state = JSON.parse(json);
            if (state.version === 1) {
                this._state = state;
                // Ensure built-in layouts are present
                Object.entries(BuiltInLayouts).forEach(([id, layout]) => {
                    this._state.layouts[id] = layout;
                });
                this._saveToStorage();
                this._emit('state-imported', { state: this._state });
                return true;
            }
        } catch (e) {
            console.error('[LayoutManager] Failed to import state:', e);
        }
        return false;
    },
    
    /**
     * Find which zone contains a panel
     */
    findPanelZone(panelId) {
        const layout = this.getActiveLayout();
        for (const zoneId of ZoneIds) {
            if (layout.zones[zoneId].panels.includes(panelId)) {
                return zoneId;
            }
        }
        return null;
    },
    
    /**
     * Check if a panel is open (in any zone)
     */
    isPanelOpen(panelId) {
        return this.findPanelZone(panelId) !== null;
    },
    
    /**
     * Get all open panels
     */
    getOpenPanels() {
        const layout = this.getActiveLayout();
        const panels = [];
        ZoneIds.forEach(zoneId => {
            panels.push(...layout.zones[zoneId].panels);
        });
        return panels;
    }
};

// Export for use in other modules
window.LayoutManager = LayoutManager;
window.BuiltInLayouts = BuiltInLayouts;
window.ZoneIds = ZoneIds;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => LayoutManager.init());
} else {
    LayoutManager.init();
}
