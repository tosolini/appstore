<template>
  <div class="imports-page">
    <header class="page-head reveal">
      <div>
        <h1>Docker Hub Imports</h1>
        <p class="text-muted">Manage imported Docker Hub apps and inspect import strategy details. Full backups (both sources) are handled on the <router-link to="/imports/github">GitHub Imports</router-link> tab.</p>
      </div>
    </header>

    <div class="toolbar reveal" :style="{ animationDelay: '50ms' }">
      <button type="button" class="btn btn-ghost btn-sm" @click="loadImports" :disabled="loading">
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <div class="import-section reveal" :style="{ animationDelay: '80ms' }">
      <h2>Import list</h2>
      <p class="text-muted">Paste Docker Hub repository URLs (one per line), e.g. <code>https://hub.docker.com/r/msdeluise/plant-it-server</code>. Official images (<code>https://hub.docker.com/_/nginx</code>) are supported too.</p>

      <div class="import-controls">
        <textarea
          v-model="importInput"
          rows="5"
          placeholder="https://hub.docker.com/r/msdeluise/plant-it-server&#10;https://hub.docker.com/_/nginx"
          class="input mono"
        ></textarea>
        <div class="import-actions">
          <label class="btn btn-ghost btn-sm file-label">
            Choose file…
            <input
              ref="importFile"
              type="file"
              accept=".json,.txt,text/plain,application/json"
              class="file-input"
              @change="handleImportFile"
            />
          </label>
          <span v-if="importFileName" class="file-name">{{ importFileName }}</span>
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="importing || !parsedImportUrls.length"
            @click="importRepositories"
          >
            {{ importButtonLabel }}
          </button>
        </div>
        <small v-if="importFileError" class="error-text">{{ importFileError }}</small>
      </div>

      <div v-if="importStatus" class="status-banner" :class="importStatus.success ? 'success' : 'error'">
        {{ importStatus.message }}
      </div>

      <div v-if="importResults.length" class="import-results">
        <div
          v-for="result in importResults"
          :key="`${result.repository}-${result.app_id || result.status}`"
          class="import-result-item"
        >
          <div>
            <strong>{{ result.title || result.repository }}</strong>
            <div class="repo-url">{{ result.repository }}</div>
            <div v-if="result.message" class="repo-meta">{{ result.message }}</div>
          </div>
          <div class="import-result-actions">
            <button
              v-if="result.status === 'skipped'"
              type="button"
              class="btn-link"
              @click="showErrorModal(result)"
            >
              View details
            </button>
            <span :class="['badge', result.status === 'imported' ? 'badge-success' : 'badge-warning']">{{ result.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="errorModal" class="modal-overlay" @click.self="closeErrorModal">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="import-error-title">
        <div class="modal-header">
          <h3 id="import-error-title">Import failed</h3>
          <button type="button" class="modal-close" aria-label="Close" @click="closeErrorModal">×</button>
        </div>
        <div class="modal-body">
          <div class="modal-repo">{{ errorModal.repository }}</div>
          <div class="modal-message">{{ errorModal.message }}</div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-ghost btn-sm" @click="closeErrorModal">Close</button>
        </div>
      </div>
    </div>

    <div class="import-debug-legend reveal">
      <span class="import-debug-legend-label">Import debug:</span>
      <span class="badge badge-success">Docker Hub (description)</span>
      <span class="badge badge-info">Docker Hub</span>
    </div>

    <div v-if="dockerhubImports.length" class="list-toolbar reveal">
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          v-model="searchQuery"
          type="search"
          class="search-input"
          placeholder="Search by name, repo or URL…"
        />
      </div>
      <span class="list-count">{{ filteredImports.length }} of {{ dockerhubImports.length }}</span>
    </div>

    <div v-if="loading" class="empty-state">Loading imports…</div>
    <div v-else-if="dockerhubImports.length === 0" class="empty-state">No Docker Hub imports yet.</div>
    <div v-else-if="filteredImports.length === 0" class="empty-state">No imports match your search.</div>

    <div v-else class="repos-list">
      <div v-for="importedApp in paginatedImports" :key="importedApp.id" class="repo-item reveal">
        <div class="repo-info">
          <div class="repo-name">{{ importedApp.title }}</div>
          <div class="repo-url mono">{{ importedApp.source_url }}</div>
          <div class="repo-meta">
            <span class="badge">{{ importedApp.repo_full_name }}</span>
            <span
              v-if="importedApp.import_debug"
              :class="['badge', importDebugClass(importedApp.import_debug)]">
              {{ formatImportDebug(importedApp.import_debug) }}
            </span>
            <span v-if="importedApp.compatibility_status === 'warning'" class="warning-text">
              No {{ importedApp.host_architecture }} image
            </span>
            <span v-if="importedApp.last_imported_at" class="badge">last import: {{ formatDate(importedApp.last_imported_at) }}</span>
          </div>
        </div>
        <div class="repo-actions">
          <button
            @click="resyncDockerHubImport(importedApp.id)"
            class="btn btn-accent btn-sm"
            :disabled="dockerhubImportBusy[importedApp.id]">
            {{ dockerhubImportBusy[importedApp.id] ? 'Syncing…' : 'Resync' }}
          </button>
          <button
            @click="deleteDockerHubImport(importedApp.id)"
            class="btn btn-soft-danger btn-sm"
            :disabled="dockerhubImportBusy[importedApp.id]">
            Delete
          </button>
        </div>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button
          type="button"
          class="page-btn"
          :disabled="currentPage === 1"
          @click="changePage(currentPage - 1)"
        >← Prev</button>
        <template v-for="(page, index) in visiblePages" :key="`${page}-${index}`">
          <span v-if="page === '…'" class="page-ellipsis">…</span>
          <button
            v-else
            type="button"
            :class="['page-btn', { active: page === currentPage }]"
            @click="changePage(page)"
          >{{ page }}</button>
        </template>
        <button
          type="button"
          class="page-btn"
          :disabled="currentPage === totalPages"
          @click="changePage(currentPage + 1)"
        >Next →</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DockerHubImports',
  data() {
    return {
      dockerhubImports: [],
      dockerhubImportBusy: {},
      loading: true,
      importInput: '',
      importFileName: '',
      importFileError: '',
      importing: false,
      importStatus: null,
      importResults: [],
      errorModal: null,
      searchQuery: '',
      currentPage: 1,
      pageSize: 20
    }
  },
  computed: {
    filteredImports() {
      const q = this.searchQuery.trim().toLowerCase()
      if (!q) return this.dockerhubImports
      return this.dockerhubImports.filter(app => {
        const haystack = [app.title, app.repo_full_name, app.source_url, app.app_id, app.description]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        return haystack.includes(q)
      })
    },
    paginatedImports() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.filteredImports.slice(start, start + this.pageSize)
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredImports.length / this.pageSize))
    },
    visiblePages() {
      const total = this.totalPages
      const current = this.currentPage
      const pages = new Set([1, total, current - 1, current, current + 1])
      const sorted = [...pages].filter(p => p >= 1 && p <= total).sort((a, b) => a - b)
      const result = []
      let prev = 0
      for (const page of sorted) {
        if (page - prev > 1) result.push('…')
        result.push(page)
        prev = page
      }
      return result
    },
    parsedImportUrls() {
      const seen = new Set()
      const urls = []
      for (const line of this.importInput.split('\n')) {
        const url = line.trim()
        if (!url || url.startsWith('#')) continue
        const normalized = this.normalizeRepoUrl(url)
        if (seen.has(normalized)) continue
        seen.add(normalized)
        urls.push(url)
      }
      return urls
    },
    importButtonLabel() {
      if (this.importing) return `Importing ${this.parsedImportUrls.length}…`
      if (!this.parsedImportUrls.length) return 'Import'
      const noun = this.parsedImportUrls.length === 1 ? 'image' : 'images'
      return `Import ${this.parsedImportUrls.length} ${noun}`
    }
  },
  watch: {
    searchQuery() {
      this.currentPage = 1
    },
    dockerhubImports() {
      const maxPage = Math.max(1, Math.ceil(this.dockerhubImports.length / this.pageSize))
      if (this.currentPage > maxPage) this.currentPage = maxPage
    }
  },
  mounted() {
    this.loadImports()
    window.addEventListener('keydown', this.handleModalKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleModalKeydown)
  },
  methods: {
    changePage(page) {
      if (page < 1 || page > this.totalPages || page === this.currentPage) return
      this.currentPage = page
    },
    normalizeRepoUrl(url) {
      let candidate = url.trim()
      if (!/^https?:\/\//i.test(candidate)) candidate = `https://${candidate}`
      try {
        const parsed = new URL(candidate)
        const host = parsed.hostname.toLowerCase()
        if (host === 'hub.docker.com' || host === 'www.hub.docker.com') {
          const parts = parsed.pathname.replace(/^\/+|\/+$/g, '').split('/').filter(Boolean)
          if (parts[0] === 'r' && parts.length >= 3) {
            return `https://hub.docker.com/r/${parts[1].toLowerCase()}/${parts[2].toLowerCase()}`
          }
          if (parts[0] === '_' && parts.length >= 2) {
            return `https://hub.docker.com/r/library/${parts[1].toLowerCase()}`
          }
        }
      } catch (e) {
        // fall through to the conservative normalization below
      }
      return candidate.replace(/\/+$/, '')
    },
    async loadImports() {
      this.loading = true
      try {
        const response = await axios.get('/api/imports/dockerhub')
        this.dockerhubImports = response.data.imports || []
      } catch (error) {
        console.error('Error loading Docker Hub imports:', error)
        this.dockerhubImports = []
      } finally {
        this.loading = false
      }
    },
    async handleImportFile(event) {
      const file = event.target.files && event.target.files[0]
      this.importFileError = ''
      if (!file) return

      this.importFileName = file.name
      try {
        const text = await file.text()
        const trimmed = text.trim()
        if (!trimmed) {
          this.importFileError = 'Selected file is empty.'
          return
        }

        if (file.name.endsWith('.json') || trimmed.startsWith('{')) {
          try {
            const parsed = JSON.parse(trimmed)
            const repos = Array.isArray(parsed)
              ? parsed
              : parsed.repositories || parsed.urls || []
            if (!Array.isArray(repos) || !repos.length) {
              this.importFileError = 'JSON file contains no repositories list.'
              return
            }
            this.importInput = repos.map(url => String(url).trim()).filter(Boolean).join('\n')
            return
          } catch (e) {
            // Fall through to plain-text parsing below
          }
        }

        const urls = trimmed
          .split('\n')
          .map(line => line.trim())
          .filter(line => line && !line.startsWith('#'))
        if (!urls.length) {
          this.importFileError = 'No repository URLs found in file.'
          return
        }
        this.importInput = urls.join('\n')
      } catch (error) {
        console.error('Error reading import file:', error)
        this.importFileError = 'Failed to read selected file.'
      } finally {
        if (this.$refs.importFile) this.$refs.importFile.value = ''
      }
    },
    async importRepositories() {
      if (!this.parsedImportUrls.length || this.importing) return

      this.importing = true
      this.importStatus = null
      try {
        const response = await axios.post('/api/imports/dockerhub', {
          repositories: this.parsedImportUrls
        })
        this.importResults = response.data.results || []
        this.importStatus = {
          success: response.data.imported > 0,
          message: `Imported ${response.data.imported} images, skipped ${response.data.skipped}.`
        }
        this.importInput = ''
        this.importFileName = ''
        await this.loadImports()
      } catch (error) {
        console.error('Error importing Docker Hub repositories:', error)
        this.importStatus = {
          success: false,
          message: error.response?.data?.detail || 'Failed to import Docker Hub repositories'
        }
      } finally {
        this.importing = false
      }
    },
    async resyncDockerHubImport(importId) {
      this.dockerhubImportBusy[importId] = true
      try {
        await axios.post(`/api/imports/dockerhub/${importId}/resync`)
        await this.loadImports()
      } catch (error) {
        console.error('Error resyncing Docker Hub import:', error)
        alert(error.response?.data?.detail || 'Failed to resync Docker Hub import')
      } finally {
        this.dockerhubImportBusy[importId] = false
      }
    },
    async deleteDockerHubImport(importId) {
      if (!confirm('Delete this imported Docker Hub app?')) {
        return
      }

      this.dockerhubImportBusy[importId] = true
      try {
        await axios.delete(`/api/imports/dockerhub/${importId}`)
        this.dockerhubImports = this.dockerhubImports.filter(app => app.id !== importId)
      } catch (error) {
        console.error('Error deleting Docker Hub import:', error)
        alert(error.response?.data?.detail || 'Failed to delete Docker Hub import')
      } finally {
        this.dockerhubImportBusy[importId] = false
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
    formatImportDebug(importDebug) {
      if (!importDebug) return ''
      if (importDebug.import_strategy === 'dockerhub-description-compose') {
        return 'Docker Hub (description)'
      }
      if (importDebug.import_strategy === 'dockerhub-generated') {
        return 'Docker Hub'
      }
      return 'Imported via Docker Hub'
    },
    importDebugClass(importDebug) {
      if (!importDebug) return ''
      if (importDebug.import_strategy === 'dockerhub-generated') return 'badge-info'
      return 'badge-success'
    },
    showErrorModal(result) {
      this.errorModal = result
    },
    closeErrorModal() {
      this.errorModal = null
    },
    handleModalKeydown(event) {
      if (event.key === 'Escape' && this.errorModal) {
        this.closeErrorModal()
      }
    }
  }
}
</script>

<style scoped>
.imports-page {
  display: grid;
  gap: 1.25rem;
}

.page-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
}

.page-head h1 {
  font-size: clamp(1.7rem, 4vw, 2.4rem);
  font-weight: 750;
  margin-bottom: 0.35rem;
}

.text-muted {
  color: var(--color-text-secondary);
  font-size: 0.92rem;
}

.toolbar {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  align-items: center;
}

/* Import section */
.import-section {
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.import-section h2 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-text-primary);
}

.import-section code {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background: var(--color-bg-tertiary);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.import-controls {
  display: grid;
  gap: 0.75rem;
}

.import-controls textarea {
  resize: vertical;
}

.import-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}

.file-label {
  cursor: pointer;
}

.file-input {
  display: none;
}

.file-name {
  font-size: 0.88rem;
  color: var(--color-text-secondary);
}

.error-text {
  color: var(--color-error);
  font-size: 0.88rem;
  font-weight: 600;
}

.import-results {
  display: grid;
  gap: 0.6rem;
}

.import-result-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-glass);
}

.import-result-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-shrink: 0;
}

.btn-link {
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-primary);
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: underline;
}

.btn-link:hover {
  opacity: 0.8;
}

/* Legend */
.import-debug-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.import-debug-legend-label {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}

/* List */
.list-toolbar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-wrap {
  position: relative;
  flex: 1;
  min-width: 220px;
}

.search-icon {
  position: absolute;
  left: 0.9rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.65rem 1rem 0.65rem 2.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-glass);
  color: var(--color-text-primary);
  font-size: 0.92rem;
  transition: all var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(109, 124, 255, 0.18);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.list-count {
  font-size: 0.88rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
  font-weight: 600;
}

.empty-state {
  background: var(--color-glass);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  padding: 2.5rem;
  text-align: center;
  color: var(--color-text-secondary);
}

/* Repo list */
.repos-list {
  display: grid;
  gap: 0.85rem;
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
  transition: border-color var(--transition-base), transform var(--transition-base), box-shadow var(--transition-base);
}

.repo-item:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
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
  font-size: 0.88rem;
  color: var(--color-text-muted);
  align-items: center;
}

.warning-text {
  color: var(--color-warning);
  font-weight: 700;
}

.repo-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Pagination */
.pagination {
  display: flex;
  gap: 0.35rem;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  padding-top: 0.5rem;
}

.page-btn {
  min-width: 2.4rem;
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-glass);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.page-btn.active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #fff;
  border-color: transparent;
  box-shadow: var(--glow-primary);
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-ellipsis {
  color: var(--color-text-muted);
  padding: 0 0.15rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(3, 6, 14, 0.6);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  animation: fadeIn 180ms ease;
}

.modal {
  width: 100%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: popIn 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text-primary);
}

.modal-close {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1.4rem;
  line-height: 1;
  color: var(--color-text-muted);
  transition: color var(--transition-fast);
}

.modal-close:hover {
  color: var(--color-text-primary);
}

.modal-body {
  padding: 1.25rem;
  overflow-y: auto;
  display: grid;
  gap: 0.75rem;
}

.modal-repo {
  font-size: 0.92rem;
  color: var(--color-text-secondary);
  word-break: break-all;
}

.modal-message {
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-tertiary);
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .page-head,
  .repo-item {
    grid-template-columns: 1fr;
    display: grid;
  }

  .repo-actions {
    grid-template-columns: 1fr;
  }
}
</style>