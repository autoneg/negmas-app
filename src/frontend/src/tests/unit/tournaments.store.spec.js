/**
 * Unit tests for tournaments Pinia store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTournamentsStore } from '@/stores/tournaments'

// Mock fetch
global.fetch = vi.fn()

describe('Tournaments Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('Tournament Presets', () => {
    it('should initialize with empty presets', () => {
      const store = useTournamentsStore()
      expect(store.tournamentPresets).toEqual([])
    })

    it('should load tournament presets from API', async () => {
      const mockPresets = [
        {
          name: 'Tournament Preset 1',
          scenario_paths: ['/path/1', '/path/2'],
          competitor_types: ['Type1', 'Type2'],
          n_repetitions: 3,
        },
        {
          name: 'Tournament Preset 2',
          scenario_paths: ['/path/3'],
          competitor_types: ['Type3'],
          n_repetitions: 5,
        },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ presets: mockPresets }),
      })

      const store = useTournamentsStore()
      await store.loadTournamentPresets()

      expect(global.fetch).toHaveBeenCalledWith('/api/settings/presets/tournaments')
      expect(store.tournamentPresets).toEqual(mockPresets)
    })

    it('should handle load presets API error gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })

      const store = useTournamentsStore()
      await store.loadTournamentPresets()

      expect(store.tournamentPresets).toEqual([])
    })

    it('should save a tournament preset with all fields', async () => {
      const presetData = {
        name: 'My Tournament Preset',
        scenario_paths: ['/path/1', '/path/2'],
        competitor_types: ['Agent1', 'Agent2'],
        opponent_types: null,
        opponents_same_as_competitors: true,
        n_repetitions: 5,
        n_steps: 100,
        mechanism_type: 'SAOMechanism',
        final_score_metric: 'advantage',
        final_score_stat: 'mean',
        rotate_ufuns: true,
        self_play: false,
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => presetData,
      })

      const store = useTournamentsStore()
      const result = await store.saveTournamentPreset(presetData)

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/settings/presets/tournaments',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(presetData),
        })
      )
      expect(result).toBe(true)
    })

    it('should delete a tournament preset', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      })

      const store = useTournamentsStore()
      const result = await store.deleteTournamentPreset('Test Preset')

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/settings/presets/tournaments/Test Preset',
        expect.objectContaining({ method: 'DELETE' })
      )
      expect(result).toBe(true)
    })

    it('should handle delete preset failure', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      })

      const store = useTournamentsStore()
      const result = await store.deleteTournamentPreset('NonExistent')

      expect(result).toBe(false)
    })
  })

  describe('Saved Tournaments', () => {
    it('should initialize with empty saved tournaments', () => {
      const store = useTournamentsStore()
      expect(store.savedTournaments).toEqual([])
    })

    it('should load saved tournaments list', async () => {
      const mockTournaments = [
        {
          id: 'tourn-1',
          name: 'Saved Tournament 1',
          status: 'completed',
          competitors: ['Agent1', 'Agent2'],
          scenarios: ['Scenario1'],
          tags: ['test'],
        },
        {
          id: 'tourn-2',
          name: 'Saved Tournament 2',
          status: 'completed',
          competitors: ['Agent3'],
          scenarios: ['Scenario2', 'Scenario3'],
          tags: [],
        },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tournaments: mockTournaments }),
      })

      const store = useTournamentsStore()
      await store.loadSavedTournaments()

      expect(global.fetch).toHaveBeenCalledWith('/api/tournament/saved/list')
      expect(store.savedTournaments).toEqual(mockTournaments)
      expect(store.savedTournamentsLoading).toBe(false)
    })

    it('should set loading state during fetch', async () => {
      global.fetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({ tournaments: [] }),
            })
          }, 100)
        })
      })

      const store = useTournamentsStore()
      
      expect(store.savedTournamentsLoading).toBe(false)
      
      const promise = store.loadSavedTournaments()
      expect(store.savedTournamentsLoading).toBe(true)
      
      await promise
      expect(store.savedTournamentsLoading).toBe(false)
    })

    it('should load a specific saved tournament', async () => {
      const mockTournament = {
        id: 'tourn-123',
        name: 'Test Tournament',
        status: 'completed',
        config: { n_repetitions: 3 },
        results: {},
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTournament,
      })

      const store = useTournamentsStore()
      const result = await store.loadSavedTournament('tourn-123')

      expect(global.fetch).toHaveBeenCalledWith('/api/tournament/saved/tourn-123')
      expect(result).toEqual(mockTournament)
    })

    it('should delete a saved tournament', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      })

      const store = useTournamentsStore()
      const result = await store.deleteSavedTournament('tourn-123')

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/tournament/saved/tourn-123',
        expect.objectContaining({ method: 'DELETE' })
      )
      expect(result).toBe(true)
    })

    it('should update tournament tags', async () => {
      const tags = ['important', 'final-demo', 'results']

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags }),
      })

      const store = useTournamentsStore()
      await store.updateTournamentTags('tourn-123', tags)

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/tournament/saved/tourn-123/tags',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tags }),
        })
      )
    })
  })

  describe('Tag Filtering', () => {
    it('should extract available tags from tournaments', async () => {
      const mockTournaments = [
        { id: '1', tags: ['test', 'demo'] },
        { id: '2', tags: ['test', 'important'] },
        { id: '3', tags: ['demo', 'final'] },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tournaments: mockTournaments }),
      })

      const store = useTournamentsStore()
      await store.loadSavedTournaments()

      expect(store.availableTournamentTags).toContain('test')
      expect(store.availableTournamentTags).toContain('demo')
      expect(store.availableTournamentTags).toContain('important')
      expect(store.availableTournamentTags).toContain('final')
      expect(store.availableTournamentTags.length).toBe(4)
    })

    it('should filter tournaments by tag', async () => {
      const mockTournaments = [
        { id: '1', name: 'T1', tags: ['test'] },
        { id: '2', name: 'T2', tags: ['demo'] },
        { id: '3', name: 'T3', tags: ['test', 'demo'] },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tournaments: mockTournaments }),
      })

      const store = useTournamentsStore()
      await store.loadSavedTournaments()

      store.tournamentTagFilter = 'demo'

      // Simulating the filter logic
      const filtered = store.savedTournaments.filter(
        (t) => !store.tournamentTagFilter || t.tags.includes(store.tournamentTagFilter)
      )

      expect(filtered.length).toBe(2)
      expect(filtered.map((t) => t.id)).toEqual(['2', '3'])
    })

    it('should show all tournaments when no tag filter is set', async () => {
      const mockTournaments = [
        { id: '1', tags: ['test'] },
        { id: '2', tags: ['demo'] },
        { id: '3', tags: [] },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tournaments: mockTournaments }),
      })

      const store = useTournamentsStore()
      await store.loadSavedTournaments()

      store.tournamentTagFilter = ''

      const filtered = store.savedTournaments.filter(
        (t) => !store.tournamentTagFilter || t.tags.includes(store.tournamentTagFilter)
      )

      expect(filtered.length).toBe(3)
    })
  })

  describe('Archive Functionality', () => {
    it('should toggle showArchivedTournaments flag', () => {
      const store = useTournamentsStore()
      
      expect(store.showArchivedTournaments).toBe(false)
      store.showArchivedTournaments = true
      expect(store.showArchivedTournaments).toBe(true)
    })

    it('should filter archived tournaments when flag is false', async () => {
      const mockTournaments = [
        { id: '1', name: 'T1', archived: false },
        { id: '2', name: 'T2', archived: true },
        { id: '3', name: 'T3', archived: false },
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tournaments: mockTournaments }),
      })

      const store = useTournamentsStore()
      await store.loadSavedTournaments()

      store.showArchivedTournaments = false

      // Simulating archive filter
      const filtered = store.savedTournaments.filter(
        (t) => store.showArchivedTournaments || !t.archived
      )

      expect(filtered.length).toBe(2)
      expect(filtered.map((t) => t.id)).toEqual(['1', '3'])
    })
  })

  describe('Tournament Configuration', () => {
    it('should handle tournament presets with variable steps', async () => {
      const presetWithVariableSteps = {
        name: 'Variable Steps Tournament',
        scenario_paths: ['/path/1'],
        competitor_types: ['Agent1'],
        n_steps_min: 50,
        n_steps_max: 200,
        n_steps: null,
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => presetWithVariableSteps,
      })

      const store = useTournamentsStore()
      await store.saveTournamentPreset(presetWithVariableSteps)

      expect(global.fetch).toHaveBeenCalled()
    })

    it('should handle tournament presets with time limits', async () => {
      const presetWithTimeLimits = {
        name: 'Time Limited Tournament',
        scenario_paths: ['/path/1'],
        competitor_types: ['Agent1'],
        time_limit: 60.0,
        time_limit_min: 30.0,
        time_limit_max: 120.0,
        step_time_limit: 5.0,
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => presetWithTimeLimits,
      })

      const store = useTournamentsStore()
      await store.saveTournamentPreset(presetWithTimeLimits)

      expect(global.fetch).toHaveBeenCalled()
    })
  })
})
