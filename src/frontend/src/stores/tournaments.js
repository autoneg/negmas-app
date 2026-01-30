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
  const setupProgress = ref(null) // Setup/initialization progress
  const tournamentComplete = ref(null)
  const liveNegotiations = ref([]) // Live negotiations as they complete
  const runningNegotiations = ref({}) // Map of run_id -> negotiation progress data
  const errorNegotiations = ref([]) // Failed negotiations with error details
  const eventLog = ref([]) // Tournament event log (populated from callbacks, not neg_* events)
  const saveLogs = ref(false) // Whether to save logs on completion
  
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

  function startStreaming(sessionId, config = {}) {
    // Close existing stream if any
    stopStreaming()
    
    streamingSession.value = sessionId
    gridInit.value = null
    cellStates.value = {}
    leaderboard.value = []
    liveNegotiations.value = []
    runningNegotiations.value = {}
    errorNegotiations.value = []
    eventLog.value = []
    progress.value = null
    setupProgress.value = null
    tournamentComplete.value = null
    saveLogs.value = config.save_logs || false
    
    const url = `/api/tournament/${sessionId}/stream`
    eventSource.value = new EventSource(url)
    
    eventSource.value.addEventListener('grid_init', (event) => {
      const data = JSON.parse(event.data)
      gridInit.value = data
      
      // Add event log entry for tournament start
      eventLog.value.push({
        id: eventLog.value.length,
        timestamp: Date.now(),
        type: 'started',
        message: 'Tournament started'
      })
    })
    
    eventSource.value.addEventListener('cell_start', (event) => {
      const data = JSON.parse(event.data)
      // Create cell key using names from gridInit
      if (gridInit.value) {
        const competitor = gridInit.value.competitors[data.competitor_idx]
        const opponent = gridInit.value.opponents[data.opponent_idx]
        const scenario = gridInit.value.scenarios[data.scenario_idx]
        const cellKey = `${competitor}::${opponent}::${scenario}`
        
        // Add event log entry for cell start
        eventLog.value.push({
          id: eventLog.value.length,
          timestamp: Date.now(),
          type: 'cell_start',
          message: `${competitor} vs ${opponent} on ${scenario} - started`
        })
        
        // Initialize or update cell state with aggregation support (create new object for reactivity)
        if (!cellStates.value[cellKey]) {
          cellStates.value = {
            ...cellStates.value,
            [cellKey]: {
              status: 'running',
              total: gridInit.value.n_repetitions * (gridInit.value.rotate_ufuns ? 2 : 1),
              completed: 0,
              agreements: 0,
              timeouts: 0,
              errors: 0,
              running: 1
            }
          }
        } else {
          cellStates.value = {
            ...cellStates.value,
            [cellKey]: {
              ...cellStates.value[cellKey],
              status: 'running',
              running: (cellStates.value[cellKey].running || 0) + 1
            }
          }
        }
      }
    })
    
    eventSource.value.addEventListener('cell_complete', (event) => {
      const data = JSON.parse(event.data)
      console.log('[Tournaments Store] cell_complete event:', data)
      
      // Create cell key using names from gridInit
      if (gridInit.value) {
        const competitor = gridInit.value.competitors[data.competitor_idx]
        const opponent = gridInit.value.opponents[data.opponent_idx]
        const scenario = gridInit.value.scenarios[data.scenario_idx]
        const cellKey = `${competitor}::${opponent}::${scenario}`
        
        console.log('[Tournaments Store] Cell indices:', {
          competitor_idx: data.competitor_idx,
          opponent_idx: data.opponent_idx,
          scenario_idx: data.scenario_idx
        })
        console.log('[Tournaments Store] Cell names:', {
          competitor,
          opponent,
          scenario
        })
        console.log('[Tournaments Store] Cell key:', cellKey)
        console.log('[Tournaments Store] Grid info:', {
          n_competitors: gridInit.value.competitors?.length,
          n_opponents: gridInit.value.opponents?.length,
          n_scenarios: gridInit.value.scenarios?.length
        })
        
        // Get existing state or create default
        const existingCell = cellStates.value[cellKey] || {
          status: 'complete',
          total: gridInit.value.n_repetitions * (gridInit.value.rotate_ufuns ? 2 : 1),
          completed: 0,
          agreements: 0,
          timeouts: 0,
          errors: 0,
          running: 0,
          has_agreement: false,
          has_error: false
        }
        
        // Calculate updated values
        const completed = (existingCell.completed || 0) + 1
        const running = Math.max(0, (existingCell.running || 0) - 1)
        let agreements = existingCell.agreements || 0
        let timeouts = existingCell.timeouts || 0
        let errors = existingCell.errors || 0
        let has_agreement = existingCell.has_agreement || false
        let has_error = existingCell.has_error || false
        
        // Update aggregated stats based on end_reason
        if (data.end_reason === 'agreement') {
          agreements += 1
          has_agreement = true
        } else if (data.end_reason === 'timeout') {
          timeouts += 1
        } else if (data.end_reason === 'error' || data.end_reason === 'broken') {
          errors += 1
          has_error = true
        }
        
        // Determine final status
        const allComplete = completed >= existingCell.total
        let status = existingCell.status || 'pending' // Preserve existing status as default
        if (allComplete) {
          if (errors > 0) {
            status = 'error'
          } else if (agreements > 0) {
            status = 'complete'
          } else if (timeouts > 0) {
            status = 'timeout'
          } else {
            status = 'complete'
          }
        } else if (running > 0) {
          status = 'running'
        } else if (completed > 0) {
          // Has some completed but not all, and nothing running
          status = 'running' // Tournament is ongoing, just no active negotiations in this cell right now
        }
        
        // Create new object to trigger reactivity
        cellStates.value = {
          ...cellStates.value,
          [cellKey]: {
            status,
            total: existingCell.total,
            completed,
            agreements,
            timeouts,
            errors,
            running,
            has_agreement,
            has_error
          }
        }
        
        // Add event log entry for cell completion
        let endReasonText = data.end_reason
        if (data.end_reason === 'agreement') {
          endReasonText = 'agreement reached'
        } else if (data.end_reason === 'timeout') {
          endReasonText = 'timeout'
        } else if (data.end_reason === 'error' || data.end_reason === 'broken') {
          endReasonText = 'failed'
        }
        
        eventLog.value.push({
          id: eventLog.value.length,
          timestamp: Date.now(),
          type: data.end_reason === 'agreement' ? 'agreement' : (data.end_reason === 'error' || data.end_reason === 'broken' ? 'failed' : 'completed'),
          message: `${competitor} vs ${opponent} on ${scenario} - ${endReasonText}`
        })
        
        // Add to live negotiations if we have the detailed data
        if (data.issue_names && data.scenario_path) {
          // Check if this negotiation already exists in liveNegotiations
          // Match by scenario path and partners (order-independent)
          const existingIndex = liveNegotiations.value.findIndex(n => {
            if (n.scenario_path !== data.scenario_path) return false
            
            // Check if partners match (order-independent)
            const nPartners = new Set(n.partners || [])
            const dataPartners = new Set([competitor, opponent])
            
            if (nPartners.size !== dataPartners.size) return false
            
            for (const p of dataPartners) {
              if (!nPartners.has(p)) return false
            }
            
            return true
          })
          
          if (existingIndex >= 0) {
            console.log('[Tournaments Store] Found duplicate negotiation:', {
              existingIndex,
              scenario: data.scenario_path,
              partners: [competitor, opponent],
              existing: liveNegotiations.value[existingIndex]
            })
          }
          
          const negotiation = {
            index: existingIndex >= 0 ? liveNegotiations.value[existingIndex].index : liveNegotiations.value.length,
            scenario: data.scenario_path || scenario,
            scenario_path: data.scenario_path,
            partners: [competitor, opponent],
            end_reason: data.end_reason,
            has_agreement: data.end_reason === 'agreement',
            has_error: data.end_reason === 'error' || data.end_reason === 'broken',
            agreement: data.agreement || null,
            utilities: data.utilities || {},
            n_steps: data.n_steps || 0,
            issue_names: data.issue_names || [],
            offers: data.offers || [],
            error: data.error || null
          }
          
          if (existingIndex >= 0) {
            // Update existing negotiation instead of adding duplicate
            console.log('[Tournaments Store] Updating existing negotiation at index', existingIndex)
            liveNegotiations.value[existingIndex] = negotiation
          } else {
            // Add new negotiation
            console.log('[Tournaments Store] Adding new negotiation:', {
              index: negotiation.index,
              scenario: negotiation.scenario_path,
              partners: negotiation.partners
            })
            liveNegotiations.value.push(negotiation)
          }
          
          // Track errors separately for error panel
          if (negotiation.has_error) {
            errorNegotiations.value.push({
              timestamp: Date.now(),
              scenario: data.scenario_path || scenario,
              partners: [competitor, opponent],
              error: data.error || 'Unknown error',
              n_steps: data.n_steps || 0,
              cellKey
            })
          }
        }
      }
    })
    
    eventSource.value.addEventListener('leaderboard', (event) => {
      const data = JSON.parse(event.data)
      console.log('[Tournaments Store] Leaderboard event received:', data)
      // Backend sends array directly, not wrapped in {leaderboard: [...]}
      leaderboard.value = Array.isArray(data) ? data : []
    })
    
    eventSource.value.addEventListener('setup_progress', (event) => {
      const data = JSON.parse(event.data)
      console.log('[Tournaments Store] Setup progress event:', data)
      setupProgress.value = data
      
      // Add event log entry for setup progress
      if (data.message) {
        eventLog.value.push({
          id: eventLog.value.length,
          timestamp: Date.now(),
          type: 'progress',
          message: data.message
        })
      }
    })
    
    eventSource.value.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data)
      progress.value = data
      
      // Add event log entry for progress updates
      if (data.message) {
        eventLog.value.push({
          id: eventLog.value.length,
          timestamp: Date.now(),
          type: 'progress',
          message: data.message
        })
      }
    })
    
    // Negotiation monitoring events
    eventSource.value.addEventListener('neg_start', (event) => {
      const data = JSON.parse(event.data)
      runningNegotiations.value[data.run_id] = {
        run_id: data.run_id,
        step: data.step,
        relative_time: data.relative_time,
        status: 'running'
      }
    })
    
    eventSource.value.addEventListener('neg_progress', (event) => {
      const data = JSON.parse(event.data)
      if (runningNegotiations.value[data.run_id]) {
        runningNegotiations.value[data.run_id].step = data.step
        runningNegotiations.value[data.run_id].relative_time = data.relative_time
        runningNegotiations.value[data.run_id].current_offer = data.current_offer
        runningNegotiations.value[data.run_id].current_proposer = data.current_proposer
      }
    })
    
    eventSource.value.addEventListener('neg_end', (event) => {
      const data = JSON.parse(event.data)
      if (runningNegotiations.value[data.run_id]) {
        runningNegotiations.value[data.run_id].status = 'complete'
        runningNegotiations.value[data.run_id].step = data.step
        runningNegotiations.value[data.run_id].relative_time = data.relative_time
        runningNegotiations.value[data.run_id].agreement = data.agreement
        runningNegotiations.value[data.run_id].timedout = data.timedout
        runningNegotiations.value[data.run_id].broken = data.broken
        runningNegotiations.value[data.run_id].has_error = data.has_error
        
        // Clean up after a delay
        setTimeout(() => {
          delete runningNegotiations.value[data.run_id]
        }, 5000)
      }
    })
    
    eventSource.value.addEventListener('complete', async (event) => {
      const data = JSON.parse(event.data)
      tournamentComplete.value = data
      
      // Add event log entry for tournament completion
      eventLog.value.push({
        id: eventLog.value.length,
        timestamp: Date.now(),
        type: 'completed',
        message: 'Tournament completed'
      })
      
      // Save logs if enabled and we have a valid results path
      if (saveLogs.value && data.results?.results_path) {
        try {
          // Extract tournament ID from path (last component)
          const pathParts = data.results.results_path.split(/[/\\]/)
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
            console.log('[Tournaments Store] Saved event log to', tournamentId)
          }
        } catch (error) {
          console.error('[Tournaments Store] Failed to save event log:', error)
        }
      }
      
      // Update current session status to completed so UI reflects the change
      if (currentSession.value && currentSession.value.id === sessionId) {
        currentSession.value = {
          ...currentSession.value,
          status: 'completed',
          isSaved: true
        }
      }
      
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

  // Clear event log
  function clearEventLog() {
    eventLog.value = []
  }

  return {
    sessions,
    currentSession,
    loading,
    streamingSession,
    gridInit,
    cellStates,
    leaderboard,
    liveNegotiations,
    runningNegotiations,
    errorNegotiations,
    eventLog,
    saveLogs,
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
    startTournament,
    startStreaming,
    stopStreaming,
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
  }
})
