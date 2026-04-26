// Keyboard shortcuts composable
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useKeyboardShortcuts() {
  const router = useRouter()

  const handleKeyPress = (event) => {
    // Ignore if user is typing in an input/textarea
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) {
      return
    }

    // Ignore if any modifier keys (except the ones we want)
    const isModified = event.ctrlKey || event.metaKey || event.altKey

    // Navigation shortcuts (no modifiers)
    if (!isModified) {
      switch (event.key.toLowerCase()) {
        case '1':
          event.preventDefault()
          router.push('/negotiations')
          break
        case '2':
          event.preventDefault()
          router.push('/tournaments')
          break
        case '3':
          event.preventDefault()
          router.push('/scenarios')
          break
        case '4':
          event.preventDefault()
          router.push('/negotiators')
          break
        case 'n':
          // Trigger new negotiation modal (emit event)
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-new-negotiation'))
          break
        case 't':
          // Trigger new tournament modal (emit event)
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-new-tournament'))
          break
        case 's':
          // Open settings modal (emit event)
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-open-settings'))
          break
        case '?':
          // Show keyboard shortcuts help
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-show-help'))
          break
        case 'r':
          // Refresh current view
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-refresh'))
          break
        case 'escape':
          // Close modals/panels
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-escape'))
          break
      }
    }

    // Cmd/Ctrl + key shortcuts
    if ((event.metaKey || event.ctrlKey) && !event.shiftKey && !event.altKey) {
      switch (event.key.toLowerCase()) {
        case 'k':
          // Quick search/command palette
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-command-palette'))
          break
        case ',':
          // Open settings
          event.preventDefault()
          window.dispatchEvent(new CustomEvent('keyboard-open-settings'))
          break
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyPress)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyPress)
  })

  return {
    // Expose any methods if needed
  }
}

// Keyboard shortcuts reference
export const KEYBOARD_SHORTCUTS = [
  { key: '1', description: 'Go to Negotiations' },
  { key: '2', description: 'Go to Tournaments' },
  { key: '3', description: 'Go to Scenarios' },
  { key: '4', description: 'Go to Negotiators' },
  { key: 'N', description: 'New Negotiation' },
  { key: 'T', description: 'New Tournament' },
  { key: 'S', description: 'Open Settings' },
  { key: 'R', description: 'Refresh Current View' },
  { key: '?', description: 'Show Keyboard Shortcuts' },
  { key: 'Esc', description: 'Close Modal/Panel' },
  { key: 'Cmd/Ctrl + K', description: 'Command Palette (future)' },
  { key: 'Cmd/Ctrl + ,', description: 'Open Settings' },
]
