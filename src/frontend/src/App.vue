<template>
  <div id="app">
    <!-- Toast Notification -->
    <div v-if="toastVisible" 
         :class="['toast-container', `toast-${toastType}`]"
         style="position: fixed; top: 20px; right: 20px; z-index: 10000; padding: 12px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-weight: 500;">
      {{ toastMessage }}
    </div>

    <div class="app-container">
      <!-- Header -->
      <header class="header">
        <div class="header-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
          <span>NegMAS Vue</span>
        </div>
        
        <nav class="header-nav">
          <router-link to="/negotiations" class="header-nav-btn" active-class="active">Negotiations</router-link>
          <router-link to="/tournaments" class="header-nav-btn" active-class="active">Tournaments</router-link>
          <router-link to="/scenarios" class="header-nav-btn" active-class="active">Scenarios</router-link>
          <router-link to="/negotiators" class="header-nav-btn" active-class="active">Negotiators</router-link>
          <button class="header-nav-btn" @click="showSettings = true">Settings</button>
        </nav>
        
        <div class="header-spacer"></div>
        
        <!-- Loading Indicator -->
        <div class="header-status header-loading" v-if="scenariosLoading || negotiatorsLoading">
          <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="12"></circle>
          </svg>
          <span>{{ scenariosLoading && negotiatorsLoading ? 'Loading data...' : (scenariosLoading ? 'Loading scenarios...' : 'Loading negotiators...') }}</span>
        </div>
        
        <div class="header-status">
          <span class="status-dot" :class="{ 'disconnected': !connected }"></span>
          <span>{{ connected ? 'Connected' : 'Disconnected' }}</span>
        </div>
        
        <div class="header-actions">
          <button class="btn btn-primary" @click="openNewNegotiation()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New Negotiation
          </button>
        </div>
      </header>

      <!-- Main Layout -->
      <div class="main-layout">
        <!-- Sidebar -->
        <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
          <button class="sidebar-toggle" @click="toggleSidebar" :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline :points="sidebarCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"></polyline>
            </svg>
          </button>
          <div class="sidebar-section">
            <div class="sidebar-section-title" v-show="!sidebarCollapsed">Quick Actions</div>
            <button class="sidebar-btn primary" @click="openNewNegotiation()" :title="sidebarCollapsed ? 'Start Negotiation' : ''">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span v-show="!sidebarCollapsed">Start Negotiation</span>
            </button>
            <button class="sidebar-btn" @click="showLoadNegotiation = true" :title="sidebarCollapsed ? 'Load from File' : ''">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                <polyline points="12 11 12 17"/>
                <polyline points="9 14 12 11 15 14"/>
              </svg>
              <span v-show="!sidebarCollapsed">Load from File</span>
            </button>
            <button class="sidebar-btn" @click="openNewTournament()" :title="sidebarCollapsed ? 'Start Tournament' : ''">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="8" r="5"></circle>
                <path d="M12 13v7"></path>
                <path d="M9 20h6"></path>
              </svg>
              <span v-show="!sidebarCollapsed">Start Tournament</span>
            </button>
          </div>
          
          <!-- Sidebar sections will be managed by individual page components -->
          <slot name="sidebar"></slot>
        </aside>

        <!-- Content Area -->
        <main class="content-area">
          <router-view />
        </main>
      </div>
    </div>

    <!-- Settings Modal -->
    <SettingsModal :show="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useSettingsStore } from './stores/settings'
import SettingsModal from './components/SettingsModal.vue'

// Settings store
const settingsStore = useSettingsStore()
const { settings } = storeToRefs(settingsStore)

// UI state
const sidebarCollapsed = ref(true)

// Modal states
const showSettings = ref(false)
const showLoadNegotiation = ref(false)

// Global loading states
const scenariosLoading = ref(false)
const negotiatorsLoading = ref(false)

// Connection status
const connected = ref(true)

// Toast notification state
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

onMounted(async () => {
  // Load settings from backend
  await settingsStore.loadSettings()
  
  // Apply theme immediately
  applyTheme()
  
  // Load sidebar state from localStorage
  sidebarCollapsed.value = localStorage.getItem('sidebarCollapsed') !== 'false'
})

// Watch for settings changes to apply theme
watch(() => settings.value, () => {
  applyTheme()
}, { deep: true })

function applyTheme() {
  if (settings.value?.general?.dark_mode) {
    document.documentElement.classList.add('dark-mode')
  } else {
    document.documentElement.classList.remove('dark-mode')
  }
  
  if (settings.value?.general?.color_blind_mode) {
    document.documentElement.classList.add('color-blind-mode')
  } else {
    document.documentElement.classList.remove('color-blind-mode')
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value.toString())
}

function openNewNegotiation() {
  // TODO: Open new negotiation modal
  window.showToast('New Negotiation modal - TODO', 'info')
}

function openNewTournament() {
  // TODO: Open new tournament modal
  window.showToast('New Tournament modal - TODO', 'info')
}

// Global toast notification function
window.showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
  setTimeout(() => {
    toastVisible.value = false
  }, 3000)
}
</script>

<style>
@import './assets/css/styles.css';
@import './assets/css/layout.css';
</style>
