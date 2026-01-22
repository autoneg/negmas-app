<template>
  <div class="tournament-scores-pane" :class="{ collapsed: isCollapsed }">
    <div class="tournament-panel-header" @click="isCollapsed = !isCollapsed">
      <h3>
        <svg 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="2" 
          width="14" 
          height="14" 
          :style="{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
        <span>{{ isCompleted ? 'Final Rankings' : 'Live Leaderboard' }}</span>
      </h3>
    </div>
    
    <div class="tournament-panel-content" v-show="!isCollapsed">
      <!-- Empty state -->
      <div v-if="leaderboard.length === 0" class="empty-state-mini">
        <p>{{ isCompleted ? 'No scores available' : 'Waiting for results...' }}</p>
      </div>
      
      <!-- Leaderboard entries -->
      <div v-else class="tournament-leaderboard-content">
        <div
          v-for="entry in leaderboard"
          :key="entry.competitor || entry.name"
          class="leaderboard-entry"
          :class="'rank-' + entry.rank"
        >
          <div class="leaderboard-rank">
            <span v-if="entry.rank === 1">🥇</span>
            <span v-else-if="entry.rank === 2">🥈</span>
            <span v-else-if="entry.rank === 3">🥉</span>
            <span v-else>{{ entry.rank }}</span>
          </div>
          <div class="leaderboard-info">
            <div class="leaderboard-name">{{ entry.competitor || entry.name }}</div>
            <div class="leaderboard-stats">
              <span v-if="!isCompleted">
                {{ entry.n_negotiations || 0 }} games • {{ entry.n_agreements || 0 }} agr
              </span>
              <span v-else>
                {{ entry.n_negotiations || '-' }} games • u:{{ (entry.mean_utility || entry.avg_utility)?.toFixed(2) || '-' }}
              </span>
            </div>
          </div>
          <div class="leaderboard-score">{{ entry.score?.toFixed(3) || 'N/A' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  leaderboard: {
    type: Array,
    default: () => []
  },
  status: {
    type: String,
    default: 'running'
  }
})

const isCollapsed = ref(false)

const isCompleted = computed(() => props.status === 'completed')
</script>

<style scoped>
.tournament-scores-pane {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.tournament-scores-pane.collapsed .tournament-panel-content {
  display: none;
}

.tournament-panel-header {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.tournament-panel-header:hover {
  background: var(--bg-hover);
}

.tournament-panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tournament-panel-content {
  padding: 0;
}

.empty-state-mini {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.tournament-leaderboard-content {
  padding: 8px;
}

.leaderboard-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 6px;
  transition: all 0.2s;
}

.leaderboard-entry:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.leaderboard-entry.rank-1 {
  border-color: #fbbf24;
  box-shadow: 0 0 0 1px #fbbf24;
}

.leaderboard-entry.rank-2 {
  border-color: #94a3b8;
  box-shadow: 0 0 0 1px #94a3b8;
}

.leaderboard-entry.rank-3 {
  border-color: #d97706;
  box-shadow: 0 0 0 1px #d97706;
}

.leaderboard-rank {
  font-size: 16px;
  font-weight: 700;
  min-width: 30px;
  text-align: center;
  color: var(--text-primary);
}

.leaderboard-info {
  flex: 1;
  min-width: 0;
}

.leaderboard-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.leaderboard-stats {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  display: flex;
  gap: 8px;
}

.leaderboard-score {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-color);
  font-family: 'Monaco', 'Menlo', monospace;
}
</style>
