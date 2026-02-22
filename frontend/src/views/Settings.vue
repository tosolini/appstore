<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <div class="settings-container">
      <!-- Portainer Configuration -->
      <div class="settings-section">
        <h2>Portainer Configuration</h2>
        <div class="mode-indicator" :class="portainerMode">
          Mode: <strong>{{ portainerMode.toUpperCase() }}</strong>
        </div>

        <div class="mode-toggle-section">
          <label class="toggle-label">Force Mock Mode</label>
          <div class="toggle-switch">
            <input 
              type="checkbox" 
              v-model="forceMockMode"
              @change="togglePortainerMode"
              class="toggle-input"
              id="force-mock"
            >
            <label for="force-mock" class="toggle-label-switch"></label>
            <span class="toggle-text">{{ forceMockMode ? 'Enabled (Mock)' : 'Disabled (Real)' }}</span>
          </div>
          <small class="hint">Toggle to switch between Mock and Real Portainer. App restart required for full effect.</small>
        </div>

        <form @submit.prevent="savePortainerConfig" class="portainer-form">
          <div class="form-group">
            <label>Base URL</label>
            <input v-model="portainerConfig.base_url" 
                   type="url" 
                   placeholder="http://portainer:9000"
                   :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
          </div>

          <div class="form-group">
            <label>API Key</label>
            <input v-model="portainerConfig.api_key" 
                   type="password" 
                   placeholder="Your Portainer API key"
                   :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
          </div>

          <div class="form-group">
            <label>Endpoint ID</label>
            <input v-model.number="portainerConfig.endpoint_id" 
                   type="number" 
                   min="1"
                   :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
          </div>

          <div v-if="!portainerConfigReadOnly" class="button-group">
            <button type="submit" class="btn-save" :disabled="portainerMode === 'mock'">
              Save Configuration
            </button>
            <button type="button" @click="testConnection" class="btn-test" :disabled="portainerMode === 'mock'">
              Test Connection
            </button>
          </div>
          <div v-else class="status info">
            Configuration is managed via docker-compose.yml env vars. Update and restart to apply changes.
          </div>

          <div v-if="testStatus" :class="['status', testStatus.success ? 'success' : 'error']">
            {{ testStatus.message }}
          </div>
        </form>

        <div v-if="portainerMode === 'mock'" class="mock-notice">
          ℹ️ Running in mock mode. Real Portainer is disabled. Switch to production for real deployments.
        </div>
      </div>

      <!-- Mock Stacks Viewer (only in mock mode) -->
      <div v-if="portainerMode === 'mock'" class="settings-section">
        <h2>Mock Deployment Stacks</h2>
        <p class="text-muted">Stacks deployed during testing (in-memory, not persisted)</p>
        
        <div v-if="mockStacks.length === 0" class="no-stacks">
          No stacks deployed yet. Deploy an app to see it here.
        </div>

        <div v-else class="stacks-list">
          <div class="stacks-header">
            <div class="col-name">Stack Name</div>
            <div class="col-status">Status</div>
            <div class="col-endpoint">Endpoint</div>
            <div class="col-created">Created</div>
          </div>
          <div v-for="stack in mockStacks" :key="stack.id" class="stack-item">
            <div class="col-name">{{ stack.name }}</div>
            <div class="col-status">
              <span class="status-badge" :class="stack.status">{{ stack.status }}</span>
            </div>
            <div class="col-endpoint">{{ stack.endpoint_id }}</div>
            <div class="col-created">{{ formatDate(stack.created_at) }}</div>
          </div>
          <button @click="resetMockStacks" class="btn-clear-all">🗑️ Clear All Stacks</button>
        </div>
      </div>

      <!-- Repository Management -->
      <div class="settings-section">
        <h2>App Repositories</h2>
        <p class="text-muted">Manage multiple app repositories</p>

        <form @submit.prevent="addRepository" class="add-repo-form">
          <div class="form-row">
            <div class="form-group">
              <label>Repository Name</label>
              <input v-model="newRepo.name" type="text" placeholder="e.g., My Apps" required>
            </div>
            <div class="form-group">
              <label>Git URL</label>
              <input v-model="newRepo.url" type="url" placeholder="https://github.com/..." required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Branch</label>
              <input v-model="newRepo.branch" type="text" placeholder="main" value="main">
            </div>
            <div class="form-group">
              <label>Priority</label>
              <input v-model.number="newRepo.priority" type="number" placeholder="100" value="100">
            </div>
          </div>
          <button type="submit" class="btn-add">Add Repository</button>
        </form>

        <div v-if="repositories.length === 0" class="no-repos">
          No repositories configured.
        </div>

        <div v-else class="repos-list">
          <div v-for="repo in repositories" :key="repo.id" class="repo-item">
            <div class="repo-info">
              <div class="repo-name">
                {{ repo.name }}
                <span v-if="repoSyncingState[repo.id]" class="syncing-indicator">⟳ Syncing...</span>
              </div>
              <div class="repo-url">{{ repo.url }}</div>
              <div class="repo-meta">
                <span>Branch: {{ repo.branch }}</span>
                <span>Priority: {{ repo.priority }}</span>
                <span v-if="repo.last_synced">Last sync: {{ formatDate(repo.last_synced) }}</span>
              </div>
            </div>
            <div class="repo-actions">
              <button @click="toggleRepository(repo.id, !repo.enabled)" 
                      :class="['btn-toggle', repo.enabled ? 'enabled' : 'disabled']"
                      :disabled="repoSyncingState[repo.id]">
                {{ repo.enabled ? 'Enabled' : 'Disabled' }}
              </button>
              <button @click="syncRepository(repo.id)" 
                      class="btn-sync"
                      :disabled="!repo.enabled || repoSyncingState[repo.id]"
                      :title="repo.enabled ? 'Sync this repository' : 'Enable repository to sync'">
                {{ repoSyncingState[repo.id] ? 'Syncing...' : 'Sync Now' }}
              </button>
              <button @click="deleteRepository(repo.id)" 
                      class="btn-delete"
                      :disabled="repoSyncingState[repo.id]">
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Cache Management -->
      <div class="settings-section">
        <h2>Cache Management</h2>
        <p class="text-muted">Manage the repository cache to fix syncing issues</p>

        <div class="cache-info">
          <div class="info-item">
            <label>Cache Size:</label>
            <span>{{ cacheStatus.cache_size }}</span>
          </div>
          <div class="info-item">
            <label>Apps Loaded:</label>
            <span>{{ cacheStatus.apps_loaded }}</span>
          </div>
          <div class="info-item">
            <label>Last Sync:</label>
            <span>{{ cacheStatus.last_sync ? formatDate(cacheStatus.last_sync) : 'Never' }}</span>
          </div>
          <div class="info-item">
            <label>Cache Path:</label>
            <span class="monospace">{{ cacheStatus.cache_dir }}</span>
          </div>
        </div>

        <div class="cache-actions">
          <button @click="clearCacheAndResync" class="btn-clear-cache" :disabled="clearingCache">
            {{ clearingCache ? 'Clearing Cache...' : '🗑️ Clear Cache & Resync' }}
          </button>
          <small class="hint">This will delete all cached repositories and reload them from Git. May take a few moments.</small>
        </div>

        <div v-if="cacheStatus" class="status info" style="margin-top: 10px; font-size: 0.9em;">
          ℹ️ Cache initialized: {{ cacheStatus.initialized ? 'Yes' : 'No' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Settings',
  data() {
    return {
      portainerMode: 'mock',
      forceMockMode: false,
      portainerConfig: {
        base_url: '',
        api_key: '',
        endpoint_id: 1
      },
      portainerConfigReadOnly: false,
      testStatus: null,
      repositories: [],
      mockStacks: [],
      newRepo: {
        name: '',
        url: '',
        branch: 'main',
        priority: 100
      },
      loading: false,
      repoSyncingState: {}, // {repoId: boolean}
      cacheStatus: {
        cache_size: 'unknown',
        apps_loaded: 0,
        last_sync: null,
        cache_dir: '',
        initialized: false
      },
      clearingCache: false
    }
  },
  mounted() {
    this.loadSettings()
  },
  methods: {
    async loadSettings() {
      try {
        const [portainerResponse, reposResponse, modeResponse, cacheStatusResponse] = await Promise.all([
          axios.get('/api/settings/portainer'),
          axios.get('/api/repositories'),
          axios.get('/api/settings/portainer-mode'),
          axios.get('/api/settings/cache/status')
        ])

        this.portainerMode = modeResponse.data.current_mode
        this.forceMockMode = modeResponse.data.force_mock_mode
        this.portainerConfig = {
          base_url: portainerResponse.data.base_url || '',
          api_key: portainerResponse.data.api_key || '',
          endpoint_id: portainerResponse.data.endpoint_id || 1
        }
        this.portainerConfigReadOnly = Boolean(portainerResponse.data.read_only)

        this.repositories = reposResponse.data.repositories || []
        
        this.cacheStatus = cacheStatusResponse.data

        if (this.portainerMode === 'mock') {
          this.loadMockStacks()
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    },

    async loadMockStacks() {
      try {
        const response = await axios.get('/api/mock/stacks')
        this.mockStacks = response.data.stacks.slice(0, 10) // Ultimi 10
      } catch (error) {
        console.error('Error loading mock stacks:', error)
      }
    },

    async togglePortainerMode() {
      try {
        const response = await axios.post('/api/settings/portainer-mode/toggle')
        this.forceMockMode = response.data.force_mock_mode
        
        // Mostra messaggio che è richiesto restart
        alert(response.data.message)
      } catch (error) {
        console.error('Error toggling portainer mode:', error)
        alert('Error toggling mode')
        this.loadSettings() // Ricarica per ripristinare lo stato precedente
      }
    },

    async savePortainerConfig() {
      this.loading = true
      try {
        await axios.post('/api/settings/portainer', {
          base_url: this.portainerConfig.base_url,
          api_key: this.portainerConfig.api_key,
          endpoint_id: this.portainerConfig.endpoint_id
        })
        this.testStatus = {
          success: true,
          message: 'Configuration saved successfully'
        }
      } catch (error) {
        this.testStatus = {
          success: false,
          message: error.response?.data?.detail || 'Failed to save configuration'
        }
      } finally {
        this.loading = false
      }
    },

    async testConnection() {
      this.loading = true
      try {
        const response = await axios.post('/api/settings/portainer', {
          base_url: this.portainerConfig.base_url,
          api_key: this.portainerConfig.api_key,
          endpoint_id: this.portainerConfig.endpoint_id
        })
        this.testStatus = {
          success: true,
          message: 'Connection successful! ✓'
        }
      } catch (error) {
        this.testStatus = {
          success: false,
          message: error.response?.data?.detail || 'Connection failed'
        }
      } finally {
        this.loading = false
      }
    },

    async addRepository() {
      try {
        const response = await axios.post('/api/repositories', this.newRepo)
        this.repositories.push(response.data)
        this.newRepo = {
          name: '',
          url: '',
          branch: 'main',
          priority: 100
        }
        alert('Repository added successfully!')
      } catch (error) {
        // Estrai il messaggio di errore dal response FASTapi
        let errorMessage = 'Unknown error'
        
        if (error.response?.data?.detail) {
          // FastAPI ritorna {detail: "message"}
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail
          } else if (Array.isArray(error.response.data.detail)) {
            // Se è un array di validation errors
            errorMessage = error.response.data.detail
              .map(e => e.msg || JSON.stringify(e))
              .join(', ')
          } else {
            errorMessage = JSON.stringify(error.response.data.detail)
          }
        } else if (error.response?.data) {
          errorMessage = JSON.stringify(error.response.data)
        } else if (error.message) {
          errorMessage = error.message
        }
        
        console.error('Error adding repository:', error)
        alert(`Error adding repository: ${errorMessage}`)
      }
    },

    async toggleRepository(repoId, enabled) {
      try {
        const response = await axios.put(`/api/repositories/${repoId}`, {
          enabled: enabled
        })
        
        const idx = this.repositories.findIndex(r => r.id === repoId)
        if (idx >= 0) {
          this.repositories[idx] = response.data
        }
        
        // Se si abilita, sincronizza automaticamente
        if (enabled) {
          await this.syncRepository(repoId)
        }
      } catch (error) {
        console.error('Error updating repository:', error)
        alert('Error updating repository: ' + (error.response?.data?.detail || error.message))
      }
    },

    async syncRepository(repoId) {
      try {
        this.repoSyncingState[repoId] = true
        await axios.post(`/api/repositories/${repoId}/sync`)
        await this.loadSettings()
      } catch (error) {
        alert('Error syncing repository: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.repoSyncingState[repoId] = false
      }
    },

    async deleteRepository(repoId) {
      if (!confirm('Are you sure you want to delete this repository?')) {
        return
      }

      try {
        await axios.delete(`/api/repositories/${repoId}`)
        this.repositories = this.repositories.filter(r => r.id !== repoId)
      } catch (error) {
        alert('Error deleting repository: ' + (error.response?.data?.detail || error.message))
      }
    },

    async resetMockStacks() {
      if (!confirm('Clear all mock stacks? This cannot be undone.')) {
        return
      }

      try {
        await axios.post('/api/mock/reset')
        this.mockStacks = []
      } catch (error) {
        console.error('Error resetting mock:', error)
      }
    },

    async clearCacheAndResync() {
      if (!confirm('This will delete all cached repositories and reload them from Git. This may take a few moments. Continue?')) {
        return
      }

      this.clearingCache = true
      try {
        const response = await axios.post('/api/settings/cache/clear')
        
        if (response.data.success) {
          alert('Cache cleared and repositories resynced successfully!')
          // Ricarica i settings per aggiornare lo stato della cache
          await this.loadSettings()
        } else {
          alert(`Error: ${response.data.message}`)
        }
      } catch (error) {
        console.error('Error clearing cache:', error)
        alert(`Error clearing cache: ${error.response?.data?.detail || error.message}`)
      } finally {
        this.clearingCache = false
      }
    },

    formatDate(isoString) {
      if (!isoString) return 'Never'
      const date = new Date(isoString)
      return date.toLocaleString('it-IT', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.settings-page {
  padding: 1rem 0;
}

.settings-page h1 {
  font-size: 2rem;
  margin-bottom: 2rem;
  color: var(--color-text-primary);
}

.settings-container {
  display: grid;
  gap: 2rem;
}

.settings-section {
  background: var(--color-bg-secondary);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border);
}

.settings-section h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--color-primary);
  padding-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.mode-indicator {
  background: var(--color-bg-tertiary);
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  font-weight: 500;
  color: var(--color-text-primary);
  border-left: 4px solid var(--color-warning);
}

.mode-indicator.mock {
  background: rgba(255, 193, 7, 0.15);
  color: var(--color-warning);
  border-left-color: var(--color-warning);
}

.mode-indicator.real {
  background: rgba(72, 187, 120, 0.15);
  color: var(--color-success);
  border-left-color: var(--color-success);
}

.mode-toggle-section {
  background: var(--color-bg-tertiary);
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  border: 1px solid var(--color-border);
}

.toggle-switch {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.5rem;
}

.toggle-input {
  appearance: none;
  width: 50px;
  height: 28px;
  background: var(--color-border);
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.3s ease;
  position: relative;
}

.toggle-input:checked {
  background: var(--color-error);
}

.toggle-input::before {
  content: '';
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: left 0.3s ease;
}

.toggle-input:checked::before {
  left: 24px;
}

.toggle-label-switch {
  display: none;
}

.toggle-text {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.portainer-form,
.add-repo-form {
  display: grid;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 1rem;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  background: var(--color-bg-tertiary);
  color: var(--color-text-muted);
  opacity: 0.6;
}

.button-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.btn-save,
.btn-test,
.btn-add,
.btn-toggle,
.btn-sync,
.btn-delete,
.btn-clear {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  font-size: 1rem;
}

.btn-save,
.btn-add {
  background: var(--color-primary);
  color: white;
}

.btn-save:hover,
.btn-add:hover {
  background: var(--color-primary-dark);
}

.btn-save:disabled,
.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-test {
  background: var(--color-info);
  color: white;
}

.btn-test:hover {
  background: #3b7cc7;
}

.btn-toggle {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  font-size: 0.9rem;
  border: 1px solid var(--color-border);
}

.btn-toggle.enabled {
  background: var(--color-success);
  color: white;
  border-color: var(--color-success);
}

.btn-toggle:hover {
  opacity: 0.9;
}

.btn-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sync {
  background: var(--color-warning);
  color: #333;
  font-size: 0.9rem;
}

.btn-sync:hover {
  background: #e0a800;
}

.btn-sync:disabled {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  cursor: not-allowed;
  opacity: 0.5;
}

.btn-delete,
.btn-clear {
  background: var(--color-error);
  color: white;
  font-size: 0.9rem;
}

.btn-delete:hover,
.btn-clear:hover {
  background: #e01c1c;
}

.btn-delete:disabled,
.btn-clear:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.status {
  padding: 1rem;
  border-radius: 4px;
  border-left: 4px solid;
}

.status.success {
  background: rgba(72, 187, 120, 0.15);
  border-color: var(--color-success);
  color: var(--color-success);
}

.status.error {
  background: rgba(245, 101, 101, 0.15);
  border-color: var(--color-error);
  color: var(--color-error);
}

.status.info {
  background: rgba(66, 153, 225, 0.15);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.mock-notice {
  background: rgba(255, 193, 7, 0.15);
  border: 1px solid var(--color-warning);
  border-radius: 4px;
  padding: 1rem;
  color: var(--color-warning);
  margin-top: 1.5rem;
  text-align: center;
}

.text-muted {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
}

.no-stacks,
.no-repos {
  background: var(--color-bg-tertiary);
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
  border-radius: 4px;
  border: 1px dashed var(--color-border);
}

.stacks-list {
  display: grid;
  gap: 1rem;
}

.stack-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.stack-name {
  font-weight: 500;
  flex: 1;
}

.stack-status {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  margin: 0 1rem;
}

.stack-status.running {
  background: rgba(72, 187, 120, 0.2);
  color: var(--color-success);
}

.repos-list {
  display: grid;
  gap: 1.5rem;
}

.repo-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-primary);
}

@media (max-width: 768px) {
  .repo-item {
    grid-template-columns: 1fr;
  }
}

.repo-info {
  display: grid;
  gap: 0.5rem;
}

.repo-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.syncing-indicator {
  font-size: 0.85rem;
  color: var(--color-warning);
  font-weight: 500;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.repo-url {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  word-break: break-all;
}

.repo-meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.repo-actions {
  display: grid;
  grid-template-columns: auto auto auto;
  gap: 0.5rem;
}

/* Mock Stacks List */
.stacks-list {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--color-bg-secondary);
}

.stacks-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  gap: 0;
  background: var(--color-bg-tertiary);
  padding: 1rem;
  font-weight: 600;
  border-bottom: 2px solid var(--color-border);
  font-size: 0.95rem;
  color: var(--color-text-primary);
}

.stack-item {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  gap: 0;
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
  align-items: center;
}

.stack-item:last-child {
  border-bottom: none;
}

.stack-item:hover {
  background: var(--color-bg-primary);
}

.col-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.col-status,
.col-endpoint,
.col-created {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.running {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-badge.pending {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-badge.error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.no-stacks {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: 6px;
  border: 1px dashed var(--color-border);
}

.btn-clear-all {
  width: 100%;
  padding: 0.75rem;
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-top: 2px solid var(--color-border);
  border-radius: 0;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s ease;
}

.btn-clear-all:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.cache-info {
  background: var(--color-bg-tertiary);
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.cache-info .info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cache-info label {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.cache-info .monospace {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.8rem;
  color: var(--color-text-primary);
  word-break: break-all;
}

.cache-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-clear-cache {
  padding: 0.75rem 1.5rem;
  background: var(--color-error);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  font-size: 1rem;
  transition: background 0.2s ease;
}

.btn-clear-cache:hover:not(:disabled) {
  background: #dc2626;
}

.btn-clear-cache:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .stacks-header {
    display: none;
  }

  .stack-item {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .col-name::before {
    content: 'Stack: ';
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .col-status::before {
    content: 'Status: ';
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .col-endpoint::before {
    content: 'Endpoint: ';
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .col-created::before {
    content: 'Created: ';
    font-weight: 600;
    color: var(--color-text-primary);
  }
}

@media (max-width: 768px) {
  .repo-actions {
    grid-template-columns: 1fr;
  }
}
</style>
