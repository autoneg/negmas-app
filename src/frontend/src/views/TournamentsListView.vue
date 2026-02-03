<template>
  <div class="tournaments-list-container">
    <!-- Header -->
    <div class="list-header">
      <div class="header-left">
        <h2>Tournaments</h2>
        <button class="btn btn-primary" @click="showNewTournamentModal = true">
          + New Tournament
        </button>
        <button class="btn btn-secondary" @click="showImportModal = true" title="Import tournament from disk">
          📥 Import
        </button>
        <button 
          class="btn btn-secondary" 
          @click="openCombineModal"
          :disabled="selectedForCombine.length < 2"
          :title="selectedForCombine.length < 2 ? 'Select 2+ tournaments to combine' : 'Combine selected tournaments'"
        >
          🔗 Combine ({{ selectedForCombine.length }})
        </button>
      </div>
      <div class="header-right">
        <!-- Preview Selector -->
        <label style="display: flex; align-items: center; gap: 8px; font-size: 14px;">
          <span>Preview:</span>
          <select v-model="selectedPreview" class="form-select">
            <option value="none">None</option>
            <option value="grid">Grid</option>
            <option value="leaderboard">Leaderboard</option>
            <option value="config">Configuration</option>
          </select>
        </label>
        
        <!-- Filters -->
        <select v-model="tournamentTagFilter" class="form-select" style="width: 150px;">
          <option value="">All Tags</option>
          <option v-for="tag in availableTournamentTags" :key="tag" :value="tag">{{ tag }}</option>
        </select>
        
        <label style="display: flex; align-items: center; gap: 6px; font-size: 14px;">
          <input type="checkbox" v-model="showArchivedTournaments" @change="loadData">
          <span>Archived</span>
        </label>
        
        <button class="btn btn-secondary" @click="loadData" :disabled="loading" title="Refresh">
          <span v-if="loading">⟳</span>
          <span v-else>↻</span>
        </button>
      </div>
    </div>
    
    <!-- Content Area -->
    <div class="content-area" :class="{ 'with-preview': selectedPreview !== 'none' }">
      <!-- Tables Container -->
      <div class="table-container" :style="{ width: selectedPreview === 'none' ? '100%' : '66.67%' }">
        
        <!-- Running Tournaments Section -->
        <div v-if="runningTournaments.length > 0" class="running-section">
          <div class="section-header">
            <h3>Running Tournaments ({{ runningTournaments.length }})</h3>
          </div>
          <div class="running-table-wrapper">
            <table class="running-tournaments-table">
              <thead>
                <tr>
                  <th style="width: 180px;">Name/ID</th>
                  <th style="width: 100px;">Competitors</th>
                  <th style="width: 100px;">Scenarios</th>
                  <th style="width: 150px;">Progress</th>
                  <th style="width: 100px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="tourn in runningTournaments" 
                  :key="tourn.id"
                  @click="selectTournament(tourn)"
                  :class="{ 'selected': selectedTournament?.id === tourn.id }"
                  class="clickable-row"
                >
                  <td class="name-cell">
                    <div class="tournament-name">{{ tourn.name || tourn.id?.slice(0, 12) || 'Unknown' }}</div>
                    <div class="session-id">{{ tourn.id?.slice(0, 8) }}</div>
                  </td>
                  <td class="count-cell">{{ tourn.n_competitors || 0 }}</td>
                  <td class="count-cell">{{ tourn.n_scenarios || 0 }}</td>
                  <td class="progress-cell">
                    <div class="progress-info">
                      <div class="progress-text">
                        {{ tourn.completed || 0 }}/{{ tourn.total || 0 }} negotiations
                      </div>
                      <div class="progress-bar-mini">
                        <div 
                          class="progress-bar-fill" 
                          :style="{ width: getProgressPercent(tourn) + '%' }"
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td class="actions-cell" @click.stop>
                    <button 
                      class="btn-icon-small btn-danger" 
                      @click="stopTournament(tourn)"
                      title="Stop tournament"
                    >
                      ⏹️
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="viewTournament(tourn.id)" 
                      title="View full details"
                    >
                      👁️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Completed Tournaments Section -->
        <div class="completed-section">
          <div class="section-header">
            <h3>Completed Tournaments ({{ completedTournaments.length }})</h3>
          </div>
          
          <!-- Search -->
          <div class="search-bar">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search by name, competitors, scenarios, or ID..."
              class="search-input"
            >
          </div>
          
          <!-- Table -->
          <div class="table-wrapper">
            <table class="tournaments-table">
              <thead>
                <tr>
                  <th style="width: 40px;" class="checkbox-header">
                    <input 
                      type="checkbox" 
                      :checked="allVisibleSelected"
                      :indeterminate="someVisibleSelected && !allVisibleSelected"
                      @change="toggleSelectAll"
                      title="Select all for combining"
                    >
                  </th>
                  <th style="width: 160px;" @click="sortBy('date')">
                    Date
                    <span v-if="sortColumn === 'date'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th @click="sortBy('name')">
                    Name/ID
                    <span v-if="sortColumn === 'name'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('competitors')">
                    Competitors
                    <span v-if="sortColumn === 'competitors'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('scenarios')">
                    Scenarios
                    <span v-if="sortColumn === 'scenarios'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('status')">
                    Status
                    <span v-if="sortColumn === 'status'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 110px;">Statistics</th>
                  <th style="width: 80px;">Tags</th>
                  <th style="width: 120px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="tourn in filteredAndSortedTournaments" 
                  :key="tourn.id"
                  @click="selectTournament(tourn)"
                  :class="{ 'selected': selectedTournament?.id === tourn.id, 'selected-for-combine': isSelectedForCombine(tourn.id) }"
                  class="clickable-row"
                >
                  <td class="checkbox-cell" @click.stop>
                    <input 
                      type="checkbox" 
                      :checked="isSelectedForCombine(tourn.id)"
                      @change="toggleSelectForCombine(tourn.id)"
                    >
                  </td>
                  <td class="date-cell">{{ formatDate(tourn.timestamp || tourn.created_at) }}</td>
                  <td class="name-cell">{{ tourn.name || tourn.id?.slice(0, 12) || 'Unknown' }}</td>
                  <td class="count-cell">{{ tourn.n_competitors || 0 }}</td>
                  <td class="count-cell">{{ tourn.n_scenarios || 0 }}</td>
                  <td class="status-cell">
                    <span v-if="tourn.is_complete" class="badge badge-completed">Completed</span>
                    <span v-else-if="tourn.status === 'failed'" class="badge badge-failed">Failed</span>
                    <span v-else class="badge badge-pending">Incomplete</span>
                  </td>
                  <td class="stats-cell">
                    <div class="tournament-stats-compact">
                      <span class="stat-compact" title="Completion Rate">{{ getTournamentStats(tourn).completion }}%</span>
                      <span class="stat-sep">/</span>
                      <span class="stat-compact stat-success" title="Agreement Rate">{{ getTournamentStats(tourn).success }}%</span>
                      <span v-if="getTournamentStats(tourn).errors > 0" class="stat-compact stat-error" title="Errors">
                        ({{ getTournamentStats(tourn).errors }} err)
                      </span>
                    </div>
                  </td>
                  <td class="tags-cell">
                    <div class="tags-list">
                      <span 
                        v-for="tag in (tourn.tags || []).slice(0, 2)" 
                        :key="tag"
                        class="tag-badge"
                      >
                        {{ tag }}
                      </span>
                      <span v-if="(tourn.tags || []).length > 2" class="tag-more">
                        +{{ (tourn.tags || []).length - 2 }}
                      </span>
                    </div>
                  </td>
                  <td class="actions-cell" @click.stop>
                    <!-- Run/Continue button for incomplete tournaments -->
                    <button 
                      v-if="!tourn.is_complete"
                      class="btn-icon-small btn-success" 
                      @click="continueTournament(tourn.id)"
                      title="Run/Continue tournament"
                    >
                      ▶️
                    </button>
                    
                    <button 
                      class="btn-icon-small" 
                      @click="viewTournament(tourn.id)" 
                      title="View full details"
                    >
                      👁️
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="editTournamentTags(tourn)" 
                      title="Edit tags"
                    >
                      🏷️
                    </button>
                    <button 
                      class="btn-icon-small btn-danger-text" 
                      @click="deleteSavedTourn(tourn.id)" 
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            
            <!-- Empty State -->
            <div v-if="filteredAndSortedTournaments.length === 0 && !loading" class="empty-state">
              <p v-if="searchQuery">No tournaments match your search</p>
              <p v-else-if="tournamentTagFilter">No tournaments with tag "{{ tournamentTagFilter }}"</p>
              <p v-else>No completed tournaments yet. Start a new one!</p>
            </div>
            
            <!-- Loading State -->
            <div v-if="loading" class="loading-state">
              <p>Loading tournaments...</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Preview Panel -->
      <div v-if="selectedPreview !== 'none'" class="preview-container">
        <div v-if="!selectedTournament" class="preview-empty">
          <p>Select a tournament to preview</p>
        </div>
        <div v-else class="preview-content">
          <!-- Grid Preview -->
          <div v-if="selectedPreview === 'grid' && previewData?.gridInit" class="preview-grid">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Grid</h3>
            <div style="overflow: auto; padding: 16px;">
              <div class="tournament-grid-compact">
                <div class="grid-header">
                  <div class="grid-corner"></div>
                  <div
                    v-for="scenario in previewData.gridInit.scenarios.slice(0, 5)"
                    :key="scenario"
                    class="grid-header-cell"
                  >
                    {{ scenario.split('/').pop().slice(0, 10) }}
                  </div>
                  <div v-if="previewData.gridInit.scenarios.length > 5" class="grid-header-cell">...</div>
                </div>
                <div
                  v-for="competitor in previewData.gridInit.competitors.slice(0, 8)"
                  :key="competitor"
                  class="grid-row"
                >
                  <div class="grid-row-header">{{ competitor.slice(0, 15) }}</div>
                  <div
                    v-for="scenario in previewData.gridInit.scenarios.slice(0, 5)"
                    :key="scenario"
                    class="grid-cell"
                    :class="getCellClass(competitor, scenario)"
                  >
                    {{ getCellContent(competitor, scenario) }}
                  </div>
                  <div v-if="previewData.gridInit.scenarios.length > 5" class="grid-cell">...</div>
                </div>
                <div v-if="previewData.gridInit.competitors.length > 8" class="grid-row">
                  <div class="grid-row-header">...</div>
                  <div class="grid-cell" v-for="i in Math.min(5, previewData.gridInit.scenarios.length)" :key="i">...</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Leaderboard Preview -->
          <div v-else-if="selectedPreview === 'leaderboard' && previewData?.leaderboard" class="preview-leaderboard">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Leaderboard</h3>
            <table class="leaderboard-table-compact">
              <thead>
                <tr>
                  <th style="width: 50px;">Rank</th>
                  <th>Competitor</th>
                  <th style="width: 80px;">Score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(entry, idx) in previewData.leaderboard.slice(0, 10)" :key="entry.name || entry.competitor || idx">
                  <td class="rank-cell">
                    <span v-if="idx === 0">🥇</span>
                    <span v-else-if="idx === 1">🥈</span>
                    <span v-else-if="idx === 2">🥉</span>
                    <span v-else>{{ idx + 1 }}</span>
                  </td>
                  <td>{{ entry.name || entry.competitor || 'Unknown' }}</td>
                  <td>{{ entry.score?.toFixed(2) || 'N/A' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Config Preview -->
          <div v-else-if="selectedPreview === 'config'" class="preview-config">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Configuration</h3>
            <div class="config-preview-content">
              <!-- Summary section -->
              <div v-if="previewData?.gridInit" class="config-summary">
                <div class="config-item">
                  <span class="config-label">Competitors:</span>
                  <span>{{ previewData.gridInit.competitors?.length || 0 }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Scenarios:</span>
                  <span>{{ previewData.gridInit.scenarios?.length || 0 }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Total Negotiations:</span>
                  <span>{{ previewData.gridInit.total_negotiations || 0 }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Repetitions:</span>
                  <span>{{ previewData.gridInit.n_repetitions || 1 }}</span>
                </div>
              </div>
              
              <!-- Full config tree -->
              <div v-if="previewData?.config" class="config-tree-section">
                <h4 style="margin: 0 0 8px 0; font-size: 12px; color: var(--text-secondary);">Full Configuration</h4>
                <div class="config-tree-container">
                  <TreeView :data="previewData.config" :default-expand-depth="1" />
                </div>
              </div>
              
              <!-- Competitors list if no full config -->
              <div v-else-if="previewData?.gridInit?.competitors" class="config-details-section">
                <h4 style="margin: 0 0 8px 0; font-size: 12px; color: var(--text-secondary);">Competitors</h4>
                <div class="config-list">
                  <div v-for="comp in previewData.gridInit.competitors.slice(0, 10)" :key="comp" class="config-list-item">
                    {{ comp }}
                  </div>
                  <div v-if="previewData.gridInit.competitors.length > 10" class="config-list-more">
                    +{{ previewData.gridInit.competitors.length - 10 }} more
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Loading -->
          <div v-else class="preview-loading">
            <p>Loading preview...</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Tournament Modal -->
    <NewTournamentModal 
      v-if="showNewTournamentModal"
      :show="showNewTournamentModal"
      @close="showNewTournamentModal = false"
      @start="onTournamentStart"
    />
    
    <!-- Tag Editor Modal -->
    <Teleport to="body">
      <div v-if="tagEditorTournament" class="modal-overlay active" @click.self="closeTagEditor">
        <div class="modal" style="max-width: 500px;">
          <div class="modal-header">
            <h3>Edit Tags</h3>
            <button class="modal-close" @click="closeTagEditor">×</button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="margin-bottom: 12px;">
              {{ tagEditorTournament.name || tagEditorTournament.id }}
            </p>
            
            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; min-height: 40px; padding: 8px; background: var(--bg-secondary); border-radius: 6px;">
              <span 
                v-for="tag in tagEditorTags" 
                :key="tag"
                class="badge badge-primary"
                style="display: flex; align-items: center; gap: 6px; cursor: pointer;"
                @click="removeTagFromEditor(tag)"
              >
                {{ tag }}
                <span style="font-weight: bold;">×</span>
              </span>
              <span v-if="tagEditorTags.length === 0" class="text-muted">
                No tags yet
              </span>
            </div>
            
            <div style="display: flex; gap: 8px;">
              <input 
                type="text" 
                v-model="newTagInput" 
                @keyup.enter="addNewTag"
                placeholder="Add new tag..."
                class="form-input"
                style="flex: 1;"
              >
              <button class="btn btn-secondary" @click="addNewTag">Add</button>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeTagEditor">Cancel</button>
            <button class="btn btn-primary" @click="saveTagsFromEditor">Save</button>
          </div>
        </div>
      </div>
    </Teleport>
    
    <!-- Import Tournament Modal -->
    <Teleport to="body">
      <div v-if="showImportModal" class="modal-overlay active" @click.self="closeImportModal">
        <div class="modal" style="max-width: 550px;">
          <div class="modal-header">
            <h3>Import Tournament</h3>
            <button class="modal-close" @click="closeImportModal">×</button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="margin-bottom: 16px;">
              Import a tournament from a directory on disk into the app's storage.
            </p>
            
            <div class="form-group">
              <label class="form-label">Source Path *</label>
              <input 
                type="text" 
                v-model="importPath" 
                @input="validateImportPathDebounced"
                placeholder="/path/to/tournament/directory"
                class="form-input"
              >
              <div v-if="importValidation" class="validation-status" :class="importValidation.valid ? 'valid' : 'invalid'">
                <span v-if="importValidation.valid">
                  ✓ Valid tournament directory
                  <span v-if="importValidation.n_negotiations">({{ importValidation.n_negotiations }} negotiations)</span>
                </span>
                <span v-else>✗ {{ importValidation.error || 'Invalid path' }}</span>
              </div>
            </div>
            
            <div class="form-group">
              <label class="form-label">Name (optional)</label>
              <input 
                type="text" 
                v-model="importName" 
                placeholder="Leave empty to use original name or generate one"
                class="form-input"
              >
            </div>
            
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="importDeleteOriginal">
                <span>Delete original after import</span>
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeImportModal">Cancel</button>
            <button 
              class="btn btn-primary" 
              @click="performImport"
              :disabled="!importPath.trim() || importLoading || (importValidation && !importValidation.valid)"
            >
              <span v-if="importLoading">Importing...</span>
              <span v-else>Import</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    
    <!-- Combine Tournaments Modal -->
    <Teleport to="body">
      <div v-if="showCombineModal" class="modal-overlay active" @click.self="closeCombineModal">
        <div class="modal" style="max-width: 700px;">
          <div class="modal-header">
            <h3>Combine Tournaments</h3>
            <button class="modal-close" @click="closeCombineModal">×</button>
          </div>
          <div class="modal-body">
            <!-- Loading State -->
            <div v-if="combineLoading && !combinePreview" class="combine-loading">
              <p>Loading preview...</p>
            </div>
            
            <!-- Error State -->
            <div v-else-if="combinePreview?.error" class="combine-error">
              <p class="error-message">{{ combinePreview.error }}</p>
            </div>
            
            <!-- Preview -->
            <div v-else-if="combinePreview" class="combine-preview">
              <!-- Summary -->
              <div class="preview-section">
                <h4>Summary</h4>
                <div class="preview-stats">
                  <div class="stat-item">
                    <span class="stat-label">Source Tournaments:</span>
                    <span class="stat-value">{{ combinePreview.n_source_tournaments }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Total Scenarios:</span>
                    <span class="stat-value">{{ combinePreview.n_scenarios }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Existing Negotiations:</span>
                    <span class="stat-value">{{ combinePreview.n_existing_negotiations }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Expected Negotiations:</span>
                    <span class="stat-value">{{ combinePreview.n_expected_negotiations }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Completion:</span>
                    <span class="stat-value" :class="combinePreview.is_complete ? 'complete' : 'incomplete'">
                      {{ combinePreview.completion_rate?.toFixed(1) }}%
                      <span v-if="combinePreview.is_complete">(Complete)</span>
                      <span v-else>(Incomplete)</span>
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- Competitors -->
              <div class="preview-section">
                <h4>Competitors ({{ combinePreview.competitors?.length || 0 }})</h4>
                <div class="preview-list">
                  <div v-for="comp in (combinePreview.competitors || []).slice(0, 10)" :key="comp.full_type" class="preview-list-item">
                    <span class="item-name">{{ comp.short_name }}</span>
                    <span class="item-detail">{{ comp.source_tournaments?.length || 0 }} tournaments</span>
                  </div>
                  <div v-if="(combinePreview.competitors || []).length > 10" class="preview-list-more">
                    +{{ combinePreview.competitors.length - 10 }} more
                  </div>
                </div>
              </div>
              
              <!-- Warnings -->
              <div v-if="combinePreview.completeness_warnings?.length > 0" class="preview-section warnings">
                <h4>Warnings ({{ combinePreview.completeness_warnings.length }})</h4>
                <div class="warnings-list">
                  <div v-for="(warning, idx) in combinePreview.completeness_warnings.slice(0, 5)" :key="idx" class="warning-item">
                    ⚠️ {{ warning }}
                  </div>
                  <div v-if="combinePreview.completeness_warnings.length > 5" class="warnings-more">
                    +{{ combinePreview.completeness_warnings.length - 5 }} more warnings
                  </div>
                </div>
              </div>
              
              <!-- Type Conflicts -->
              <div v-if="combinePreview.type_conflicts?.length > 0" class="preview-section errors">
                <h4>Type Conflicts ({{ combinePreview.type_conflicts.length }})</h4>
                <div class="errors-list">
                  <div v-for="conflict in combinePreview.type_conflicts.slice(0, 5)" :key="conflict.short_name" class="error-item">
                    ❌ "{{ conflict.short_name }}" has multiple types: {{ conflict.full_types?.join(', ') }}
                  </div>
                </div>
              </div>
              
              <!-- Name Input -->
              <div class="form-group" style="margin-top: 16px;">
                <label class="form-label">Combined Tournament Name (optional)</label>
                <input 
                  type="text" 
                  v-model="combineName" 
                  placeholder="Leave empty to generate automatically"
                  class="form-input"
                >
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeCombineModal">Cancel</button>
            <button 
              class="btn btn-primary" 
              @click="performCombine"
              :disabled="combineLoading || !combinePreview || combinePreview.error || combinePreview.type_conflicts?.length > 0"
            >
              <span v-if="combineLoading">Combining...</span>
              <span v-else>Combine</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTournamentsStore } from '../stores/tournaments'
import { storeToRefs } from 'pinia'
import NewTournamentModal from '../components/NewTournamentModal.vue'
import TreeView from '../components/TreeView.vue'

const router = useRouter()
const tournamentsStore = useTournamentsStore()
const {
  sessions,
  loading,
  savedTournaments,
  savedTournamentsLoading,
  tournamentTagFilter,
  showArchivedTournaments,
  availableTournamentTags,
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
const searchQuery = ref('')
const selectedPreview = ref('none')
const selectedTournament = ref(null)
const previewData = ref(null)

// Sorting
const sortColumn = ref('date')
const sortDirection = ref('desc')

// Tag editor state
const tagEditorTournament = ref(null)
const tagEditorTags = ref([])
const newTagInput = ref('')

// Selection for combine
const selectedForCombine = ref([])

// Import modal state
const showImportModal = ref(false)
const importPath = ref('')
const importName = ref('')
const importDeleteOriginal = ref(false)
const importValidation = ref(null)
const importLoading = ref(false)

// Combine modal state
const showCombineModal = ref(false)
const combinePreview = ref(null)
const combineName = ref('')
const combineLoading = ref(false)

// Running tournaments come from sessions only
const runningTournaments = computed(() => {
  return sessions.value
    .filter(s => s.status === 'running' || s.status === 'pending')
    .map(s => ({
      ...s,
      source: 'session',
      timestamp: s.created_at || s.started_at || Date.now()
    }))
})

// Completed tournaments come from saved tournaments, excluding any that are currently running
const completedTournaments = computed(() => {
  // Get IDs of running tournaments to exclude them from saved list
  const runningIds = new Set(runningTournaments.value.map(t => t.id))
  
  return savedTournaments.value
    .filter(s => !runningIds.has(s.id)) // Don't show running tournaments in completed section
    .map(s => ({
      ...s,
      source: 'saved',
      timestamp: s.created_at || s.completed_at || Date.now()
    }))
})

// For backward compatibility - combine all tournaments
const allTournaments = computed(() => {
  return [...runningTournaments.value, ...completedTournaments.value]
})

// Computed properties for select-all checkbox
const allVisibleSelected = computed(() => {
  if (filteredAndSortedTournaments.value.length === 0) return false
  return filteredAndSortedTournaments.value.every(t => selectedForCombine.value.includes(t.id))
})

const someVisibleSelected = computed(() => {
  if (filteredAndSortedTournaments.value.length === 0) return false
  return filteredAndSortedTournaments.value.some(t => selectedForCombine.value.includes(t.id))
})

// Helper to calculate progress percentage
function getProgressPercent(tourn) {
  const total = tourn.total || 0
  const completed = tourn.completed || 0
  if (total === 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

// Filter and sort completed tournaments only (running shown separately)
const filteredAndSortedTournaments = computed(() => {
  let result = completedTournaments.value
  
  // Filter by tag
  if (tournamentTagFilter.value) {
    result = result.filter(tourn => tourn.tags && tourn.tags.includes(tournamentTagFilter.value))
  }
  
  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(tourn => {
      const nameMatch = (tourn.name || '').toLowerCase().includes(query)
      const idMatch = (tourn.id || '').toLowerCase().includes(query)
      return nameMatch || idMatch
    })
  }
  
  // Sort
  result.sort((a, b) => {
    let aVal, bVal
    
    switch (sortColumn.value) {
      case 'date':
        aVal = new Date(a.timestamp || 0)
        bVal = new Date(b.timestamp || 0)
        break
      case 'name':
        aVal = (a.name || a.id || '').toLowerCase()
        bVal = (b.name || b.id || '').toLowerCase()
        break
      case 'competitors':
        aVal = a.n_competitors || 0
        bVal = b.n_competitors || 0
        break
      case 'scenarios':
        aVal = a.n_scenarios || 0
        bVal = b.n_scenarios || 0
        break
      case 'status':
        aVal = a.status || 'unknown'
        bVal = b.status || 'unknown'
        break
      default:
        return 0
    }
    
    if (aVal < bVal) return sortDirection.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection.value === 'asc' ? 1 : -1
    return 0
  })
  
  return result
})

onMounted(async () => {
  await loadData()
  // Start polling for running tournaments
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

// Polling for running tournaments to update progress
let pollingInterval = null

function startPolling() {
  // Poll every 3 seconds when there are running tournaments
  pollingInterval = setInterval(async () => {
    if (runningTournaments.value.length > 0) {
      // Only reload sessions to update progress - don't reload saved
      await tournamentsStore.loadSessions()
    } else if (pollingInterval) {
      // No running tournaments, switch to slower polling
      clearInterval(pollingInterval)
      pollingInterval = setInterval(async () => {
        await tournamentsStore.loadSessions()
        // If we found running tournaments, switch back to fast polling
        if (runningTournaments.value.length > 0) {
          stopPolling()
          startPolling()
        }
      }, 10000) // Check every 10 seconds when idle
    }
  }, 3000) // Update every 3 seconds when running
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// Watch for preview selection changes
watch(selectedPreview, (newVal) => {
  if (newVal === 'none') {
    previewData.value = null
  } else if (selectedTournament.value) {
    loadPreviewData(selectedTournament.value)
  }
})

// Watch for tournament selection changes
watch(selectedTournament, (newVal) => {
  if (newVal && selectedPreview.value !== 'none') {
    loadPreviewData(newVal)
  } else {
    previewData.value = null
  }
})

async function loadData() {
  await tournamentsStore.loadSessions()
  await tournamentsStore.loadSavedTournaments(showArchivedTournaments.value)
}

async function selectTournament(tourn) {
  selectedTournament.value = tourn
  
  if (selectedPreview.value !== 'none') {
    await loadPreviewData(tourn)
  }
}

async function loadPreviewData(tourn) {
  try {
    let fullData
    
    if (tourn.source === 'saved') {
      fullData = await tournamentsStore.loadSavedTournament(tourn.id)
    } else {
      fullData = tourn
    }
    
    if (!fullData) {
      previewData.value = null
      return
    }
    
    previewData.value = {
      id: fullData.id,
      name: fullData.name,
      gridInit: fullData.gridInit,
      cellStates: fullData.cellStates || {},
      leaderboard: fullData.leaderboard || [],
      config: fullData.config || null,
      scores: fullData.scores || [],
    }
  } catch (error) {
    console.error('Failed to load preview data:', error)
    previewData.value = null
  }
}

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'asc'
  }
}

function formatDate(timestamp) {
  if (!timestamp) return 'Unknown'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return `${mins}m ago`
  }
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }
  
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

function getTournamentStats(tourn) {
  // Calculate statistics from tournament data
  const total = tourn.total || 0
  const completed = tourn.completed || 0
  const errors = tourn.n_errors || 0
  
  if (total === 0) {
    return { completion: 0, success: 0, errors: 0 }
  }
  
  const completion = Math.round((completed / total) * 100)
  const success = completed > 0 ? Math.round(((completed - errors) / completed) * 100) : 0
  
  return { 
    completion, 
    success, 
    errors 
  }
}

function getCellClass(competitor, scenario) {
  if (!previewData.value?.cellStates) return 'pending'
  
  // Backend uses format: competitor::opponent::scenario
  // For the grid preview, we show competitor vs scenarios (aggregated across opponents)
  // Try to find any matching cell for this competitor+scenario combination
  const cellStates = previewData.value.cellStates
  for (const key of Object.keys(cellStates)) {
    const parts = key.split('::')
    // Handle both formats: "comp::scenario" and "comp::opponent::scenario"
    if (parts.length === 3 && parts[0] === competitor && parts[2] === scenario) {
      const state = cellStates[key]
      return state.status === 'complete' ? 'completed' : (state.status || 'pending')
    } else if (parts.length === 2 && parts[0] === competitor && parts[1] === scenario) {
      const state = cellStates[key]
      return state.status === 'complete' ? 'completed' : (state.status || 'pending')
    }
  }
  return 'pending'
}

function getCellContent(competitor, scenario) {
  if (!previewData.value?.cellStates) return '⋯'
  
  // Backend uses format: competitor::opponent::scenario
  // For the grid preview, aggregate across opponents
  const cellStates = previewData.value.cellStates
  let totalAgreements = 0
  let totalCount = 0
  let foundAny = false
  
  for (const key of Object.keys(cellStates)) {
    const parts = key.split('::')
    let matches = false
    
    // Handle both formats: "comp::scenario" and "comp::opponent::scenario"
    if (parts.length === 3 && parts[0] === competitor && parts[2] === scenario) {
      matches = true
    } else if (parts.length === 2 && parts[0] === competitor && parts[1] === scenario) {
      matches = true
    }
    
    if (matches) {
      foundAny = true
      const state = cellStates[key]
      
      if (state.status === 'running') return '⟳'
      if (state.status === 'error' || state.status === 'failed') return '✗'
      
      // Aggregate counts
      totalCount += state.total || 1
      totalAgreements += state.agreements || (state.has_agreement ? 1 : 0)
    }
  }
  
  if (!foundAny) return '⋯'
  
  // Show agreement rate as percentage
  if (totalCount > 0) {
    const rate = Math.round((totalAgreements / totalCount) * 100)
    return `${rate}%`
  }
  
  return '✓'
}

function viewTournament(tournamentId) {
  router.push({ name: 'SingleTournament', params: { id: tournamentId } })
}

async function deleteSavedTourn(tournamentId) {
  if (confirm('Are you sure you want to delete this saved tournament?')) {
    try {
      console.log('[TournamentsListView] Deleting tournament:', tournamentId)
      await tournamentsStore.deleteSavedTournament(tournamentId)
      console.log('[TournamentsListView] Tournament deleted successfully')
      
      // Clear selection if deleted tournament was selected
      if (selectedTournament.value?.id === tournamentId) {
        selectedTournament.value = null
        previewData.value = null
      }
    } catch (error) {
      console.error('[TournamentsListView] Failed to delete tournament:', error)
      alert(`Failed to delete tournament: ${error.message}`)
    }
  }
}

function editTournamentTags(tourn) {
  tagEditorTournament.value = tourn
  tagEditorTags.value = [...(tourn.tags || [])]
  newTagInput.value = ''
}

function closeTagEditor() {
  tagEditorTournament.value = null
  tagEditorTags.value = []
  newTagInput.value = ''
}

function removeTagFromEditor(tag) {
  const index = tagEditorTags.value.indexOf(tag)
  if (index > -1) {
    tagEditorTags.value.splice(index, 1)
  }
}

function addNewTag() {
  const tag = newTagInput.value.trim()
  if (tag && !tagEditorTags.value.includes(tag)) {
    tagEditorTags.value.push(tag)
    newTagInput.value = ''
  }
}

async function saveTagsFromEditor() {
  if (tagEditorTournament.value) {
    await tournamentsStore.updateTournamentTags(
      tagEditorTournament.value.id,
      tagEditorTags.value
    )
    closeTagEditor()
  }
}

// Selection for combine
function isSelectedForCombine(id) {
  return selectedForCombine.value.includes(id)
}

function toggleSelectForCombine(id) {
  const index = selectedForCombine.value.indexOf(id)
  if (index === -1) {
    selectedForCombine.value.push(id)
  } else {
    selectedForCombine.value.splice(index, 1)
  }
}

function toggleSelectAll() {
  if (allVisibleSelected.value) {
    // Deselect all visible
    const visibleIds = new Set(filteredAndSortedTournaments.value.map(t => t.id))
    selectedForCombine.value = selectedForCombine.value.filter(id => !visibleIds.has(id))
  } else {
    // Select all visible
    const visibleIds = filteredAndSortedTournaments.value.map(t => t.id)
    const currentSet = new Set(selectedForCombine.value)
    visibleIds.forEach(id => currentSet.add(id))
    selectedForCombine.value = Array.from(currentSet)
  }
}

// Import functions
async function validateImportPathDebounced() {
  if (!importPath.value.trim()) {
    importValidation.value = null
    return
  }
  
  importLoading.value = true
  try {
    importValidation.value = await tournamentsStore.validateImportPath(importPath.value.trim())
  } finally {
    importLoading.value = false
  }
}

async function performImport() {
  if (!importPath.value.trim()) return
  
  importLoading.value = true
  try {
    const result = await tournamentsStore.importTournament(importPath.value.trim(), {
      name: importName.value.trim() || null,
      deleteOriginal: importDeleteOriginal.value,
    })
    
    // Success - close modal and show notification
    showImportModal.value = false
    importPath.value = ''
    importName.value = ''
    importDeleteOriginal.value = false
    importValidation.value = null
    
    alert(`Successfully imported tournament: ${result.output_id}`)
  } catch (error) {
    alert(`Import failed: ${error.message}`)
  } finally {
    importLoading.value = false
  }
}

function closeImportModal() {
  showImportModal.value = false
  importPath.value = ''
  importName.value = ''
  importDeleteOriginal.value = false
  importValidation.value = null
}

// Combine functions
async function openCombineModal() {
  if (selectedForCombine.value.length < 2) return
  
  showCombineModal.value = true
  combineLoading.value = true
  combinePreview.value = null
  combineName.value = ''
  
  try {
    combinePreview.value = await tournamentsStore.previewCombineTournaments(selectedForCombine.value)
  } catch (error) {
    combinePreview.value = { error: error.message }
  } finally {
    combineLoading.value = false
  }
}

async function performCombine() {
  if (!combinePreview.value || combinePreview.value.error) return
  
  // Warn if incomplete
  if (!combinePreview.value.is_complete) {
    const proceed = confirm(
      `Warning: The combined tournament will be incomplete (${combinePreview.value.completion_rate?.toFixed(1)}% complete).\n\n` +
      `${combinePreview.value.completeness_warnings?.slice(0, 3).join('\n') || ''}\n\n` +
      `Do you want to continue?`
    )
    if (!proceed) return
  }
  
  combineLoading.value = true
  try {
    const result = await tournamentsStore.combineTournaments(selectedForCombine.value, {
      outputName: combineName.value.trim() || null,
    })
    
    // Success - close modal and clear selection
    showCombineModal.value = false
    selectedForCombine.value = []
    combinePreview.value = null
    combineName.value = ''
    
    alert(`Successfully combined tournaments into: ${result.output_id}`)
  } catch (error) {
    alert(`Combine failed: ${error.message}`)
  } finally {
    combineLoading.value = false
  }
}

function closeCombineModal() {
  showCombineModal.value = false
  combinePreview.value = null
  combineName.value = ''
}

function onTournamentStart(data) {
  showNewTournamentModal.value = false
  
  if (data.session_id) {
    // Store scenarios if provided
    if (data.scenarios) {
      tournamentsStore.tournamentScenarios = data.scenarios
    }
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  }
}

async function continueTournament(tournamentId) {
  try {
    const response = await fetch(`/api/tournament/saved/${tournamentId}/continue`, {
      method: 'POST'
    })
    
    if (!response.ok) {
      const error = await response.json()
      alert(`Failed to continue tournament: ${error.detail || 'Unknown error'}`)
      return
    }
    
    const data = await response.json()
    // Navigate to tournament view with streaming
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  } catch (error) {
    console.error('Failed to continue tournament:', error)
    alert(`Failed to continue tournament: ${error.message}`)
  }
}

async function stopTournament(tourn) {
  if (!confirm(`Stop tournament ${tourn.name || tourn.id}?`)) {
    return
  }
  
  try {
    // Find the session ID if this is a running session
    let sessionId = tourn.id
    if (tourn.source === 'session' && tourn.session_id) {
      sessionId = tourn.session_id
    }
    
    const response = await fetch(`/api/tournament/${sessionId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delete_results: false })
    })
    
    if (!response.ok) {
      const error = await response.json()
      alert(`Failed to stop tournament: ${error.detail || 'Unknown error'}`)
      return
    }
    
    // Refresh tournament list
    await loadData()
    
    // Clear selection if we stopped the selected tournament
    if (selectedTournament.value?.id === tourn.id) {
      selectedTournament.value = null
      previewData.value = null
    }
  } catch (error) {
    console.error('Failed to stop tournament:', error)
    alert(`Failed to stop tournament: ${error.message}`)
  }
}
</script>

<style scoped>
.tournaments-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-area {
  display: flex;
  flex-direction: row;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
  transition: width 0.3s ease;
  overflow: auto;
}

/* When preview is visible, don't let flex override explicit width */
.content-area.with-preview .table-container {
  flex: none;
  overflow: hidden;
}

/* Running Tournaments Section */
.running-section {
  flex-shrink: 0;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.section-header {
  padding: 8px 16px;
  background: var(--bg-secondary);
}

.section-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.running-table-wrapper {
  overflow-x: auto;
}

.running-tournaments-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.running-tournaments-table thead {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.running-tournaments-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.running-tournaments-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.running-tournaments-table tbody tr:hover {
  background: var(--bg-hover);
}

.running-tournaments-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.running-tournaments-table tbody tr.clickable-row {
  cursor: pointer;
}

.running-tournaments-table td {
  padding: 8px 12px;
}

.tournament-name {
  font-weight: 500;
}

.session-id {
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
  margin-top: 2px;
}

.progress-cell {
  min-width: 120px;
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-text {
  font-size: 11px;
  color: var(--text-secondary);
}

.progress-bar-mini {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

/* Completed Tournaments Section */
.completed-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.completed-section .section-header {
  flex-shrink: 0;
}

.search-bar {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  position: relative;
  min-width: 0;
}

.tournaments-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  table-layout: fixed;
}

.tournaments-table thead {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  z-index: 10;
  border-bottom: 2px solid var(--border-color);
}

.tournaments-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.tournaments-table th:hover {
  background: var(--bg-hover);
}

.tournaments-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.tournaments-table tbody tr:hover {
  background: var(--bg-hover);
}

.tournaments-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.tournaments-table tbody tr.clickable-row {
  cursor: pointer;
}

.tournaments-table td {
  padding: 12px 16px;
}

.date-cell {
  color: var(--text-secondary);
  font-size: 13px;
}

.name-cell {
  font-weight: 500;
}

.count-cell {
  text-align: center;
  color: var(--text-secondary);
}

.stats-cell {
  padding: 6px 8px !important;
}

.tournament-stats-compact {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
}

.stat-compact {
  font-weight: 500;
  color: var(--text-primary);
}

.stat-sep {
  color: var(--text-tertiary);
  margin: 0 1px;
}

.stat-success {
  color: var(--success-color, #10b981);
}

.stat-error {
  color: var(--error-color, #ef4444);
  font-size: 10px;
  margin-left: 2px;
}

.text-muted {
  color: var(--text-secondary);
  font-size: 12px;
}

.status-cell .badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-running {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

.badge-pending {
  background: rgba(245, 158, 11, 0.2);
  color: rgb(245, 158, 11);
}

.badge-completed {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-failed {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.tags-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag-badge {
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 3px;
  font-size: 11px;
  color: var(--text-secondary);
}

.tag-more {
  font-size: 11px;
  color: var(--text-secondary);
}

.actions-cell {
  display: flex;
  gap: 4px;
}

.btn-icon-small {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-icon-small:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.btn-icon-small.btn-success {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.btn-icon-small.btn-success:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
}

.btn-icon-small.btn-danger {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.btn-icon-small.btn-danger:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
}

.btn-icon-small.btn-danger-text {
  color: #ef4444;
}

.btn-icon-small.btn-danger-text:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}

.empty-state,
.loading-state {
  padding: 48px 24px;
  text-align: center;
  color: var(--text-secondary);
}

.preview-container {
  width: 33.33%;
  min-width: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  overflow: hidden;
  border-left: 1px solid var(--border-color);
}

.preview-empty,
.preview-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.preview-content {
  flex: 1;
  overflow: auto;
}

.tournament-grid-compact {
  display: inline-block;
  font-size: 11px;
}

.grid-header,
.grid-row {
  display: flex;
}

.grid-corner,
.grid-header-cell,
.grid-row-header,
.grid-cell {
  border: 1px solid var(--border-color);
  padding: 4px 6px;
  text-align: center;
}

.grid-corner {
  width: 100px;
  background: var(--bg-tertiary);
}

.grid-header-cell {
  width: 60px;
  background: var(--bg-tertiary);
  font-weight: 600;
}

.grid-row-header {
  width: 100px;
  background: var(--bg-tertiary);
  font-weight: 600;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grid-cell {
  width: 60px;
  font-family: monospace;
}

.grid-cell.pending {
  background: var(--bg-primary);
}

.grid-cell.running {
  background: rgba(59, 130, 246, 0.1);
  color: rgb(59, 130, 246);
}

.grid-cell.completed {
  background: rgba(16, 185, 129, 0.1);
}

.grid-cell.failed {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.leaderboard-table-compact {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.leaderboard-table-compact th,
.leaderboard-table-compact td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.leaderboard-table-compact th {
  background: var(--bg-tertiary);
  font-weight: 600;
  position: sticky;
  top: 0;
}

.leaderboard-table-compact .rank-cell {
  text-align: center;
  font-weight: 600;
}

.config-preview-content {
  padding: 16px;
  overflow: auto;
  max-height: calc(100vh - 200px);
}

.config-summary {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 13px;
}

.config-tree-section {
  margin-top: 16px;
}

.config-tree-container {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  max-height: 400px;
  overflow: auto;
}

.config-details-section {
  margin-top: 16px;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-list-item {
  padding: 6px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
}

.config-list-more {
  padding: 6px 10px;
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
}

.form-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
}

/* Checkbox cells for combine selection */
.checkbox-header,
.checkbox-cell {
  text-align: center;
  width: 40px;
}

.checkbox-header input,
.checkbox-cell input {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.selected-for-combine {
  background: rgba(59, 130, 246, 0.08) !important;
}

.selected-for-combine:hover {
  background: rgba(59, 130, 246, 0.15) !important;
}

/* Form styles for modals */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  font-size: 14px;
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}

.checkbox-label input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.validation-status {
  margin-top: 6px;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 4px;
}

.validation-status.valid {
  background: rgba(16, 185, 129, 0.1);
  color: rgb(16, 185, 129);
}

.validation-status.invalid {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

/* Combine preview styles */
.combine-loading,
.combine-error {
  padding: 24px;
  text-align: center;
}

.error-message {
  color: rgb(239, 68, 68);
}

.combine-preview {
  max-height: 60vh;
  overflow-y: auto;
}

.preview-section {
  margin-bottom: 20px;
}

.preview-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 13px;
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  font-weight: 500;
}

.stat-value.complete {
  color: rgb(16, 185, 129);
}

.stat-value.incomplete {
  color: rgb(245, 158, 11);
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 150px;
  overflow-y: auto;
}

.preview-list-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 12px;
}

.item-name {
  font-weight: 500;
  font-family: monospace;
}

.item-detail {
  color: var(--text-secondary);
}

.preview-list-more {
  padding: 6px 10px;
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
}

.preview-section.warnings {
  padding: 12px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: 6px;
}

.preview-section.warnings h4 {
  color: rgb(245, 158, 11);
}

.warnings-list,
.errors-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.warning-item,
.error-item {
  font-size: 12px;
  padding: 4px 0;
}

.warnings-more {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.preview-section.errors {
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 6px;
}

.preview-section.errors h4 {
  color: rgb(239, 68, 68);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-overlay.active {
  display: flex;
}

.modal {
  background: var(--bg-primary);
  border-radius: 12px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  line-height: 1;
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  border: none;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.badge-primary {
  background: var(--primary-color);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
