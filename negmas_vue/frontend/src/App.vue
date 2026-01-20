<template>
  <div id="app" :class="{ 'dark-mode': isDarkMode, 'color-blind-mode': isColorBlindMode }">
    <!-- Toast Notification -->
    <div v-if="toastVisible" :class="['toast', `toast-${toastType}`]">
      {{ toastMessage }}
    </div>

    <div class="app-container">
      <!-- Header -->
      <header class="app-header">
        <div class="header-left">
          <button class="sidebar-toggle" @click="toggleSidebar">
            ☰
          </button>
          <h1 class="app-title">NegMAS Vue</h1>
        </div>
        <div class="header-right">
          <button class="btn btn-sm" @click="showSettings = true">⚙️ Settings</button>
        </div>
      </header>

      <!-- Main Layout -->
      <div class="main-layout">
        <!-- Sidebar -->
        <aside :class="['sidebar', { collapsed: sidebarCollapsed }]">
          <nav class="sidebar-nav">
            <router-link to="/negotiations" class="sidebar-item">
              🤝 Negotiations
            </router-link>
            <router-link to="/scenarios" class="sidebar-item">
              📊 Scenarios
            </router-link>
            <router-link to="/negotiators" class="sidebar-item">
              🤖 Negotiators
            </router-link>
            <router-link to="/tournaments" class="sidebar-item">
              🏆 Tournaments
            </router-link>
          </nav>
        </aside>

        <!-- Content Area -->
        <main class="content-area">
          <router-view />
        </main>
      </div>
    </div>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Settings</h2>
          <button class="modal-close" @click="showSettings = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="isDarkMode" @change="toggleDarkMode" />
              Dark Mode
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="isColorBlindMode" @change="toggleColorBlindMode" />
              Color Blind Mode
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showSettings = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const isDarkMode = ref(false)
const isColorBlindMode = ref(false)
const sidebarCollapsed = ref(true)
const showSettings = ref(false)

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

onMounted(() => {
  // Load settings from localStorage
  isDarkMode.value = localStorage.getItem('darkMode') === 'true'
  isColorBlindMode.value = localStorage.getItem('colorBlindMode') === 'true'
  sidebarCollapsed.value = localStorage.getItem('sidebarCollapsed') !== 'false'

  // Apply dark mode class immediately
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark-mode')
  }
  if (isColorBlindMode.value) {
    document.documentElement.classList.add('color-blind-mode')
  }
})

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value.toString())
}

function toggleDarkMode() {
  localStorage.setItem('darkMode', isDarkMode.value.toString())
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark-mode')
  } else {
    document.documentElement.classList.remove('dark-mode')
  }
}

function toggleColorBlindMode() {
  localStorage.setItem('colorBlindMode', isColorBlindMode.value.toString())
  if (isColorBlindMode.value) {
    document.documentElement.classList.add('color-blind-mode')
  } else {
    document.documentElement.classList.remove('color-blind-mode')
  }
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
@import './assets/css/layout.css';

.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 20px;
  border-radius: 4px;
  color: white;
  z-index: 10000;
  animation: slideIn 0.3s ease-out;
}

.toast-success {
  background-color: #22c55e;
}

.toast-error {
  background-color: #ef4444;
}

.toast-info {
  background-color: #3b82f6;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow: auto;
}

.dark-mode .modal {
  background: #1f2937;
  color: #f3f4f6;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.dark-mode .modal-header {
  border-bottom-color: #374151;
}

.modal-header h2 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #6b7280;
}

.modal-close:hover {
  color: #111827;
}

.dark-mode .modal-close:hover {
  color: #f3f4f6;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dark-mode .modal-footer {
  border-top-color: #374151;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
</style>
