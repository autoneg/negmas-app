import { defineStore } from 'pinia'

export const useScenarioStore = defineStore('scenarios', {
  state: () => ({
    // Scenarios list with different loading stages
    scenarios: [],
    
    // Loading states
    loading: {
      names: false,
      basicInfo: false,
      fullData: false
    },
    
    // Optimization mode: 'space' | 'balanced' | 'speed'
    optimizationMode: 'balanced',
    
    // Filters
    search: '',
    sourceFilter: '',
    filters: {
      minOutcomes: null,
      maxOutcomes: null,
      minRationalFraction: null,
      maxRationalFraction: null,
      minOpposition: null,
      maxOpposition: null
    },
    
    // Selected scenario
    selectedScenario: null,
    scenarioStats: null,
    statsLoading: false,
    statsError: null,
    
    // Sources
    sources: []
  }),
  
  getters: {
    filteredScenarios: (state) => {
      let results = state.scenarios
      
      // Filter by source
      if (state.sourceFilter) {
        results = results.filter(s => s.source === state.sourceFilter)
      }
      
      // Filter by search
      if (state.search) {
        const searchLower = state.search.toLowerCase()
        results = results.filter(s => 
          s.name.toLowerCase().includes(searchLower) ||
          s.source.toLowerCase().includes(searchLower) ||
          (s.tags && s.tags.some(tag => tag.toLowerCase().includes(searchLower)))
        )
      }
      
      // Filter by n_outcomes range
      if (state.filters.minOutcomes) {
        const min = parseInt(state.filters.minOutcomes, 10)
        if (!isNaN(min)) {
          results = results.filter(s => s.n_outcomes !== null && s.n_outcomes >= min)
        }
      }
      if (state.filters.maxOutcomes) {
        const max = parseInt(state.filters.maxOutcomes, 10)
        if (!isNaN(max)) {
          results = results.filter(s => s.n_outcomes !== null && s.n_outcomes <= max)
        }
      }
      
      // Filter by rational_fraction range
      if (state.filters.minRationalFraction) {
        const min = parseFloat(state.filters.minRationalFraction)
        if (!isNaN(min)) {
          results = results.filter(s => s.rational_fraction !== null && s.rational_fraction >= min)
        }
      }
      if (state.filters.maxRationalFraction) {
        const max = parseFloat(state.filters.maxRationalFraction)
        if (!isNaN(max)) {
          results = results.filter(s => s.rational_fraction !== null && s.rational_fraction <= max)
        }
      }
      
      // Filter by opposition range
      if (state.filters.minOpposition) {
        const min = parseFloat(state.filters.minOpposition)
        if (!isNaN(min)) {
          results = results.filter(s => s.opposition !== null && s.opposition >= min)
        }
      }
      if (state.filters.maxOpposition) {
        const max = parseFloat(state.filters.maxOpposition)
        if (!isNaN(max)) {
          results = results.filter(s => s.opposition !== null && s.opposition <= max)
        }
      }
      
      return results
    }
  },
  
  actions: {
    async loadSources() {
      try {
        const res = await fetch('/api/scenarios/sources')
        const data = await res.json()
        this.sources = data.sources
      } catch (e) {
        console.error('Failed to load sources:', e)
      }
    },
    
    async loadScenarios(stage = 'full') {
      // Stage can be: 'names', 'basic', 'full'
      // Depending on optimizationMode, we might skip stages
      
      if (stage === 'names') {
        this.loading.names = true
      } else if (stage === 'basic') {
        this.loading.basicInfo = true
      } else {
        this.loading.fullData = true
      }
      
      try {
        const res = await fetch('/api/scenarios')
        const data = await res.json()
        this.scenarios = data.scenarios
      } catch (e) {
        console.error('Failed to load scenarios:', e)
      } finally {
        if (stage === 'names') {
          this.loading.names = false
        } else if (stage === 'basic') {
          this.loading.basicInfo = false
        } else {
          this.loading.fullData = false
        }
      }
    },
    
    async loadScenarioStats(path, force = false) {
      this.statsLoading = true
      this.statsError = null
      try {
        const endpoint = force 
          ? `/api/scenarios/${encodeURIComponent(path)}/stats/calculate?force=true`
          : `/api/scenarios/${encodeURIComponent(path)}/stats`
        
        const method = force ? 'POST' : 'GET'
        const res = await fetch(endpoint, { method })
        
        if (!res.ok) throw new Error('Failed to load stats')
        this.scenarioStats = await res.json()
        
        // Update has_stats flag on selected scenario
        if (this.selectedScenario) {
          this.selectedScenario.has_stats = true
        }
      } catch (e) {
        console.error('Failed to load scenario stats:', e)
        this.statsError = 'Failed to load stats'
      } finally {
        this.statsLoading = false
      }
    },
    
    selectScenario(scenario) {
      this.selectedScenario = scenario
      this.scenarioStats = null
      this.statsError = null
      
      // Auto-load stats if cached
      if (scenario.has_stats) {
        this.loadScenarioStats(scenario.path)
      }
    },
    
    clearSelection() {
      this.selectedScenario = null
      this.scenarioStats = null
      this.statsError = null
    }
  }
})
