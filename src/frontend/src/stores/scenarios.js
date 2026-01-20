import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useScenariosStore = defineStore('scenarios', () => {
  const scenarios = ref([])
  const sources = ref([])
  const selectedScenario = ref(null)
  const selectedScenarioStats = ref(null)
  const selectedScenarioPlotData = ref(null)
  const loading = ref(false)
  const loadingStats = ref(false)
  const loadingPlotData = ref(false)
  const filter = ref({
    search: '',
    source: '',
    minOutcomes: null,
    maxOutcomes: null,
    minOpposition: null,
    maxOpposition: null,
    minRationalFraction: null,
    maxRationalFraction: null,
  })

  async function loadSources() {
    try {
      const response = await fetch('/api/scenarios/sources')
      const data = await response.json()
      sources.value = data.sources || []
    } catch (error) {
      console.error('Failed to load sources:', error)
    }
  }

  async function loadScenarios(source = null) {
    loading.value = true
    try {
      const url = source ? `/api/scenarios?source=${source}` : '/api/scenarios'
      const response = await fetch(url)
      const data = await response.json()
      scenarios.value = data.scenarios || []
    } catch (error) {
      console.error('Failed to load scenarios:', error)
      scenarios.value = []
    } finally {
      loading.value = false
    }
  }

  async function loadScenarioDetails(path) {
    try {
      const response = await fetch(`/api/scenarios/${encodeURIComponent(path)}`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to load scenario details:', error)
      return null
    }
  }

  async function loadScenarioStats(path) {
    loadingStats.value = true
    try {
      const response = await fetch(`/api/scenarios/${encodeURIComponent(path)}/stats`)
      const data = await response.json()
      selectedScenarioStats.value = data
      return data
    } catch (error) {
      console.error('Failed to load scenario stats:', error)
      selectedScenarioStats.value = null
      return null
    } finally {
      loadingStats.value = false
    }
  }

  async function calculateScenarioStats(path, force = false) {
    loadingStats.value = true
    try {
      const url = `/api/scenarios/${encodeURIComponent(path)}/stats/calculate${force ? '?force=true' : ''}`
      const response = await fetch(url, { method: 'POST' })
      const data = await response.json()
      selectedScenarioStats.value = data
      return data
    } catch (error) {
      console.error('Failed to calculate scenario stats:', error)
      return null
    } finally {
      loadingStats.value = false
    }
  }

  async function loadScenarioPlotData(path, maxSamples = 10000) {
    loadingPlotData.value = true
    try {
      const response = await fetch(`/api/scenarios/${encodeURIComponent(path)}/plot-data?max_samples=${maxSamples}`)
      const data = await response.json()
      selectedScenarioPlotData.value = data
      return data
    } catch (error) {
      console.error('Failed to load scenario plot data:', error)
      selectedScenarioPlotData.value = null
      return null
    } finally {
      loadingPlotData.value = false
    }
  }

  function selectScenario(scenario) {
    selectedScenario.value = scenario
    selectedScenarioStats.value = null
    selectedScenarioPlotData.value = null
  }

  function updateFilter(newFilter) {
    filter.value = { ...filter.value, ...newFilter }
  }

  const filteredScenarios = computed(() => {
    return scenarios.value.filter(scenario => {
      // Search filter
      if (filter.value.search && !scenario.name.toLowerCase().includes(filter.value.search.toLowerCase())) {
        return false
      }
      // Source filter
      if (filter.value.source && scenario.source !== filter.value.source) {
        return false
      }
      // Outcomes filter
      if (filter.value.minOutcomes !== null && scenario.n_outcomes < filter.value.minOutcomes) {
        return false
      }
      if (filter.value.maxOutcomes !== null && scenario.n_outcomes > filter.value.maxOutcomes) {
        return false
      }
      // Opposition filter
      if (filter.value.minOpposition !== null && scenario.opposition < filter.value.minOpposition) {
        return false
      }
      if (filter.value.maxOpposition !== null && scenario.opposition > filter.value.maxOpposition) {
        return false
      }
      // Rational fraction filter
      if (filter.value.minRationalFraction !== null && scenario.rational_fraction < filter.value.minRationalFraction) {
        return false
      }
      if (filter.value.maxRationalFraction !== null && scenario.rational_fraction > filter.value.maxRationalFraction) {
        return false
      }
      return true
    })
  })

  return {
    scenarios,
    sources,
    selectedScenario,
    selectedScenarioStats,
    selectedScenarioPlotData,
    loading,
    loadingStats,
    loadingPlotData,
    filter,
    filteredScenarios,
    loadSources,
    loadScenarios,
    loadScenarioDetails,
    loadScenarioStats,
    calculateScenarioStats,
    loadScenarioPlotData,
    selectScenario,
    updateFilter,
  }
})
