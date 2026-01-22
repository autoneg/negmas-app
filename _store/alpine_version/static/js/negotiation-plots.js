/**
 * Negotiation Plots - Extends the Alpine.js app with plotting functionality
 * for the negotiation view (2D utility view, timeline plots, histogram)
 */

// Initialize plot state flags
document.addEventListener('alpine:init', () => {
    window.outcomeSpacePlotInitialized = false;
    window.timelinePlotsInitialized = false;
    window.histogramPlotInitialized = false;
});

// Override/extend app functions for plotting
const originalApp = app;
app = function() {
    const base = originalApp();
    
    // Color-blind friendly palette (Okabe-Ito)
    const COLORBLIND_COLORS = [
        '#0072B2',  // Blue
        '#E69F00',  // Orange
        '#009E73',  // Bluish Green
        '#CC79A7',  // Reddish Purple
        '#F0E442',  // Yellow
        '#56B4E9',  // Sky Blue
        '#D55E00',  // Vermillion
        '#000000',  // Black
    ];
    
    // Dark mode color-blind colors (brighter)
    const COLORBLIND_COLORS_DARK = [
        '#56B4E9',  // Sky Blue
        '#E69F00',  // Orange
        '#009E73',  // Bluish Green
        '#CC79A7',  // Reddish Purple
        '#F0E442',  // Yellow
        '#0072B2',  // Blue
        '#D55E00',  // Vermillion
        '#FFFFFF',  // White
    ];
    
    // Line dash patterns
    const LINE_DASHES = ['solid', 'dash', 'dot', 'dashdot', 'longdash', 'longdashdot'];
    
    // Marker symbols
    const MARKER_SYMBOLS = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down', 'star'];
    
    // Add our custom properties/methods by merging with base
    const plotExtensions = {
        // Panel state for controls
        zoomedPanel: null,
        showIssueFrequency: false,  // Hidden feature for now
        showScenarioStatsModal: false,  // Stats modal visibility
        currentNegotiationStats: null,  // Stats for current negotiation's scenario
        currentNegotiationStatsLoading: false,
        currentNegotiationStatsError: null,
        panelState: {
            utilityView: { xAxis: 0, yAxis: 1 },
            timeline: { xAxis: 'relative_time' },
            issueSpace: { xAxis: 0, yAxis: 1 }
        },
        
        // Layout state - integrates with LayoutManager
        currentLayoutId: 'default',
        zoneModes: {
            left: 'stacked',   // 'stacked' or 'tabbed'
            right: 'stacked'
        },
        activeTab: {
            left: 'info',      // Active panel ID when in tabbed mode
            right: 'utility2d',
            fullscreen: 'utility2d'
        },
        
        // Panel definitions for each zone
        panelDefs: {
            left: ['info', 'history', 'result'],
            right: ['utility2d', 'timeline']
        },
        
        // Panel collapse state
        panelCollapsed: {
            info: false,
            history: false,
            result: false,
            utility2d: false,
            timeline: false,
            histogram: false,
            issueSpace2d: false
        },
        
        // Timeline view mode: false = full (per-agent), true = simplified (single plot)
        timelineSimplifiedView: false,
        
        // Resize state
        resizeState: {
            active: false,
            type: null,  // 'column' or panel resize type
            startX: 0,
            startY: 0,
            startWidth: 0,
            startHeight: 0
        },
        
        // Saved negotiations state
        savedNegotiations: [],
        savedNegotiationsLoading: false,
        showArchivedNegotiations: false,
        availableTags: [],
        tagFilter: '',
        
        // Tabulator instances
        _runningTable: null,
        _completedTable: null,
        _savedTable: null,
        
        // Throttle timestamps for SSE updates (max 30fps)
        _lastPlotUpdate: 0,
        _lastScrollUpdate: 0,
        
        // Override init
        async init() {
            await base.init.call(this);
            
            // Wait for LayoutManager to initialize (it loads from server)
            if (window.LayoutManager && !window.LayoutManager._initialized) {
                await window.LayoutManager.init();
            }
            
            // Load saved panel collapse state from LayoutManager
            if (window.LayoutManager) {
                const savedCollapsed = window.LayoutManager.getPanelCollapsed();
                if (savedCollapsed && Object.keys(savedCollapsed).length > 0) {
                    Object.assign(this.panelCollapsed, savedCollapsed);
                }
                
                // Load saved column width from LayoutManager
                const savedColumnWidth = window.LayoutManager.getLeftColumnWidth();
                if (savedColumnWidth) {
                    this.$nextTick(() => {
                        const leftCol = this.$refs.leftColumn;
                        if (leftCol) {
                            leftCol.style.flex = `0 0 ${savedColumnWidth}`;
                        }
                    });
                }
            }
            
            // Add mouse move/up listeners for resize
            document.addEventListener('mousemove', this.handleResizeMove.bind(this));
            document.addEventListener('mouseup', this.handleResizeEnd.bind(this));
            
            // Watch for panel collapse changes and save to server via LayoutManager
            this.$watch('panelCollapsed', () => {
                if (window.LayoutManager) {
                    window.LayoutManager.setPanelCollapsedAll(this.panelCollapsed);
                }
            }, { deep: true });
            
            // Listen for theme changes to redraw charts
            window.addEventListener('colorblind-mode-changed', () => {
                if (this.currentNegotiation) {
                    this.$nextTick(() => {
                        this.initOutcomeSpacePlot();
                        this.initUtilityTimelinePlots();
                        this.initHistogramPlot();
                    });
                }
            });
            
            window.addEventListener('dark-mode-changed', () => {
                if (this.currentNegotiation) {
                    this.$nextTick(() => {
                        this.initOutcomeSpacePlot();
                        this.initUtilityTimelinePlots();
                        this.initHistogramPlot();
                    });
                }
            });
            
            // Watch for changes to negotiations arrays to update tables
            // Use shallow watch - only trigger on array length changes, not nested offer updates
            this.$watch('runningNegotiations.length', () => this.updateRunningTable());
            this.$watch('completedNegotiations.length', () => this.updateCompletedTable());
            this.$watch('savedNegotiations.length', () => this.updateSavedTable());
            
            // Watch for currentNegotiation changes to redraw tables when returning to table view
            this.$watch('currentNegotiation', (newVal, oldVal) => {
                if (newVal === null && oldVal !== null) {
                    // Returning from single negotiation view to table view
                    // Need to redraw tables after they become visible again
                    this.$nextTick(() => {
                        if (this._runningTable) this._runningTable.redraw(true);
                        if (this._completedTable) this._completedTable.redraw(true);
                        if (this._savedTable) this._savedTable.redraw(true);
                    });
                } else if (newVal !== null) {
                    // Selecting a negotiation - sync panel state from negotiation's panel settings
                    if (newVal.panelSettings) {
                        if (newVal.panelSettings.timeline) {
                            this.panelState.timeline = { ...newVal.panelSettings.timeline };
                            // Sync timelineSimplifiedView from settings if available
                            if ('simplified' in newVal.panelSettings.timeline) {
                                this.timelineSimplifiedView = newVal.panelSettings.timeline.simplified;
                            }
                        }
                        if (newVal.panelSettings.issueSpace) {
                            this.panelState.issueSpace = { ...newVal.panelSettings.issueSpace };
                        }
                        if (newVal.panelSettings.utilityView) {
                            this.panelState.utilityView = { ...newVal.panelSettings.utilityView };
                        }
                    }
                }
            });
            
            // Auto-load saved negotiations on startup
            this.loadSavedNegotiations();
            this.loadAvailableTags();
        },
        
        // Initialize Tabulator tables for negotiations view
        initNegotiationsTables() {
            this.$nextTick(() => {
                this.initRunningTable();
                this.initCompletedTable();
                this.initSavedTable();
            });
        },
        
        // Helper to format negotiator badges HTML
        formatNegotiatorBadges(names, colors) {
            if (!names || names.length === 0) return '';
            return names.map((name, idx) => {
                const color = colors?.[idx] || 'var(--primary)';
                return `<span class="badge badge-sm" style="background: ${color}; color: white;">${name}</span>`;
            }).join(' ');
        },
        
        // Helper to format utilities HTML
        formatUtilities(utilities, colors) {
            if (!utilities || utilities.length === 0) return '<span class="text-muted">-</span>';
            return utilities.map((util, idx) => {
                const color = colors?.[idx] || 'inherit';
                return `<span style="color: ${color};">${util.toFixed(2)}</span>`;
            }).join(' ');
        },
        
        // Helper to format result badge
        formatResultBadge(neg) {
            if (neg.agreement) {
                return '<span class="badge badge-success">Agreement</span>';
            } else if (neg.error) {
                return '<span class="badge badge-danger">Error</span>';
            } else {
                return `<span class="badge badge-warning">${neg.end_reason || 'No Agreement'}</span>`;
            }
        },
        
        // Initialize running negotiations table
        initRunningTable() {
            const container = document.getElementById('running-negotiations-table');
            if (!container || this._runningTable) return;
            
            const self = this;
            this._runningTable = new Tabulator(container, {
                data: this.runningNegotiations,
                layout: "fitColumns",
                height: "150px",
                placeholder: "No running negotiations",
                selectableRows: 1,
                columns: [
                    { title: "ID", field: "id", width: 70, resizable: false, formatter: (cell) => {
                        const id = cell.getValue();
                        return `<code style="font-size: 11px; cursor: pointer;" title="${id}" onclick="navigator.clipboard.writeText('${id}'); event.stopPropagation();">${id.substring(0, 6)}...</code>`;
                    } },
                    { title: "Scenario", field: "scenario", widthGrow: 2, minWidth: 100, formatter: (cell) => cell.getValue() || 'Loading...' },
                    { title: "Negotiators", field: "negotiator_names", widthGrow: 2, minWidth: 120, formatter: (cell, params, onRendered) => {
                        const row = cell.getRow().getData();
                        return self.formatNegotiatorBadges(row.negotiator_names, row.negotiator_colors);
                    }, headerSort: false },
                    { title: "Progress", field: "relative_time", width: 130, resizable: false, formatter: (cell) => {
                        const row = cell.getRow().getData();
                        // For background negotiations, use the progress field directly
                        const progress = row.background 
                            ? Math.min(100, row.progress || 0) 
                            : Math.min(100, (row.relative_time || 0) * 100);
                        const statusText = row.background 
                            ? (row.step ? 'Step ' + row.step : 'Running...')
                            : (row.step ? 'Step ' + row.step : 'Starting...');
                        return `<div style="display: flex; align-items: center; gap: 8px;">
                            <div class="progress" style="width: 60px; height: 6px;">
                                <div class="progress-bar" style="width: ${progress}%"></div>
                            </div>
                            <span style="font-size: 11px;">${statusText}</span>
                        </div>`;
                    }, headerSort: false },
                    { title: "Status", field: "paused", width: 85, hozAlign: "center", resizable: false, formatter: (cell) => {
                        const row = cell.getRow().getData();
                        if (row.background) {
                            return `<span class="badge badge-info badge-sm">Background</span>`;
                        }
                        const paused = cell.getValue();
                        return `<span class="badge badge-primary badge-sm">${paused ? 'Paused' : 'Running'}</span>`;
                    } }
                ]
            });
            this._runningTable.on("rowClick", function(e, row) {
                self.selectNegotiation(row.getData());
            });
        },
        
        // Initialize completed negotiations table
        initCompletedTable() {
            const container = document.getElementById('completed-negotiations-table');
            if (!container || this._completedTable) return;
            
            const self = this;
            this._completedTable = new Tabulator(container, {
                data: this.completedNegotiations,
                layout: "fitColumns",
                height: "200px",
                placeholder: "No completed negotiations",
                selectableRows: 1,
                columns: [
                    { title: "ID", field: "id", width: 70, resizable: false, formatter: (cell) => {
                        const id = cell.getValue();
                        return `<code style="font-size: 11px; cursor: pointer;" title="Click to copy: ${id}" onclick="navigator.clipboard.writeText('${id}'); event.stopPropagation();">${id.substring(0, 6)}...</code>`;
                    } },
                    { title: "Scenario", field: "scenario", widthGrow: 2, minWidth: 100, sorter: "string" },
                    { title: "Negotiators", field: "negotiator_names", widthGrow: 2, minWidth: 120, formatter: (cell, params, onRendered) => {
                        const row = cell.getRow().getData();
                        return self.formatNegotiatorBadges(row.negotiator_names, row.negotiator_colors);
                    }, headerSort: false },
                    { title: "Steps", field: "step", width: 55, hozAlign: "center", resizable: false, sorter: "number", formatter: (cell) => {
                        const row = cell.getRow().getData();
                        return row.step || row.offers?.length || '-';
                    } },
                    { title: "Result", field: "agreement", width: 85, hozAlign: "center", resizable: false, formatter: (cell) => {
                        return self.formatResultBadge(cell.getRow().getData());
                    } },
                    { title: "Utilities", field: "final_utilities", widthGrow: 1, minWidth: 100, formatter: (cell, params, onRendered) => {
                        const row = cell.getRow().getData();
                        return self.formatUtilities(row.final_utilities, row.negotiator_colors);
                    }, headerSort: false }
                ]
            });
            this._completedTable.on("rowClick", function(e, row) {
                self.selectNegotiation(row.getData());
            });
        },
        
        // Initialize saved negotiations table
        initSavedTable() {
            const container = document.getElementById('saved-negotiations-table');
            if (!container || this._savedTable) return;
            
            const self = this;
            this._savedTable = new Tabulator(container, {
                data: this.savedNegotiations,
                layout: "fitColumns",
                height: "300px",
                placeholder: "No saved negotiations",
                selectableRows: 1,
                columns: [
                    { title: "ID", field: "id", width: 70, resizable: false, formatter: (cell) => {
                        const id = cell.getValue();
                        return `<code style="font-size: 11px; cursor: pointer;" title="Click to copy: ${id}" onclick="navigator.clipboard.writeText('${id}'); event.stopPropagation();">${id.substring(0, 6)}...</code>`;
                    } },
                    { title: "Scenario", field: "scenario_name", widthGrow: 2, minWidth: 100, sorter: "string" },
                    { title: "Negotiators", field: "negotiator_names", widthGrow: 2, minWidth: 120, formatter: (cell, params, onRendered) => {
                        const row = cell.getRow().getData();
                        return self.formatNegotiatorBadges(row.negotiator_names, row.negotiator_colors);
                    }, headerSort: false },
                    { title: "Steps", field: "n_offers", width: 55, hozAlign: "center", resizable: false, sorter: "number", formatter: (cell) => {
                        return cell.getValue() || '-';
                    } },
                    { title: "Result", field: "has_agreement", width: 85, hozAlign: "center", resizable: false, formatter: (cell) => {
                        const row = cell.getRow().getData();
                        if (row.has_agreement) {
                            return '<span class="badge badge-success badge-sm">Agreement</span>';
                        } else if (row.error) {
                            return '<span class="badge badge-danger badge-sm">Error</span>';
                        } else {
                            return `<span class="badge badge-warning badge-sm">${row.end_reason || 'No Agr.'}</span>`;
                        }
                    } },
                    { title: "Tags", field: "tags", width: 80, resizable: false, formatter: (cell) => {
                        const tags = cell.getValue() || [];
                        if (tags.length === 0) return '<span class="text-muted">-</span>';
                        return tags.map(t => `<span class="badge badge-neutral badge-sm">${t}</span>`).join(' ');
                    }, headerSort: false },
                    { title: "Date", field: "end_time", width: 80, hozAlign: "center", resizable: false, sorter: "datetime", formatter: (cell) => {
                        const val = cell.getValue();
                        if (!val) return '-';
                        const date = new Date(val);
                        return date.toLocaleDateString();
                    } },
                    { title: "", field: "actions", width: 75, hozAlign: "center", headerSort: false, resizable: false, formatter: (cell) => {
                        const row = cell.getRow().getData();
                        const archiveIcon = row.archived 
                            ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M3 10v11h18V10"/><path d="M21 3H3v7h18V3z"/><path d="M10 14h4"/></svg>`
                            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 8v13H3V8"/><path d="M23 3H1v5h22V3z"/><path d="M10 12h4"/></svg>`;
                        const archiveTitle = row.archived ? 'Unarchive' : 'Archive';
                        return `<div style="display: flex; gap: 4px; justify-content: center;">
                            <button class="btn btn-ghost btn-xs tag-btn" title="Edit Tags" style="padding: 2px 4px;">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                                    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                                    <line x1="7" y1="7" x2="7.01" y2="7"/>
                                </svg>
                            </button>
                            <button class="btn btn-ghost btn-xs archive-btn" title="${archiveTitle}" style="padding: 2px 4px;">
                                ${archiveIcon.replace(/width="14" height="14"/g, 'width="12" height="12"')}
                            </button>
                            <button class="btn btn-ghost btn-xs delete-btn" title="Delete" style="padding: 2px 4px;">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg>
                            </button>
                        </div>`;
                    }, cellClick: (e, cell) => {
                        e.stopPropagation();
                        const row = cell.getRow().getData();
                        if (e.target.closest('.delete-btn')) {
                            self.deleteSavedNegotiation(row.id);
                        } else if (e.target.closest('.archive-btn')) {
                            self.toggleArchiveNegotiation(row.id, row.archived);
                        } else if (e.target.closest('.tag-btn')) {
                            self.openTagEditor(row);
                        }
                    } }
                ],
                rowFormatter: (row) => {
                    const data = row.getData();
                    if (data.archived) {
                        row.getElement().style.opacity = '0.6';
                    }
                }
            });
            this._savedTable.on("rowClick", function(e, row) {
                // Don't trigger row click if clicking action buttons
                if (e.target.closest('.delete-btn') || e.target.closest('.archive-btn') || e.target.closest('.tag-btn')) return;
                self.loadAndSelectSavedNegotiation(row.getData().id);
            });
        },
        
        // Update running table data
        updateRunningTable() {
            if (this._runningTable) {
                this._runningTable.replaceData(this.runningNegotiations);
            }
        },
        
        // Update completed table data
        updateCompletedTable() {
            if (this._completedTable) {
                this._completedTable.replaceData(this.completedNegotiations);
            }
        },
        
        // Update saved table data
        updateSavedTable() {
            if (this._savedTable) {
                this._savedTable.replaceData(this.savedNegotiations);
            }
        },
        
        // Return to tournament view from a negotiation
        returnToTournament() {
            // Clear current negotiation
            this.currentNegotiation = null;
            // Switch to tournaments page
            this.currentPage = 'tournaments';
            // If we have a stored tournament reference, restore it
            if (this._returnToTournament) {
                this.selectedTournament = this._returnToTournament;
                this._returnToTournament = null;
            }
        },
        
        // Load saved negotiations from disk
        async loadSavedNegotiations() {
            this.savedNegotiationsLoading = true;
            try {
                const includeArchived = this.showArchivedNegotiations ? 'true' : 'false';
                const response = await fetch(`/api/negotiation/saved/list?include_archived=${includeArchived}`);
                const data = await response.json();
                let negotiations = data.negotiations || [];
                
                // Apply tag filter if set
                if (this.tagFilter) {
                    negotiations = negotiations.filter(n => 
                        n.tags && n.tags.includes(this.tagFilter)
                    );
                }
                
                this.savedNegotiations = negotiations;
            } catch (e) {
                console.error('Failed to load saved negotiations:', e);
            } finally {
                this.savedNegotiationsLoading = false;
            }
        },
        
        // Load available tags
        async loadAvailableTags() {
            try {
                const response = await fetch('/api/negotiation/tags');
                const data = await response.json();
                this.availableTags = data.tags || [];
            } catch (e) {
                console.error('Failed to load tags:', e);
            }
        },
        
        // Toggle archive state for a negotiation
        async toggleArchiveNegotiation(sessionId, isArchived) {
            try {
                const endpoint = isArchived ? 'unarchive' : 'archive';
                await fetch(`/api/negotiation/saved/${sessionId}/${endpoint}`, { method: 'POST' });
                // Reload the list
                await this.loadSavedNegotiations();
            } catch (e) {
                console.error('Failed to toggle archive:', e);
            }
        },
        
        // Tag editor state
        tagEditorNegotiation: null,
        tagEditorTags: [],
        newTagInput: '',
        
        // Open tag editor for a negotiation
        openTagEditor(negotiation) {
            this.tagEditorNegotiation = negotiation;
            this.tagEditorTags = [...(negotiation.tags || [])];
            this.newTagInput = '';
        },
        
        // Close tag editor
        closeTagEditor() {
            this.tagEditorNegotiation = null;
            this.tagEditorTags = [];
            this.newTagInput = '';
        },
        
        // Add a new tag in the editor
        addNewTag() {
            const tag = this.newTagInput.trim();
            if (tag && !this.tagEditorTags.includes(tag)) {
                this.tagEditorTags.push(tag);
            }
            this.newTagInput = '';
        },
        
        // Remove a tag in the editor
        removeTagFromEditor(tag) {
            this.tagEditorTags = this.tagEditorTags.filter(t => t !== tag);
        },
        
        // Save tags from editor
        async saveTagsFromEditor() {
            if (!this.tagEditorNegotiation) return;
            
            try {
                await fetch(`/api/negotiation/saved/${this.tagEditorNegotiation.id}/tags`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tags: this.tagEditorTags })
                });
                
                // Update local state
                const neg = this.savedNegotiations.find(n => n.id === this.tagEditorNegotiation.id);
                if (neg) {
                    neg.tags = [...this.tagEditorTags];
                }
                
                // Reload tags list
                await this.loadAvailableTags();
                
                this.closeTagEditor();
                this.updateSavedTable();
            } catch (e) {
                console.error('Failed to save tags:', e);
            }
        },
        
        // Load and select a saved negotiation
        async loadAndSelectSavedNegotiation(sessionId) {
            try {
                const response = await fetch(`/api/negotiation/saved/${sessionId}`);
                if (!response.ok) throw new Error('Failed to load negotiation');
                const negData = await response.json();
                
                // Transform to match our negotiation format
                const neg = {
                    id: negData.id,
                    scenario: negData.scenario_name,
                    scenario_path: negData.scenario_path,
                    mechanism_type: negData.mechanism_type,
                    negotiator_names: negData.negotiator_names,
                    negotiator_types: negData.negotiator_types,
                    negotiator_colors: negData.negotiator_colors,
                    issue_names: negData.issue_names,
                    step: negData.current_step,
                    n_steps: negData.n_steps,
                    time_limit: negData.time_limit,
                    offers: negData.offers || [],
                    outcome_space_data: negData.outcome_space_data,
                    agreement: negData.agreement,
                    final_utilities: negData.final_utilities,
                    end_reason: negData.end_reason,
                    error: negData.error,
                    start_time: negData.start_time,
                    end_time: negData.end_time,
                    // Mark as loaded from disk
                    _fromSaved: true
                };
                
                this.selectNegotiation(neg);
            } catch (e) {
                console.error('Failed to load saved negotiation:', e);
            }
        },
        
        // Delete a saved negotiation
        async deleteSavedNegotiation(sessionId) {
            if (!confirm('Delete this saved negotiation?')) return;
            
            try {
                await fetch(`/api/negotiation/saved/${sessionId}`, { method: 'DELETE' });
                this.savedNegotiations = this.savedNegotiations.filter(n => n.id !== sessionId);
            } catch (e) {
                console.error('Failed to delete negotiation:', e);
            }
        },
        
        // Clear all saved negotiations
        async clearSavedNegotiations() {
            if (!confirm('Delete ALL saved negotiations? This cannot be undone.')) return;
            
            try {
                await fetch('/api/negotiation/saved', { method: 'DELETE' });
                this.savedNegotiations = [];
            } catch (e) {
                console.error('Failed to clear negotiations:', e);
            }
        },
        
        // Get colors based on theme
        getPlotColors() {
            const isDark = document.documentElement.classList.contains('dark-mode') || 
                           document.body.classList.contains('dark-mode');
            return {
                textColor: isDark ? '#b6c2cf' : '#172b4d',
                gridColor: isDark ? '#38414a' : '#dfe1e6',
                bgColor: 'transparent',
                outcomeColor: isDark ? 'rgba(100, 120, 140, 0.3)' : 'rgba(100, 120, 140, 0.4)',
                // Pareto points use black/white
                paretoColor: isDark ? '#ffffff' : '#000000',
                // Distinct colors for special solution points (hollow markers)
                nashColor: isDark ? '#ff6b6b' : '#dc2626',           // Red
                kalaiColor: isDark ? '#4ecdc4' : '#0891b2',          // Cyan/Teal
                kalaiSmorodinskyColor: isDark ? '#a855f7' : '#7c3aed', // Purple
                maxWelfareColor: isDark ? '#fbbf24' : '#d97706',     // Amber/Orange
                agreementColor: '#10b981'
            };
        },
        
        // Get negotiator colors - avoid black/white as they're used for special points
        getNegotiatorColors() {
            const neg = this.currentNegotiation;
            // Colors that avoid black/white (reserved for Pareto/Nash/Kalai/Welfare)
            const defaultColors = neg?.negotiator_colors || ['#4a6fa5', '#22a06b', '#e65100', '#7b1fa2', '#00695c', '#c62828', '#1565c0', '#6a1b9a'];
            const isColorBlind = document.documentElement.classList.contains('color-blind-mode');
            const isDark = document.documentElement.classList.contains('dark-mode');
            return isColorBlind ? (isDark ? COLORBLIND_COLORS_DARK : COLORBLIND_COLORS) : defaultColors;
        },
        
        // Calculate negotiation progress (0-1)
        // For TAU mechanism: max(relative_time, step/(n_outcomes+1))
        // For others: relative_time (falls back to step/n_steps if no relative_time)
        getNegotiationProgress(neg) {
            if (!neg) return 0;
            
            const relativeTime = neg.relative_time || 0;
            const step = neg.step || 0;
            const nSteps = neg.n_steps;
            const nOutcomes = neg.n_outcomes;
            const mechType = neg.mechanism_type || '';
            
            // For TAU mechanism: use max of relative_time and step-based progress
            if (mechType.includes('TAU') && nOutcomes && nOutcomes > 0) {
                const stepProgress = step / (nOutcomes + 1);
                return Math.min(1, Math.max(relativeTime, stepProgress));
            }
            
            // For other mechanisms: prefer relative_time, fallback to step/n_steps
            if (relativeTime > 0) {
                return Math.min(1, relativeTime);
            }
            
            // Fallback to step-based progress if n_steps is defined
            if (nSteps && nSteps > 0) {
                return Math.min(1, step / nSteps);
            }
            
            // No progress info available
            return 0;
        },
        
        // Save panel collapse state
        savePanelCollapsed() {
            if (window.LayoutManager) {
                window.LayoutManager.setPanelCollapsedAll(this.panelCollapsed);
            }
        },
        
        // Column resize start
        startColumnResize(event) {
            event.preventDefault();
            const leftCol = this.$refs.leftColumn;
            if (!leftCol) return;
            
            this.resizeState = {
                active: true,
                type: 'column',
                startX: event.clientX,
                startY: 0,
                startWidth: leftCol.offsetWidth,
                startHeight: 0
            };
            
            this.$refs.columnResizer?.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        },
        
        // Panel resize start
        startPanelResize(event, resizeType) {
            event.preventDefault();
            this.resizeState = {
                active: true,
                type: resizeType,
                startX: event.clientX,
                startY: event.clientY,
                startWidth: 0,
                startHeight: 0
            };
            
            // Store starting heights
            const panels = {
                'info-history': [this.$refs.panelInfo, this.$refs.panelHistory],
                'history-histogram': [this.$refs.panelHistory, this.$refs.panelHistogram],
                'histogram-result': [this.$refs.panelHistogram, this.$refs.panelResult],
                'history-result': [this.$refs.panelHistory, this.$refs.panelResult],
                'utility2d-timeline': [this.$refs.panel2dUtility, this.$refs.panelTimeline]
            };
            
            const [panel1, panel2] = panels[resizeType] || [];
            if (panel1 && panel2) {
                this.resizeState.panel1Height = panel1.offsetHeight;
                this.resizeState.panel2Height = panel2.offsetHeight;
                this.resizeState.panel1 = panel1;
                this.resizeState.panel2 = panel2;
            }
            
            event.target.classList.add('dragging');
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
        },
        
        // Handle resize move
        handleResizeMove(event) {
            if (!this.resizeState.active) return;
            
            if (this.resizeState.type === 'column') {
                const delta = event.clientX - this.resizeState.startX;
                const newWidth = Math.max(200, Math.min(window.innerWidth * 0.85, this.resizeState.startWidth + delta));
                const leftCol = this.$refs.leftColumn;
                if (leftCol) {
                    leftCol.style.flex = `0 0 ${newWidth}px`;
                }
            } else if (this.resizeState.panel1 && this.resizeState.panel2) {
                const delta = event.clientY - this.resizeState.startY;
                const panel1 = this.resizeState.panel1;
                const panel2 = this.resizeState.panel2;
                
                const newHeight1 = Math.max(40, this.resizeState.panel1Height + delta);
                const newHeight2 = Math.max(40, this.resizeState.panel2Height - delta);
                
                // Use flex basis instead of fixed height for flexible panels
                const totalFlex = (newHeight1 + newHeight2) / 100;
                panel1.style.flex = `1 1 ${(newHeight1 / totalFlex)}%`;
                panel2.style.flex = `1 1 ${(newHeight2 / totalFlex)}%`;
            }
        },
        
        // Handle resize end
        handleResizeEnd() {
            if (!this.resizeState.active) return;
            
            // Save column width to server via LayoutManager
            if (this.resizeState.type === 'column') {
                const leftCol = this.$refs.leftColumn;
                if (leftCol && window.LayoutManager) {
                    const width = leftCol.style.flex.replace('0 0 ', '');
                    window.LayoutManager.setLeftColumnWidth(width);
                }
            }
            
            // Remove dragging classes
            document.querySelectorAll('.dragging').forEach(el => el.classList.remove('dragging'));
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            
            this.resizeState = { active: false, type: null, startX: 0, startY: 0, startWidth: 0, startHeight: 0 };
            
            // Resize plots after panel resize
            this.$nextTick(() => {
                if (this.currentNegotiation) {
                    // Force Plotly to resize to new container dimensions
                    const outcomeSpacePlot = document.getElementById('outcome-space-plot');
                    if (outcomeSpacePlot && window.Plotly) {
                        Plotly.Plots.resize(outcomeSpacePlot);
                    }
                    
                    // Timeline plots need to be reinitialized due to dynamic subplot heights
                    this.initUtilityTimelinePlots();
                    
                    // Histogram: resize if initialized, otherwise try to initialize
                    const histogramPlot = document.getElementById('histogram-plot');
                    if (histogramPlot && window.Plotly && window.histogramPlotInitialized) {
                        Plotly.Plots.resize(histogramPlot);
                    } else if (!window.histogramPlotInitialized) {
                        // Plot wasn't initialized (maybe panel was too small), try now
                        this.initHistogramPlot();
                    }
                }
            });
        },
        
        // Apply utility view axis changes
        applyUtilityViewAxes() {
            window.outcomeSpacePlotInitialized = false;
            this.initOutcomeSpacePlot();
        },
        
        // Initialize outcome space plot (2D Utility View)
        async initOutcomeSpacePlot() {
            const plotDiv = document.getElementById('outcome-space-plot');
            if (!plotDiv) return;
            
            // Don't try to render if panel is collapsed or hidden
            if (plotDiv.offsetParent === null || plotDiv.clientWidth === 0) {
                window.outcomeSpacePlotInitialized = false;
                return;
            }
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.outcome_space_data) {
                window.outcomeSpacePlotInitialized = false;
                return;
            }
            
            try {
                const colors = this.getPlotColors();
                const osd = neg.outcome_space_data;
                const negColors = this.getNegotiatorColors();
                const isColorBlind = document.documentElement.classList.contains('color-blind-mode');
            
            // Get axis indices from panel state
            const xIdx = this.panelState.utilityView.xAxis;
            const yIdx = this.panelState.utilityView.yAxis;
            
            const traces = [];
            
            // 1. All outcomes - use scattergl (WebGL) for large outcome spaces
            if (osd.outcome_utilities && osd.outcome_utilities.length > 0) {
                traces.push({
                    x: osd.outcome_utilities.map(u => u[xIdx] || 0),
                    y: osd.outcome_utilities.map(u => u[yIdx] || 0),
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Outcomes',
                    marker: { color: colors.outcomeColor, size: 3, opacity: 0.5 },
                    hoverinfo: 'skip'
                });
            }
            
            // 2. Pareto frontier (markers only, no lines, using special point color) - use scattergl
            if (osd.pareto_utilities && osd.pareto_utilities.length > 0) {
                traces.push({
                    x: osd.pareto_utilities.map(u => u[xIdx] || 0),
                    y: osd.pareto_utilities.map(u => u[yIdx] || 0),
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Pareto Frontier',
                    marker: { color: colors.paretoColor, size: 6, opacity: 0.7 }
                });
            }
            
            // 3. Nash point (triangle-left marker, hollow) - use scattergl
            if (osd.nash_point && osd.nash_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.nash_point[xIdx]],
                    y: [osd.nash_point[yIdx]],
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Nash',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 14, 
                        symbol: 'triangle-left',
                        line: { color: colors.nashColor, width: 2.5 }
                    }
                });
            }
            
            // 4. Kalai point (triangle-down marker, hollow) - use scattergl
            if (osd.kalai_point && osd.kalai_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.kalai_point[xIdx]],
                    y: [osd.kalai_point[yIdx]],
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Kalai',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 14, 
                        symbol: 'triangle-down',
                        line: { color: colors.kalaiColor, width: 2.5 }
                    }
                });
            }
            
            // 5. Kalai-Smorodinsky point (triangle-up marker, hollow) - use scattergl
            if (osd.kalai_smorodinsky_point && osd.kalai_smorodinsky_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.kalai_smorodinsky_point[xIdx]],
                    y: [osd.kalai_smorodinsky_point[yIdx]],
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Kalai-Smorodinsky',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 14, 
                        symbol: 'triangle-up',
                        line: { color: colors.kalaiSmorodinskyColor, width: 2.5 }
                    }
                });
            }
            
            // 6. Max welfare point (triangle-right marker, hollow) - use scattergl
            if (osd.max_welfare_point && osd.max_welfare_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.max_welfare_point[xIdx]],
                    y: [osd.max_welfare_point[yIdx]],
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Max Welfare',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 14, 
                        symbol: 'triangle-right',
                        line: { color: colors.maxWelfareColor, width: 2.5 }
                    }
                });
            }
            
            // 7. Offer traces per negotiator - always create traces (even if empty) for incremental updates
            // Use scattergl for WebGL acceleration
            const offers = neg.offers || [];
            const numAgents = neg.negotiator_names?.length || 2;
            for (let i = 0; i < numAgents; i++) {
                // Use Number() for type coercion (proposer_index may be string or number from JSON)
                const agentOffers = offers.filter(o => Number(o.proposer_index) === i);
                traces.push({
                    x: agentOffers.map(o => o.utilities[xIdx] || 0),
                    y: agentOffers.map(o => o.utilities[yIdx] || 0),
                    type: 'scattergl',
                    mode: 'lines+markers',
                    name: neg.negotiator_names?.[i] || `Agent ${i + 1}`,
                    line: { 
                        color: negColors[i % negColors.length], 
                        width: 2,
                        dash: isColorBlind ? LINE_DASHES[i % LINE_DASHES.length] : 'solid'
                    },
                    marker: { 
                        color: negColors[i % negColors.length], 
                        size: isColorBlind ? 8 : 6,
                        symbol: isColorBlind ? MARKER_SYMBOLS[i % MARKER_SYMBOLS.length] : 'circle'
                    }
                });
            }
            
            // 8. Agreement point - use scattergl
            if (neg.agreement && neg.final_utilities && neg.final_utilities.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [neg.final_utilities[xIdx]],
                    y: [neg.final_utilities[yIdx]],
                    type: 'scattergl',
                    mode: 'markers',
                    name: 'Agreement',
                    marker: { color: colors.agreementColor, size: 16, symbol: 'star', line: { color: '#fff', width: 2 } }
                });
            }
            
            const layout = {
                xaxis: { 
                    title: { text: neg.negotiator_names?.[xIdx] || `Agent ${xIdx + 1}`, font: { color: colors.textColor } },
                    tickfont: { color: colors.textColor },
                    gridcolor: colors.gridColor,
                    linecolor: colors.gridColor,
                    zerolinecolor: colors.gridColor
                },
                yaxis: { 
                    title: { text: neg.negotiator_names?.[yIdx] || `Agent ${yIdx + 1}`, font: { color: colors.textColor } },
                    tickfont: { color: colors.textColor },
                    gridcolor: colors.gridColor,
                    linecolor: colors.gridColor,
                    zerolinecolor: colors.gridColor
                },
                margin: { t: 30, r: 30, b: 50, l: 50 },
                legend: { orientation: 'h', y: -0.15, font: { color: colors.textColor, size: 10 } },
                paper_bgcolor: colors.bgColor,
                plot_bgcolor: colors.bgColor,
                font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 11, color: colors.textColor }
            };
            
            const config = {
                responsive: true,
                displayModeBar: 'hover',
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                toImageButtonOptions: { format: 'png', filename: '2d-utility-view', scale: 2 }
            };
            
                await Plotly.react(plotDiv, traces, layout, config);
                window.outcomeSpacePlotInitialized = true;
            } catch (e) {
                console.warn('Failed to initialize outcome space plot:', e);
                window.outcomeSpacePlotInitialized = false;
            }
        },
        
        // Update 2D plot with new offer (incremental update using extendTraces)
        async updateOutcomeSpacePlot(offer) {
            if (!window.outcomeSpacePlotInitialized) {
                await this.initOutcomeSpacePlot();
                return;
            }
            
            const plotDiv = document.getElementById('outcome-space-plot');
            if (!plotDiv || !plotDiv.data) return;
            
            const neg = this.currentNegotiation;
            if (!neg) return;
            
            const xIdx = this.panelState.utilityView.xAxis;
            const yIdx = this.panelState.utilityView.yAxis;
            const proposerIndex = Number(offer.proposer_index);
            
            // Find the trace index for this proposer
            // Trace order: outcomes, pareto, nash, kalai, ks, max_welfare, then negotiator traces
            const numAgents = neg.negotiator_names?.length || 2;
            const osd = neg.outcome_space_data || {};
            
            // Count fixed traces (outcomes + special points that exist)
            let fixedTraces = 1; // outcomes
            if (osd.pareto_utilities?.length > 0) fixedTraces++;
            if (osd.nash_point?.length > 0) fixedTraces++;
            if (osd.kalai_point?.length > 0) fixedTraces++;
            if (osd.kalai_smorodinsky_point?.length > 0) fixedTraces++;
            if (osd.max_welfare_point?.length > 0) fixedTraces++;
            
            const traceIndex = fixedTraces + proposerIndex;
            
            // Check if trace exists
            if (traceIndex < plotDiv.data.length) {
                try {
                    await Plotly.extendTraces(plotDiv, {
                        x: [[offer.utilities[xIdx] || 0]],
                        y: [[offer.utilities[yIdx] || 0]]
                    }, [traceIndex]);
                } catch (e) {
                    // Fallback to full rebuild if extend fails
                    await this.initOutcomeSpacePlot();
                }
            } else {
                // Trace doesn't exist yet, do full rebuild
                await this.initOutcomeSpacePlot();
            }
        },
        
        // Batched update for outcome space plot - processes multiple offers at once
        async updateOutcomeSpacePlotBatched(offers) {
            if (!offers || offers.length === 0) return;
            
            if (!window.outcomeSpacePlotInitialized) {
                await this.initOutcomeSpacePlot();
                return;
            }
            
            const plotDiv = document.getElementById('outcome-space-plot');
            if (!plotDiv || !plotDiv.data) return;
            
            const neg = this.currentNegotiation;
            if (!neg) return;
            
            const xIdx = this.panelState.utilityView.xAxis;
            const yIdx = this.panelState.utilityView.yAxis;
            const numAgents = neg.negotiator_names?.length || 2;
            const osd = neg.outcome_space_data || {};
            
            // Count fixed traces (outcomes + special points that exist)
            let fixedTraces = 1; // outcomes
            if (osd.pareto_utilities?.length > 0) fixedTraces++;
            if (osd.nash_point?.length > 0) fixedTraces++;
            if (osd.kalai_point?.length > 0) fixedTraces++;
            if (osd.kalai_smorodinsky_point?.length > 0) fixedTraces++;
            if (osd.max_welfare_point?.length > 0) fixedTraces++;
            
            // Group offers by proposer
            const offersByProposer = {};
            for (const offer of offers) {
                const proposerIndex = Number(offer.proposer_index);
                if (!offersByProposer[proposerIndex]) {
                    offersByProposer[proposerIndex] = { x: [], y: [] };
                }
                offersByProposer[proposerIndex].x.push(offer.utilities[xIdx] || 0);
                offersByProposer[proposerIndex].y.push(offer.utilities[yIdx] || 0);
            }
            
            // Batch update all traces at once
            const traceIndices = [];
            const updateData = { x: [], y: [] };
            
            for (const [proposerStr, data] of Object.entries(offersByProposer)) {
                const proposerIndex = parseInt(proposerStr);
                const traceIndex = fixedTraces + proposerIndex;
                if (traceIndex < plotDiv.data.length) {
                    traceIndices.push(traceIndex);
                    updateData.x.push(data.x);
                    updateData.y.push(data.y);
                }
            }
            
            if (traceIndices.length > 0) {
                try {
                    await Plotly.extendTraces(plotDiv, updateData, traceIndices);
                } catch (e) {
                    // Fallback to full rebuild if extend fails
                    await this.initOutcomeSpacePlot();
                }
            }
        },
        
        resetPlotView() {
            const plotDiv = document.getElementById('outcome-space-plot');
            if (plotDiv) {
                Plotly.relayout(plotDiv, { 'xaxis.autorange': true, 'yaxis.autorange': true });
            }
        },
        
        // Initialize utility timeline plots - N plots for N negotiators (full) or single plot (simplified)
        async initUtilityTimelinePlots() {
            const container = document.getElementById('utility-timeline-container');
            if (!container) return;
            
            // Don't try to render if panel is collapsed or hidden
            if (container.offsetParent === null || container.clientWidth === 0) {
                window.timelinePlotsInitialized = false;
                return;
            }
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.offers || neg.offers.length === 0) {
                container.innerHTML = '';
                window.timelinePlotsInitialized = false;
                return;
            }
            
            try {
                const colors = this.getPlotColors();
                const negColors = this.getNegotiatorColors();
                const numAgents = neg.negotiator_names?.length || 2;
                const isColorBlind = document.documentElement.classList.contains('color-blind-mode');
                const xAxisType = this.panelState.timeline.xAxis;
                
                // Get X values based on selected axis type
                const getXValue = (offer) => {
                    switch (xAxisType) {
                        case 'time': return offer.time || 0;
                        case 'relative_time': return offer.relative_time || 0;
                        default: return offer.step;
                    }
                };
                
                const xAxisTitle = xAxisType === 'time' ? 'Time (s)' : (xAxisType === 'relative_time' ? 'Relative Time' : 'Step');
                
                // Clear and rebuild container
                container.innerHTML = '';
                
                if (this.timelineSimplifiedView) {
                    // SIMPLIFIED VIEW: Single plot showing each agent's own utility for their offers
                    const plotId = 'timeline-plot-simplified';
                    const plotWrapper = document.createElement('div');
                    plotWrapper.style.cssText = 'flex: 1; min-height: 0; height: 100%;';
                    plotWrapper.innerHTML = `<div id="${plotId}" style="width: 100%; height: 100%;"></div>`;
                    container.appendChild(plotWrapper);
                    
                    const traces = [];
                    
                    // Each agent gets one trace showing their own utility for their own offers
                    for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                        const agentOffers = neg.offers.filter(o => Number(o.proposer_index) === agentIdx);
                        
                        const xValues = agentOffers.map(getXValue);
                        const yValues = agentOffers.map(o => o.utilities[agentIdx] || 0);
                        
                        traces.push({
                            x: xValues,
                            y: yValues,
                            type: 'scatter',
                            mode: 'lines+markers',
                            name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
                            line: { 
                                color: negColors[agentIdx % negColors.length], 
                                width: 2,
                                dash: isColorBlind ? LINE_DASHES[agentIdx % LINE_DASHES.length] : 'solid'
                            },
                            marker: {
                                color: negColors[agentIdx % negColors.length],
                                size: 6,
                                symbol: isColorBlind ? MARKER_SYMBOLS[agentIdx % MARKER_SYMBOLS.length] : 'circle'
                            }
                        });
                    }
                    
                    // Add agreement markers if exists
                    if (neg.agreement && neg.final_utilities) {
                        const lastOffer = neg.offers[neg.offers.length - 1];
                        for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                            if (neg.final_utilities.length > agentIdx) {
                                traces.push({
                                    x: [getXValue(lastOffer)],
                                    y: [neg.final_utilities[agentIdx]],
                                    type: 'scatter',
                                    mode: 'markers',
                                    name: agentIdx === 0 ? 'Agreement' : undefined,
                                    showlegend: agentIdx === 0,
                                    marker: { color: colors.agreementColor, size: 14, symbol: 'star', line: { color: '#fff', width: 1 } }
                                });
                            }
                        }
                    }
                    
                    const layout = {
                        title: { 
                            text: 'Utility of Own Offers',
                            font: { size: 13, color: colors.textColor }
                        },
                        xaxis: { 
                            title: { text: xAxisTitle, font: { color: colors.textColor, size: 11 } },
                            tickfont: { color: colors.textColor, size: 10 },
                            gridcolor: colors.gridColor,
                            linecolor: colors.gridColor
                        },
                        yaxis: { 
                            title: { text: 'Utility', font: { color: colors.textColor, size: 11 } },
                            tickfont: { color: colors.textColor, size: 10 },
                            gridcolor: colors.gridColor,
                            linecolor: colors.gridColor
                        },
                        margin: { t: 40, r: 20, b: 50, l: 50 },
                        showlegend: true,
                        legend: { orientation: 'h', y: -0.15, x: 0.5, xanchor: 'center', font: { color: colors.textColor, size: 10 } },
                        paper_bgcolor: colors.bgColor,
                        plot_bgcolor: colors.bgColor,
                        font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 11, color: colors.textColor }
                    };
                    
                    const config = {
                        responsive: true,
                        displayModeBar: 'hover',
                        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                        toImageButtonOptions: { format: 'png', filename: 'utility-timeline-simplified', scale: 2 }
                    };
                    
                    await Plotly.newPlot(plotId, traces, layout, config);
                } else {
                    // FULL VIEW: N plots, one per negotiator
                    // Calculate height per plot based on container
                    const containerHeight = container.clientHeight || 300;
                    const plotHeight = Math.max(120, Math.floor((containerHeight - (numAgents - 1) * 8) / numAgents));
                    
                    for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                        const plotId = `timeline-plot-${agentIdx}`;
                        const plotWrapper = document.createElement('div');
                        plotWrapper.style.cssText = `flex: 0 0 ${plotHeight}px; min-height: ${plotHeight}px; height: ${plotHeight}px;`;
                        plotWrapper.innerHTML = `<div id="${plotId}" style="width: 100%; height: 100%;"></div>`;
                        container.appendChild(plotWrapper);
                        
                        const traces = [];
                        
                        // Create N series per plot - each series j shows utility of offers from agent j for agent agentIdx
                        for (let proposerIdx = 0; proposerIdx < numAgents; proposerIdx++) {
                            const proposerOffers = neg.offers.filter(o => Number(o.proposer_index) === proposerIdx);
                            
                            const xValues = proposerOffers.map(getXValue);
                            const yValues = proposerOffers.map(o => o.utilities[agentIdx] || 0);
                            
                            // Own offers get thick solid line, others get dashed
                            const isOwnOffers = proposerIdx === agentIdx;
                            
                            traces.push({
                                x: xValues,
                                y: yValues,
                                type: 'scatter',
                                mode: 'lines',
                                name: neg.negotiator_names?.[proposerIdx] || `Agent ${proposerIdx + 1}`,
                                line: { 
                                    color: negColors[proposerIdx % negColors.length], 
                                    width: isOwnOffers ? 3 : 1.5,
                                    dash: isOwnOffers ? 'solid' : LINE_DASHES[(proposerIdx + 1) % LINE_DASHES.length]
                                }
                            });
                        }
                        
                        // Add agreement marker if exists
                        if (neg.agreement && neg.final_utilities && neg.final_utilities.length > agentIdx) {
                            const lastOffer = neg.offers[neg.offers.length - 1];
                            traces.push({
                                x: [getXValue(lastOffer)],
                                y: [neg.final_utilities[agentIdx]],
                                type: 'scatter',
                                mode: 'markers',
                                name: 'Agreement',
                                showlegend: agentIdx === 0,
                                marker: { color: colors.agreementColor, size: 10, symbol: 'star', line: { color: '#fff', width: 1 } }
                            });
                        }
                        
                        // Only show legend on the last plot to avoid overlap
                        const isLastPlot = agentIdx === numAgents - 1;
                        
                        const layout = {
                            title: { 
                                text: `${neg.negotiator_names?.[agentIdx] || 'Agent ' + (agentIdx + 1)}'s Utility`,
                                font: { size: 11, color: colors.textColor }
                            },
                            xaxis: { 
                                title: { text: isLastPlot ? xAxisTitle : '', font: { color: colors.textColor, size: 9 } },
                                tickfont: { color: colors.textColor, size: 8 },
                                gridcolor: colors.gridColor,
                                linecolor: colors.gridColor
                            },
                            yaxis: { 
                                title: { text: 'Utility', font: { color: colors.textColor, size: 9 } },
                                tickfont: { color: colors.textColor, size: 8 },
                                gridcolor: colors.gridColor,
                                linecolor: colors.gridColor
                            },
                            margin: { t: 25, r: 15, b: isLastPlot ? 40 : 20, l: 35 },
                            showlegend: isLastPlot,
                            legend: { orientation: 'h', y: -0.35, x: 0.5, xanchor: 'center', font: { color: colors.textColor, size: 8 } },
                            paper_bgcolor: colors.bgColor,
                            plot_bgcolor: colors.bgColor,
                            font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 9, color: colors.textColor }
                        };
                        
                        const config = {
                            responsive: true,
                            displayModeBar: 'hover',
                            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                            toImageButtonOptions: { format: 'png', filename: `utility-timeline-${agentIdx}`, scale: 2 }
                        };
                        
                        await Plotly.newPlot(plotId, traces, layout, config);
                    }
                }
                
                window.timelinePlotsInitialized = true;
            } catch (e) {
                console.warn('Failed to initialize timeline plots:', e);
                window.timelinePlotsInitialized = false;
            }
        },
        
        async updateUtilityTimelinePlots(offer) {
            if (!window.timelinePlotsInitialized) {
                await this.initUtilityTimelinePlots();
                return;
            }
            
            const neg = this.currentNegotiation;
            if (!neg) return;
            
            const numAgents = neg.negotiator_names?.length || 2;
            const xAxisType = this.panelState.timeline.xAxis;
            
            // Get X value based on selected axis type
            const getXValue = (o) => {
                switch (xAxisType) {
                    case 'time': return o.time || 0;
                    case 'relative_time': return o.relative_time || 0;
                    default: return o.step;
                }
            };
            
            const xVal = getXValue(offer);
            const proposerIndex = Number(offer.proposer_index);
            
            // Build update promises for all timeline plots in parallel
            const updatePromises = [];
            
            for (let i = 0; i < numAgents; i++) {
                const plotDiv = document.getElementById(`timeline-plot-${i}`);
                if (!plotDiv || !plotDiv.data) continue;
                
                // Each timeline plot has N traces (one per proposer)
                // The trace index matches the proposer index
                if (proposerIndex < plotDiv.data.length) {
                    const yVal = offer.utilities[i] || 0;
                    updatePromises.push(
                        Plotly.extendTraces(plotDiv, {
                            x: [[xVal]],
                            y: [[yVal]]
                        }, [proposerIndex]).catch(() => null) // Ignore individual failures
                    );
                }
            }
            
            // Execute all updates in parallel
            if (updatePromises.length > 0) {
                try {
                    await Promise.all(updatePromises);
                } catch (e) {
                    // Fallback to full rebuild if all fail
                    await this.initUtilityTimelinePlots();
                }
            }
        },
        
        // Batched update for timeline plots - processes multiple offers at once
        async updateUtilityTimelinePlotsBatched(offers) {
            if (!offers || offers.length === 0) return;
            
            if (!window.timelinePlotsInitialized) {
                await this.initUtilityTimelinePlots();
                return;
            }
            
            const neg = this.currentNegotiation;
            if (!neg) return;
            
            const numAgents = neg.negotiator_names?.length || 2;
            const xAxisType = this.panelState.timeline.xAxis;
            
            // Get X value based on selected axis type
            const getXValue = (o) => {
                switch (xAxisType) {
                    case 'time': return o.time || 0;
                    case 'relative_time': return o.relative_time || 0;
                    default: return o.step;
                }
            };
            
            // Group offers by proposer with their x/y values
            const offersByProposer = {};
            for (const offer of offers) {
                const proposerIndex = Number(offer.proposer_index);
                if (!offersByProposer[proposerIndex]) {
                    offersByProposer[proposerIndex] = { x: [], utilities: [] };
                }
                offersByProposer[proposerIndex].x.push(getXValue(offer));
                offersByProposer[proposerIndex].utilities.push(offer.utilities);
            }
            
            // Update each agent's timeline plot with a single batched extendTraces call
            const updatePromises = [];
            
            for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                const plotDiv = document.getElementById(`timeline-plot-${agentIdx}`);
                if (!plotDiv || !plotDiv.data) continue;
                
                // Build batched update for this plot - all proposers at once
                const traceIndices = [];
                const updateData = { x: [], y: [] };
                
                for (const [proposerStr, data] of Object.entries(offersByProposer)) {
                    const proposerIndex = parseInt(proposerStr);
                    if (proposerIndex < plotDiv.data.length) {
                        traceIndices.push(proposerIndex);
                        updateData.x.push(data.x);
                        // Extract this agent's utility from each offer
                        updateData.y.push(data.utilities.map(u => u[agentIdx] || 0));
                    }
                }
                
                if (traceIndices.length > 0) {
                    updatePromises.push(
                        Plotly.extendTraces(plotDiv, updateData, traceIndices).catch(() => null)
                    );
                }
            }
            
            // Execute all plot updates in parallel
            if (updatePromises.length > 0) {
                try {
                    await Promise.all(updatePromises);
                } catch (e) {
                    // Fallback to full rebuild if all fail
                    await this.initUtilityTimelinePlots();
                }
            }
        },
        
        resetTimelinePlotView() {
            const neg = this.currentNegotiation;
            if (!neg) return;
            const numAgents = neg.negotiator_names?.length || 2;
            
            if (this.timelineSimplifiedView) {
                const plotDiv = document.getElementById('timeline-plot-simplified');
                if (plotDiv) {
                    Plotly.relayout(plotDiv, { 'xaxis.autorange': true, 'yaxis.autorange': true });
                }
            } else {
                for (let i = 0; i < numAgents; i++) {
                    const plotDiv = document.getElementById(`timeline-plot-${i}`);
                    if (plotDiv) {
                        Plotly.relayout(plotDiv, { 'xaxis.autorange': true, 'yaxis.autorange': true });
                    }
                }
            }
        },
        
        // Initialize histogram plot showing offer frequency per issue value
        async initHistogramPlot(retryCount = 0) {
            const container = document.getElementById('issue-frequency-container');
            if (!container) return;
            
            // Don't try to render if panel is collapsed or hidden
            // But retry a few times with delay in case the panel is still being rendered
            if (container.offsetParent === null || container.clientWidth === 0) {
                window.histogramPlotInitialized = false;
                // Retry up to 5 times with increasing delay (longer delays for later retries)
                if (retryCount < 5) {
                    setTimeout(() => this.initHistogramPlot(retryCount + 1), 150 * (retryCount + 1));
                }
                return;
            }
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.offers || neg.offers.length === 0) {
                container.innerHTML = '';
                window.histogramPlotInitialized = false;
                return;
            }
            
            try {
                const colors = this.getPlotColors();
                const negColors = this.getNegotiatorColors();
                const numAgents = neg.negotiator_names?.length || 2;
                
                // Determine if we have issue-based or enumerated outcome space
                const firstOffer = neg.offers[0]?.offer;
                const issueNames = neg.issue_names || (typeof firstOffer === 'object' && firstOffer !== null && !Array.isArray(firstOffer) 
                    ? Object.keys(firstOffer) 
                    : []);
                
                const isEnumerated = issueNames.length === 0;
                
                // Clear container and create plot div
                container.innerHTML = '<div id="histogram-plot" style="width: 100%; height: 100%;"></div>';
                const plotDiv = document.getElementById('histogram-plot');
                if (!plotDiv) return;
                
                if (isEnumerated) {
                    // Enumerated outcome space: single histogram of outcomes
                    const outcomeFreq = {};
                    
                    neg.offers.forEach(offer => {
                        const offerData = offer.offer;
                        const key = Array.isArray(offerData) 
                            ? offerData.join(', ')
                            : typeof offerData === 'object' 
                                ? JSON.stringify(offerData)
                                : String(offerData);
                        
                        if (!outcomeFreq[key]) {
                            outcomeFreq[key] = new Array(numAgents).fill(0);
                        }
                        outcomeFreq[key][offer.proposer_index]++;
                    });
                    
                    // Sort outcomes by total frequency
                    const outcomes = Object.keys(outcomeFreq).sort((a, b) => {
                        const totalA = outcomeFreq[a].reduce((s, v) => s + v, 0);
                        const totalB = outcomeFreq[b].reduce((s, v) => s + v, 0);
                        return totalB - totalA;
                    });
                    
                    // Limit to top 15 outcomes
                    const displayOutcomes = outcomes.slice(0, 15);
                    
                    // Create grouped bar traces per negotiator
                    const traces = [];
                    for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                        traces.push({
                            x: displayOutcomes,
                            y: displayOutcomes.map(o => outcomeFreq[o][agentIdx]),
                            type: 'bar',
                            name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
                            marker: { 
                                color: negColors[agentIdx % negColors.length],
                                opacity: 0.85
                            }
                        });
                    }
                    
                    const layout = {
                        barmode: 'group',
                        bargap: 0.15,
                        bargroupgap: 0.1,
                        margin: { t: 10, r: 10, b: 60, l: 35 },
                        paper_bgcolor: 'transparent',
                        plot_bgcolor: 'transparent',
                        font: { 
                            family: '-apple-system, BlinkMacSystemFont, sans-serif', 
                            size: 9, 
                            color: colors.textColor 
                        },
                        legend: { 
                            orientation: 'h', 
                            y: 1.02,
                            x: 0.5,
                            xanchor: 'center',
                            font: { color: colors.textColor, size: 8 } 
                        },
                        xaxis: {
                            tickfont: { color: colors.textColor, size: 7 },
                            tickangle: -45,
                            gridcolor: colors.gridColor
                        },
                        yaxis: {
                            title: { text: 'Count', font: { size: 9, color: colors.textColor } },
                            tickfont: { color: colors.textColor, size: 8 },
                            gridcolor: colors.gridColor
                        }
                    };
                    
                    await Plotly.newPlot(plotDiv, traces, layout, {
                        responsive: true,
                        displayModeBar: 'hover',
                        modeBarButtonsToRemove: ['lasso2d', 'select2d']
                    });
                } else {
                    // Issue-based outcome space: subplots per issue
                    const numIssues = issueNames.length;
                    const cols = Math.min(numIssues, 2);
                    const rows = Math.ceil(numIssues / cols);
                    
                    // Calculate subplot domains
                    const hGap = 0.12;
                    const vGap = 0.15;
                    const plotWidth = (1 - hGap * (cols - 1)) / cols;
                    const plotHeight = (1 - vGap * (rows - 1)) / rows;
                    
                    const traces = [];
                    const layout = {
                        barmode: 'group',
                        bargap: 0.1,
                        bargroupgap: 0.05,
                        margin: { t: 20, r: 10, b: 20, l: 30 },
                        paper_bgcolor: 'transparent',
                        plot_bgcolor: 'transparent',
                        font: { 
                            family: '-apple-system, BlinkMacSystemFont, sans-serif', 
                            size: 8, 
                            color: colors.textColor 
                        },
                        legend: { 
                            orientation: 'h', 
                            y: 1.02,
                            x: 0.5,
                            xanchor: 'center',
                            font: { color: colors.textColor, size: 8 } 
                        },
                        annotations: []
                    };
                    
                    issueNames.forEach((issue, issueIdx) => {
                        const row = Math.floor(issueIdx / cols);
                        const col = issueIdx % cols;
                        
                        // Calculate domain for this subplot
                        const xStart = col * (plotWidth + hGap);
                        const xEnd = xStart + plotWidth;
                        const yEnd = 1 - row * (plotHeight + vGap);
                        const yStart = yEnd - plotHeight;
                        
                        // Axis names
                        const xAxisName = issueIdx === 0 ? 'x' : `x${issueIdx + 1}`;
                        const yAxisName = issueIdx === 0 ? 'y' : `y${issueIdx + 1}`;
                        const xAxisKey = issueIdx === 0 ? 'xaxis' : `xaxis${issueIdx + 1}`;
                        const yAxisKey = issueIdx === 0 ? 'yaxis' : `yaxis${issueIdx + 1}`;
                        
                        // Count frequencies for this issue per negotiator
                        const valueFreq = {};
                        neg.offers.forEach(offer => {
                            const offerData = offer.offer;
                            const value = typeof offerData === 'object' && offerData !== null
                                ? offerData[issue]
                                : undefined;
                            
                            if (value !== undefined) {
                                const key = String(value);
                                if (!valueFreq[key]) {
                                    valueFreq[key] = new Array(numAgents).fill(0);
                                }
                                valueFreq[key][offer.proposer_index]++;
                            }
                        });
                        
                        // Sort values
                        const values = Object.keys(valueFreq).sort((a, b) => {
                            const numA = parseFloat(a);
                            const numB = parseFloat(b);
                            if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
                            return a.localeCompare(b);
                        });
                        
                        // Create grouped bar traces per negotiator for this issue
                        for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                            traces.push({
                                x: values,
                                y: values.map(v => valueFreq[v][agentIdx]),
                                type: 'bar',
                                name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
                                marker: { 
                                    color: negColors[agentIdx % negColors.length],
                                    opacity: 0.85
                                },
                                xaxis: xAxisName,
                                yaxis: yAxisName,
                                showlegend: issueIdx === 0,
                                legendgroup: `agent${agentIdx}`
                            });
                        }
                        
                        // Configure axes for this subplot
                        layout[xAxisKey] = {
                            domain: [xStart, xEnd],
                            tickfont: { color: colors.textColor, size: 7 },
                            tickangle: values.some(v => v.length > 4) ? -45 : 0,
                            gridcolor: colors.gridColor,
                            anchor: yAxisName
                        };
                        
                        layout[yAxisKey] = {
                            domain: [yStart, yEnd],
                            tickfont: { color: colors.textColor, size: 7 },
                            gridcolor: colors.gridColor,
                            anchor: xAxisName
                        };
                        
                        // Add subplot title as annotation
                        layout.annotations.push({
                            text: `<b>${issue}</b>`,
                            x: (xStart + xEnd) / 2,
                            y: yEnd + 0.02,
                            xref: 'paper',
                            yref: 'paper',
                            xanchor: 'center',
                            yanchor: 'bottom',
                            showarrow: false,
                            font: { size: 9, color: colors.textColor }
                        });
                    });
                    
                    await Plotly.newPlot(plotDiv, traces, layout, {
                        responsive: true,
                        displayModeBar: 'hover',
                        modeBarButtonsToRemove: ['lasso2d', 'select2d']
                    });
                }
                
                window.histogramPlotInitialized = true;
                
                // Force Plotly to resize to container dimensions after initialization
                this.$nextTick(() => {
                    if (plotDiv && window.Plotly) {
                        Plotly.Plots.resize(plotDiv);
                    }
                });
            } catch (e) {
                console.warn('Failed to initialize histogram plot:', e);
                window.histogramPlotInitialized = false;
            }
        },
        
        // Zoom panel
        zoomPanel(panelName, plotId) {
            this.zoomedPanel = panelName;
            if (plotId) {
                this.$nextTick(() => {
                    // Render the plot to the zoomed container
                    const zoomedContainerId = 'zoomed-' + panelName.replace(/\s+/g, '-').toLowerCase();
                    const zoomedContainer = document.getElementById(zoomedContainerId);
                    if (zoomedContainer) {
                        if (plotId === 'outcome-space-plot') {
                            this.initOutcomeSpacePlotToElement(zoomedContainerId);
                        } else if (plotId === 'utility-timeline-container') {
                            this.initUtilityTimelinePlotsToElement(zoomedContainerId);
                        } else if (plotId === 'issue-frequency-container') {
                            this.initHistogramPlotToElement(zoomedContainerId);
                        } else if (plotId === 'issue-space-plot') {
                            this.renderIssueSpacePlotToElement(zoomedContainerId);
                        }
                    }
                });
            }
        },
        
        // Zoom offer history - show all offers in a modal with virtual scrolling
        zoomOfferHistory() {
            this.zoomedPanel = 'Offer History';
            this.$nextTick(() => {
                const zoomedContainer = document.getElementById('zoomed-offer-history');
                if (zoomedContainer && this.currentNegotiation?.offers) {
                    const offers = this.currentNegotiation.offers;
                    const negotiatorNames = this.currentNegotiation.negotiator_names || [];
                    const negotiatorColors = this.currentNegotiation.negotiator_colors || [];
                    
                    // Build HTML for all offers
                    let html = `<div style="padding: 16px; height: 100%; overflow-y: auto; font-size: 12px;">`;
                    html += `<div style="margin-bottom: 12px; color: var(--text-secondary);">Showing all ${offers.length} offers</div>`;
                    
                    for (let i = 0; i < offers.length; i++) {
                        const offer = offers[i];
                        const color = negotiatorColors[offer.proposer_index] || 'var(--border-color)';
                        const proposerName = offer.proposer || negotiatorNames[offer.proposer_index] || `Agent ${offer.proposer_index}`;
                        
                        html += `<div style="padding: 6px 8px; margin-bottom: 4px; border-left: 3px solid ${color}; background: var(--bg-tertiary); border-radius: 4px;">`;
                        html += `<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">`;
                        html += `<span style="font-weight: 500; color: ${color};">${proposerName}</span>`;
                        html += `<span style="color: var(--text-muted);">#${offer.step}</span>`;
                        html += `</div>`;
                        
                        // Offer values
                        html += `<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">`;
                        if (offer.offer && typeof offer.offer === 'object') {
                            for (const [key, value] of Object.entries(offer.offer)) {
                                html += `<span><span style="color: var(--text-muted);">${key}:</span> <strong>${value}</strong></span>`;
                            }
                        }
                        html += `</div>`;
                        
                        // Utilities
                        if (offer.utilities && Array.isArray(offer.utilities)) {
                            html += `<div style="display: flex; gap: 12px; font-size: 11px;">`;
                            for (let u = 0; u < offer.utilities.length; u++) {
                                const utilColor = negotiatorColors[u] || 'inherit';
                                const utilName = (negotiatorNames[u] || `A${u+1}`).substring(0, 6);
                                const utilValue = typeof offer.utilities[u] === 'number' ? offer.utilities[u].toFixed(3) : offer.utilities[u];
                                html += `<span style="color: ${utilColor};"><span style="opacity: 0.7;">${utilName}:</span> ${utilValue}</span>`;
                            }
                            html += `</div>`;
                        }
                        
                        html += `</div>`;
                    }
                    
                    html += `</div>`;
                    zoomedContainer.innerHTML = html;
                }
            });
        },
        
        // Load stats for current negotiation's scenario
        async loadCurrentNegotiationStats() {
            const neg = this.currentNegotiation;
            if (!neg || !neg.scenario_path) {
                this.currentNegotiationStatsError = 'No scenario path available';
                return;
            }
            
            this.currentNegotiationStatsLoading = true;
            this.currentNegotiationStatsError = null;
            
            try {
                const res = await fetch(`/api/scenarios/${encodeURIComponent(neg.scenario_path)}/stats`);
                if (!res.ok) throw new Error('Failed to load stats');
                this.currentNegotiationStats = await res.json();
            } catch (e) {
                console.error('Failed to load negotiation stats:', e);
                this.currentNegotiationStatsError = 'Failed to load stats';
            } finally {
                this.currentNegotiationStatsLoading = false;
            }
        },
        
        // Calculate stats for current negotiation's scenario
        async calculateCurrentNegotiationStats(force = false) {
            const neg = this.currentNegotiation;
            if (!neg || !neg.scenario_path) {
                this.currentNegotiationStatsError = 'No scenario path available';
                return;
            }
            
            this.currentNegotiationStatsLoading = true;
            this.currentNegotiationStatsError = null;
            
            try {
                const res = await fetch(`/api/scenarios/${encodeURIComponent(neg.scenario_path)}/stats/calculate?force=${force}`, {
                    method: 'POST'
                });
                if (!res.ok) throw new Error('Failed to calculate stats');
                this.currentNegotiationStats = await res.json();
            } catch (e) {
                console.error('Failed to calculate negotiation stats:', e);
                this.currentNegotiationStatsError = 'Failed to calculate stats';
            } finally {
                this.currentNegotiationStatsLoading = false;
            }
        },
        
        // Open scenario stats modal
        openScenarioStatsModal() {
            this.showScenarioStatsModal = true;
            this.loadCurrentNegotiationStats();
        },
        
        // Initialize outcome space plot to a specific element (for zoom)
        async initOutcomeSpacePlotToElement(elementId) {
            const plotDiv = document.getElementById(elementId);
            if (!plotDiv) return;
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.outcome_space_data) return;
            
            const colors = this.getPlotColors();
            const osd = neg.outcome_space_data;
            const negColors = this.getNegotiatorColors();
            const isColorBlind = document.documentElement.classList.contains('color-blind-mode');
            
            // Get axis indices from panel state
            const xIdx = this.panelState.utilityView.xAxis;
            const yIdx = this.panelState.utilityView.yAxis;
            
            const traces = [];
            
            // 1. All outcomes
            if (osd.outcome_utilities && osd.outcome_utilities.length > 0) {
                traces.push({
                    x: osd.outcome_utilities.map(u => u[xIdx] || 0),
                    y: osd.outcome_utilities.map(u => u[yIdx] || 0),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Outcomes',
                    marker: { color: colors.outcomeColor, size: 4, opacity: 0.5 },
                    hoverinfo: 'skip'
                });
            }
            
            // 2. Pareto frontier (markers only, no lines, using special point color)
            if (osd.pareto_utilities && osd.pareto_utilities.length > 0) {
                traces.push({
                    x: osd.pareto_utilities.map(u => u[xIdx] || 0),
                    y: osd.pareto_utilities.map(u => u[yIdx] || 0),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Pareto Frontier',
                    marker: { color: colors.paretoColor, size: 7, opacity: 0.7 }
                });
            }
            
            // 3. Nash point (triangle-up marker, hollow)
            if (osd.nash_point && osd.nash_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.nash_point[xIdx]],
                    y: [osd.nash_point[yIdx]],
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Nash',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 16, 
                        symbol: 'triangle-up',
                        line: { color: colors.nashColor, width: 3 }
                    }
                });
            }
            
            // 4. Kalai point (triangle-down marker, hollow)
            if (osd.kalai_point && osd.kalai_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.kalai_point[xIdx]],
                    y: [osd.kalai_point[yIdx]],
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Kalai',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 16, 
                        symbol: 'triangle-down',
                        line: { color: colors.kalaiColor, width: 3 }
                    }
                });
            }
            
            // 5. Kalai-Smorodinsky point (triangle-left marker, hollow)
            if (osd.kalai_smorodinsky_point && osd.kalai_smorodinsky_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.kalai_smorodinsky_point[xIdx]],
                    y: [osd.kalai_smorodinsky_point[yIdx]],
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Kalai-Smorodinsky',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 16, 
                        symbol: 'triangle-left',
                        line: { color: colors.kalaiSmorodinskyColor, width: 3 }
                    }
                });
            }
            
            // 6. Max welfare point (triangle-right marker, hollow)
            if (osd.max_welfare_point && osd.max_welfare_point.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [osd.max_welfare_point[xIdx]],
                    y: [osd.max_welfare_point[yIdx]],
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Max Welfare',
                    marker: { 
                        color: 'rgba(0,0,0,0)',
                        size: 16, 
                        symbol: 'triangle-right',
                        line: { color: colors.maxWelfareColor, width: 3 }
                    }
                });
            }
            
            // 7. Offer traces per negotiator - always create traces for consistency
            const offers = neg.offers || [];
            const numAgents = neg.negotiator_names?.length || 2;
            for (let i = 0; i < numAgents; i++) {
                // Use Number() for type coercion (proposer_index may be string or number from JSON)
                const agentOffers = offers.filter(o => Number(o.proposer_index) === i);
                traces.push({
                    x: agentOffers.map(o => o.utilities[xIdx] || 0),
                    y: agentOffers.map(o => o.utilities[yIdx] || 0),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: neg.negotiator_names?.[i] || `Agent ${i + 1}`,
                    line: { 
                        color: negColors[i % negColors.length], 
                        width: 2,
                        dash: isColorBlind ? LINE_DASHES[i % LINE_DASHES.length] : 'solid'
                    },
                    marker: { 
                        color: negColors[i % negColors.length], 
                        size: isColorBlind ? 10 : 8,
                        symbol: isColorBlind ? MARKER_SYMBOLS[i % MARKER_SYMBOLS.length] : 'circle'
                    }
                });
            }
            
            // 8. Agreement point
            if (neg.agreement && neg.final_utilities && neg.final_utilities.length > Math.max(xIdx, yIdx)) {
                traces.push({
                    x: [neg.final_utilities[xIdx]],
                    y: [neg.final_utilities[yIdx]],
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Agreement',
                    marker: { color: colors.agreementColor, size: 18, symbol: 'star', line: { color: '#fff', width: 2 } }
                });
            }
            
            const layout = {
                xaxis: { 
                    title: { text: neg.negotiator_names?.[xIdx] || `Agent ${xIdx + 1}`, font: { color: colors.textColor, size: 14 } },
                    tickfont: { color: colors.textColor, size: 12 },
                    gridcolor: colors.gridColor,
                    linecolor: colors.gridColor,
                    zerolinecolor: colors.gridColor
                },
                yaxis: { 
                    title: { text: neg.negotiator_names?.[yIdx] || `Agent ${yIdx + 1}`, font: { color: colors.textColor, size: 14 } },
                    tickfont: { color: colors.textColor, size: 12 },
                    gridcolor: colors.gridColor,
                    linecolor: colors.gridColor,
                    zerolinecolor: colors.gridColor
                },
                margin: { t: 40, r: 40, b: 60, l: 60 },
                legend: { orientation: 'h', y: -0.12, font: { color: colors.textColor, size: 12 } },
                paper_bgcolor: colors.bgColor,
                plot_bgcolor: colors.bgColor,
                font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 13, color: colors.textColor }
            };
            
            const config = {
                responsive: true,
                displayModeBar: 'hover',
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                toImageButtonOptions: { format: 'png', filename: '2d-utility-view-zoomed', scale: 2 }
            };
            
            await Plotly.newPlot(plotDiv, traces, layout, config);
        },
        
        // Initialize utility timeline plots to a specific element (for zoom)
        async initUtilityTimelinePlotsToElement(elementId) {
            const container = document.getElementById(elementId);
            if (!container) return;
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.offers || neg.offers.length === 0) {
                container.innerHTML = '';
                return;
            }
            
            const colors = this.getPlotColors();
            const negColors = this.getNegotiatorColors();
            const numAgents = neg.negotiator_names?.length || 2;
            const isColorBlind = document.documentElement.classList.contains('color-blind-mode');
            const xAxisType = this.panelState.timeline.xAxis;
            
            // Get X values based on selected axis type
            const getXValue = (offer) => {
                switch (xAxisType) {
                    case 'time': return offer.time || 0;
                    case 'relative_time': return offer.relative_time || 0;
                    default: return offer.step;
                }
            };
            
            const xAxisTitle = xAxisType === 'time' ? 'Time (s)' : (xAxisType === 'relative_time' ? 'Relative Time' : 'Step');
            
            // Clear and rebuild container
            container.innerHTML = '';
            
            // Create N plots, one per negotiator
            for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                const plotId = `zoomed-timeline-plot-${agentIdx}`;
                const plotWrapper = document.createElement('div');
                plotWrapper.style.cssText = 'flex: 1; min-height: 200px;';
                plotWrapper.innerHTML = `<div id="${plotId}" style="width: 100%; height: 100%;"></div>`;
                container.appendChild(plotWrapper);
                
                const traces = [];
                
                // Create N series per plot - each series j shows utility of offers from agent j for agent agentIdx
                // Always create traces for consistency with main plot
                for (let proposerIdx = 0; proposerIdx < numAgents; proposerIdx++) {
                    // Use Number() for type coercion (proposer_index may be string or number from JSON)
                    const proposerOffers = neg.offers.filter(o => Number(o.proposer_index) === proposerIdx);
                    
                    const xValues = proposerOffers.map(getXValue);
                    const yValues = proposerOffers.map(o => o.utilities[agentIdx] || 0);
                    
                    // Own offers get thick solid line, others get dashed
                    const isOwnOffers = proposerIdx === agentIdx;
                    
                    traces.push({
                        x: xValues,
                        y: yValues,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: neg.negotiator_names?.[proposerIdx] || `Agent ${proposerIdx + 1}`,
                        line: { 
                            color: negColors[proposerIdx % negColors.length], 
                            width: isOwnOffers ? 3 : 2,
                            dash: isOwnOffers ? 'solid' : LINE_DASHES[(proposerIdx + 1) % LINE_DASHES.length]
                        },
                        marker: { 
                            color: negColors[proposerIdx % negColors.length], 
                            size: isOwnOffers ? 10 : 6,
                            symbol: isColorBlind ? MARKER_SYMBOLS[proposerIdx % MARKER_SYMBOLS.length] : 'circle'
                        }
                    });
                }
                
                // Add agreement marker if exists
                if (neg.agreement && neg.final_utilities && neg.final_utilities.length > agentIdx) {
                    const lastOffer = neg.offers[neg.offers.length - 1];
                    traces.push({
                        x: [getXValue(lastOffer)],
                        y: [neg.final_utilities[agentIdx]],
                        type: 'scatter',
                        mode: 'markers',
                        name: 'Agreement',
                        showlegend: agentIdx === 0,
                        marker: { color: colors.agreementColor, size: 14, symbol: 'star', line: { color: '#fff', width: 1 } }
                    });
                }
                
                // Only show legend on the last plot to avoid overlap
                const isLastPlot = agentIdx === numAgents - 1;
                
                const layout = {
                    title: { 
                        text: `${neg.negotiator_names?.[agentIdx] || 'Agent ' + (agentIdx + 1)}'s Utility`,
                        font: { size: 14, color: colors.textColor }
                    },
                    xaxis: { 
                        title: { text: isLastPlot ? xAxisTitle : '', font: { color: colors.textColor, size: 12 } },
                        tickfont: { color: colors.textColor, size: 11 },
                        gridcolor: colors.gridColor,
                        linecolor: colors.gridColor
                    },
                    yaxis: { 
                        title: { text: 'Utility', font: { color: colors.textColor, size: 12 } },
                        tickfont: { color: colors.textColor, size: 11 },
                        gridcolor: colors.gridColor,
                        linecolor: colors.gridColor
                    },
                    margin: { t: 45, r: 30, b: isLastPlot ? 60 : 35, l: 50 },
                    showlegend: isLastPlot,
                    legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center', font: { color: colors.textColor, size: 11 } },
                    paper_bgcolor: colors.bgColor,
                    plot_bgcolor: colors.bgColor,
                    font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 12, color: colors.textColor }
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: 'hover',
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                    toImageButtonOptions: { format: 'png', filename: `utility-timeline-${agentIdx}-zoomed`, scale: 2 }
                };
                
                await Plotly.newPlot(plotId, traces, layout, config);
            }
        },
        
        // Initialize histogram plot to a specific element (for zoom)
        async initHistogramPlotToElement(elementId) {
            const container = document.getElementById(elementId);
            if (!container) return;
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.offers || neg.offers.length === 0) {
                container.innerHTML = '<div class="empty-state-mini"><span class="text-muted">No offers yet</span></div>';
                return;
            }
            
            const colors = this.getPlotColors();
            const negColors = this.getNegotiatorColors();
            const numAgents = neg.negotiator_names?.length || 2;
            
            // Determine if we have issue-based or enumerated outcome space
            const firstOffer = neg.offers[0]?.offer;
            const issueNames = neg.issue_names || (typeof firstOffer === 'object' && firstOffer !== null && !Array.isArray(firstOffer) 
                ? Object.keys(firstOffer) 
                : []);
            
            const isEnumerated = issueNames.length === 0;
            
            // Clear container and create plot div
            container.innerHTML = '<div id="histogram-plot-zoomed" style="width: 100%; height: 100%;"></div>';
            const plotDiv = document.getElementById('histogram-plot-zoomed');
            if (!plotDiv) return;
            
            if (isEnumerated) {
                // Same as main histogram but with larger fonts
                const outcomeFreq = {};
                
                neg.offers.forEach(offer => {
                    const offerData = offer.offer;
                    const key = Array.isArray(offerData) 
                        ? offerData.join(', ')
                        : typeof offerData === 'object' 
                            ? JSON.stringify(offerData)
                            : String(offerData);
                    
                    if (!outcomeFreq[key]) {
                        outcomeFreq[key] = new Array(numAgents).fill(0);
                    }
                    outcomeFreq[key][offer.proposer_index]++;
                });
                
                const outcomes = Object.keys(outcomeFreq).sort((a, b) => {
                    const totalA = outcomeFreq[a].reduce((s, v) => s + v, 0);
                    const totalB = outcomeFreq[b].reduce((s, v) => s + v, 0);
                    return totalB - totalA;
                });
                
                const displayOutcomes = outcomes.slice(0, 20);
                
                const traces = [];
                for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                    traces.push({
                        x: displayOutcomes,
                        y: displayOutcomes.map(o => outcomeFreq[o][agentIdx]),
                        type: 'bar',
                        name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
                        marker: { 
                            color: negColors[agentIdx % negColors.length],
                            opacity: 0.85
                        }
                    });
                }
                
                const layout = {
                    title: { text: 'Outcome Frequency', font: { size: 16, color: colors.textColor } },
                    barmode: 'group',
                    bargap: 0.15,
                    bargroupgap: 0.1,
                    margin: { t: 50, r: 30, b: 80, l: 50 },
                    paper_bgcolor: colors.bgColor,
                    plot_bgcolor: colors.bgColor,
                    font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 12, color: colors.textColor },
                    legend: { orientation: 'h', y: 1.02, x: 0.5, xanchor: 'center', font: { color: colors.textColor, size: 11 } },
                    xaxis: {
                        title: { text: 'Outcome', font: { size: 12, color: colors.textColor } },
                        tickfont: { color: colors.textColor, size: 10 },
                        tickangle: -45,
                        gridcolor: colors.gridColor
                    },
                    yaxis: {
                        title: { text: 'Count', font: { size: 12, color: colors.textColor } },
                        tickfont: { color: colors.textColor, size: 10 },
                        gridcolor: colors.gridColor
                    }
                };
                
                await Plotly.newPlot(plotDiv, traces, layout, {
                    responsive: true,
                    displayModeBar: 'hover',
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                    toImageButtonOptions: { format: 'png', filename: 'issue-frequency-zoomed', scale: 2 }
                });
            } else {
                // Issue-based with larger fonts
                const numIssues = issueNames.length;
                const cols = Math.min(numIssues, 3);
                const rows = Math.ceil(numIssues / cols);
                
                const hGap = 0.1;
                const vGap = 0.12;
                const plotWidth = (1 - hGap * (cols - 1)) / cols;
                const plotHeight = (1 - vGap * (rows - 1)) / rows;
                
                const traces = [];
                const layout = {
                    title: { text: 'Issue Value Frequency', font: { size: 16, color: colors.textColor } },
                    barmode: 'group',
                    bargap: 0.1,
                    bargroupgap: 0.05,
                    margin: { t: 50, r: 30, b: 30, l: 40 },
                    paper_bgcolor: colors.bgColor,
                    plot_bgcolor: colors.bgColor,
                    font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 11, color: colors.textColor },
                    legend: { orientation: 'h', y: 1.02, x: 0.5, xanchor: 'center', font: { color: colors.textColor, size: 11 } },
                    annotations: []
                };
                
                issueNames.forEach((issue, issueIdx) => {
                    const row = Math.floor(issueIdx / cols);
                    const col = issueIdx % cols;
                    
                    const xStart = col * (plotWidth + hGap);
                    const xEnd = xStart + plotWidth;
                    const yEnd = 1 - row * (plotHeight + vGap) - 0.05;
                    const yStart = yEnd - plotHeight;
                    
                    const xAxisName = issueIdx === 0 ? 'x' : `x${issueIdx + 1}`;
                    const yAxisName = issueIdx === 0 ? 'y' : `y${issueIdx + 1}`;
                    const xAxisKey = issueIdx === 0 ? 'xaxis' : `xaxis${issueIdx + 1}`;
                    const yAxisKey = issueIdx === 0 ? 'yaxis' : `yaxis${issueIdx + 1}`;
                    
                    const valueFreq = {};
                    neg.offers.forEach(offer => {
                        const offerData = offer.offer;
                        const value = typeof offerData === 'object' && offerData !== null ? offerData[issue] : undefined;
                        
                        if (value !== undefined) {
                            const key = String(value);
                            if (!valueFreq[key]) {
                                valueFreq[key] = new Array(numAgents).fill(0);
                            }
                            valueFreq[key][offer.proposer_index]++;
                        }
                    });
                    
                    const values = Object.keys(valueFreq).sort((a, b) => {
                        const numA = parseFloat(a);
                        const numB = parseFloat(b);
                        if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
                        return a.localeCompare(b);
                    });
                    
                    for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
                        traces.push({
                            x: values,
                            y: values.map(v => valueFreq[v][agentIdx]),
                            type: 'bar',
                            name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
                            marker: { color: negColors[agentIdx % negColors.length], opacity: 0.85 },
                            xaxis: xAxisName,
                            yaxis: yAxisName,
                            showlegend: issueIdx === 0,
                            legendgroup: `agent${agentIdx}`
                        });
                    }
                    
                    layout[xAxisKey] = {
                        domain: [xStart, xEnd],
                        tickfont: { color: colors.textColor, size: 9 },
                        tickangle: values.some(v => v.length > 4) ? -45 : 0,
                        gridcolor: colors.gridColor,
                        anchor: yAxisName
                    };
                    
                    layout[yAxisKey] = {
                        domain: [yStart, yEnd],
                        tickfont: { color: colors.textColor, size: 9 },
                        gridcolor: colors.gridColor,
                        anchor: xAxisName
                    };
                    
                    layout.annotations.push({
                        text: `<b>${issue}</b>`,
                        x: (xStart + xEnd) / 2,
                        y: yEnd + 0.02,
                        xref: 'paper',
                        yref: 'paper',
                        xanchor: 'center',
                        yanchor: 'bottom',
                        showarrow: false,
                        font: { size: 12, color: colors.textColor }
                    });
                });
                
                await Plotly.newPlot(plotDiv, traces, layout, {
                    responsive: true,
                    displayModeBar: 'hover',
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                    toImageButtonOptions: { format: 'png', filename: 'issue-frequency-zoomed', scale: 2 }
                });
            }
        },
        
        // Reset Issue Space 2D plot view
        resetIssueSpacePlot() {
            const plotDiv = document.getElementById('issue-space-plot');
            if (plotDiv) {
                Plotly.relayout(plotDiv, { 'xaxis.autorange': true, 'yaxis.autorange': true });
            }
        },
        
        // Render Issue Space 2D plot (issues as axes instead of utilities)
        renderIssueSpacePlot() {
            const plotDiv = document.getElementById('issue-space-plot');
            if (!plotDiv) return;
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.issue_names || neg.issue_names.length < 2) {
                return;
            }
            
            const xIssueIdx = this.panelState.issueSpace.xAxis;
            const yIssueIdx = this.panelState.issueSpace.yAxis;
            const xIssueName = neg.issue_names[xIssueIdx];
            const yIssueName = neg.issue_names[yIssueIdx];
            
            const colors = this.getPlotColors();
            const negColors = this.getNegotiatorColors();
            const offers = neg.offers || [];
            
            // Get issue values from outcomes or offers
            const outcomeData = neg.outcome_space_data;
            const traces = [];
            
            // Plot all outcomes as background scatter (if available)
            if (outcomeData && outcomeData.outcomes) {
                const outcomes = outcomeData.outcomes;
                const xValues = [];
                const yValues = [];
                const hoverTexts = [];
                
                for (const outcome of outcomes) {
                    // outcome could be array or object
                    const xVal = Array.isArray(outcome) ? outcome[xIssueIdx] : outcome[xIssueName];
                    const yVal = Array.isArray(outcome) ? outcome[yIssueIdx] : outcome[yIssueName];
                    if (xVal !== undefined && yVal !== undefined) {
                        xValues.push(xVal);
                        yValues.push(yVal);
                        hoverTexts.push(`${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`);
                    }
                }
                
                if (xValues.length > 0) {
                    traces.push({
                        x: xValues,
                        y: yValues,
                        mode: 'markers',
                        type: xValues.length > 5000 ? 'scattergl' : 'scatter',
                        name: 'All Outcomes',
                        marker: {
                            size: 6,
                            color: colors.gridColor,
                            opacity: 0.3
                        },
                        hoverinfo: 'text',
                        text: hoverTexts,
                        showlegend: false
                    });
                }
            }
            
            // Plot offers by each negotiator
            const offersByAgent = {};
            for (const offer of offers) {
                const agentIdx = offer.proposer_index;
                if (!offersByAgent[agentIdx]) {
                    offersByAgent[agentIdx] = [];
                }
                offersByAgent[agentIdx].push(offer);
            }
            
            for (const [agentIdxStr, agentOffers] of Object.entries(offersByAgent)) {
                const agentIdx = parseInt(agentIdxStr);
                const agentName = neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`;
                const agentColor = negColors[agentIdx] || colors.textColor;
                
                const xValues = [];
                const yValues = [];
                const hoverTexts = [];
                
                for (const offer of agentOffers) {
                    const offerData = offer.offer;
                    if (!offerData) continue;
                    
                    const xVal = typeof offerData === 'object' && !Array.isArray(offerData) 
                        ? offerData[xIssueName] 
                        : (Array.isArray(offerData) ? offerData[xIssueIdx] : undefined);
                    const yVal = typeof offerData === 'object' && !Array.isArray(offerData) 
                        ? offerData[yIssueName] 
                        : (Array.isArray(offerData) ? offerData[yIssueIdx] : undefined);
                    
                    if (xVal !== undefined && yVal !== undefined) {
                        xValues.push(xVal);
                        yValues.push(yVal);
                        hoverTexts.push(`${agentName} (step ${offer.step})<br>${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`);
                    }
                }
                
                if (xValues.length > 0) {
                    traces.push({
                        x: xValues,
                        y: yValues,
                        mode: 'lines+markers',
                        type: 'scatter',
                        name: agentName,
                        line: {
                            color: agentColor,
                            width: 2
                        },
                        marker: {
                            size: 8,
                            color: agentColor,
                            opacity: 0.5,
                            line: { width: 1, color: colors.isDark ? '#fff' : '#000' }
                        },
                        hoverinfo: 'text',
                        text: hoverTexts
                    });
                }
            }
            
            // Mark agreement if present
            if (neg.agreement) {
                const xVal = neg.agreement[xIssueName];
                const yVal = neg.agreement[yIssueName];
                if (xVal !== undefined && yVal !== undefined) {
                    traces.push({
                        x: [xVal],
                        y: [yVal],
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Agreement',
                        marker: {
                            size: 18,
                            color: 'gold',
                            symbol: 'star',
                            line: { width: 2, color: '#000' }
                        },
                        hoverinfo: 'text',
                        text: [`Agreement<br>${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`]
                    });
                }
            }
            
            const layout = {
                margin: { t: 20, r: 20, b: 45, l: 50 },
                xaxis: {
                    title: { text: xIssueName, font: { size: 11, color: colors.textColor } },
                    gridcolor: colors.gridColor,
                    tickfont: { color: colors.textColor, size: 10 }
                },
                yaxis: {
                    title: { text: yIssueName, font: { size: 11, color: colors.textColor } },
                    gridcolor: colors.gridColor,
                    tickfont: { color: colors.textColor, size: 10 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                legend: {
                    orientation: 'h',
                    y: 1.05,
                    x: 0.5,
                    xanchor: 'center',
                    font: { color: colors.textColor, size: 9 }
                },
                hovermode: 'closest'
            };
            
            const config = {
                responsive: true,
                displayModeBar: 'hover',
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            };
            
            Plotly.react(plotDiv, traces, layout, config);
        },
        
        // Render Issue Space 2D plot to a specific element (for zoom modal)
        renderIssueSpacePlotToElement(elementId) {
            const plotDiv = document.getElementById(elementId);
            if (!plotDiv) return;
            
            const neg = this.currentNegotiation;
            if (!neg || !neg.issue_names || neg.issue_names.length < 2) {
                return;
            }
            
            const xIssueIdx = this.panelState.issueSpace.xAxis;
            const yIssueIdx = this.panelState.issueSpace.yAxis;
            const xIssueName = neg.issue_names[xIssueIdx];
            const yIssueName = neg.issue_names[yIssueIdx];
            
            const colors = this.getPlotColors();
            const negColors = this.getNegotiatorColors();
            const offers = neg.offers || [];
            
            // Get issue values from outcomes or offers
            const outcomeData = neg.outcome_space_data;
            const traces = [];
            
            // Plot all outcomes as background scatter (if available)
            if (outcomeData && outcomeData.outcomes) {
                const outcomes = outcomeData.outcomes;
                const xValues = [];
                const yValues = [];
                const hoverTexts = [];
                
                for (const outcome of outcomes) {
                    // outcome could be array or object
                    const xVal = Array.isArray(outcome) ? outcome[xIssueIdx] : outcome[xIssueName];
                    const yVal = Array.isArray(outcome) ? outcome[yIssueIdx] : outcome[yIssueName];
                    if (xVal !== undefined && yVal !== undefined) {
                        xValues.push(xVal);
                        yValues.push(yVal);
                        hoverTexts.push(`${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`);
                    }
                }
                
                if (xValues.length > 0) {
                    traces.push({
                        x: xValues,
                        y: yValues,
                        mode: 'markers',
                        type: xValues.length > 5000 ? 'scattergl' : 'scatter',
                        name: 'All Outcomes',
                        marker: {
                            size: 6,
                            color: colors.gridColor,
                            opacity: 0.3
                        },
                        hoverinfo: 'text',
                        text: hoverTexts,
                        showlegend: false
                    });
                }
            }
            
            // Plot offers by each negotiator
            const offersByAgent = {};
            for (const offer of offers) {
                const agentIdx = offer.proposer_index;
                if (!offersByAgent[agentIdx]) {
                    offersByAgent[agentIdx] = [];
                }
                offersByAgent[agentIdx].push(offer);
            }
            
            for (const [agentIdxStr, agentOffers] of Object.entries(offersByAgent)) {
                const agentIdx = parseInt(agentIdxStr);
                const agentName = neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`;
                const agentColor = negColors[agentIdx] || colors.textColor;
                
                const xValues = [];
                const yValues = [];
                const hoverTexts = [];
                
                for (const offer of agentOffers) {
                    const offerData = offer.offer;
                    if (!offerData) continue;
                    
                    const xVal = typeof offerData === 'object' && !Array.isArray(offerData) 
                        ? offerData[xIssueName] 
                        : (Array.isArray(offerData) ? offerData[xIssueIdx] : undefined);
                    const yVal = typeof offerData === 'object' && !Array.isArray(offerData) 
                        ? offerData[yIssueName] 
                        : (Array.isArray(offerData) ? offerData[yIssueIdx] : undefined);
                    
                    if (xVal !== undefined && yVal !== undefined) {
                        xValues.push(xVal);
                        yValues.push(yVal);
                        hoverTexts.push(`${agentName} (step ${offer.step})<br>${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`);
                    }
                }
                
                if (xValues.length > 0) {
                    traces.push({
                        x: xValues,
                        y: yValues,
                        mode: 'lines+markers',
                        type: 'scatter',
                        name: agentName,
                        line: {
                            color: agentColor,
                            width: 2
                        },
                        marker: {
                            size: 8,
                            color: agentColor,
                            opacity: 0.5,
                            line: { width: 1, color: colors.isDark ? '#fff' : '#000' }
                        },
                        hoverinfo: 'text',
                        text: hoverTexts
                    });
                }
            }
            
            // Mark agreement if present
            if (neg.agreement) {
                const xVal = neg.agreement[xIssueName];
                const yVal = neg.agreement[yIssueName];
                if (xVal !== undefined && yVal !== undefined) {
                    traces.push({
                        x: [xVal],
                        y: [yVal],
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Agreement',
                        marker: {
                            size: 18,
                            color: 'gold',
                            symbol: 'star',
                            line: { width: 2, color: '#000' }
                        },
                        hoverinfo: 'text',
                        text: [`Agreement<br>${xIssueName}: ${xVal}<br>${yIssueName}: ${yVal}`]
                    });
                }
            }
            
            const layout = {
                margin: { t: 20, r: 20, b: 45, l: 50 },
                xaxis: {
                    title: { text: xIssueName, font: { size: 11, color: colors.textColor } },
                    gridcolor: colors.gridColor,
                    tickfont: { color: colors.textColor, size: 10 }
                },
                yaxis: {
                    title: { text: yIssueName, font: { size: 11, color: colors.textColor } },
                    gridcolor: colors.gridColor,
                    tickfont: { color: colors.textColor, size: 10 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                legend: {
                    orientation: 'h',
                    y: 1.05,
                    x: 0.5,
                    xanchor: 'center',
                    font: { color: colors.textColor, size: 9 }
                },
                hovermode: 'closest'
            };
            
            const config = {
                responsive: true,
                displayModeBar: 'hover',
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            };
            
            Plotly.react(plotDiv, traces, layout, config);
        },
        
        // Save plot as image
        savePlot(plotId, filename) {
            const plotDiv = document.getElementById(plotId);
            if (plotDiv) {
                Plotly.downloadImage(plotDiv, { format: 'png', filename: filename, scale: 2 });
            }
        },
        
        // Save offers as JSON
        saveOffersAsJson() {
            const neg = this.currentNegotiation;
            if (!neg || !neg.offers) return;
            
            const data = {
                scenario: neg.scenario,
                negotiators: neg.negotiator_names,
                offers: neg.offers,
                agreement: neg.agreement,
                final_utilities: neg.final_utilities
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `negotiation-${neg.id}.json`;
            a.click();
            URL.revokeObjectURL(url);
        },
        
        // Save results
        saveResults() {
            this.saveOffersAsJson();
        },
        
        // Override connectToStream to handle init event and plotting
        connectToStream(sessionId, url, autoStart = true) {
            const eventSource = new EventSource(url);
            
            const neg = this.runningNegotiations.find(n => n.id === sessionId);
            if (neg) {
                neg.offers = [];
                neg.pendingStart = !autoStart;
                neg.panelSettings = neg.panelSettings || { adjustable: true };
            }
            
            eventSource.addEventListener('init', (event) => {
                const initData = JSON.parse(event.data);
                const neg = this.runningNegotiations.find(n => n.id === sessionId);
                if (neg) {
                    neg.negotiator_names = initData.negotiator_names;
                    neg.negotiator_types = initData.negotiator_types;
                    neg.negotiator_colors = initData.negotiator_colors;
                    neg.issue_names = initData.issue_names;
                    neg.n_steps = initData.n_steps;
                    neg.time_limit = initData.time_limit;
                    neg.n_outcomes = initData.n_outcomes;
                    neg.outcome_space_data = initData.outcome_space_data;
                    neg.scenario = initData.scenario_name;
                    neg.scenario_path = initData.scenario_path;
                    
                    // Initialize panel state for this negotiation
                    const numAgents = neg.negotiator_names?.length || 2;
                    this.panelState.utilityView.xAxis = neg.panelSettings?.utilityView?.xAxis ?? 0;
                    this.panelState.utilityView.yAxis = neg.panelSettings?.utilityView?.yAxis ?? Math.min(1, numAgents - 1);
                    this.panelState.timeline.xAxis = neg.panelSettings?.timeline?.xAxis ?? 'relative_time';
                    
                    if (this.currentNegotiation?.id === sessionId) {
                        this.currentNegotiation = neg;
                        this.$nextTick(() => {
                            this.initOutcomeSpacePlot();
                        });
                    }
                }
            });
            
            eventSource.addEventListener('offer', (event) => {
                const offer = JSON.parse(event.data);
                const neg = this.runningNegotiations.find(n => n.id === sessionId);
                if (neg) {
                    neg.step = offer.step;
                    neg.relative_time = offer.relative_time;
                    neg.lastOffer = offer;
                    neg.offers = neg.offers || [];
                    neg.offers.push(offer);
                    neg.pendingStart = false;
                    
                    // Track pending offers for batched updates
                    neg._pendingOffers = neg._pendingOffers || [];
                    neg._pendingOffers.push(offer);
                    
                    // Update currentNegotiation if it's the active one
                    if (this.currentNegotiation?.id === sessionId) {
                        this.currentNegotiation.step = neg.step;
                        this.currentNegotiation.relative_time = neg.relative_time;
                        this.currentNegotiation.lastOffer = neg.lastOffer;
                        // Share the same offers array reference - don't copy!
                        this.currentNegotiation.offers = neg.offers;
                        this.currentNegotiation.pendingStart = false;
                        
                        // Time-based throttling: max 30 updates per second (33ms between updates)
                        const now = performance.now();
                        const MIN_UPDATE_INTERVAL = 33; // ~30fps
                        
                        if (!this._lastPlotUpdate || (now - this._lastPlotUpdate) >= MIN_UPDATE_INTERVAL) {
                            this._lastPlotUpdate = now;
                            // Grab pending offers and clear the queue
                            const pendingOffers = neg._pendingOffers || [];
                            neg._pendingOffers = [];
                            
                            // Use non-blocking update with batched offers
                            requestAnimationFrame(() => {
                                if (this.currentNegotiation?.id === sessionId && pendingOffers.length > 0) {
                                    this.updateOutcomeSpacePlotBatched(pendingOffers);
                                    this.updateUtilityTimelinePlotsBatched(pendingOffers);
                                }
                            });
                        }
                        
                        // Throttle scroll updates (less frequent - every 100ms)
                        if (!this._lastScrollUpdate || (now - this._lastScrollUpdate) >= 100) {
                            this._lastScrollUpdate = now;
                            requestAnimationFrame(() => {
                                const log = this.$refs.offerLog;
                                if (log) log.scrollTop = log.scrollHeight;
                            });
                        }
                    }
                }
            });
            
            eventSource.addEventListener('complete', (event) => {
                const result = JSON.parse(event.data);
                const idx = this.runningNegotiations.findIndex(n => n.id === sessionId);
                if (idx >= 0) {
                    const neg = this.runningNegotiations.splice(idx, 1)[0];
                    neg.agreement = result.agreement;
                    neg.final_utilities = result.final_utilities;
                    // Always set end_reason for completed negotiations
                    neg.end_reason = result.end_reason || (result.error ? 'error' : (result.agreement ? 'agreement' : 'completed'));
                    neg.error = result.error;
                    neg.step = result.n_steps;
                    neg.pendingStart = false;
                    neg.optimality_stats = result.optimality_stats;
                    this.completedNegotiations.unshift(neg);
                    
                    if (this.currentNegotiation?.id === sessionId) {
                        this.currentNegotiation = neg;
                        this.$nextTick(() => {
                            this.initOutcomeSpacePlot();
                            this.initUtilityTimelinePlots();
                            this.initHistogramPlot();
                        });
                    }
                }
                eventSource.close();
            });
            
            eventSource.addEventListener('error', () => {
                eventSource.close();
            });
            
            // Auto-select the negotiation to show its details
            if (neg) {
                this.selectNegotiation(neg);
            }
            
            // Store eventSource reference for manual start
            if (neg) {
                neg._eventSource = eventSource;
            }
        },
        
        // Actually start a pending negotiation
        async actuallyStartNegotiation() {
            const neg = this.currentNegotiation;
            if (!neg || !neg.pendingStart) return;
            
            try {
                await fetch(`/api/negotiation/${neg.id}/start`, { method: 'POST' });
                neg.pendingStart = false;
            } catch (e) {
                console.error('Failed to start negotiation:', e);
            }
        },
        
        // Override selectNegotiation to init plots
        selectNegotiation(neg) {
            // If neg is from Tabulator (plain object copy), find the actual object by ID
            // to preserve the offers array and other properties
            let actualNeg = neg;
            if (neg && neg.id) {
                actualNeg = this.runningNegotiations.find(n => n.id === neg.id) 
                    || this.completedNegotiations.find(n => n.id === neg.id)
                    || neg;
            }
            this.currentNegotiation = actualNeg;
            
            // Update panel state from negotiation settings (use actualNeg, not neg)
            const numAgents = actualNeg?.negotiator_names?.length || 2;
            this.panelState.utilityView.xAxis = actualNeg?.panelSettings?.utilityView?.xAxis ?? 0;
            this.panelState.utilityView.yAxis = actualNeg?.panelSettings?.utilityView?.yAxis ?? Math.min(1, numAgents - 1);
            this.panelState.timeline.xAxis = actualNeg?.panelSettings?.timeline?.xAxis ?? 'step';
            
            // Apply panel visibility settings (visible=true means collapsed=false)
            if (actualNeg?.panelSettings?.visible) {
                const visible = actualNeg.panelSettings.visible;
                this.panelCollapsed.info = !visible.info;
                this.panelCollapsed.history = !visible.history;
                this.panelCollapsed.result = !visible.result;
                this.panelCollapsed.utility2d = !visible.utility2d;
                this.panelCollapsed.issueSpace2d = !visible.issueSpace2d;
                this.panelCollapsed.timeline = !visible.timeline;
                this.panelCollapsed.histogram = !visible.histogram;
            }
            
            window.outcomeSpacePlotInitialized = false;
            window.timelinePlotsInitialized = false;
            window.histogramPlotInitialized = false;
            this.$nextTick(() => {
                this.initOutcomeSpacePlot();
                this.initUtilityTimelinePlots();
                this.initHistogramPlot();
            });
        },
        
        // Toggle pause state
        async togglePause() {
            if (!this.currentNegotiation) return;
            const sessionId = this.currentNegotiation.id;
            const isPaused = this.currentNegotiation.paused;
            
            try {
                const endpoint = isPaused ? 'resume' : 'pause';
                await fetch(`/api/negotiation/${sessionId}/${endpoint}`, { method: 'POST' });
                this.currentNegotiation.paused = !isPaused;
            } catch (e) {
                console.error('Failed to toggle pause:', e);
            }
        },
        
        // Cancel the current negotiation
        async stopNegotiation() {
            if (!this.currentNegotiation) return;
            const sessionId = this.currentNegotiation.id;
            try {
                await fetch(`/api/negotiation/${sessionId}/cancel`, { method: 'POST' });
            } catch (e) {
                console.error('Failed to cancel negotiation:', e);
            }
        }
    };
    
    // Merge base with plot extensions, base properties first so extensions can override
    return { ...base, ...plotExtensions };
};
