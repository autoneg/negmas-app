<template>
  <!-- Offer History Panel - Shows offers with virtualization for large datasets -->
  <div 
    class="panel panel-compact panel-history" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">OFFERS</span>
    
    <!-- Floating Actions -->
    <div class="panel-floating-actions">
      <span class="text-muted" style="font-size: 9px;">
        {{ offers?.length || 0 }} offers
      </span>
      <button class="panel-btn" title="Save as JSON" @click="$emit('saveOffersJson')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      <button class="panel-btn" title="Zoom (show all)" @click.stop="$emit('zoom')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 3 21 3 21 9"/>
          <polyline points="9 21 3 21 3 15"/>
          <line x1="21" y1="3" x2="14" y2="10"/>
          <line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
      </button>
      <button 
        class="panel-btn panel-collapse-btn" 
        title="Toggle panel" 
        @click="collapsed = !collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
    
    <!-- Panel Content -->
    <div class="panel-content panel-content-compact" style="padding: 4px;" v-show="!collapsed">
      <div class="offer-log" ref="offerLog">
        <!-- Empty state -->
        <div v-show="!offers || offers.length === 0" class="empty-state-mini">
          <span class="text-muted">Waiting for offers...</span>
        </div>
        
        <!-- Show message if truncated -->
        <div 
          v-show="offers && offers.length > 10" 
          style="padding: 4px 8px; background: var(--bg-tertiary); border-radius: 4px; margin-bottom: 4px; font-size: 10px; color: var(--text-secondary);"
        >
          Showing last 10 of {{ offers?.length }} offers.
          <button 
            class="btn-link" 
            style="font-size: 10px; padding: 0; color: var(--primary); border: none; background: none; cursor: pointer; text-decoration: underline;" 
            @click.stop="$emit('zoom')"
          >
            View all
          </button>
        </div>
        
        <!-- Render offers (limited to last 10 for performance during live updates) -->
        <div 
          v-for="(offer, offerIdx) in displayOffers" 
          :key="`${offer.step ?? offerIdx}-${offerIdx}`"
          class="offer-item-compact" 
          :class="{
            'offer-item-bilateral-first': negotiatorNames?.length === 2 && offer.proposer_index === 0,
            'offer-item-bilateral-second': negotiatorNames?.length === 2 && offer.proposer_index === 1
          }"
          :style="`border-left: 2px solid ${negotiatorColors?.[offer.proposer_index] || 'var(--border-color)'}`"
        >
          <div class="offer-header-compact">
            <span 
              class="offer-agent" 
              :style="`color: ${negotiatorColors?.[offer.proposer_index] || 'inherit'}`"
            >
              {{ offer.proposer }}
            </span>
            <span class="offer-step">#{{ offer.step }}</span>
          </div>
          <div class="offer-values-compact">
            <span v-for="(value, key) in offer.offer" :key="key">
              <span class="text-muted">{{ key }}:</span> <span>{{ value }}</span>
            </span>
          </div>
          <div class="offer-utilities-compact">
            <span 
              v-for="(util, uidx) in offer.utilities" 
              :key="uidx"
              class="offer-utility-label" 
              :style="`color: ${negotiatorColors?.[uidx] || 'inherit'}`"
            >
              <span class="utility-name">
                {{ (negotiatorNames?.[uidx] || `A${uidx+1}`).substring(0, 3) }}
              </span>
              <span>{{ typeof util === 'number' ? util.toFixed(2) : util }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  negotiation: {
    type: Object,
    default: () => null
  }
})

const emit = defineEmits(['saveOffersJson', 'zoom'])

// Extract data from negotiation object
const offers = computed(() => props.negotiation?.offers || [])
const negotiatorNames = computed(() => props.negotiation?.negotiator_names || [])
const negotiatorColors = computed(() => props.negotiation?.negotiator_colors || [])

// Collapse state
const collapsed = ref(false)

// Ref to offer log for auto-scrolling
const offerLog = ref(null)

// Display only last 10 offers for performance
const displayOffers = computed(() => {
  if (!offers.value || offers.value.length === 0) return []
  return offers.value.slice(-10)
})

// Auto-scroll to bottom when new offers arrive - throttled
let scrollScheduled = false
watch(() => offers.value?.length, () => {
  if (collapsed.value || scrollScheduled) return
  
  scrollScheduled = true
  requestAnimationFrame(async () => {
    await nextTick()
    
    if (offerLog.value) {
      const logElement = offerLog.value
      logElement.scrollTop = logElement.scrollHeight
    }
    
    scrollScheduled = false
  })
}, { immediate: false })
</script>

<style>
/* All styles are in panels.css */
/* Additional compact offer styles from Alpine CSS (lines 3419+) */
</style>
