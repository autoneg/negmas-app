# Frontend Simplification for Polling Architecture

## Changes Needed

### 1. SingleNegotiationView.vue - Major Simplification

**Remove:**
- All SSE stream logic (streamingSession, eventSource checks)
- Complex state synchronization between SSE and polling
- Early return for active streams (line 520-526)
- stopStreaming() calls
- Watch for sessionInit, sessionComplete from store
- All console.log debugging statements

**Keep:**
- Panel layout system
- Error modal
- Zoom modal
- Navigation (back button, etc.)

**New Logic:**
```javascript
// Simple state
const negotiation = ref(null)  // Single source of truth
const loading = ref(true)
const error = ref(null)
let pollInterval = null

// Load and poll
async function loadNegotiation(sessionId) {
  loading.value = true
  
  try {
    // Load initial state
    const data = await negotiationsStore.getSession(sessionId)
    if (!data) {
      error.value = 'Negotiation not found'
      return
    }
    
    negotiation.value = data
    loading.value = false
    
    // Poll if running
    if (data.status === 'running' || data.status === 'pending') {
      pollInterval = setInterval(async () => {
        const updated = await negotiationsStore.getSession(sessionId)
        if (updated) {
          negotiation.value = updated
          
          if (updated.status === 'completed' || updated.status === 'failed') {
            clearInterval(pollInterval)
            await negotiationsStore.loadSessions()
          }
        }
      }, 1000)
    }
  } catch (err) {
    error.value = err.message
    loading.value = false
  }
}

// Cleanup
onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
```

**Pass data to panels:**
```vue
<Utility2DPanel :negotiation="negotiation" />
<TimelinePanel :negotiation="negotiation" />
<OfferHistoryPanel :negotiation="negotiation" />
```

### 2. NegotiationsListView.vue - Remove SSE

**Line 1189:** Remove `negotiationsStore.startStreaming()`

**Replace:**
```javascript
function onNegotiationStart(data) {
  showNewNegotiationModal.value = false
  
  if (data.session_id) {
    // Just navigate - view will handle polling
    router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
  }
}
```

### 3. NewNegotiationModal.vue - Use start_background

**Find:** Line that creates `stream_url`

**Remove:**
```javascript
stream_url: `/api/negotiation/${data.session_id}/stream?...`
```

**Just return:**
```javascript
const result = {
  session_id: data.session_id,
}
emit('start', result)
```

### 4. Switch Store Import

**In all files using negotiations store:**
```javascript
// OLD
import { useNegotiationsStore } from '../stores/negotiations'

// NEW
import { useNegotiationsStore } from '../stores/negotiations_polling'
```

**Files to update:**
- src/frontend/src/views/SingleNegotiationView.vue
- src/frontend/src/views/NegotiationsListView.vue
- src/frontend/src/components/NewNegotiationModal.vue

### 5. Remove Old Store

After switching all imports:
```bash
rm src/frontend/src/stores/negotiations.js
mv src/frontend/src/stores/negotiations_polling.js src/frontend/src/stores/negotiations.js
```

## Testing Checklist

- [ ] Start first negotiation - runs smoothly
- [ ] Start second negotiation - no blank screen
- [ ] View updates in real-time
- [ ] Refresh during running negotiation - continues from current state
- [ ] Negotiation completes - shows results
- [ ] No error modal on success
- [ ] Console is clean (no excessive logging)
- [ ] Navigation between negotiations works
- [ ] Multiple running negotiations update independently
