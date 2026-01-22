import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref({
    general: {
      dark_mode: false,
      color_blind_mode: false,
      save_negotiations: true,
      cache_scenario_stats: true,
    },
    negotiation: {
      default_max_steps: 100,
      default_step_delay_ms: 100,
      default_time_limit: null,
    },
    genius_bridge: {
      auto_start: true,
      java_path: null,
      port: 25337,
    },
    paths: {
      scenario_paths: [],
      user_scenarios: '~/negmas/app/scenarios',
    },
    performance: {
      max_outcomes_run: null,
      max_outcomes_stats: 1000000,
      max_outcomes_info: 10000000,
      plot_image_format: 'webp',
    },
  })

  const loading = ref(false)
  const saving = ref(false)

  async function loadSettings() {
    loading.value = true
    try {
      const response = await fetch('/api/settings')
      const data = await response.json()
      settings.value = data
      
      // Apply dark mode immediately
      applyTheme()
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      loading.value = false
    }
  }

  async function saveSettings() {
    saving.value = true
    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings.value),
      })
      const data = await response.json()
      settings.value = data
      
      // Apply theme changes
      applyTheme()
      
      return { success: true }
    } catch (error) {
      console.error('Failed to save settings:', error)
      return { success: false, error }
    } finally {
      saving.value = false
    }
  }

  function applyTheme() {
    const html = document.documentElement
    
    // Dark mode
    if (settings.value.general.dark_mode) {
      html.classList.add('dark-mode')
    } else {
      html.classList.remove('dark-mode')
    }
    
    // Color blind mode
    if (settings.value.general.color_blind_mode) {
      html.classList.add('color-blind-mode')
    } else {
      html.classList.remove('color-blind-mode')
    }
  }

  async function exportSettings() {
    try {
      const response = await fetch('/api/settings/export')
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        
        // Get filename from Content-Disposition header
        const disposition = response.headers.get('Content-Disposition')
        const filenameMatch = disposition?.match(/filename=([^;]+)/)
        a.download = filenameMatch ? filenameMatch[1] : 'negmas_settings.zip'
        
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        return { success: true }
      } else {
        return { success: false, error: 'Export failed' }
      }
    } catch (error) {
      console.error('Failed to export settings:', error)
      return { success: false, error }
    }
  }

  async function importSettings(file) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch('/api/settings/import', {
        method: 'POST',
        body: formData,
      })
      
      const result = await response.json()
      
      if (result.status === 'success' || result.status === 'partial') {
        // Reload settings after import
        await loadSettings()
        return { 
          success: true, 
          message: `Imported ${result.imported?.length || 0} files`,
          partial: result.status === 'partial',
        }
      } else {
        return { success: false, error: result.message || 'Import failed' }
      }
    } catch (error) {
      console.error('Failed to import settings:', error)
      return { success: false, error }
    }
  }

  function resetToDefaults() {
    settings.value = {
      general: {
        dark_mode: false,
        color_blind_mode: false,
        save_negotiations: true,
        cache_scenario_stats: true,
      },
      negotiation: {
        default_max_steps: 100,
        default_step_delay_ms: 100,
        default_time_limit: null,
      },
      genius_bridge: {
        auto_start: true,
        java_path: null,
        port: 25337,
      },
      paths: {
        scenario_paths: [],
        user_scenarios: '~/negmas/app/scenarios',
      },
      performance: {
        max_outcomes_run: null,
        max_outcomes_stats: 1000000,
        max_outcomes_info: 10000000,
      },
    }
  }

  return {
    settings,
    loading,
    saving,
    loadSettings,
    saveSettings,
    applyTheme,
    exportSettings,
    importSettings,
    resetToDefaults,
  }
})
