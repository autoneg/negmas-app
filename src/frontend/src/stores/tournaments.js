import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Tournaments store using polling instead of SSE.
 * Much simpler, more reliable, easier to debug.
 */
export const useTournamentsStore = defineStore('tournaments', () => {
  const sessions = ref([])
  const currentSession = ref(null)
  const loading = ref(false)
  const pollingSession = ref(null)
  let pollInterval = null
  
  // Current tournament state (updated via polling)
  const gridInit = ref(null)
  const cellStates = ref({}) // Map of cell_id -> state
  const leaderboard = ref([])
  const progress = ref(null)
  const setupProgress = ref(null) // Setup/initialization progress
  const tournamentComplete = ref(null)
  const liveNegotiations = ref([]) // Live negotiations as they complete
  const runningNegotiations = ref({}) // Map of run_id -> negotiation progress data
  const errorNegotiations = ref([]) // Failed negotiations with error details
  const eventLog = ref([]) // Tournament event log
  const scoreHistory = ref([]) // Score snapshots for chart
  const saveLogs = ref(false) // Whether to save logs on completion
  const tournamentScenarios = ref([]) // Scenario objects for the current tournament
  
  // Grid display settings
  const gridDisplayModes = ref([
    'completion'  // Default: show completion percentage
  ])
  
  // Tournament presets (saved configurations)
  const tournamentPresets = ref([])
  
  // Saved tournaments
  const savedTournaments = ref([])
  const savedTournamentsLoading = ref(false)
  const showArchivedTournaments = ref(false)
  const tournamentTagFilter = ref('')
  const availableTournamentTags = ref([])

  // Track previous state for detecting changes (for event log)
  let previousCompleted = 0
  let previousCellStates = {}

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

  /**
   * Get current tournament state (for polling)
   */
  async function getState(sessionId) {
    try {
      const response = await fetch(`/api/tournament/${sessionId}/state`)
      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Failed to get tournament state:', error)
      return null
    }
  }

  /**
   * Start tournament using the new background endpoint
   */
  async function startTournament(config) {
    try {
      const response = await fetch('/api/tournament/start_background', {
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

  /**
   * Start polling for tournament state updates
   */
  function startPolling(sessionId, config = {}) {
    // Stop any existing polling
    stopPolling()
    
    pollingSession.value = sessionId
    gridInit.value = null
    cellStates.value = {}
    leaderboard.value = []
    liveNegotiations.value = []
    runningNegotiations.value = {}
    errorNegotiations.value = []
    eventLog.value = []
    scoreHistory.value = []
    progress.value = null
    setupProgress.value = null
    tournamentComplete.value = null
    saveLogs.value = config.save_logs || false
    tournamentScenarios.value = config.scenarios || []
    previousCompleted = 0
    previousCellStates = {}
    
    // Add initial event log entry
    eventLog.value.push({
      id: 0,
      timestamp: Date.now(),
      type: 'started',
      message: 'Tournament started'
    })
    
    // Poll every 250ms (4 times per second)
    pollInterval = setInterval(async () => {
      const state = await getState(sessionId)
      
      if (!state) {
        // Session not found - stop polling
        console.log('[Tournaments Store] Session not found, stopping polling')
        stopPolling()
        return
      }
      
      // Update grid init - always update when names change from placeholders
      if (state.grid_init) {
        // Check if we have placeholder names that need updating
        const hasPlaceholders = gridInit.value?.competitors?.some(c => c.startsWith('Competitor '))
        const hasRealNames = state.grid_init.competitors?.some(c => !c.startsWith('Competitor '))
        
        // Update if: no gridInit yet, OR placeholder names being replaced with real names
        if (!gridInit.value || (hasPlaceholders && hasRealNames)) {
          gridInit.value = state.grid_init
        }
      }
      
      // Update cell states
      if (state.cell_states) {
        // Detect new completions for event log
        for (const [cellKey, cellData] of Object.entries(state.cell_states)) {
          const prevCell = previousCellStates[cellKey]
          if (cellData.completed > (prevCell?.completed || 0)) {
            // New completion detected
            const parts = cellKey.split('::')
            if (parts.length >= 3) {
              const [competitor, opponent, scenario] = parts
              let endReasonText = cellData.status
              if (cellData.agreements > (prevCell?.agreements || 0)) {
                endReasonText = 'agreement reached'
              } else if (cellData.errors > (prevCell?.errors || 0)) {
                endReasonText = 'failed'
              } else if (cellData.timeouts > (prevCell?.timeouts || 0)) {
                endReasonText = 'timeout'
              }
              
              eventLog.value.push({
                id: eventLog.value.length,
                timestamp: Date.now(),
                type: cellData.status === 'error' ? 'failed' : (cellData.agreements > 0 ? 'agreement' : 'completed'),
                message: `${competitor} vs ${opponent} on ${scenario} - ${endReasonText}`
              })
            }
          }
        }
        previousCellStates = JSON.parse(JSON.stringify(state.cell_states))
        cellStates.value = state.cell_states
      }
      
      // Update leaderboard and capture score history
      if (state.leaderboard) {
        leaderboard.value = state.leaderboard
        
        // Capture score snapshot for history chart
        if (state.leaderboard.length > 0 && state.progress) {
          const completedCount = state.progress.completed || 0
          
          // Only add if we have new completions
          if (completedCount > previousCompleted) {
            const scores = {}
            state.leaderboard.forEach(entry => {
              const score = entry.score ?? entry.mean_utility ?? null
              if (score !== null && !isNaN(score)) {
                scores[entry.name] = score
              }
            })
            
            if (Object.keys(scores).length > 0) {
              scoreHistory.value.push({
                negotiation: completedCount,
                timestamp: Date.now(),
                scores: scores
              })
            }
            previousCompleted = completedCount
          }
        }
      }
      
      // Update progress
      if (state.progress) {
        progress.value = state.progress
      }
      
      // Update setup progress (for event log during setup phase)
      if (state.setup_progress) {
        const sp = state.setup_progress
        // Only add to event log if message changed
        if (!setupProgress.value || setupProgress.value.message !== sp.message) {
          eventLog.value.push({
            id: eventLog.value.length,
            timestamp: Date.now(),
            type: 'setup',
            message: sp.message
          })
        }
        setupProgress.value = sp
      }
      
      // Update live negotiations (currently running)
      if (state.live_negotiations) {
        // Convert to array format expected by the UI
        runningNegotiations.value = state.live_negotiations
      }
      
      // Update completed negotiations list
      if (state.completed_negotiations) {
        liveNegotiations.value = state.completed_negotiations
      }
      
      // Update current session status
      if (currentSession.value && currentSession.value.id === sessionId) {
        currentSession.value = {
          ...currentSession.value,
          status: state.status
        }
      }
      
      // Check if completed/failed
      if (state.status === 'completed' || state.status === 'failed' || state.status === 'cancelled') {
        tournamentComplete.value = {
          status: state.status,
          results: state.results,
          error: state.error,
          duration_seconds: state.duration_seconds
        }
        
        // Add completion event
        eventLog.value.push({
          id: eventLog.value.length,
          timestamp: Date.now(),
          type: state.status === 'completed' ? 'completed' : 'failed',
          message: state.status === 'completed' ? 'Tournament completed' : `Tournament ${state.status}`
        })
        
        // Save logs if enabled
        if (saveLogs.value && state.results?.results_path) {
          try {
            const pathParts = state.results.results_path.split(/[/\\]/)
            const tournamentId = pathParts[pathParts.length - 1]
            
            if (tournamentId && eventLog.value.length > 0) {
              await fetch(`/api/tournament/saved/${tournamentId}/logs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  logs: eventLog.value.map(e => ({
                    timestamp: e.timestamp,
                    type: e.type,
                    message: e.message
                  }))
                })
              })
            }
          } catch (error) {
            console.error('[Tournaments Store] Failed to save event log:', error)
          }
        }
        
        // Update session status
        if (currentSession.value && currentSession.value.id === sessionId) {
          currentSession.value = {
            ...currentSession.value,
            status: state.status,
            isSaved: state.status === 'completed'
          }
        }
        
        stopPolling()
        loadSessions()
      }
    }, 250) // Poll 4 times per second
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    pollingSession.value = null
  }

  // Keep old function names for compatibility but map to new polling functions
  function startStreaming(sessionId, config = {}) {
    startPolling(sessionId, config)
  }

  function stopStreaming() {
    stopPolling()
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

  // Tournament preset management
  async function loadTournamentPresets() {
    try {
      const response = await fetch('/api/settings/presets/tournaments')
      if (response.ok) {
        const data = await response.json()
        tournamentPresets.value = data.presets || []
      }
    } catch (error) {
      console.error('Failed to load tournament presets:', error)
      tournamentPresets.value = []
    }
  }

  async function saveTournamentPreset(preset) {
    try {
      const response = await fetch('/api/settings/presets/tournaments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset)
      })
      if (response.ok) {
        await loadTournamentPresets()
        return await response.json()
      }
    } catch (error) {
      console.error('Failed to save tournament preset:', error)
      return null
    }
  }

  async function deleteTournamentPreset(name) {
    try {
      const response = await fetch(`/api/settings/presets/tournaments/${encodeURIComponent(name)}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        await loadTournamentPresets()
        return await response.json()
      }
    } catch (error) {
      console.error('Failed to delete tournament preset:', error)
      return null
    }
  }

  // Saved tournaments management
  async function loadSavedTournaments(includeArchived = false) {
    savedTournamentsLoading.value = true
    try {
      const params = new URLSearchParams()
      if (includeArchived !== null) {
        params.append('archived', includeArchived)
      }
      if (tournamentTagFilter.value) {
        params.append('tags', tournamentTagFilter.value)
      }

      const response = await fetch(`/api/tournament/saved/list?${params}`)
      if (response.ok) {
        const data = await response.json()
        savedTournaments.value = data.tournaments || []
        
        // Extract unique tags
        const tags = new Set()
        savedTournaments.value.forEach(t => {
          if (t.tags) {
            t.tags.forEach(tag => tags.add(tag))
          }
        })
        availableTournamentTags.value = Array.from(tags)
        
        return data
      }
      savedTournaments.value = []
      return null
    } catch (error) {
      console.error('Failed to load saved tournaments:', error)
      savedTournaments.value = []
      return null
    } finally {
      savedTournamentsLoading.value = false
    }
  }

  async function loadSavedTournament(tournamentId) {
    try {
      const response = await fetch(`/api/tournament/saved/${tournamentId}`)
      if (!response.ok) {
        if (response.status === 404) {
          console.warn(`Tournament ${tournamentId} not found`)
          return null
        }
        throw new Error(`Failed to load tournament: ${response.statusText}`)
      }
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Failed to load saved tournament:', error)
      return null
    }
  }

  async function deleteSavedTournament(tournamentId) {
    try {
      console.log('[Tournaments Store] Deleting tournament:', tournamentId)
      const response = await fetch(`/api/tournament/saved/${tournamentId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('[Tournaments Store] Delete failed:', response.status, errorData)
        throw new Error(`Delete failed: ${errorData.detail || response.statusText}`)
      }
      
      const result = await response.json()
      console.log('[Tournaments Store] Delete successful:', result)
      
      await loadSavedTournaments(showArchivedTournaments.value)
      return result
    } catch (error) {
      console.error('[Tournaments Store] Failed to delete saved tournament:', error)
      throw error
    }
  }

  async function updateTournamentTags(tournamentId, tags) {
    try {
      const response = await fetch(`/api/tournament/saved/${tournamentId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags })
      })
      await loadSavedTournaments(showArchivedTournaments.value)
      return await response.json()
    } catch (error) {
      console.error('Failed to update tournament tags:', error)
      return null
    }
  }

  async function loadTournamentNegotiations(tournamentId) {
    try {
      const response = await fetch(`/api/tournament/saved/${tournamentId}/details`)
      if (!response.ok) {
        throw new Error(`Failed to load negotiations: ${response.statusText}`)
      }
      const data = await response.json()
      
      // Convert details to liveNegotiations format
      if (data.details && Array.isArray(data.details)) {
        liveNegotiations.value = data.details.map((neg, index) => ({
          index,
          scenario: neg.scenario || neg.effective_scenario_name,
          scenario_path: neg.scenario || neg.effective_scenario_name,
          partners: neg.partners || [],
          end_reason: neg.timedout ? 'timeout' : (neg.broken ? 'broken' : (neg.has_error ? 'error' : (neg.agreement ? 'agreement' : 'disagreement'))),
          has_agreement: !!neg.agreement,
          agreement: neg.agreement,
          utilities: neg.utilities,
          n_steps: neg.n_steps || neg.step || 0,
          issue_names: [], // Not available in details
          offers: [], // Not available in details
          run_id: neg.run_id,
          mechanism_name: neg.mechanism_name
        }))
      }
    } catch (error) {
      console.error('Failed to load tournament negotiations:', error)
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

  // Computed for compatibility - map pollingSession to streamingSession
  const streamingSession = computed(() => pollingSession.value)

  // Clear event log
  function clearEventLog() {
    eventLog.value = []
  }

  /**
   * Set tournament data directly (used when loading from external path)
   * This properly sets the ref values for externally loaded tournaments
   */
  function setLoadedTournamentData(data) {
    if (data.gridInit !== undefined) {
      gridInit.value = data.gridInit
    }
    if (data.cellStates !== undefined) {
      cellStates.value = data.cellStates
    }
    if (data.leaderboard !== undefined) {
      leaderboard.value = data.leaderboard
    }
    if (data.liveNegotiations !== undefined) {
      liveNegotiations.value = data.liveNegotiations
    }
    if (data.eventLog !== undefined) {
      eventLog.value = data.eventLog
    }
    if (data.scoreHistory !== undefined) {
      scoreHistory.value = data.scoreHistory
    }
    if (data.tournamentScenarios !== undefined) {
      tournamentScenarios.value = data.tournamentScenarios
    }
    if (data.progress !== undefined) {
      progress.value = data.progress
    }
    if (data.tournamentComplete !== undefined) {
      tournamentComplete.value = data.tournamentComplete
    }
  }

  // Load event log for a saved tournament
  async function loadEventLog(tournamentId) {
    try {
      const response = await fetch(`/api/tournament/saved/${tournamentId}/logs`)
      if (!response.ok) {
        console.warn(`Failed to load event log for ${tournamentId}:`, response.statusText)
        return []
      }
      const data = await response.json()
      if (data.logs && data.logs.length > 0) {
        // Convert logs to eventLog format
        eventLog.value = data.logs.map((log, index) => ({
          id: index,
          timestamp: new Date(log.timestamp).getTime(),
          type: log.type,
          message: log.message
        }))
        return eventLog.value
      }
      return []
    } catch (error) {
      console.error('Failed to load event log:', error)
      return []
    }
  }

  async function loadScenariosSummary(tournamentId) {
    // Load scenarios summary for saved tournaments (for opposition vs n_outcomes plot)
    try {
      const response = await fetch(`/api/tournament/saved/${tournamentId}/scenarios_summary`)
      if (!response.ok) {
        console.warn(`Failed to load scenarios summary for ${tournamentId}:`, response.statusText)
        return []
      }
      const data = await response.json()
      if (data.scenarios && data.scenarios.length > 0) {
        tournamentScenarios.value = data.scenarios
        return data.scenarios
      }
      return []
    } catch (error) {
      console.error('Failed to load scenarios summary:', error)
      return []
    }
  }

  // Import a tournament from disk
  async function importTournament(sourcePath, options = {}) {
    try {
      const response = await fetch('/api/tournament/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          name: options.name || null,
          delete_original: options.deleteOriginal || false,
          on_collision: options.onCollision || 'rename',
        }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Import failed')
      }
      
      const data = await response.json()
      
      // Refresh the saved tournaments list
      await loadSavedTournaments()
      
      return data
    } catch (error) {
      console.error('Failed to import tournament:', error)
      throw error
    }
  }

  // Load a tournament from disk (view without copying)
  async function loadTournamentFromPath(tournamentPath) {
    try {
      const response = await fetch('/api/tournament/load_from_path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: tournamentPath }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Load failed')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to load tournament from path:', error)
      throw error
    }
  }

  // Validate a path for import
  async function validateImportPath(path) {
    try {
      const response = await fetch('/api/tournament/validate_path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      
      if (!response.ok) {
        return { valid: false, error: 'Validation request failed' }
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to validate path:', error)
      return { valid: false, error: error.message }
    }
  }

  // Preview combining tournaments
  async function previewCombineTournaments(tournamentIds, options = {}) {
    try {
      const response = await fetch('/api/tournament/combine/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tournament_ids: tournamentIds,
          input_paths: options.inputPaths || null,
          recursive: options.recursive !== false,
        }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Preview failed')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to preview combine:', error)
      throw error
    }
  }

  // Combine tournaments
  async function combineTournaments(tournamentIds, options = {}) {
    try {
      const response = await fetch('/api/tournament/combine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tournament_ids: tournamentIds,
          input_paths: options.inputPaths || null,
          output_name: options.outputName || null,
          recursive: options.recursive !== false,
          metadata: options.metadata || null,
        }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Combine failed')
      }
      
      const data = await response.json()
      
      // Refresh the saved tournaments list
      await loadSavedTournaments()
      
      return data
    } catch (error) {
      console.error('Failed to combine tournaments:', error)
      throw error
    }
  }

  // Get storage statistics
  async function getStorageStats() {
    try {
      const response = await fetch('/api/tournament/storage/stats')
      if (!response.ok) {
        throw new Error('Failed to get storage stats')
      }
      return await response.json()
    } catch (error) {
      console.error('Failed to get storage stats:', error)
      throw error
    }
  }

  // Cleanup storage
  async function cleanupStorage(options = {}) {
    try {
      const response = await fetch('/api/tournament/storage/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tournament_id: options.tournamentId || null,
          remove_redundant_csvs: options.removeRedundantCsvs !== false,
          remove_config_json: options.removeConfigJson || false,
        }),
      })
      
      if (!response.ok) {
        throw new Error('Cleanup failed')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to cleanup storage:', error)
      throw error
    }
  }

  return {
    sessions,
    currentSession,
    loading,
    streamingSession, // Computed for compatibility
    pollingSession,
    gridInit,
    cellStates,
    leaderboard,
    liveNegotiations,
    runningNegotiations,
    errorNegotiations,
    eventLog,
    scoreHistory,
    saveLogs,
    tournamentScenarios,
    gridDisplayModes,
    progress,
    setupProgress,
    tournamentComplete,
    tournamentPresets,
    savedTournaments,
    savedTournamentsLoading,
    showArchivedTournaments,
    tournamentTagFilter,
    availableTournamentTags,
    runningSessions,
    completedSessions,
    failedSessions,
    loadSessions,
    getSession,
    getState,
    startTournament,
    startPolling,
    stopPolling,
    cancelSession,
    getProgress,
    getResults,
    selectSession,
    loadTournamentPresets,
    saveTournamentPreset,
    deleteTournamentPreset,
    loadSavedTournaments,
    loadSavedTournament,
    loadTournamentNegotiations,
    deleteSavedTournament,
    updateTournamentTags,
    clearEventLog,
    setLoadedTournamentData,
    loadEventLog,
    loadScenariosSummary,
    // Import/Load/Combine/Storage
    importTournament,
    loadTournamentFromPath,
    validateImportPath,
    previewCombineTournaments,
    combineTournaments,
    getStorageStats,
    cleanupStorage,
  }
})
