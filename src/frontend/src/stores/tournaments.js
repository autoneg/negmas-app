import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTournamentsStore = defineStore('tournaments', () => {
  const sessions = ref([])
  const currentSession = ref(null)
  const loading = ref(false)
  const streamingSession = ref(null)
  const eventSource = ref(null)
  
  // Current tournament state (updated via SSE)
  const gridInit = ref(null)
  const cellStates = ref({}) // Map of cell_id -> state
  const leaderboard = ref([])
  const progress = ref(null)
  const tournamentComplete = ref(null)

  async function loadSessions() {
    loading.value = true
    try {
      const response = await fetch('/api/tournament/sessions/list')
      const data = await response.json()
      sessions.value = data.sessions || []
    } catch (error) {
      console.error('Failed to load tournament sessions:', error)
      sessions.value = []
    } finally {
      loading.value = false
    }
  }

  async function getSession(sessionId) {
    try {
      const response = await fetch(`/api/tournament/${sessionId}`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to get tournament session:', error)
      return null
    }
  }

  async function startTournament(config) {
    try {
      const response = await fetch('/api/tournament/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to start tournament:', error)
      return null
    }
  }

  function startStreaming(sessionId) {
    // Close existing stream if any
    stopStreaming()
    
    streamingSession.value = sessionId
    gridInit.value = null
    cellStates.value = {}
    leaderboard.value = []
    progress.value = null
    tournamentComplete.value = null
    
    const url = `/api/tournament/${sessionId}/stream`
    eventSource.value = new EventSource(url)
    
    eventSource.value.addEventListener('grid_init', (event) => {
      const data = JSON.parse(event.data)
      gridInit.value = data
    })
    
    eventSource.value.addEventListener('cell_start', (event) => {
      const data = JSON.parse(event.data)
      cellStates.value[data.cell_id] = { status: 'running', ...data }
    })
    
    eventSource.value.addEventListener('cell_complete', (event) => {
      const data = JSON.parse(event.data)
      cellStates.value[data.cell_id] = { status: 'complete', ...data }
    })
    
    eventSource.value.addEventListener('leaderboard', (event) => {
      const data = JSON.parse(event.data)
      leaderboard.value = data.leaderboard || []
    })
    
    eventSource.value.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data)
      progress.value = data
    })
    
    eventSource.value.addEventListener('complete', (event) => {
      const data = JSON.parse(event.data)
      tournamentComplete.value = data
      stopStreaming()
      loadSessions() // Refresh sessions list
    })
    
    eventSource.value.addEventListener('error', (event) => {
      console.error('Tournament SSE error:', event)
      const data = event.data ? JSON.parse(event.data) : { error: 'Unknown error' }
      tournamentComplete.value = { error: data.error, status: 'failed' }
      stopStreaming()
    })
  }

  function stopStreaming() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    streamingSession.value = null
  }

  async function cancelSession(sessionId) {
    try {
      const response = await fetch(`/api/tournament/${sessionId}/cancel`, {
        method: 'POST',
      })
      const data = await response.json()
      await loadSessions()
      return data
    } catch (error) {
      console.error('Failed to cancel tournament:', error)
      return null
    }
  }

  async function getProgress(sessionId) {
    try {
      const response = await fetch(`/api/tournament/${sessionId}/progress`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to get tournament progress:', error)
      return null
    }
  }

  async function getResults(sessionId) {
    try {
      const response = await fetch(`/api/tournament/${sessionId}/results`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to get tournament results:', error)
      return null
    }
  }

  function selectSession(session) {
    currentSession.value = session
  }

  // Computed: Group sessions by status
  const runningSessions = computed(() => {
    return sessions.value.filter(s => s.status === 'running' || s.status === 'pending')
  })

  const completedSessions = computed(() => {
    return sessions.value.filter(s => s.status === 'completed')
  })

  const failedSessions = computed(() => {
    return sessions.value.filter(s => s.status === 'failed')
  })

  return {
    sessions,
    currentSession,
    loading,
    streamingSession,
    gridInit,
    cellStates,
    leaderboard,
    progress,
    tournamentComplete,
    runningSessions,
    completedSessions,
    failedSessions,
    loadSessions,
    getSession,
    startTournament,
    startStreaming,
    stopStreaming,
    cancelSession,
    getProgress,
    getResults,
    selectSession,
  }
})
