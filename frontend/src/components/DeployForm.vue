<template>
  <form @submit.prevent="submitDeploy" class="deploy-form">
    <div class="form-group">
      <label>Stack Name</label>
      <input v-model="formData.stack_name" 
             type="text" 
             required 
             placeholder="my-app-stack">
      <small class="hint">Name for this deployment (must be unique)</small>
    </div>

    <div v-for="param in schema" :key="param.name" class="form-group">
      <label>{{ param.name }}</label>
      
      <input v-if="param.type === 'int'" 
             v-model.number="formData.env_overrides[param.name]"
             type="number"
             :placeholder="param.default || ''">
      
      <input v-else-if="param.type === 'port'" 
             v-model.number="formData.env_overrides[param.name]"
             type="number"
             min="1"
             max="65535"
             :placeholder="param.default || '8000'">
      
      <input v-else-if="param.type === 'bool'" 
             v-model="formData.env_overrides[param.name]"
             type="checkbox">
      
      <input v-else 
             v-model="formData.env_overrides[param.name]"
             type="text"
             :placeholder="param.default || ''">
      
      <small v-if="param.required" class="required">Required</small>
      <small v-else>Optional</small>
    </div>

    <div v-if="volumes && volumes.length > 0" class="volumes-section">
      <h3>Volume Bind Mounts</h3>
      <p class="volumes-hint">Customize host paths for volume mounts (useful for macOS compatibility)</p>
      
      <div v-for="volume in volumes" :key="volume.source" class="form-group volume-group">
        <label>
          <span class="volume-target">{{ volume.target }}</span>
          <span class="volume-service">({{ volume.service }})</span>
        </label>
        
        <input 
          v-model="formData.volume_overrides[volume.source]"
          type="text"
          :placeholder="volume.source">
        
        <small class="volume-info">
          Original: <code>{{ volume.source }}</code> → Container: <code>{{ volume.target }}</code>
        </small>
      </div>
    </div>

    <div class="button-group">
      <button type="submit" class="btn-deploy" :disabled="isSubmitting">
        {{ isSubmitting ? 'Deploying...' : 'Deploy Stack' }}
      </button>
      <button v-if="showCancel" type="button" @click="cancelDeploy" class="btn-cancel">
        Cancel
      </button>
    </div>

    <div v-if="deployResult" :class="['deploy-result', deployResult.success ? 'success' : 'error']">
      <div class="result-title">{{ deployResult.success ? '✓ Success' : '✗ Error' }}</div>
      <div class="result-message">{{ deployResult.message }}</div>
      <div v-if="deployResult.stack_id" class="result-detail">
        Stack ID: <code>{{ deployResult.stack_id }}</code>
      </div>
      <div v-if="deployResult.error_message" class="result-error">
        {{ deployResult.error_message }}
      </div>
    </div>
  </form>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DeployForm',
  props: {
    appId: {
      type: String,
      required: true
    },
    schema: {
      type: Array,
      default: () => []
    },
    volumes: {
      type: Array,
      default: () => []
    },
    showCancel: {
      type: Boolean,
      default: false
    }
  },
  emits: ['deploy-success', 'deploy-error', 'cancel'],
  data() {
    return {
      formData: {
        stack_name: '',
        portainer_endpoint_id: 3,
        env_overrides: {},
        volume_overrides: {}
      },
      isSubmitting: false,
      deployResult: null
    }
  },
  watch: {
    schema: {
      handler() {
        this.initializeOverrides()
      },
      deep: true
    },
    volumes: {
      handler() {
        this.initializeVolumeOverrides()
      },
      deep: true
    }
  },
  mounted() {
    this.initializeOverrides()
    this.initializeVolumeOverrides()
  },
  methods: {
    initializeOverrides() {
      this.formData.env_overrides = {}
      this.schema.forEach(param => {
        if (param.default) {
          this.formData.env_overrides[param.name] = param.default
        }
      })
    },

    initializeVolumeOverrides() {
      this.formData.volume_overrides = {}
      this.volumes.forEach(volume => {
        // Initialize with original source path
        this.formData.volume_overrides[volume.source] = volume.source
      })
    },

    generateStackName() {
      const timestamp = Date.now()
      return `${this.appId}-${timestamp}`
    },

    async submitDeploy() {
      if (!this.formData.stack_name) {
        this.formData.stack_name = this.generateStackName()
      }

      this.isSubmitting = true
      this.deployResult = null

      try {
        const modeResponse = await axios.get('/api/settings/portainer-mode')
        const isMock = modeResponse.data.current_mode === 'mock'
        const deployEndpoint = isMock
          ? `/apps/${this.appId}/deploy-mock`
          : `/apps/${this.appId}/deploy`

        const response = await axios.post(
          deployEndpoint,
          this.formData
        )

        this.deployResult = {
          success: true,
          ...response.data
        }

        this.$emit('deploy-success', response.data)

        // Reset form after 2 seconds
        setTimeout(() => {
          this.resetForm()
        }, 2000)
      } catch (error) {
        this.deployResult = {
          success: false,
          message: error.response?.data?.detail || 'Deployment failed',
          error_message: error.response?.data?.error || error.message
        }

        this.$emit('deploy-error', error.response?.data || { detail: error.message })
      } finally {
        this.isSubmitting = false
      }
    },

    resetForm() {
      this.formData.stack_name = ''
      this.deployResult = null
      this.initializeOverrides()
    },

    cancelDeploy() {
      this.resetForm()
      this.$emit('cancel')
    }
  }
}
</script>

<style scoped>
.deploy-form {
  display: grid;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="email"],
.form-group input[type="password"],
.form-group select,
.form-group textarea {
  padding: 0.75rem;
  border: 2px solid var(--color-border);
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
  transition: border-color 0.2s;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group input[type="email"]:focus,
.form-group input[type="password"]:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input[type="checkbox"] {
  width: 24px;
  height: 24px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

.form-group small {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

.form-group small.required {
  color: var(--color-error);
}

.hint {
  display: block;
  margin-top: 0.25rem;
}

.button-group {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-deploy,
.btn-cancel {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-deploy {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
}

.btn-deploy:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-deploy:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-cancel:hover {
  background: var(--color-border);
}

.deploy-result {
  margin-top: 1.5rem;
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid;
}

.deploy-result.success {
  background: rgba(72, 187, 120, 0.15);
  border-color: var(--color-success);
  color: var(--color-success);
}

.deploy-result.error {
  background: rgba(245, 101, 101, 0.15);
  border-color: var(--color-error);
  color: var(--color-error);
}

.result-title {
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.result-message {
  margin-bottom: 0.5rem;
}

.result-detail {
  margin-top: 0.75rem;
  font-size: 0.95rem;
}

.result-detail code {
  background: var(--color-bg-tertiary);
  padding: 0.25rem 0.5rem;
  border-radius: 2px;
  font-family: monospace;
  color: var(--color-text-primary);
}

.result-error {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--color-bg-tertiary);
  border-radius: 4px;
  font-size: 0.9rem;
  max-height: 200px;
  overflow-y: auto;
  color: var(--color-text-primary);
}

.volumes-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid var(--color-border);
}

.volumes-section h3 {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.volumes-hint {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.volume-group {
  background: var(--color-bg-secondary);
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid var(--color-primary);
}

.volume-target {
  font-family: monospace;
  color: var(--color-primary);
  font-weight: 600;
}

.volume-service {
  margin-left: 0.5rem;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.volume-info {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.volume-info code {
  background: var(--color-bg-tertiary);
  padding: 0.2rem 0.4rem;
  border-radius: 2px;
  font-family: monospace;
  font-size: 0.85rem;
}
</style>

