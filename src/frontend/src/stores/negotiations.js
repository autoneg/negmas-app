import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNegotiationsStore = defineStore('negotiations', () => {
  const runningNegotiations = ref([])
  const completedNegotiations = ref([])
  const currentNegotiation = ref(null)
  const loading = ref(false)

  async function loadNegotiations() {
    // TODO: Implement API call to load negotiations
    loading.value = true
    try {
      // const response = await fetch('/api/negotiations')
      // const data = await response.json()
      // runningNegotiations.value = data.running
      // completedNegotiations.value = data.completed
    } finally {
      loading.value = false
    }
  }

  function selectNegotiation(negotiation) {
    currentNegotiation.value = negotiation
  }

  return {
    runningNegotiations,
    completedNegotiations,
    currentNegotiation,
    loading,
    loadNegotiations,
    selectNegotiation,
  }
})
