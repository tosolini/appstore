<template>
  <div class="settings-page">
    <header class="page-head reveal">
      <div>
        <h1>Settings</h1>
        <p class="text-muted">Deployment backends, repositories, cache and app display options.</p>
      </div>
    </header>

    <div class="settings-container">
      <!-- Backend Selector -->
      <section class="panel settings-section reveal">
        <h2>Deployment Backend</h2>
        <p class="text-muted">Choose which container management platform to use for deployments</p>

        <div class="backend-selector">
          <div class="backend-option"
               :class="{ active: activeBackend === 'portainer', available: backends.portainer?.configured }"
               @click="selectBackend('portainer')"
               role="button"
               tabindex="0"
               @keydown.enter="selectBackend('portainer')">
            <span class="backend-indicator" :class="backends.portainer?.mode"></span>
            <div class="backend-info">
              <strong>Portainer</strong>
              <span class="backend-status">
                Mode: {{ (backends.portainer?.mode || 'mock').toUpperCase() }}
              </span>
              <span v-if="backends.portainer?.connected" class="status-connected">
                <span class="dot"></span> Connected
              </span>
              <span v-else class="status-disconnected">
                <span class="dot"></span> Not connected
              </span>
            </div>
            <div v-if="activeBackend === 'portainer'" class="active-badge">
              <span class="pulse"></span> ACTIVE
            </div>
          </div>

          <div class="backend-option"
               :class="{ active: activeBackend === 'arcane', available: backends.arcane?.configured }"
               @click="selectBackend('arcane')"
               role="button"
               tabindex="0"
               @keydown.enter="selectBackend('arcane')">
            <span class="backend-indicator" :class="backends.arcane?.mode"></span>
            <div class="backend-info">
              <strong>Arcane</strong>
              <span class="backend-status">
                Mode: {{ (backends.arcane?.mode || 'mock').toUpperCase() }}
              </span>
              <span v-if="backends.arcane?.connected" class="status-connected">
                <span class="dot"></span> Connected
              </span>
              <span v-else class="status-disconnected">
                <span class="dot"></span> Not connected
              </span>
            </div>
            <div v-if="activeBackend === 'arcane'" class="active-badge">
              <span class="pulse"></span> ACTIVE
            </div>
          </div>
        </div>

        <div v-if="backendSelectMessage" class="status-banner" :class="backendSelectMessage.success ? 'success' : 'error'">
          {{ backendSelectMessage.message }}
        </div>
      </section>

      <!-- Backend Configuration (tabs) -->
      <section class="panel settings-section reveal">
        <div class="config-tabs" role="tablist" aria-label="Backend configuration">
          <button
            :class="['config-tab', { active: configTab === 'portainer' }]"
            role="tab"
            :aria-selected="configTab === 'portainer'"
            @click="configTab = 'portainer'"
          >
            <span class="config-tab-dot portainer"></span>
            Portainer
            <span v-if="activeBackend === 'portainer'" class="config-tab-badge">active</span>
          </button>
          <button
            :class="['config-tab', { active: configTab === 'arcane' }]"
            role="tab"
            :aria-selected="configTab === 'arcane'"
            @click="configTab = 'arcane'"
          >
            <span class="config-tab-dot arcane"></span>
            Arcane
            <span v-if="activeBackend === 'arcane'" class="config-tab-badge">active</span>
          </button>
        </div>

        <transition name="tab" mode="out-in">
          <!-- Portainer tab -->
          <div v-if="configTab === 'portainer'" class="config-panel" key="portainer">
            <div class="config-head">
              <h2>Portainer Configuration</h2>
              <div class="mode-indicator" :class="portainerMode">
                <span class="mode-dot"></span>
                Mode: <strong>{{ portainerMode.toUpperCase() }}</strong>
              </div>
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
                       class="input"
                       :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
              </div>

              <div class="form-group">
                <label>API Key</label>
                <input v-model="portainerConfig.api_key"
                       type="password"
                       placeholder="Your Portainer API key"
                       class="input"
                       :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
              </div>

              <div class="form-group">
                <label>Endpoint ID</label>
                <input v-model.number="portainerConfig.endpoint_id"
                       type="number"
                       min="1"
                       class="input"
                       :disabled="portainerMode === 'mock' || portainerConfigReadOnly">
              </div>

              <div v-if="!portainerConfigReadOnly" class="button-group">
                <button type="submit" class="btn btn-primary" :disabled="portainerMode === 'mock'">
                  Save Configuration
                </button>
                <button type="button" @click="testConnection" class="btn btn-ghost" :disabled="portainerMode === 'mock'">
                  Test Connection
                </button>
              </div>
              <div v-else class="status-banner info">
                Configuration is managed via docker-compose.yml env vars. Update and restart to apply changes.
              </div>

              <div v-if="testStatus" class="status-banner" :class="testStatus.success ? 'success' : 'error'">
                {{ testStatus.message }}
              </div>
            </form>

            <div v-if="portainerMode === 'mock'" class="mock-notice">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8h.01M12 12v4" />
              </svg>
              Running in mock mode. Real Portainer is disabled. Switch to production for real deployments.
            </div>
          </div>

          <!-- Arcane tab -->
          <div v-else class="config-panel" key="arcane">
            <div class="config-head">
              <h2>Arcane Configuration</h2>
              <div class="mode-indicator" :class="arcaneMode">
                <span class="mode-dot"></span>
                Mode: <strong>{{ arcaneMode.toUpperCase() }}</strong>
              </div>
            </div>

            <div class="mode-toggle-section">
              <label class="toggle-label">Force Mock Mode</label>
              <div class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="arcaneForceMockMode"
                  @change="toggleArcaneMode"
                  class="toggle-input"
                  id="force-arcane-mock"
                >
                <label for="force-arcane-mock" class="toggle-label-switch"></label>
                <span class="toggle-text">{{ arcaneForceMockMode ? 'Enabled (Mock)' : 'Disabled (Real)' }}</span>
              </div>
              <small class="hint">Toggle to switch between Mock and Real Arcane. App restart required for full effect.</small>
            </div>

            <form @submit.prevent="saveArcaneConfig" class="arcane-form">
              <div class="form-group">
                <label>Base URL</label>
                <input v-model="arcaneConfig.base_url"
                       type="url"
                       placeholder="http://arcane:3552"
                       class="input"
                       :disabled="arcaneMode === 'mock' || arcaneConfigReadOnly">
              </div>

              <div class="form-group">
                <label>API Key</label>
                <input v-model="arcaneConfig.api_key"
                       type="password"
                       placeholder="Your Arcane API key"
                       class="input"
                       :disabled="arcaneMode === 'mock' || arcaneConfigReadOnly">
              </div>

              <div class="form-group">
                <label>Environment ID</label>
                <input v-model.number="arcaneConfig.environment_id"
                       type="number"
                       min="0"
                       class="input"
                       :disabled="arcaneMode === 'mock' || arcaneConfigReadOnly">
              </div>

              <div class="status-banner info">
                Configuration is managed via docker-compose.yml env vars. Update ARCANE_BASE_URL/API_KEY and restart.
              </div>
            </form>

            <div v-if="arcaneMode === 'mock'" class="mock-notice">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8h.01M12 12v4" />
              </svg>
              Running in mock mode. Real Arcane is disabled. Switch to production for real deployments.
            </div>
          </div>
        </transition>
      </section>

      <!-- App Display Settings -->
      <section class="panel settings-section reveal">
        <h2>App Display Settings</h2>
        <p class="text-muted">Customize how apps are displayed in the home page</p>

        <form @submit.prevent="saveDisplaySettings" class="display-form">
          <div class="form-group">
            <label>Apps per page</label>
            <input
              v-model.number="displaySettings.appsPerPage"
              type="number"
              min="1"
              max="100"
              placeholder="10"
              class="input"
            >
            <small class="hint">Number of apps to display per page (default: 10)</small>
          </div>

          <div class="button-group">
            <button type="submit" class="btn btn-primary">
              Save Display Settings
            </button>
          </div>

          <div v-if="displaySaveStatus" class="status-banner" :class="displaySaveStatus.success ? 'success' : 'error'">
            {{ displaySaveStatus.message }}
          </div>
        </form>
      </section>

      <!-- Mock Stacks Viewer -->
      <section v-if="backends.portainer?.mode === 'mock'" class="panel settings-section reveal">
        <h2>Portainer Mock Stacks</h2>
        <p class="text-muted">Stacks deployed to mock Portainer (in-memory, not persisted)</p>

        <div v-if="portainerMockStacks.length === 0" class="no-stacks">
          No stacks deployed yet. Deploy an app to see it here.
        </div>

        <div v-else class="stacks-list">
          <div class="stacks-header">
            <div class="col-name">Stack Name</div>
            <div class="col-status">Status</div>
            <div class="col-endpoint">Endpoint</div>
            <div class="col-created">Created</div>
          </div>
          <div v-for="stack in portainerMockStacks" :key="stack.id" class="stack-item">
            <div class="col-name">{{ stack.name }}</div>
            <div class="col-status">
              <span class="status-badge" :class="stack.status">{{ stack.status }}</span>
            </div>
            <div class="col-endpoint">{{ stack.endpoint_id }}</div>
            <div class="col-created">{{ formatDate(stack.created_at) }}</div>
          </div>
          <button @click="resetPortainerMock" class="btn btn-soft-danger btn-sm btn-clear-all">
            Clear All Portainer Stacks
          </button>
        </div>
      </section>

      <section v-if="backends.arcane?.mode === 'mock'" class="panel settings-section reveal">
        <h2>Arcane Mock Projects</h2>
        <p class="text-muted">Projects deployed to mock Arcane (in-memory, not persisted)</p>

        <div v-if="arcaneMockProjects.length === 0" class="no-stacks">
          No projects deployed yet. Deploy an app to see it here.
        </div>

        <div v-else class="stacks-list">
          <div class="stacks-header">
            <div class="col-name">Project Name</div>
            <div class="col-status">Status</div>
            <div class="col-id">Project ID</div>
            <div class="col-created">Created</div>
          </div>
          <div v-for="project in arcaneMockProjects" :key="project.id" class="stack-item">
            <div class="col-name">{{ project.name }}</div>
            <div class="col-status">
              <span class="status-badge" :class="project.status">{{ project.status }}</span>
            </div>
            <div class="col-id">{{ project.id }}</div>
            <div class="col-created">{{ formatDate(project.created_at) }}</div>
          </div>
          <button @click="resetArcaneMock" class="btn btn-soft-danger btn-sm btn-clear-all">
            Clear All Arcane Projects
          </button>
        </div>
      </section>

      <!-- CasaOS Repositories -->
      <section class="panel settings-section reveal">
        <h2>CasaOS compatible App Repositories</h2>
        <p class="text-muted">Manage multiple CasaOS compatible app repositories</p>

        <form @submit.prevent="addRepository" class="add-repo-form">
          <div class="form-row">
            <div class="form-group">
              <label>CasaOS Repository Name</label>
              <input v-model="newRepo.name" type="text" placeholder="e.g., My Apps" required class="input">
            </div>
            <div class="form-group">
              <label>Git URL</label>
              <input v-model="newRepo.url" type="url" placeholder="https://github.com/..." required class="input">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Branch</label>
              <input v-model="newRepo.branch" type="text" placeholder="main" value="main" class="input">
            </div>
            <div class="form-group">
              <label>Priority</label>
              <input v-model.number="newRepo.priority" type="number" placeholder="100" value="100" class="input">
            </div>
          </div>
          <div class="button-group">
            <button type="submit" class="btn btn-primary">Add CasaOS Repository</button>
          </div>
        </form>

        <div v-if="repositories.length === 0" class="no-stacks no-repos">
          No CasaOS repositories configured.
        </div>

        <div v-else class="repos-list">
          <div v-for="repo in repositories" :key="repo.id" class="repo-item">
            <div class="repo-info">
              <div class="repo-name">
                {{ repo.name }}
                <span v-if="repoSyncingState[repo.id]" class="syncing-indicator">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
                    <path d="M21 12a9 9 0 1 1-2.6-6.3M21 3v6h-6" />
                  </svg>
                  Syncing…
                </span>
              </div>
              <div class="repo-url mono">{{ repo.url }}</div>
              <div class="repo-meta">
                <span class="badge">branch: {{ repo.branch }}</span>
                <span class="badge">priority: {{ repo.priority }}</span>
                <span v-if="repo.last_synced" class="badge">last sync: {{ formatDate(repo.last_synced) }}</span>
                <span v-else class="badge">never synced</span>
              </div>
            </div>
            <div class="repo-actions">
              <button @click="toggleRepository(repo.id, !repo.enabled)"
                      :class="['btn', 'btn-sm', repo.enabled ? 'btn-primary' : 'btn-ghost']"
                      :disabled="repoSyncingState[repo.id]">
                {{ repo.enabled ? 'Enabled' : 'Disabled' }}
              </button>
              <button @click="syncRepository(repo.id)"
                      class="btn btn-accent btn-sm"
                      :disabled="!repo.enabled || repoSyncingState[repo.id]"
                      :title="repo.enabled ? 'Sync this repository' : 'Enable repository to sync'">
                {{ repoSyncingState[repo.id] ? 'Syncing…' : 'Sync Now' }}
              </button>
              <button @click="deleteRepository(repo.id)"
                      class="btn btn-soft-danger btn-sm"
                      :disabled="repoSyncingState[repo.id]">
                Delete
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- GitHub Import -->
      <section class="panel settings-section reveal">
        <div class="sub-section">
          <h3 class="section-subtitle">Reset imported apps</h3>
          <p class="text-muted">Replace all imported GitHub apps with the bundled default set without contacting GitHub.</p>
          <button type="button" class="btn btn-soft-danger" :disabled="resettingGithub" @click="resetGitHubImports">
            {{ resettingGithub ? 'Resetting…' : 'Full Reset to Default' }}
          </button>
          <div v-if="githubResetStatus" class="status-banner" :class="githubResetStatus.success ? 'success' : 'error'">
            {{ githubResetStatus.message }}
          </div>
        </div>
        <br />
        <div class="status-banner info">
          Imported apps are managed on the dedicated
          <router-link to="/imports/github">GitHub Imports</router-link>
          page.
        </div>
      </section>

      <!-- Cache Management -->
      <section class="panel settings-section reveal">
        <h2>Cache Management</h2>
        <p class="text-muted">Manage the repository cache to fix syncing issues</p>

        <div class="cache-info">
          <div class="info-item">
            <label>Cache Size</label>
            <span class="mono">{{ cacheStatus.cache_size }}</span>
          </div>
          <div class="info-item">
            <label>Apps Loaded</label>
            <span class="mono">{{ cacheStatus.apps_loaded }}</span>
          </div>
          <div class="info-item">
            <label>Last Sync</label>
            <span>{{ cacheStatus.last_sync ? formatDate(cacheStatus.last_sync) : 'Never' }}</span>
          </div>
          <div class="info-item">
            <label>Cache Path</label>
            <span class="mono">{{ cacheStatus.cache_dir }}</span>
          </div>
          <div class="info-item">
            <label>Initialized</label>
            <span class="badge" :class="cacheStatus.initialized ? 'badge-success' : 'badge-error'">
              {{ cacheStatus.initialized ? 'Yes' : 'No' }}
            </span>
          </div>
        </div>

        <div class="cache-actions">
          <button @click="clearCacheAndResync" class="btn btn-soft-danger" :disabled="clearingCache">
            {{ clearingCache ? 'Clearing Cache…' : 'Clear Cache & Resync' }}
          </button>
          <small class="hint">This will delete all cached repositories and reload them from Git. May take a few moments.</small>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Settings',
  data() {
    return {
      activeBackend: 'portainer',
      backends: {
        portainer: { mode: 'mock', configured: false, connected: false },
        arcane: { mode: 'mock', configured: false, connected: false }
      },
      backendSelectMessage: null,
      portainerMode: 'mock',
      forceMockMode: false,
      portainerConfig: {
        base_url: '',
        api_key: '',
        endpoint_id: 1
      },
      portainerConfigReadOnly: false,
      testStatus: null,
      arcaneMode: 'mock',
      arcaneForceMockMode: false,
      arcaneConfig: {
        base_url: '',
        api_key: '',
        environment_id: 0
      },
      arcaneConfigReadOnly: false,
      repositories: [],
      githubImportInput: '',
      githubImportResults: [],
      githubImportStatus: null,
      importingGithub: false,
      resettingGithub: false,
      githubResetStatus: null,
      portainerMockStacks: [],
      arcaneMockProjects: [],
      newRepo: {
        name: '',
        url: '',
        branch: 'main',
        priority: 100
      },
      loading: false,
      repoSyncingState: {},
      cacheStatus: {
        cache_size: 'unknown',
        apps_loaded: 0,
        last_sync: null,
        cache_dir: '',
        initialized: false
      },
      clearingCache: false,
      displaySettings: {
        appsPerPage: 12
      },
      displaySaveStatus: null,
      configTab: 'portainer'
    }
  },
  mounted() {
    this.loadSettings()
    this.loadDisplaySettings()
  },
  watch: {
    activeBackend(val) {
      if (val === 'portainer' || val === 'arcane') {
        this.configTab = val
      }
    }
  },
  methods: {
    async loadSettings() {
      try {
        const [backendResponse, portainerResponse, reposResponse, modeResponse, cacheStatusResponse] = await Promise.all([
          axios.get('/api/settings/backend'),
          axios.get('/api/settings/portainer'),
          axios.get('/api/repositories'),
          axios.get('/api/settings/portainer-mode'),
          axios.get('/api/settings/cache/status')
        ])

        this.activeBackend = backendResponse.data.active_backend
        this.backends = backendResponse.data.available_backends

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

        try {
          const arcaneModeResponse = await axios.get('/api/settings/arcane-mode')
          const arcaneConfigResponse = await axios.get('/api/settings/arcane')
          this.arcaneMode = arcaneModeResponse.data.current_mode
          this.arcaneForceMockMode = arcaneModeResponse.data.force_mock_mode
          this.arcaneConfig = {
            base_url: arcaneConfigResponse.data.base_url || '',
            api_key: arcaneConfigResponse.data.api_key || '',
            environment_id: arcaneConfigResponse.data.environment_id || 0
          }
        } catch (e) {
          console.error('Error loading arcane config:', e)
        }

        if (this.backends.portainer?.mode === 'mock') {
          this.loadPortainerMockStacks()
        }
        if (this.backends.arcane?.mode === 'mock') {
          this.loadArcaneMockProjects()
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    },

    async selectBackend(backend) {
      try {
        const response = await axios.post('/api/settings/backend/select', { backend })
        this.activeBackend = response.data.active_backend
        this.backendSelectMessage = {
          success: true,
          message: `Active backend switched to ${backend.toUpperCase()}`
        }
        setTimeout(() => { this.backendSelectMessage = null }, 3000)
      } catch (error) {
        this.backendSelectMessage = {
          success: false,
          message: error.response?.data?.detail || 'Failed to switch backend'
        }
      }
    },

    async loadPortainerMockStacks() {
      try {
        const response = await axios.get('/api/mock/stacks')
        this.portainerMockStacks = response.data.stacks.slice(0, 10)
      } catch (error) {
        console.error('Error loading mock stacks:', error)
      }
    },

    async loadArcaneMockProjects() {
      try {
        const response = await axios.get('/api/mock/arcane/projects')
        this.arcaneMockProjects = response.data.projects.slice(0, 10)
      } catch (error) {
        console.error('Error loading arcane mock projects:', error)
      }
    },

    async togglePortainerMode() {
      try {
        const response = await axios.post('/api/settings/portainer-mode/toggle')
        this.forceMockMode = response.data.force_mock_mode
        alert(response.data.message)
      } catch (error) {
        console.error('Error toggling portainer mode:', error)
        alert('Error toggling mode')
        this.loadSettings()
      }
    },

    async toggleArcaneMode() {
      try {
        const response = await axios.post('/api/settings/arcane-mode/toggle')
        this.arcaneForceMockMode = response.data.force_mock_mode
        alert(response.data.message)
      } catch (error) {
        console.error('Error toggling arcane mode:', error)
        alert('Error toggling mode')
        this.loadSettings()
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

    async saveArcaneConfig() {
      try {
        await axios.post('/api/settings/arcane', {
          base_url: this.arcaneConfig.base_url,
          api_key: this.arcaneConfig.api_key,
          environment_id: this.arcaneConfig.environment_id
        })
        alert('Arcane configuration saved')
      } catch (error) {
        alert(error.response?.data?.detail || 'Arcane config is managed via env vars')
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
          message: 'Connection successful!'
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
        let errorMessage = 'Unknown error'
        if (error.response?.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail
          } else if (Array.isArray(error.response.data.detail)) {
            errorMessage = error.response.data.detail.map(e => e.msg || JSON.stringify(e)).join(', ')
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

    async importGitHubRepositories() {
      const seen = new Set()
      const repositories = []
      for (const line of this.githubImportInput.split('\n')) {
        const url = line.trim()
        if (!url || url.startsWith('#') || seen.has(url)) continue
        seen.add(url)
        repositories.push(url)
      }

      if (!repositories.length) {
        this.githubImportStatus = {
          success: false,
          message: 'Please add at least one GitHub repository URL.'
        }
        return
      }

      this.importingGithub = true
      this.githubImportStatus = null

      try {
        const response = await axios.post('/api/imports/github', { repositories })
        this.githubImportResults = response.data.results || []
        this.githubImportStatus = {
          success: response.data.imported > 0,
          message: `Imported ${response.data.imported} repositories, skipped ${response.data.skipped}.`
        }
        this.githubImportInput = ''
        await this.loadSettings()
      } catch (error) {
        console.error('Error importing GitHub repositories:', error)
        this.githubImportStatus = {
          success: false,
          message: error.response?.data?.detail || 'Failed to import GitHub repositories'
        }
      } finally {
        this.importingGithub = false
      }
    },

    async resetGitHubImports() {
      if (!confirm('This will replace ALL imported GitHub apps with the bundled default set. Current imports will be removed. Continue?')) return

      this.resettingGithub = true
      this.githubResetStatus = null

      try {
        const response = await axios.post('/api/imports/github/reset')
        this.githubResetStatus = {
          success: response.data.restored > 0,
          message: response.data.message
        }
        await this.loadSettings()
      } catch (error) {
        console.error('Error resetting GitHub imports:', error)
        this.githubResetStatus = {
          success: false,
          message: error.response?.data?.detail || 'Failed to reset GitHub imports'
        }
      } finally {
        this.resettingGithub = false
      }
    },

    async toggleRepository(repoId, enabled) {
      try {
        const response = await axios.put(`/api/repositories/${repoId}`, { enabled: enabled })
        const idx = this.repositories.findIndex(r => r.id === repoId)
        if (idx >= 0) {
          this.repositories[idx] = response.data
        }
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

    async resetPortainerMock() {
      if (!confirm('Clear all mock Portainer stacks? This cannot be undone.')) return
      try {
        await axios.post('/api/mock/reset')
        this.portainerMockStacks = []
      } catch (error) {
        console.error('Error resetting mock:', error)
      }
    },

    async resetArcaneMock() {
      if (!confirm('Clear all mock Arcane projects? This cannot be undone.')) return
      try {
        await axios.post('/api/mock/arcane/reset')
        this.arcaneMockProjects = []
      } catch (error) {
        console.error('Error resetting arcane mock:', error)
      }
    },

    async clearCacheAndResync() {
      if (!confirm('This will delete all cached repositories and reload them from Git. Continue?')) return
      this.clearingCache = true
      try {
        const response = await axios.post('/api/settings/cache/clear')
        if (response.data.success) {
          alert('Cache cleared and repositories resynced successfully!')
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
    },

    loadDisplaySettings() {
      const saved = localStorage.getItem('appDisplaySettings')
      if (saved) {
        try {
          this.displaySettings = JSON.parse(saved)
        } catch (e) {
          console.error('Error parsing display settings:', e)
        }
      }
    },

    saveDisplaySettings() {
      try {
        localStorage.setItem('appDisplaySettings', JSON.stringify(this.displaySettings))
        this.displaySaveStatus = {
          success: true,
          message: 'Display settings saved successfully!'
        }
        setTimeout(() => { this.displaySaveStatus = null }, 3000)
      } catch (error) {
        this.displaySaveStatus = {
          success: false,
          message: 'Error saving display settings'
        }
      }
    }
  }
}
</script>

<style scoped>
.settings-page {
  display: grid;
  gap: 1.5rem;
}

.page-head h1 {
  font-size: clamp(1.7rem, 4vw, 2.4rem);
  font-weight: 750;
  margin-bottom: 0.35rem;
}

.page-head .text-muted {
  font-size: 0.95rem;
}

.settings-container {
  display: grid;
  gap: 1.25rem;
}

.settings-section {
  padding: 1.6rem;
}

.settings-section h2 {
  font-size: 1.2rem;
  margin-bottom: 0.35rem;
}

.settings-section > .text-muted {
  margin-bottom: 1.4rem;
}

.section-subtitle {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  color: var(--color-text-primary);
}

.sub-section {
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--color-border-light);
  display: grid;
  gap: 0.5rem;
}

/* Backend selector */
.backend-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.backend-option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--color-glass);
}

.backend-option:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.backend-option.active {
  border-color: var(--color-primary);
  background: linear-gradient(135deg, rgba(109, 124, 255, 0.14), rgba(34, 211, 238, 0.08));
  box-shadow: var(--glow-primary);
}

.backend-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.backend-indicator.real {
  background: var(--color-success);
  box-shadow: 0 0 12px var(--color-success);
}

.backend-indicator.mock {
  background: var(--color-warning);
  box-shadow: 0 0 12px var(--color-warning);
}

.backend-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.backend-info strong {
  font-size: 1.05rem;
  color: var(--color-text-primary);
}

.backend-status {
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}

.status-connected,
.status-disconnected {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 600;
}

.status-connected { color: var(--color-success); }
.status-disconnected { color: var(--color-text-muted); }

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.active-badge {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.18rem 0.6rem;
  border-radius: var(--radius-pill);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #fff;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: pulse 1.6s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}

/* Config tabs */
.config-tabs {
  display: inline-flex;
  padding: 0.25rem;
  gap: 0.2rem;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.config-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.1rem;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.config-tab:hover {
  color: var(--color-text-primary);
}

.config-tab.active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #fff;
  box-shadow: var(--glow-primary);
}

.config-tab-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.config-tab-dot.portainer {
  background: var(--color-accent);
  box-shadow: 0 0 8px var(--color-accent);
}

.config-tab-dot.arcane {
  background: var(--color-primary-light);
  box-shadow: 0 0 8px var(--color-primary-light);
}

.config-tab-badge {
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.12rem 0.5rem;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.2);
}

.config-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.config-head h2 {
  margin: 0;
}

.config-head .mode-indicator {
  margin-bottom: 0;
}

.config-panel {
  display: grid;
  gap: 1.25rem;
}

/* Tab transition */
.tab-enter-active,
.tab-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.tab-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.tab-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Mode indicator */
.mode-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 1rem;
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 1.1rem;
  border: 1px solid;
}

.mode-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.mode-indicator.mock {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
  color: var(--color-warning);
}

.mode-indicator.real {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.3);
  color: var(--color-success);
}

.mode-toggle-section {
  display: grid;
  gap: 0.4rem;
  background: var(--color-bg-tertiary);
  padding: 1rem 1.1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  margin-bottom: 1.25rem;
}

.toggle-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-text-primary);
}

.toggle-switch {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.toggle-input {
  appearance: none;
  width: 50px;
  height: 28px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-strong);
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.3s ease;
  position: relative;
  flex-shrink: 0;
}

.toggle-input:checked {
  background: var(--color-warning);
}

.toggle-input::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  top: 2px;
  left: 2px;
  transition: left 0.3s ease;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.toggle-input:checked::before {
  left: 24px;
}

.toggle-label-switch {
  display: none;
}

.toggle-text {
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: 0.88rem;
}

/* Forms */
.portainer-form,
.arcane-form,
.add-repo-form,
.display-form {
  display: grid;
  gap: 1.1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  font-size: 0.88rem;
  margin-bottom: 0.4rem;
  color: var(--color-text-primary);
}

.form-group .hint {
  margin-top: 0.35rem;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.button-group {
  display: flex;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.mock-notice {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--radius-md);
  padding: 0.85rem 1rem;
  color: var(--color-warning);
  margin-top: 1.25rem;
  font-size: 0.9rem;
  font-weight: 500;
}

.no-stacks {
  background: var(--color-glass);
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border-strong);
}

/* Tables */
.stacks-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-glass);
}

.stacks-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  background: var(--color-bg-tertiary);
  padding: 0.85rem 1rem;
  font-weight: 700;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.stack-item {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--color-border-light);
  align-items: center;
  transition: background var(--transition-fast);
}

.stack-item:last-child { border-bottom: none; }
.stack-item:hover { background: var(--color-bg-tertiary); }

.col-name { font-weight: 600; color: var(--color-text-primary); }
.col-status,
.col-endpoint,
.col-id,
.col-created { color: var(--color-text-secondary); font-size: 0.9rem; }

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.7rem;
  border-radius: var(--radius-pill);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-badge.running {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.status-badge.pending,
.status-badge.error {
  background: rgba(239, 68, 68, 0.14);
  color: var(--color-error);
}

.btn-clear-all {
  width: 100%;
  border-radius: 0;
  border-top: 1px solid var(--color-border);
}

/* Repos */
.repos-list {
  display: grid;
  gap: 1rem;
}

.repo-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.25rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-glass);
  transition: border-color var(--transition-base);
}

.repo-item:hover {
  border-color: var(--color-border-strong);
}

.repo-info {
  display: grid;
  gap: 0.55rem;
  min-width: 0;
}

.repo-name {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.syncing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--color-warning);
  font-weight: 600;
}

.syncing-indicator svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.repo-url {
  color: var(--color-text-secondary);
  font-size: 0.88rem;
  word-break: break-all;
}

.repo-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.repo-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* GitHub import results */
.github-import-results {
  display: grid;
  gap: 0.6rem;
  margin-top: 1rem;
}

.github-import-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-glass);
}

.github-import-item strong {
  color: var(--color-text-primary);
}

/* Cache */
.cache-info {
  background: var(--color-glass);
  padding: 1rem 1.25rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.info-item label {
  font-weight: 700;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-item span {
  color: var(--color-text-primary);
  font-size: 0.92rem;
}

.info-item .mono {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  word-break: break-all;
}

.cache-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.cache-actions .hint {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

/* ---------- Responsive ---------- */
@media (max-width: 768px) {
  .backend-selector,
  .form-row {
    grid-template-columns: 1fr;
  }

  .repo-item {
    grid-template-columns: 1fr;
  }

  .stacks-header {
    display: none;
  }

  .stack-item {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }

  .col-name::before { content: 'Stack: '; font-weight: 700; color: var(--color-text-primary); }
  .col-status::before { content: 'Status: '; font-weight: 700; color: var(--color-text-primary); }
  .col-endpoint::before { content: 'Endpoint: '; font-weight: 700; color: var(--color-text-primary); }
  .col-created::before { content: 'Created: '; font-weight: 700; color: var(--color-text-primary); }
}
</style>