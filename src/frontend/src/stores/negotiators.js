import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNegotiatorsStore = defineStore('negotiators', () => {
  const negotiators = ref([])
  const sources = ref([])
  const selectedNegotiator = ref(null)
  const selectedNegotiatorParams = ref(null)
  const virtualNegotiators = ref([])
  const loading = ref(false)
  const loadingParams = ref(false)
  const filter = ref({
    search: '',
    source: '',
    group: '',
    mechanism: '',
    availableOnly: true,
  })

  async function loadNegotiators(sourceFilter = null, groupFilter = null, searchFilter = null) {
    loading.value = true
    try {
      const params = new URLSearchParams()
      if (sourceFilter) params.append('source', sourceFilter)
      if (groupFilter) params.append('group', groupFilter)
      if (searchFilter) params.append('search', searchFilter)
      
      const url = `/api/negotiators${params.toString() ? '?' + params.toString() : ''}`
      const response = await fetch(url)
      const data = await response.json()
      negotiators.value = data.negotiators || []
    } catch (error) {
      console.error('Failed to load negotiators:', error)
      negotiators.value = []
    } finally {
      loading.value = false
    }
  }

  async function loadSources() {
    try {
      const response = await fetch('/api/negotiators/sources')
      const data = await response.json()
      sources.value = data.sources || []
    } catch (error) {
      console.error('Failed to load negotiator sources:', error)
      sources.value = []
    }
  }

  async function loadNegotiatorParameters(typeName) {
    loadingParams.value = true
    try {
      const response = await fetch(`/api/negotiators/${encodeURIComponent(typeName)}/parameters`)
      const data = await response.json()
      selectedNegotiatorParams.value = data.parameters || []
      return data
    } catch (error) {
      console.error('Failed to load negotiator parameters:', error)
      selectedNegotiatorParams.value = []
      return null
    } finally {
      loadingParams.value = false
    }
  }

  async function loadVirtualNegotiators() {
    try {
      const response = await fetch('/api/negotiators/virtual')
      const data = await response.json()
      virtualNegotiators.value = data.virtual_negotiators || []
    } catch (error) {
      console.error('Failed to load virtual negotiators:', error)
      virtualNegotiators.value = []
    }
  }

  async function createVirtualNegotiator(name, baseTypeName, params = {}, description = '', tags = []) {
    try {
      const response = await fetch('/api/negotiators/virtual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          base_type_name: baseTypeName,
          params,
          description,
          tags,
        }),
      })
      const data = await response.json()
      if (data.success) {
        await loadVirtualNegotiators()
        return data
      }
      return null
    } catch (error) {
      console.error('Failed to create virtual negotiator:', error)
      return null
    }
  }

  async function deleteVirtualNegotiator(id) {
    try {
      const response = await fetch(`/api/negotiators/virtual/${id}`, {
        method: 'DELETE',
      })
      const data = await response.json()
      if (data.success) {
        await loadVirtualNegotiators()
        return true
      }
      return false
    } catch (error) {
      console.error('Failed to delete virtual negotiator:', error)
      return false
    }
  }

  function selectNegotiator(negotiator) {
    selectedNegotiator.value = negotiator
    selectedNegotiatorParams.value = null
  }

  function updateFilter(newFilter) {
    filter.value = { ...filter.value, ...newFilter }
  }

  const filteredNegotiators = computed(() => {
    return negotiators.value.filter(negotiator => {
      // Search filter
      if (filter.value.search) {
        const search = filter.value.search.toLowerCase()
        if (!negotiator.name.toLowerCase().includes(search) && 
            !negotiator.type_name.toLowerCase().includes(search) &&
            !(negotiator.description || '').toLowerCase().includes(search)) {
          return false
        }
      }
      
      // Source filter
      if (filter.value.source && negotiator.source !== filter.value.source) {
        return false
      }
      
      // Group filter
      if (filter.value.group && negotiator.group !== filter.value.group) {
        return false
      }
      
      // Mechanism filter
      if (filter.value.mechanism && !negotiator.mechanisms.includes(filter.value.mechanism)) {
        return false
      }
      
      // Available only filter
      if (filter.value.availableOnly && !negotiator.available) {
        return false
      }
      
      return true
    })
  })

  // Get unique groups from current negotiators
  const availableGroups = computed(() => {
    const groups = new Set()
    negotiators.value.forEach(n => {
      if (n.group) groups.add(n.group)
    })
    return Array.from(groups).sort()
  })

  // Get unique mechanisms from current negotiators
  const availableMechanisms = computed(() => {
    const mechanisms = new Set()
    negotiators.value.forEach(n => {
      n.mechanisms.forEach(m => mechanisms.add(m))
    })
    return Array.from(mechanisms).sort()
  })

  return {
    negotiators,
    sources,
    selectedNegotiator,
    selectedNegotiatorParams,
    virtualNegotiators,
    loading,
    loadingParams,
    filter,
    filteredNegotiators,
    availableGroups,
    availableMechanisms,
    loadNegotiators,
    loadSources,
    loadNegotiatorParameters,
    loadVirtualNegotiators,
    createVirtualNegotiator,
    deleteVirtualNegotiator,
    selectNegotiator,
    updateFilter,
  }
})
