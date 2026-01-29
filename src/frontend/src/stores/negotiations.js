import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Simplified negotiations store using polling instead of SSE.
 * Much simpler, more reliable, easier to debug.
 */
export const useNegotiationsStore = defineStore('negotiations', () => {
  // State
  const sessions = ref([])
  const currentSession = ref(null)
  const loading = ref(false)
  
  // Saved negotiations
  const savedNegotiations = ref([])
  const savedNegotiationsLoading = ref(false)
  const tagFilter = ref('')
  const showArchived = ref(false)
  const availableTags = ref([])
  
  // Session presets
  const sessionPresets = ref([])
  const recentSessions = ref([])

  /**
   * Load all sessions from backend
   */
  async function loadSessions() {
    loading.value = true
    try {
      const response = await fetch('/api/negotiation/sessions/list')
      const data = await response.json()
      sessions.value = data.sessions || []
    } catch (error) {
      console.error('[negotiations store] Failed to load sessions:', error)
      sessions.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Get detailed state for a specific session (for polling)
   */
  async function getSession(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/${sessionId}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      return data
    } catch (error) {
      console.error('[negotiations store] Failed to get session:', error)
      return null
    }
  }

  /**
   * Start a new negotiation (runs in background)
   */
  async function startNegotiation(config) {
    try {
      const response = await fetch('/api/negotiation/start_background', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      return data
    } catch (error) {
      console.error('[negotiations store] Failed to start negotiation:', error)
      throw error
    }
  }

  /**
   * Select current session
   */
  function selectSession(session) {
    currentSession.value = session
  }

  /**
   * Cancel a running session
   */
  async function cancelSession(sessionId) {
    try {
      await fetch(`/api/negotiation/${sessionId}/cancel`, { method: 'POST' })
      await loadSessions()
    } catch (error) {
      console.error('[negotiations store] Failed to cancel session:', error)
    }
  }

  // ============================================================================
  // Saved Negotiations
  // ============================================================================

  async function loadSavedNegotiations() {
    savedNegotiationsLoading.value = true
    try {
      const response = await fetch(
        `/api/negotiation/saved/list?include_archived=${showArchived.value}`
      )
      const data = await response.json()
      savedNegotiations.value = data.negotiations || []
      availableTags.value = data.tags || []
    } catch (error) {
      console.error('[negotiations store] Failed to load saved negotiations:', error)
      savedNegotiations.value = []
    } finally {
      savedNegotiationsLoading.value = false
    }
  }

  async function loadSavedNegotiation(sessionId) {
    try {
      const response = await fetch(`/api/negotiation/saved/${sessionId}`)
      if (!response.ok) return null
      return await response.json()
    } catch (error) {
      console.error('[negotiations store] Failed to load saved negotiation:', error)
      return null
    }
  }

  async function archiveNegotiation(sessionId) {
    try {
      await fetch(`/api/negotiation/saved/${sessionId}/archive`, { method: 'POST' })
      await loadSavedNegotiations()
    } catch (error) {
      console.error('[negotiations store] Failed to archive negotiation:', error)
    }
  }

  async function unarchiveNegotiation(sessionId) {
    try {
      await fetch(`/api/negotiation/saved/${sessionId}/unarchive`, { method: 'POST' })
      await loadSavedNegotiations()
    } catch (error) {
      console.error('[negotiations store] Failed to unarchive negotiation:', error)
    }
  }

  async function deleteNegotiation(sessionId) {
    try {
      await fetch(`/api/negotiation/saved/${sessionId}`, { method: 'DELETE' })
      await loadSavedNegotiations()
    } catch (error) {
      console.error('[negotiations store] Failed to delete negotiation:', error)
    }
  }

  // ============================================================================
  // Session Presets & Recent Sessions
  // ============================================================================

  async function loadSessionPresets() {
    try {
      const response = await fetch('/api/settings/presets/sessions')
      if (response.ok) {
        const data = await response.json()
        sessionPresets.value = data.presets || []
      }
    } catch (error) {
      console.error('[negotiations store] Failed to load session presets:', error)
      sessionPresets.value = []
    }
  }

  async function loadRecentSessions() {
    try {
      const response = await fetch('/api/settings/presets/recent')
      if (response.ok) {
        const data = await response.json()
        recentSessions.value = data.sessions || data.presets || []
      }
    } catch (error) {
      console.error('[negotiations store] Failed to load recent sessions:', error)
      recentSessions.value = []
    }
  }

  async function saveSessionPreset(preset) {
    try {
      const response = await fetch('/api/settings/presets/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset)
      })
      if (response.ok) {
        const result = await response.json()
        await loadSessionPresets()
        return result
      }
      return null
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
      console.error('[negotiations store] Failed to delete session preset:', error)
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
      console.error('[negotiations store] Failed to add to recent sessions:', error)
    }
  }

  return {
    // State
    sessions,
    currentSession,
    loading,
    savedNegotiations,
    savedNegotiationsLoading,
    tagFilter,
    showArchived,
    availableTags,
    sessionPresets,
    recentSessions,
    
    // Actions
    loadSessions,
    getSession,
    startNegotiation,
    selectSession,
    cancelSession,
    loadSavedNegotiations,
    loadSavedNegotiation,
    archiveNegotiation,
    unarchiveNegotiation,
    deleteNegotiation,
    loadSessionPresets,
    loadRecentSessions,
    saveSessionPreset,
    deleteSessionPreset,
    addToRecentSessions,
  }
})
