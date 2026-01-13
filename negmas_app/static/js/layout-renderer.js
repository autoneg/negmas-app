/**
 * Layout Renderer - DOM rendering engine for the panel layout system
 * 
 * This module provides:
 * - Zone container rendering
 * - Tabbed and stacked panel display modes
 * - Panel content rendering with lifecycle management
 * - Resize handle interactions
 * - Integration with LayoutManager and PanelRegistry
 */

const LayoutRenderer = {
    _container: null,
    _state: null,  // Reference to application state for panels
    _resizing: null,
    _initialized: false,
    
    /**
     * Initialize the layout renderer
     * @param {HTMLElement} container - The container element for the layout
     * @param {Object} state - Application state object (passed to panels)
     */
    init(container, state = {}) {
        if (this._initialized) return this;
        
        this._container = container;
        this._state = state;
        
        // Subscribe to layout changes
        LayoutManager.on('layout-changed', () => this.render());
        LayoutManager.on('panel-activated', ({ zoneId }) => this._updateZone(zoneId));
        LayoutManager.on('panel-added', ({ zoneId }) => this._updateZone(zoneId));
        LayoutManager.on('panel-removed', ({ zoneId }) => this._updateZone(zoneId));
        LayoutManager.on('panel-moved', () => this.render());
        LayoutManager.on('zone-mode-changed', ({ zoneId }) => this._updateZone(zoneId));
        LayoutManager.on('zone-resized', () => this._applyZoneSizes());
        LayoutManager.on('top-row-mode-changed', () => this.render());
        
        // Initial render
        this.render();
        
        this._initialized = true;
        console.log('[LayoutRenderer] Initialized');
        
        return this;
    },
    
    /**
     * Update the application state (for panels to access)
     */
    setState(state) {
        this._state = state;
        this._updateAllPanels();
    },
    
    /**
     * Update specific state property
     */
    updateState(key, value) {
        this._state[key] = value;
        this._updateAllPanels();
    },
    
    /**
     * Render the complete layout
     */
    render() {
        if (!this._container) return;
        
        const layout = LayoutManager.getActiveLayout();
        const topRowMode = layout.topRowMode;
        const bottomState = LayoutManager.getBottomRowState();
        
        // Build layout structure
        this._container.innerHTML = '';
        this._container.className = 'layout-container';
        this._container.dataset.topMode = topRowMode;
        this._container.dataset.bottomState = bottomState;
        
        // Create top row
        const topRow = this._createTopRow(layout, topRowMode);
        this._container.appendChild(topRow);
        
        // Create resize handle between top and bottom
        if (bottomState !== 'hidden') {
            const vHandle = this._createResizeHandle('vertical', 'top-bottom');
            this._container.appendChild(vHandle);
        }
        
        // Create bottom row
        if (bottomState !== 'hidden') {
            const bottomRow = this._createBottomRow(layout, bottomState);
            this._container.appendChild(bottomRow);
        }
        
        // Apply zone sizes
        this._applyZoneSizes();
        
        // Initialize all panels
        this._initAllPanels();
    },
    
    /**
     * Create the top row container
     */
    _createTopRow(layout, mode) {
        const row = document.createElement('div');
        row.className = 'layout-top-row';
        
        if (mode === 'two-column') {
            // Left zone
            row.appendChild(this._createZone('left', layout.zones.left));
            
            // Resize handle
            row.appendChild(this._createResizeHandle('horizontal', 'left-right'));
            
            // Right zone
            row.appendChild(this._createZone('right', layout.zones.right));
        } else {
            // Three-column mode
            // Left zone
            row.appendChild(this._createZone('left', layout.zones.left));
            
            // Resize handle
            row.appendChild(this._createResizeHandle('horizontal', 'left-center'));
            
            // Center zone
            row.appendChild(this._createZone('center', layout.zones.center));
            
            // Resize handle
            row.appendChild(this._createResizeHandle('horizontal', 'center-right'));
            
            // Right zone
            row.appendChild(this._createZone('right', layout.zones.right));
        }
        
        return row;
    },
    
    /**
     * Create the bottom row container
     */
    _createBottomRow(layout, state) {
        const row = document.createElement('div');
        row.className = 'layout-bottom-row';
        row.dataset.state = state;
        
        if (state === 'split') {
            // Both zones visible
            row.appendChild(this._createZone('bottomLeft', layout.zones.bottomLeft));
            row.appendChild(this._createResizeHandle('horizontal', 'bottom-split'));
            row.appendChild(this._createZone('bottomRight', layout.zones.bottomRight));
        } else if (state === 'merged-left') {
            row.appendChild(this._createZone('bottomLeft', layout.zones.bottomLeft, true));
        } else if (state === 'merged-right') {
            row.appendChild(this._createZone('bottomRight', layout.zones.bottomRight, true));
        }
        
        return row;
    },
    
    /**
     * Create a zone container
     */
    _createZone(zoneId, zoneConfig, merged = false) {
        const zone = document.createElement('div');
        zone.className = 'layout-zone';
        zone.dataset.zoneId = zoneId;
        zone.dataset.displayMode = zoneConfig.displayMode || 'tabbed';
        if (merged) zone.dataset.merged = 'true';
        
        // Don't render if no panels
        if (!zoneConfig.panels || zoneConfig.panels.length === 0) {
            zone.classList.add('layout-zone-empty');
            zone.innerHTML = `
                <div class="zone-empty-state">
                    <button class="zone-add-btn" data-zone="${zoneId}">
                        ${PanelIcons.add}
                        <span>Add Panel</span>
                    </button>
                </div>
            `;
            return zone;
        }
        
        // Create zone header with tabs (for tabbed mode)
        if (zoneConfig.displayMode === 'tabbed') {
            zone.appendChild(this._createTabBar(zoneId, zoneConfig));
        }
        
        // Create panel container
        const panelContainer = document.createElement('div');
        panelContainer.className = 'zone-panel-container';
        
        // Render panels based on display mode
        if (zoneConfig.displayMode === 'tabbed') {
            // Only render active panel
            const activePanel = zoneConfig.activePanel || zoneConfig.panels[0];
            panelContainer.appendChild(this._createPanelElement(activePanel, zoneId, true));
        } else {
            // Stacked mode: render all panels with resize handles
            zoneConfig.panels.forEach((panelId, idx) => {
                panelContainer.appendChild(this._createStackedPanel(panelId, zoneId, idx, zoneConfig.panels.length));
                
                // Add resize handle between stacked panels
                if (idx < zoneConfig.panels.length - 1) {
                    const handle = document.createElement('div');
                    handle.className = 'stack-resize-handle';
                    handle.dataset.zoneId = zoneId;
                    handle.dataset.above = panelId;
                    handle.dataset.below = zoneConfig.panels[idx + 1];
                    panelContainer.appendChild(handle);
                }
            });
        }
        
        zone.appendChild(panelContainer);
        
        return zone;
    },
    
    /**
     * Create tab bar for a zone
     */
    _createTabBar(zoneId, zoneConfig) {
        const tabBar = document.createElement('div');
        tabBar.className = 'zone-tab-bar';
        
        const tabs = document.createElement('div');
        tabs.className = 'zone-tabs';
        
        zoneConfig.panels.forEach(panelId => {
            const panel = PanelRegistry.get(panelId);
            if (!panel) return;
            
            const tab = document.createElement('button');
            tab.className = 'zone-tab';
            tab.dataset.panelId = panelId;
            tab.dataset.zoneId = zoneId;
            
            if (panelId === zoneConfig.activePanel) {
                tab.classList.add('active');
            }
            
            tab.innerHTML = `
                <span class="tab-icon">${panel.icon || ''}</span>
                <span class="tab-name">${panel.name}</span>
                ${panel.closable !== false ? `<button class="tab-close" data-panel="${panelId}" data-zone="${zoneId}">${PanelIcons.close}</button>` : ''}
            `;
            
            // Tab click handler
            tab.addEventListener('click', (e) => {
                if (e.target.closest('.tab-close')) {
                    e.stopPropagation();
                    LayoutManager.removePanelFromZone(panelId, zoneId);
                } else {
                    LayoutManager.setActivePanel(zoneId, panelId);
                }
            });
            
            tabs.appendChild(tab);
        });
        
        tabBar.appendChild(tabs);
        
        // Add panel button
        const addBtn = document.createElement('button');
        addBtn.className = 'zone-add-panel-btn';
        addBtn.dataset.zoneId = zoneId;
        addBtn.innerHTML = PanelIcons.add;
        addBtn.title = 'Add panel';
        addBtn.addEventListener('click', () => this._showPanelPicker(zoneId));
        tabBar.appendChild(addBtn);
        
        // Zone menu button
        const menuBtn = document.createElement('button');
        menuBtn.className = 'zone-menu-btn';
        menuBtn.innerHTML = PanelIcons.menu;
        menuBtn.title = 'Zone options';
        menuBtn.addEventListener('click', (e) => this._showZoneMenu(zoneId, e.target));
        tabBar.appendChild(menuBtn);
        
        return tabBar;
    },
    
    /**
     * Create a stacked panel (with header)
     */
    _createStackedPanel(panelId, zoneId, index, total) {
        const panel = PanelRegistry.get(panelId);
        if (!panel) return document.createElement('div');
        
        const wrapper = document.createElement('div');
        wrapper.className = 'stacked-panel';
        wrapper.dataset.panelId = panelId;
        wrapper.dataset.zoneId = zoneId;
        wrapper.dataset.index = index;
        
        // Panel header
        const header = document.createElement('div');
        header.className = 'stacked-panel-header';
        header.innerHTML = `
            <span class="panel-icon">${panel.icon || ''}</span>
            <span class="panel-name">${panel.name}</span>
            <div class="panel-actions">
                ${panel.closable !== false ? `<button class="panel-close-btn" data-panel="${panelId}" data-zone="${zoneId}">${PanelIcons.close}</button>` : ''}
            </div>
        `;
        
        // Close button handler
        const closeBtn = header.querySelector('.panel-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                LayoutManager.removePanelFromZone(panelId, zoneId);
            });
        }
        
        wrapper.appendChild(header);
        
        // Panel content
        wrapper.appendChild(this._createPanelElement(panelId, zoneId, true));
        
        return wrapper;
    },
    
    /**
     * Create a panel element
     */
    _createPanelElement(panelId, zoneId, active = false) {
        const panel = PanelRegistry.get(panelId);
        
        const element = document.createElement('div');
        element.className = 'panel-content';
        element.dataset.panelId = panelId;
        element.dataset.zoneId = zoneId;
        if (active) element.classList.add('active');
        
        if (!panel) {
            element.innerHTML = `<div class="panel-error">Panel "${panelId}" not found</div>`;
            return element;
        }
        
        // Render panel content
        if (panel.render) {
            element.innerHTML = panel.render(this._state);
        }
        
        return element;
    },
    
    /**
     * Create a resize handle
     */
    _createResizeHandle(direction, id) {
        const handle = document.createElement('div');
        handle.className = `resize-handle resize-handle-${direction}`;
        handle.dataset.resizeId = id;
        handle.dataset.direction = direction;
        
        // Setup drag interaction
        handle.addEventListener('mousedown', (e) => this._startResize(e, handle, direction, id));
        
        return handle;
    },
    
    /**
     * Apply zone sizes from layout configuration
     */
    _applyZoneSizes() {
        const sizes = LayoutManager.getZoneSizes();
        const topMode = LayoutManager.getTopRowMode();
        const bottomState = LayoutManager.getBottomRowState();
        
        // Apply CSS custom properties
        this._container.style.setProperty('--left-width', sizes.leftWidth);
        this._container.style.setProperty('--center-width', sizes.centerWidth || '0');
        this._container.style.setProperty('--right-width', sizes.rightWidth);
        this._container.style.setProperty('--bottom-height', sizes.bottomHeight);
        this._container.style.setProperty('--bottom-split', sizes.bottomSplit);
        
        // Set top row grid template based on mode
        const topRow = this._container.querySelector('.layout-top-row');
        if (topRow) {
            if (topMode === 'two-column') {
                topRow.style.gridTemplateColumns = `${sizes.leftWidth} 4px ${sizes.rightWidth}`;
            } else {
                topRow.style.gridTemplateColumns = `${sizes.leftWidth} 4px ${sizes.centerWidth} 4px ${sizes.rightWidth}`;
            }
        }
        
        // Set bottom row split
        const bottomRow = this._container.querySelector('.layout-bottom-row');
        if (bottomRow && bottomState === 'split') {
            bottomRow.style.gridTemplateColumns = `${sizes.bottomSplit} 4px calc(100% - ${sizes.bottomSplit} - 4px)`;
        }
    },
    
    /**
     * Initialize all panels after render
     */
    _initAllPanels() {
        const layout = LayoutManager.getActiveLayout();
        
        ZoneIds.forEach(zoneId => {
            const zone = layout.zones[zoneId];
            if (!zone || !zone.panels) return;
            
            zone.panels.forEach(panelId => {
                const panel = PanelRegistry.get(panelId);
                const element = this._container.querySelector(`[data-panel-id="${panelId}"]`);
                
                if (panel && element && panel.init) {
                    try {
                        panel.init(element, this._state);
                    } catch (e) {
                        console.error(`[LayoutRenderer] Error initializing panel "${panelId}":`, e);
                    }
                }
            });
        });
    },
    
    /**
     * Update all panels (e.g., when state changes)
     */
    _updateAllPanels() {
        const layout = LayoutManager.getActiveLayout();
        
        ZoneIds.forEach(zoneId => {
            const zone = layout.zones[zoneId];
            if (!zone || !zone.panels) return;
            
            zone.panels.forEach(panelId => {
                const panel = PanelRegistry.get(panelId);
                const element = this._container.querySelector(`[data-panel-id="${panelId}"]`);
                
                if (panel && element && panel.update) {
                    try {
                        panel.update(element, this._state);
                    } catch (e) {
                        console.error(`[LayoutRenderer] Error updating panel "${panelId}":`, e);
                    }
                }
            });
        });
    },
    
    /**
     * Update a specific zone
     */
    _updateZone(zoneId) {
        const zoneEl = this._container.querySelector(`[data-zone-id="${zoneId}"]`);
        if (!zoneEl) {
            // Zone doesn't exist, need full re-render
            this.render();
            return;
        }
        
        const layout = LayoutManager.getActiveLayout();
        const zoneConfig = layout.zones[zoneId];
        
        // Replace zone element
        const newZone = this._createZone(zoneId, zoneConfig);
        zoneEl.replaceWith(newZone);
        
        // Re-initialize panels in this zone
        zoneConfig.panels.forEach(panelId => {
            const panel = PanelRegistry.get(panelId);
            const element = newZone.querySelector(`[data-panel-id="${panelId}"]`);
            
            if (panel && element && panel.init) {
                try {
                    panel.init(element, this._state);
                } catch (e) {
                    console.error(`[LayoutRenderer] Error initializing panel "${panelId}":`, e);
                }
            }
        });
    },
    
    // ========== Resize Handling ==========
    
    /**
     * Start resize operation
     */
    _startResize(e, handle, direction, id) {
        e.preventDefault();
        
        this._resizing = {
            handle,
            direction,
            id,
            startX: e.clientX,
            startY: e.clientY,
            startSizes: { ...LayoutManager.getZoneSizes() }
        };
        
        handle.classList.add('active');
        document.body.classList.add('resizing');
        document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
        
        // Bind methods to preserve 'this' context
        this._boundOnResize = this._onResize.bind(this);
        this._boundEndResize = this._endResize.bind(this);
        
        document.addEventListener('mousemove', this._boundOnResize);
        document.addEventListener('mouseup', this._boundEndResize);
    },
    
    /**
     * Handle resize movement (bound in init)
     */
    _onResize(e) {
        if (!this._resizing) return;
        
        const { direction, id, startX, startY, startSizes } = this._resizing;
        const containerRect = this._container.getBoundingClientRect();
        
        if (direction === 'horizontal') {
            const deltaX = e.clientX - startX;
            
            if (id === 'left-right' || id === 'left-center') {
                // Resize left zone
                const startWidth = this._parseSize(startSizes.leftWidth, containerRect.width);
                const newWidth = Math.max(150, Math.min(containerRect.width - 200, startWidth + deltaX));
                LayoutManager.setZoneSize('leftWidth', `${newWidth}px`);
            } else if (id === 'center-right') {
                // Resize center zone (adjust right)
                const startWidth = this._parseSize(startSizes.rightWidth, containerRect.width);
                const newWidth = Math.max(150, Math.min(containerRect.width - 200, startWidth - deltaX));
                LayoutManager.setZoneSize('rightWidth', `${newWidth}px`);
            } else if (id === 'bottom-split') {
                // Resize bottom split
                const pct = Math.max(20, Math.min(80, ((e.clientX - containerRect.left) / containerRect.width) * 100));
                LayoutManager.setZoneSize('bottomSplit', `${pct}%`);
            }
        } else {
            // Vertical resize (top-bottom)
            const deltaY = e.clientY - startY;
            const startHeight = this._parseSize(startSizes.bottomHeight, containerRect.height);
            const newHeight = Math.max(60, Math.min(containerRect.height - 200, startHeight - deltaY));
            LayoutManager.setZoneSize('bottomHeight', `${newHeight}px`);
        }
    },
    
    /**
     * End resize operation (bound in init)
     */
    _endResize() {
        if (this._resizing) {
            this._resizing.handle.classList.remove('active');
            this._resizing = null;
        }
        
        document.body.classList.remove('resizing');
        document.body.style.cursor = '';
        
        document.removeEventListener('mousemove', this._boundOnResize);
        document.removeEventListener('mouseup', this._boundEndResize);
        
        // Trigger resize event for Plotly charts
        window.dispatchEvent(new Event('resize'));
    },
    
    /**
     * Parse CSS size value to pixels
     */
    _parseSize(size, containerSize) {
        if (typeof size === 'number') return size;
        if (size.endsWith('px')) return parseFloat(size);
        if (size.endsWith('%')) return (parseFloat(size) / 100) * containerSize;
        if (size === '1fr') return containerSize / 2; // Approximate
        return parseFloat(size) || 0;
    }
    
    // ========== Panel Picker ==========
    
    /**
     * Show panel picker for a zone
     */
    _showPanelPicker(zoneId) {
        // Remove any existing picker
        const existing = document.querySelector('.panel-picker-overlay');
        if (existing) existing.remove();
        
        const openPanels = LayoutManager.getOpenPanels();
        const availablePanels = PanelRegistry.getForContext('negotiation')
            .filter(p => !openPanels.includes(p.id) || p.allowMultiple);
        
        const overlay = document.createElement('div');
        overlay.className = 'panel-picker-overlay';
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
        
        const picker = document.createElement('div');
        picker.className = 'panel-picker';
        
        picker.innerHTML = `
            <div class="panel-picker-header">
                <span>Add Panel</span>
                <button class="panel-picker-close">${PanelIcons.close}</button>
            </div>
            <div class="panel-picker-list">
                ${availablePanels.length > 0 
                    ? availablePanels.map(p => `
                        <button class="panel-picker-item" data-panel="${p.id}">
                            <span class="panel-icon">${p.icon || ''}</span>
                            <span class="panel-name">${p.name}</span>
                        </button>
                    `).join('')
                    : '<div class="panel-picker-empty">All panels are open</div>'
                }
            </div>
        `;
        
        // Close button
        picker.querySelector('.panel-picker-close').addEventListener('click', () => overlay.remove());
        
        // Panel selection
        picker.querySelectorAll('.panel-picker-item').forEach(item => {
            item.addEventListener('click', () => {
                const panelId = item.dataset.panel;
                LayoutManager.addPanelToZone(panelId, zoneId);
                overlay.remove();
            });
        });
        
        overlay.appendChild(picker);
        document.body.appendChild(overlay);
    },
    
    /**
     * Show zone context menu
     */
    _showZoneMenu(zoneId, target) {
        // Remove any existing menu
        const existing = document.querySelector('.zone-context-menu');
        if (existing) existing.remove();
        
        const zone = LayoutManager.getZone(zoneId);
        const currentMode = zone.displayMode;
        
        const menu = document.createElement('div');
        menu.className = 'zone-context-menu';
        
        const rect = target.getBoundingClientRect();
        menu.style.top = `${rect.bottom + 4}px`;
        menu.style.left = `${rect.left}px`;
        
        menu.innerHTML = `
            <button class="zone-menu-item" data-action="mode" data-mode="${currentMode === 'tabbed' ? 'stacked' : 'tabbed'}">
                ${currentMode === 'tabbed' ? 'Stack Panels' : 'Tab Panels'}
            </button>
            <button class="zone-menu-item" data-action="close-all">Close All Panels</button>
        `;
        
        menu.querySelectorAll('.zone-menu-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                if (action === 'mode') {
                    LayoutManager.setZoneDisplayMode(zoneId, item.dataset.mode);
                } else if (action === 'close-all') {
                    const panels = [...zone.panels];
                    panels.forEach(p => LayoutManager.removePanelFromZone(p, zoneId));
                }
                menu.remove();
            });
        });
        
        // Close menu on outside click
        setTimeout(() => {
            const closeHandler = (e) => {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeHandler);
                }
            };
            document.addEventListener('click', closeHandler);
        }, 0);
        
        document.body.appendChild(menu);
    },
    
    // ========== Utility Methods ==========
    
    /**
     * Get a panel element by ID
     */
    getPanelElement(panelId) {
        return this._container?.querySelector(`[data-panel-id="${panelId}"]`);
    },
    
    /**
     * Force refresh a specific panel
     */
    refreshPanel(panelId) {
        const panel = PanelRegistry.get(panelId);
        const element = this.getPanelElement(panelId);
        
        if (panel && element) {
            if (panel.render) {
                element.innerHTML = panel.render(this._state);
            }
            if (panel.init) {
                panel.init(element, this._state);
            }
        }
    },
    
    /**
     * Destroy all panels (cleanup)
     */
    destroy() {
        const layout = LayoutManager.getActiveLayout();
        
        ZoneIds.forEach(zoneId => {
            const zone = layout.zones[zoneId];
            if (!zone || !zone.panels) return;
            
            zone.panels.forEach(panelId => {
                const panel = PanelRegistry.get(panelId);
                const element = this.getPanelElement(panelId);
                
                if (panel && element && panel.destroy) {
                    try {
                        panel.destroy(element);
                    } catch (e) {
                        console.error(`[LayoutRenderer] Error destroying panel "${panelId}":`, e);
                    }
                }
            });
        });
        
        if (this._container) {
            this._container.innerHTML = '';
        }
        
        this._initialized = false;
    }
};

// Export for use in other modules
window.LayoutRenderer = LayoutRenderer;
