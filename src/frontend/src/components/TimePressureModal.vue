<template>
  <!-- Time Pressure Configuration Modal -->
  <Teleport to="body">
    <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
      <div class="modal small">
        <div class="modal-header">
          <h3>
            Time Pressure
            <span v-if="negotiatorName" class="text-muted" style="font-size: 14px; font-weight: normal;">
              - {{ negotiatorName }}
            </span>
          </h3>
          <button class="modal-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-hint" style="margin-bottom: 20px;">
            Override the mechanism's time limits for this negotiator only. Leave empty to use mechanism defaults.
          </div>
          
          <div class="form-group" style="margin-bottom: 16px;">
            <label class="form-label">
              <span>Steps Limit</span>
              <span class="text-muted" style="margin-left: 8px;">(optional)</span>
            </label>
            <input
              type="number"
              class="form-input"
              v-model.number="localNSteps"
              placeholder="Use mechanism default"
              min="1"
            />
            <div class="form-hint">Maximum steps allowed for this negotiator</div>
          </div>
          
          <div class="form-group">
            <label class="form-label">
              <span>Time Limit</span>
              <span class="text-muted" style="margin-left: 8px;">(seconds, optional)</span>
            </label>
            <input
              type="number"
              class="form-input"
              step="0.1"
              v-model.number="localTimeLimit"
              placeholder="Use mechanism default"
              min="0"
            />
            <div class="form-hint">Maximum time allowed for this negotiator</div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="clear">
            Clear
          </button>
          <div style="flex: 1;"></div>
          <button class="btn btn-secondary" @click="$emit('close')">
            Cancel
          </button>
          <button class="btn btn-primary" @click="apply">
            Apply
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  negotiatorName: {
    type: String,
    default: ''
  },
  existingNSteps: {
    type: Number,
    default: null
  },
  existingTimeLimit: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['close', 'apply'])

const localNSteps = ref(null)
const localTimeLimit = ref(null)

// Watch for prop changes to update local values
watch(() => props.show, (newVal) => {
  if (newVal) {
    // Modal opened - load existing values
    localNSteps.value = props.existingNSteps
    localTimeLimit.value = props.existingTimeLimit
  }
})

function clear() {
  localNSteps.value = null
  localTimeLimit.value = null
}

function apply() {
  emit('apply', {
    n_steps: localNSteps.value,
    time_limit: localTimeLimit.value
  })
  emit('close')
}
</script>

<style scoped>
/* Modal styles inherited from global styles */
.modal.small {
  max-width: 500px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  font-size: 13px;
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.text-muted {
  color: var(--text-muted);
}

.btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.btn-primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}
</style>
