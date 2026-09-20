<template>
  <form @submit.prevent="submitDeploy" class="deploy-form">
    <div class="form-group">
      <label>Stack Name</label>
      <input v-model="formData.stack_name"
             type="text"
             required
             placeholder="my-app-stack"
             class="input">
      <small class="hint">Name for this deployment (must be unique)</small>
    </div>

    <div v-for="param in schema" :key="param.name" class="form-group">
      <label>{{ param.name }}</label>

      <div v-if="param.type === 'bool'" class="bool-field">
        <input
          v-model="formData.env_overrides[param.name]"
          type="checkbox"
          class="bool-check"
          :id="`bool-${param.name}`"
        >
        <label :for="`bool-${param.name}`" class="bool-toggle"></label>
        <span class="bool-text">{{ formData.env_overrides[param.name] ? 'Enabled' : 'Disabled' }}</span>
      </div>

      <input v-else-if="param.type === 'int'"
             v-model.number="formData.env_overrides[param.name]"
             type="number"
             :placeholder="param.default || ''"
             class="input">

      <input v-else-if="param.type === 'port'"
             v-model.number="formData.env_overrides[param.name]"
             type="number"
             min="1"
             max="65535"
             :placeholder="param.default || '8000'"
             class="input">

      <input v-else
             v-model="formData.env_overrides[param.name]"
             type="text"
             :placeholder="param.default || ''"
             class="input">

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
          :placeholder="volume.source"
          class="input">

        <small class="volume-info">
          Original: <code>{{ volume.source }}</code> → Container: <code>{{ volume.target }}</code>
        </small>
      </div>
    </div>

    <div class="button-group">
      <button type="submit" class="btn btn-primary btn-deploy" :disabled="isSubmitting">
        <svg v-if="!isSubmitting" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3v12M6 11l6 6 6-6M4 21h16" />
        </svg>
        {{ isSubmitting ? 'Deploying…' : 'Deploy Stack' }}
      </button>
      <button v-if="showCancel" type="button" @click="cancelDeploy" class="btn btn-ghost">
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
        backend: 'portainer',
        portainer_endpoint_id: 3,
        arcane_environment_id: 0,
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
        const backendResponse = await axios.get('/api/settings/backend')
        this.formData.backend = backendResponse.data.active_backend

        const isMock = backendResponse.data.available_backends[this.formData.backend]?.mode === 'mock'
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
  gap: 1.1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  font-size: 0.88rem;
  margin-bottom: 0.45rem;
  color: var(--color-text-primary);
}

.form-group small {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 0.3rem;
}

.form-group small.required {
  color: var(--color-error);
}

.hint {
  display: block;
}

/* Bool switch */
.bool-field {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.bool-check {
  display: none;
}

.bool-toggle {
  position: relative;
  width: 46px;
  height: 26px;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.bool-toggle::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  transition: transform var(--transition-base), background var(--transition-base);
}

.bool-check:checked + .bool-toggle {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-color: transparent;
}

.bool-check:checked + .bool-toggle::after {
  transform: translateX(20px);
  background: #fff;
}

.bool-text {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}

/* Volume mounts */
.volumes-section {
  margin-top: 0.75rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--color-border-light);
}

.volumes-section h3 {
  font-size: 1.02rem;
  margin-bottom: 0.3rem;
  color: var(--color-text-primary);
}

.volumes-hint {
  color: var(--color-text-secondary);
  font-size: 0.84rem;
  margin-bottom: 1.1rem;
}

.volume-group {
  background: var(--color-glass);
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  border-left: 3px solid var(--color-primary);
}

.volume-target {
  font-family: var(--font-mono);
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.88rem;
}

.volume-service {
  margin-left: 0.45rem;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.volume-info {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.volume-info code {
  background: var(--color-bg-tertiary);
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

/* Buttons */
.button-group {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.85rem;
  margin-top: 0.75rem;
}

.btn-deploy {
  width: 100%;
}

/* Result */
.deploy-result {
  margin-top: 0.75rem;
  padding: 1.1rem 1.25rem;
  border-radius: var(--radius-md);
  border: 1px solid;
  animation: popIn 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.deploy-result.success {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.28);
  color: var(--color-success);
}

.deploy-result.error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.28);
  color: var(--color-error);
}

.result-title {
  font-weight: 700;
  font-size: 1.05rem;
  margin-bottom: 0.4rem;
}

.result-message {
  margin-bottom: 0.4rem;
  font-size: 0.92rem;
}

.result-detail {
  margin-top: 0.6rem;
  font-size: 0.9rem;
}

.result-detail code {
  background: var(--color-bg-tertiary);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.result-error {
  margin-top: 0.85rem;
  padding: 0.75rem;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  max-height: 200px;
  overflow-y: auto;
  color: var(--color-text-primary);
}
</style>