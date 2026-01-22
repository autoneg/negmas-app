import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNegotiationsStore = defineStore('negotiations', () => {
  const sessions = ref([])
  const currentSession = ref(null)
  const loading = ref(false)
  const streamingSession = ref(null)
  const eventSource = ref(null)
  
  // Current session state (updated via SSE)
  const sessionInit = ref(null)
  const offers = ref([])
  const sessionComplete = ref(null)
  
  // Saved negotiations
  const savedNegotiations = ref([])
  const savedNegotiationsLoading = ref(false)
  const tagFilter = ref('')
  const showArchived = ref(false)
  const availableTags = ref([])
  
  // Session presets (saved configurations)
  const sessionPresets = ref([])
  const recentSessions = ref([])

  async function loadSessions() {
    loading.value = true
    try {
      const response = await fetch('/api/negotiation/sessions/list')
      const data = await response.json()
      sessions.value = data.sessions || []
    } catch (error) {
      console.error('Failed to load negotiation sessions:', error)
      sessions.value = []
    } finally {
      loading.value = false
    }
  }

  async function getSession(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to get session:', error)
      return null
    }
  }

  async function startNegotiation(config) {
    try {
      const response = await fetch('/api/negotiation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to start negotiation:', error)
      return null
    }
  }

  async function startNegotiationBackground(config) {
    try {
      const response = await fetch('/api/negotiation/start_background', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to start background negotiation:', error)
      return null
    }
  }

  // Throttling state for smooth updates
  let pendingOffers = []
  let lastUpdateTime = 0
  let updateScheduled = false
  const MIN_UPDATE_INTERVAL = 33 // ~30fps (max 30 updates per second)

  function flushPendingOffers() {
    if (pendingOffers.length === 0) return
    
    // Batch push all pending offers at once
    offers.value.push(...pendingOffers)
    pendingOffers = []
    updateScheduled = false
  }

  function scheduleUpdate() {
    if (updateScheduled) return
    
    const now = performance.now()
    const timeSinceLastUpdate = now - lastUpdateTime
    
    if (timeSinceLastUpdate >= MIN_UPDATE_INTERVAL) {
      // Enough time has passed, update immediately
      lastUpdateTime = now
      requestAnimationFrame(flushPendingOffers)
      updateScheduled = true
    } else {
      // Schedule update for later
      const delay = MIN_UPDATE_INTERVAL - timeSinceLastUpdate
      updateScheduled = true
      setTimeout(() => {
        lastUpdateTime = performance.now()
        requestAnimationFrame(flushPendingOffers)
      }, delay)
    }
  }

  function startStreaming(sessionId, stepDelay = 0.1, shareUfuns = false) {
    // Close existing stream if any
    stopStreaming()
    
    streamingSession.value = sessionId
    sessionInit.value = null
    offers.value = []
    sessionComplete.value = null
    pendingOffers = []
    lastUpdateTime = 0
    updateScheduled = false
    
    const url = `/api/negotiation/${sessionId}/stream?step_delay=${stepDelay}&share_ufuns=${shareUfuns}`
    eventSource.value = new EventSource(url)
    
    eventSource.value.addEventListener('init', (event) => {
      const data = JSON.parse(event.data)
      console.log('[negotiations store] SSE init event received:', {
        hasOutcomeSpaceData: !!data.outcome_space_data,
        data
      })
      sessionInit.value = data
    })
    
    eventSource.value.addEventListener('offer', (event) => {
      const data = JSON.parse(event.data)
      // Queue offer instead of pushing immediately
      pendingOffers.push(data)
      scheduleUpdate()
    })
    
    eventSource.value.addEventListener('complete', (event) => {
      // Flush any remaining offers
      if (pendingOffers.length > 0) {
        offers.value.push(...pendingOffers)
        pendingOffers = []
      }
      
      const data = JSON.parse(event.data)
      sessionComplete.value = data
      stopStreaming()
      loadSessions() // Refresh sessions list
    })
    
    eventSource.value.addEventListener('error', (event) => {
      console.error('SSE error:', event)
      const data = event.data ? JSON.parse(event.data) : { error: 'Unknown error' }
      sessionComplete.value = { error: data.error, status: 'failed' }
      stopStreaming()
    })
  }

  function stopStreaming() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    streamingSession.value = null
    
    // Flush any remaining offers
    if (pendingOffers.length > 0) {
      offers.value.push(...pendingOffers)
      pendingOffers = []
    }
    updateScheduled = false
  }

  async function cancelSession(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}/cancel`, {
        method: 'POST',
      })
      const data = await response.json()
      await loadSessions()
      return data
    } catch (error) {
      console.error('Failed to cancel session:', error)
      return null
    }
  }

  async function pauseSession(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}/pause`, {
        method: 'POST',
      })
      const data = await response.json()
      await loadSessions()
      return data
    } catch (error) {
      console.error('Failed to pause session:', error)
      return null
    }
  }

  async function resumeSession(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}/resume`, {
        method: 'POST',
      })
      const data = await response.json()
      await loadSessions()
      return data
    } catch (error) {
      console.error('Failed to resume session:', error)
      return null
    }
  }

  async function getProgress(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}/progress`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to get progress:', error)
      return null
    }
  }

  async function loadSavedNegotiations(includeArchived = false) {
    savedNegotiationsLoading.value = true
    try {
      const url = `/api/negotiation/saved/list?include_archived=${includeArchived ? 'true' : 'false'}`
      const response = await fetch(url)
      const data = await response.json()
      savedNegotiations.value = data.negotiations || []
      
      // Extract unique tags
      const tags = new Set()
      savedNegotiations.value.forEach(neg => {
        if (neg.tags) {
          neg.tags.forEach(tag => tags.add(tag))
        }
      })
      availableTags.value = Array.from(tags).sort()
      
      return data
    } catch (error) {
      console.error('Failed to load saved negotiations:', error)
      savedNegotiations.value = []
      return null
    } finally {
      savedNegotiationsLoading.value = false
    }
  }

  async function loadSavedNegotiation(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/saved/${sessionId}`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to load saved negotiation:', error)
      return null
    }
  }

  async function deleteSavedNegotiation(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/saved/${sessionId}`, {
        method: 'DELETE'
      })
      await loadSavedNegotiations(showArchived.value)
      return await response.json()
    } catch (error) {
      console.error('Failed to delete saved negotiation:', error)
      return null
    }
  }

  async function clearAllSavedNegotiations(includeArchived = false) {
    try {
      const response = await fetch(`/api/negotiation/saved?include_archived=${includeArchived}`, {
        method: 'DELETE'
      })
      await loadSavedNegotiations(showArchived.value)
      return await response.json()
    } catch (error) {
      console.error('Failed to clear saved negotiations:', error)
      return null
    }
  }

  async function updateNegotiationTags(sessionId, tags) {
    try {
      const response = await fetch(`/api/negotiation/saved/${sessionId}/tags`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags })
      })
      await loadSavedNegotiations(showArchived.value)
      return await response.json()
    } catch (error) {
      console.error('Failed to update tags:', error)
      return null
    }
  }

  function selectSession(session) {
    currentSession.value = session
  }

  // Session preset management
  async function loadSessionPresets() {
    console.log('[negotiations store] loadSessionPresets called')
    try {
      const response = await fetch('/api/settings/presets/sessions')
      console.log('[negotiations store] loadSessionPresets response:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('[negotiations store] Loaded session presets:', data.presets?.length || 0)
        console.log('[negotiations store] Session presets data:', data.presets)
        sessionPresets.value = data.presets || []
        console.log('[negotiations store] sessionPresets.value after assignment:', sessionPresets.value)
      }
    } catch (error) {
      console.error('[negotiations store] Failed to load session presets:', error)
      sessionPresets.value = []
    }
  }

  async function loadRecentSessions() {
    console.log('[negotiations store] loadRecentSessions called')
    try {
      const response = await fetch('/api/settings/presets/recent')
      console.log('[negotiations store] loadRecentSessions response:', response.status)
      if (response.ok) {
        const data = await response.json()
        // Backend returns 'sessions', not 'presets'
        const sessions = data.sessions || data.presets || []
        console.log('[negotiations store] Loaded recent sessions:', sessions.length)
        recentSessions.value = sessions
      }
    } catch (error) {
      console.error('[negotiations store] Failed to load recent sessions:', error)
      recentSessions.value = []
    }
  }

  async function saveSessionPreset(preset) {
    console.log('[negotiations store] saveSessionPreset called with:', preset)
    try {
      const response = await fetch('/api/settings/presets/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset)
      })
      console.log('[negotiations store] Response status:', response.status, response.statusText)
      if (response.ok) {
        const result = await response.json()
        console.log('[negotiations store] Response data:', result)
        await loadSessionPresets()
        return result
      } else {
        const errorText = await response.text()
        console.error('[negotiations store] Save failed:', response.status, errorText)
        return null
      }
    } catch (error) {
      console.error('[negotiations store] Failed to save session preset:', error)
      return null
    }
  }

  async function deleteSessionPreset(name) {
    try {
      const response = await fetch(`/api/settings/presets/sessions/${encodeURIComponent(name)}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        await loadSessionPresets()
        return await response.json()
      }
    } catch (error) {
      console.error('Failed to delete session preset:', error)
      return null
    }
  }

  async function addToRecentSessions(preset) {
    try {
      await fetch('/api/settings/presets/recent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset)
      })
    } catch (error) {
      console.error('Failed to add to recent sessions:', error)
    }
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

  function loadTournamentNegotiation(sessionData) {
    // Load a negotiation from a tournament into the current session
    // This allows viewing tournament negotiations in the negotiation viewer
    
    // Create a session-like object that matches what the viewer expects
    const session = {
      id: sessionData.id,
      status: 'completed',
      fromTournament: true,
      tournamentId: sessionData.tournamentId,
      tournamentNegIndex: sessionData.tournamentNegIndex,
    }
    
    // Set up the session state
    currentSession.value = session
    streamingSession.value = null
    
    // Set up the init data (scenario information)
    sessionInit.value = {
      scenario: sessionData.scenario,
      issue_names: sessionData.issue_names,
      partners: sessionData.partners,
      outcome_space_data: sessionData.outcome_space_data,
    }
    
    // Load all offers
    offers.value = sessionData.offers || []
    
    // Set completion state
    sessionComplete.value = {
      status: 'completed',
      agreement: sessionData.agreement,
      utilities: sessionData.utilities,
      n_steps: sessionData.n_steps,
      end_reason: sessionData.end_reason,
    }
  }

  return {
    sessions,
    currentSession,
    loading,
    streamingSession,
    sessionInit,
    offers,
    sessionComplete,
    runningSessions,
    completedSessions,
    failedSessions,
    savedNegotiations,
    savedNegotiationsLoading,
    tagFilter,
    showArchived,
    availableTags,
    sessionPresets,
    recentSessions,
    loadSessions,
    getSession,
    startNegotiation,
    startNegotiationBackground,
    startStreaming,
    stopStreaming,
    cancelSession,
    pauseSession,
    resumeSession,
    getProgress,
    selectSession,
    loadSavedNegotiations,
    loadSavedNegotiation,
    deleteSavedNegotiation,
    clearAllSavedNegotiations,
    updateNegotiationTags,
    loadSessionPresets,
    loadRecentSessions,
    saveSessionPreset,
    deleteSessionPreset,
    addToRecentSessions,
    loadTournamentNegotiation,
  }
})
