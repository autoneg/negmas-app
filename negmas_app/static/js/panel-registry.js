/**
 * Panel Registry - Central registry for all panel definitions
 * 
 * This module provides:
 * - Panel registration and lookup
 * - Core panel definitions (info, history, histogram, 2d-view, timeline, result)
 * - Context-based panel filtering
 */

// SVG Icons for panels
const PanelIcons = {
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
    </svg>`,
    
    history: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="8" y1="6" x2="21" y2="6"></line>
        <line x1="8" y1="12" x2="21" y2="12"></line>
        <line x1="8" y1="18" x2="21" y2="18"></line>
        <line x1="3" y1="6" x2="3.01" y2="6"></line>
        <line x1="3" y1="12" x2="3.01" y2="12"></line>
        <line x1="3" y1="18" x2="3.01" y2="18"></line>
    </svg>`,
    
    histogram: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="12" width="4" height="9"></rect>
        <rect x="10" y="8" width="4" height="13"></rect>
        <rect x="17" y="4" width="4" height="17"></rect>
    </svg>`,
    
    scatter: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="7" cy="14" r="2"></circle>
        <circle cx="11" cy="6" r="2"></circle>
        <circle cx="16" cy="10" r="2"></circle>
        <circle cx="13" cy="16" r="2"></circle>
        <circle cx="19" cy="14" r="2"></circle>
        <line x1="3" y1="21" x2="3" y2="3"></line>
        <line x1="3" y1="21" x2="21" y2="21"></line>
    </svg>`,
    
    timeline: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
    </svg>`,
    
    result: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>`,
    
    download: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>`,
    
    zoom: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 3 21 3 21 9"></polyline>
        <polyline points="9 21 3 21 3 15"></polyline>
        <line x1="21" y1="3" x2="14" y2="10"></line>
        <line x1="3" y1="21" x2="10" y2="14"></line>
    </svg>`,
    
    reset: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
        <path d="M3 3v5h5"></path>
    </svg>`,
    
    collapse: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"></polyline>
    </svg>`,
    
    close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>`,
    
    add: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>`,
    
    menu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="1"></circle>
        <circle cx="19" cy="12" r="1"></circle>
        <circle cx="5" cy="12" r="1"></circle>
    </svg>`,
    
    play: `<svg viewBox="0 0 24 24" fill="currentColor">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>`,
    
    pause: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="6" y="4" width="4" height="16"></rect>
        <rect x="14" y="4" width="4" height="16"></rect>
    </svg>`,
    
    stop: `<svg viewBox="0 0 24 24" fill="currentColor">
        <rect x="4" y="4" width="16" height="16" rx="2"></rect>
    </svg>`
};

/**
 * Panel Registry - Manages all panel definitions
 */
const PanelRegistry = {
    _panels: new Map(),
    _initialized: false,
    
    /**
     * Register a panel definition
     * @param {Object} definition - Panel definition object
     */
    register(definition) {
        if (!definition.id) {
            console.error('Panel definition must have an id');
            return;
        }
        
        // Apply defaults
        const panel = {
            contexts: ['negotiation'],
            defaultZone: 'left',
            defaultOrder: 100,
            allowMultiple: false,
            minWidth: 200,
            minHeight: 100,
            closable: true,
            ...definition
        };
        
        this._panels.set(panel.id, panel);
        
        // Dispatch event for listeners
        window.dispatchEvent(new CustomEvent('negmas:panel-registered', {
            detail: panel
        }));
    },
    
    /**
     * Get a panel definition by ID
     * @param {string} id - Panel ID
     * @returns {Object|undefined}
     */
    get(id) {
        return this._panels.get(id);
    },
    
    /**
     * Get all registered panels
     * @returns {Array}
     */
    getAll() {
        return [...this._panels.values()];
    },
    
    /**
     * Get panels for a specific context
     * @param {string} context - Context name (negotiation, tournament, scenarios, global)
     * @returns {Array}
     */
    getForContext(context) {
        return this.getAll().filter(p => p.contexts.includes(context) || p.contexts.includes('global'));
    },
    
    /**
     * Check if a panel exists
     * @param {string} id - Panel ID
     * @returns {boolean}
     */
    has(id) {
        return this._panels.has(id);
    },
    
    /**
     * Initialize core panels
     */
    initCorePanels() {
        if (this._initialized) return;
        
        // Info Panel
        this.register({
            id: 'info',
            name: 'Info',
            icon: PanelIcons.info,
            contexts: ['negotiation'],
            defaultZone: 'bottom-left',
            defaultOrder: 10,
            minHeight: 60,
            closable: false,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                return `
                    <div class="panel-content-ultra-compact">
                        <div class="info-row">
                            <span class="info-scenario">${neg.scenario || 'Unknown'}</span>
                            <span class="badge badge-xs ${this._getStatusClass(neg)}">${this._getStatusText(neg)}</span>
                            <span class="info-stats">${(neg.step || 0)}/${neg.n_steps || '∞'} steps</span>
                            <span class="info-stats">${(neg.offers?.length || 0)} offers</span>
                            ${this._renderProgress(neg)}
                        </div>
                        <div class="info-row info-row-negotiators">
                            ${this._renderNegotiators(neg)}
                        </div>
                    </div>
                `;
            },
            
            _getStatusClass(neg) {
                if (neg.pendingStart) return 'badge-warning';
                if (neg.agreement) return 'badge-success';
                if (neg.end_reason) return 'badge-neutral';
                if (neg.paused) return 'badge-info';
                return 'badge-primary';
            },
            
            _getStatusText(neg) {
                if (neg.pendingStart) return 'Pending';
                if (neg.agreement) return 'Done';
                if (neg.end_reason) return 'End';
                if (neg.paused) return 'Paused';
                return 'Running';
            },
            
            _renderProgress(neg) {
                if (neg.pendingStart || neg.agreement || neg.end_reason) return '';
                const pct = Math.min(100, (neg.relative_time || 0) * 100);
                return `
                    <div class="info-progress">
                        <div class="progress-mini">
                            <div class="progress-bar" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
            },
            
            _renderNegotiators(neg) {
                const names = neg.negotiator_names || [];
                const colors = neg.negotiator_colors || [];
                return names.map((name, idx) => 
                    `<span class="badge badge-xs" style="background: ${colors[idx] || 'var(--primary)'}; color: white;">${name}</span>`
                ).join('');
            }
        });
        
        // Offer History Panel
        this.register({
            id: 'offer-history',
            name: 'Offer History',
            icon: PanelIcons.history,
            contexts: ['negotiation'],
            defaultZone: 'left',
            defaultOrder: 20,
            minHeight: 150,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                const offers = neg.offers || [];
                if (offers.length === 0) {
                    return '<div class="empty-state-mini"><span class="text-muted">Waiting for offers...</span></div>';
                }
                
                // Show last 10 offers for performance during live updates
                const recentOffers = offers.slice(-10);
                const truncated = offers.length > 10;
                return `
                    ${truncated ? `<div style="padding: 4px 8px; background: var(--bg-tertiary); border-radius: 4px; margin-bottom: 4px; font-size: 10px; color: var(--text-secondary);">
                        Showing last 10 of ${offers.length} offers.
                    </div>` : ''}
                    <div class="offer-log">
                        ${recentOffers.map((offer, idx) => this._renderOffer(offer, neg)).join('')}
                    </div>
                `;
            },
            
            _renderOffer(offer, neg) {
                const color = neg.negotiator_colors?.[offer.proposer_index] || 'var(--border-color)';
                const proposerColor = neg.negotiator_colors?.[offer.proposer_index] || 'inherit';
                
                return `
                    <div class="offer-item-compact animate-slide-up" style="border-left: 2px solid ${color}">
                        <div class="offer-header-compact">
                            <span class="offer-agent" style="color: ${proposerColor}">${offer.proposer}</span>
                            <span class="offer-step">#${offer.step}</span>
                        </div>
                        <div class="offer-values-compact">
                            ${Object.entries(offer.offer || {}).map(([key, value]) =>
                                `<span><span class="text-muted">${key}:</span> ${value}</span>`
                            ).join('')}
                        </div>
                        <div class="offer-utilities-compact">
                            ${(offer.utilities || []).map((util, idx) =>
                                `<span style="color: ${neg.negotiator_colors?.[idx] || 'inherit'}">${util.toFixed(2)}</span>`
                            ).join('')}
                        </div>
                    </div>
                `;
            },
            
            init(element, state) {
                // Scroll to bottom on init
                const log = element.querySelector('.offer-log');
                if (log) log.scrollTop = log.scrollHeight;
            },
            
            update(element, state) {
                // Re-render and scroll to bottom
                element.innerHTML = this.render(state);
                const log = element.querySelector('.offer-log');
                if (log) log.scrollTop = log.scrollHeight;
            }
        });
        
        // Offer Histogram Panel
        // Shows histogram of offer values per issue (one subplot per issue)
        // For enumerated outcome spaces (no issues), shows a single histogram of outcomes
        // X-axis: issue values, Y-axis: count of proposals, N grouped bars per negotiator
        this.register({
            id: 'offer-histogram',
            name: 'Offer Histogram',
            icon: PanelIcons.histogram,
            contexts: ['negotiation'],
            defaultZone: 'left',
            defaultOrder: 30,
            minHeight: 200,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                const offers = neg.offers || [];
                if (offers.length === 0) {
                    return `
                        <div class="empty-state-mini" style="height: 100%;">
                            <span class="panel-icon">${PanelIcons.histogram}</span>
                            <span class="text-muted">Waiting for offers...</span>
                        </div>
                    `;
                }
                
                return '<div id="offer-histogram-plot" style="width: 100%; height: 100%;"></div>';
            },
            
            init(element, state) {
                this._initPlot(element, state);
            },
            
            update(element, state) {
                this._initPlot(element, state);
            },
            
            _initPlot(element, state) {
                const plotDiv = element.querySelector('#offer-histogram-plot');
                if (!plotDiv || !window.Plotly) return;
                
                const neg = state.currentNegotiation;
                if (!neg || !neg.offers || neg.offers.length === 0) return;
                
                const colors = this._getPlotColors();
                const negColors = neg.negotiator_colors || ['#4a6fa5', '#22a06b', '#e65100', '#7b1fa2'];
                const numAgents = neg.negotiator_names?.length || 2;
                
                // Determine if we have issue-based or enumerated outcome space
                const firstOffer = neg.offers[0]?.offer;
                const issueNames = neg.issue_names || (typeof firstOffer === 'object' && firstOffer !== null && !Array.isArray(firstOffer) 
                    ? Object.keys(firstOffer) 
                    : []);
                
                const isEnumerated = issueNames.length === 0;
                
                if (isEnumerated) {
                    // Enumerated outcome space: single histogram
                    this._renderEnumeratedHistogram(plotDiv, neg, numAgents, negColors, colors);
                } else {
                    // Issue-based outcome space: one subplot per issue
                    this._renderIssueHistograms(plotDiv, neg, issueNames, numAgents, negColors, colors);
                }
            },
            
            _renderEnumeratedHistogram(plotDiv, neg, numAgents, negColors, colors) {
                // Count frequency of each outcome per negotiator
                const outcomeFreq = {};
                
                neg.offers.forEach(offer => {
                    // Convert offer to string key (handle both tuples/arrays and objects)
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
                
                // Sort outcomes by total frequency (most common first)
                const outcomes = Object.keys(outcomeFreq).sort((a, b) => {
                    const totalA = outcomeFreq[a].reduce((s, v) => s + v, 0);
                    const totalB = outcomeFreq[b].reduce((s, v) => s + v, 0);
                    return totalB - totalA;
                });
                
                // Limit to top 20 outcomes for readability
                const displayOutcomes = outcomes.slice(0, 20);
                
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
                            opacity: 0.8
                        }
                    });
                }
                
                const layout = {
                    barmode: 'group',
                    bargap: 0.15,
                    bargroupgap: 0.1,
                    margin: { t: 20, r: 10, b: 80, l: 40 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                    font: { 
                        family: '-apple-system, BlinkMacSystemFont, sans-serif', 
                        size: 10, 
                        color: colors.textColor 
                    },
                    legend: { 
                        orientation: 'h', 
                        y: 1.05,
                        x: 0.5,
                        xanchor: 'center',
                        font: { color: colors.textColor, size: 9 } 
                    },
                    xaxis: {
                        title: { text: 'Outcome', font: { size: 10, color: colors.textColor } },
                        tickfont: { color: colors.textColor, size: 8 },
                        tickangle: -45,
                        gridcolor: colors.gridColor
                    },
                    yaxis: {
                        title: { text: 'Count', font: { size: 10, color: colors.textColor } },
                        tickfont: { color: colors.textColor, size: 8 },
                        gridcolor: colors.gridColor
                    }
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: 'hover',
                    modeBarButtonsToRemove: ['lasso2d', 'select2d']
                };
                
                Plotly.react(plotDiv, traces, layout, config);
            },
            
            _renderIssueHistograms(plotDiv, neg, issueNames, numAgents, negColors, colors) {
                const numIssues = issueNames.length;
                const cols = Math.min(numIssues, 2);
                const rows = Math.ceil(numIssues / cols);
                
                // Calculate subplot domains
                const hGap = 0.08;
                const vGap = 0.12;
                const plotWidth = (1 - hGap * (cols - 1)) / cols;
                const plotHeight = (1 - vGap * (rows - 1)) / rows;
                
                const traces = [];
                const layout = {
                    barmode: 'group',
                    bargap: 0.15,
                    bargroupgap: 0.1,
                    margin: { t: 30, r: 10, b: 30, l: 40 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                    font: { 
                        family: '-apple-system, BlinkMacSystemFont, sans-serif', 
                        size: 10, 
                        color: colors.textColor 
                    },
                    legend: { 
                        orientation: 'h', 
                        y: 1.02,
                        x: 0.5,
                        xanchor: 'center',
                        font: { color: colors.textColor, size: 9 } 
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
                    
                    // Sort values (try numeric sort first, then alphabetic)
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
                                opacity: 0.8
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
                        tickfont: { color: colors.textColor, size: 8 },
                        tickangle: values.some(v => v.length > 5) ? -45 : 0,
                        gridcolor: colors.gridColor,
                        anchor: yAxisName
                    };
                    
                    layout[yAxisKey] = {
                        domain: [yStart, yEnd],
                        title: { text: 'Count', font: { size: 9, color: colors.textColor } },
                        tickfont: { color: colors.textColor, size: 8 },
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
                        font: { size: 10, color: colors.textColor }
                    });
                });
                
                const config = {
                    responsive: true,
                    displayModeBar: 'hover',
                    modeBarButtonsToRemove: ['lasso2d', 'select2d']
                };
                
                Plotly.react(plotDiv, traces, layout, config);
            },
            
            _getPlotColors() {
                const isDark = document.documentElement.classList.contains('dark-mode');
                return {
                    textColor: isDark ? '#b6c2cf' : '#172b4d',
                    gridColor: isDark ? '#38414a' : '#dfe1e6'
                };
            },
            
            destroy(element) {
                const plotDiv = element.querySelector('#offer-histogram-plot');
                if (plotDiv && window.Plotly) {
                    Plotly.purge(plotDiv);
                }
            }
        });
        
        // 2D Utility View Panel
        this.register({
            id: 'utility-2d',
            name: '2D Utility View',
            icon: PanelIcons.scatter,
            contexts: ['negotiation'],
            defaultZone: 'right',
            defaultOrder: 10,
            minHeight: 200,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                if (!neg.outcome_space_data) {
                    return `
                        <div class="empty-state-mini" style="height: 100%;">
                            <span class="panel-icon">${PanelIcons.scatter}</span>
                            <span class="text-muted">Loading outcome space...</span>
                        </div>
                    `;
                }
                
                return '<div id="outcome-space-plot" style="width: 100%; height: 100%;"></div>';
            },
            
            init(element, state) {
                this._initPlot(element, state);
            },
            
            update(element, state) {
                this._initPlot(element, state);
            },
            
            _initPlot(element, state) {
                // This will be implemented by the existing plotting code
                // For now, we trigger a custom event that the main app can handle
                window.dispatchEvent(new CustomEvent('negmas:init-outcome-plot', {
                    detail: { element, state }
                }));
            },
            
            destroy(element) {
                const plotDiv = element.querySelector('#outcome-space-plot');
                if (plotDiv && window.Plotly) {
                    Plotly.purge(plotDiv);
                }
            }
        });
        
        // Utility Timeline Panel
        this.register({
            id: 'utility-timeline',
            name: 'Utility Timeline',
            icon: PanelIcons.timeline,
            contexts: ['negotiation'],
            defaultZone: 'right',
            defaultOrder: 20,
            minHeight: 150,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                const offers = neg.offers || [];
                if (offers.length === 0) {
                    return `
                        <div class="empty-state-mini" style="height: 100%;">
                            <span class="panel-icon">${PanelIcons.timeline}</span>
                            <span class="text-muted">Waiting for offers...</span>
                        </div>
                    `;
                }
                
                return '<div id="utility-timeline-container" style="width: 100%; height: 100%; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; padding: 2px;"></div>';
            },
            
            init(element, state) {
                this._initPlot(element, state);
            },
            
            update(element, state) {
                this._initPlot(element, state);
            },
            
            _initPlot(element, state) {
                // This will be implemented by the existing plotting code
                window.dispatchEvent(new CustomEvent('negmas:init-timeline-plot', {
                    detail: { element, state }
                }));
            },
            
            destroy(element) {
                const container = element.querySelector('#utility-timeline-container');
                if (container && window.Plotly) {
                    container.querySelectorAll('[id^="timeline-plot-"]').forEach(el => {
                        Plotly.purge(el);
                    });
                }
            }
        });
        
        // Result Panel
        this.register({
            id: 'result',
            name: 'Result',
            icon: PanelIcons.result,
            contexts: ['negotiation'],
            defaultZone: 'right',
            defaultOrder: 30,
            minHeight: 60,
            closable: false,
            
            render(state) {
                const neg = state.currentNegotiation;
                if (!neg) return '<div class="panel-empty">No negotiation selected</div>';
                
                if (neg.agreement) {
                    return this._renderAgreement(neg);
                } else if (neg.end_reason && !neg.agreement) {
                    return this._renderNoAgreement(neg);
                } else if (neg.pendingStart) {
                    return '<div class="result-row result-row-center"><span class="text-muted">Ready</span></div>';
                } else {
                    return '<div class="result-row result-row-center"><div class="spinner spinner-xs"></div><span class="text-muted">Running...</span></div>';
                }
            },
            
            _renderAgreement(neg) {
                const agreementParts = Object.entries(neg.agreement).map(([key, value]) =>
                    `<span class="result-item"><span class="text-muted">${key}</span>=<strong>${value}</strong></span>`
                ).join('');
                
                const utilities = (neg.final_utilities || []).map((util, idx) =>
                    `<span class="result-utility" style="color: ${neg.negotiator_colors?.[idx] || 'var(--primary)'}">${util.toFixed(3)}</span>`
                ).join('');
                
                return `
                    <div class="result-row">
                        ${agreementParts}
                        <span class="result-separator">→</span>
                        ${utilities}
                    </div>
                `;
            },
            
            _renderNoAgreement(neg) {
                const badgeClass = neg.error ? 'badge-danger' : 'badge-warning';
                const badgeText = neg.error ? 'Error' : 'No Agreement';
                const reason = neg.error || neg.end_reason;
                
                return `
                    <div class="result-row">
                        <span class="badge badge-xs ${badgeClass}">${badgeText}</span>
                        <span class="text-muted result-reason">${reason}</span>
                    </div>
                `;
            }
        });
        
        this._initialized = true;
        console.log('[PanelRegistry] Core panels initialized:', this.getAll().map(p => p.id));
    }
};

// Export for use in other modules
window.PanelRegistry = PanelRegistry;
window.PanelIcons = PanelIcons;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PanelRegistry.initCorePanels());
} else {
    PanelRegistry.initCorePanels();
}
