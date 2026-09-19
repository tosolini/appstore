<template>
  <div class="imports-page">
    <div class="page-header">
      <div>
        <h1>GitHub Imports</h1>
        <p class="text-muted">Manage imported GitHub apps, export the source list, and inspect import strategy details.</p>
      </div>
      <router-link to="/settings" class="btn-secondary">← Back to Settings</router-link>
    </div>

    <div class="toolbar">
      <button type="button" class="btn-test" @click="exportGitHubImports('json')">Export JSON</button>
      <button type="button" class="btn-test" @click="exportGitHubImports('urls')">Export URL List</button>
      <button type="button" class="btn-secondary" @click="loadImports" :disabled="loading">
        {{ loading ? 'Refreshing...' : 'Refresh' }}
      </button>
    </div>

    <div class="import-section">
      <h2>Import list</h2>
      <p class="text-muted">Paste repository URLs (one per line) or upload a previously exported list (<code>github-imports.json</code> / <code>github-imports.txt</code>).</p>

      <div class="import-controls">
        <textarea
          v-model="importInput"
          rows="5"
          placeholder="https://github.com/example/project&#10;https://github.com/example/another-project"
        ></textarea>
        <div class="import-actions">
          <label class="btn-secondary file-label">
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
            class="btn-test"
            :disabled="importing || !parsedImportUrls.length"
            @click="importRepositories"
          >
            {{ importButtonLabel }}
          </button>
        </div>
        <small v-if="importFileError" class="error-text">{{ importFileError }}</small>
      </div>

      <div v-if="importStatus" :class="['status', importStatus.success ? 'success' : 'error']">
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
            <span :class="['status-pill', result.status]">{{ result.status }}</span>
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
          <button type="button" class="btn-secondary" @click="closeErrorModal">Close</button>
        </div>
      </div>
    </div>

    <div class="import-debug-legend">
      <span class="import-debug-legend-label">Import debug:</span>
      <span class="import-debug-badge github-api">GitHub API</span>
      <span class="import-debug-badge git-fallback">git fallback</span>
      <span class="import-debug-badge dockerfile-fallback">Dockerfile fallback</span>
    </div>

    <div v-if="loading" class="empty-state">Loading imports...</div>
    <div v-else-if="githubImports.length === 0" class="empty-state">No GitHub imports yet.</div>

    <div v-else class="repos-list">
      <div v-for="importedApp in githubImports" :key="importedApp.id" class="repo-item">
        <div class="repo-info">
          <div class="repo-name">{{ importedApp.title }}</div>
          <div class="repo-url">{{ importedApp.source_url }}</div>
          <div class="repo-meta">
            <span>{{ importedApp.repo_full_name }}</span>
            <span
              v-if="importedApp.import_debug"
              :class="['import-debug-badge', importDebugClass(importedApp.import_debug)]">
              {{ formatImportDebug(importedApp.import_debug) }}
            </span>
            <span v-if="importedApp.compatibility_status === 'warning'" class="warning-text">
              No {{ importedApp.host_architecture }} image
            </span>
            <span v-if="importedApp.last_imported_at">Last import: {{ formatDate(importedApp.last_imported_at) }}</span>
          </div>
        </div>
        <div class="repo-actions">
          <button
            @click="resyncGitHubImport(importedApp.id)"
            class="btn-sync"
            :disabled="githubImportBusy[importedApp.id]">
            {{ githubImportBusy[importedApp.id] ? 'Syncing...' : 'Resync' }}
          </button>
          <button
            @click="deleteGitHubImport(importedApp.id)"
            class="btn-delete"
            :disabled="githubImportBusy[importedApp.id]">
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'GitHubImports',
  data() {
    return {
      githubImports: [],
      githubImportBusy: {},
      loading: true,
      importInput: '',
      importFileName: '',
      importFileError: '',
      importing: false,
      importStatus: null,
      importResults: [],
      errorModal: null
    }
  },
  computed: {
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
      const noun = this.parsedImportUrls.length === 1 ? 'repository' : 'repositories'
      return `Import ${this.parsedImportUrls.length} ${noun}`
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
    normalizeRepoUrl(url) {
      let candidate = url.trim()
      if (!/^https?:\/\//i.test(candidate)) candidate = `https://${candidate}`
      try {
        const parsed = new URL(candidate)
        const host = parsed.hostname.toLowerCase()
        if (host === 'github.com' || host === 'www.github.com') {
          let path = parsed.pathname
            .replace(/\.git\/?$/i, '')
            .replace(/^\/+|\/+$/g, '')
          const parts = path.split('/').filter(Boolean).slice(0, 2)
          if (parts.length === 2) {
            return `https://github.com/${parts[0].toLowerCase()}/${parts[1].toLowerCase()}`
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
        const response = await axios.get('/api/imports/github')
        this.githubImports = response.data.imports || []
      } catch (error) {
        console.error('Error loading GitHub imports:', error)
        this.githubImports = []
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

        // Try exported JSON first: { repositories: [...] }
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

        // Plain-text URL list (exported .txt): one URL per line, ignore blanks/comments
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
        // Allow re-selecting the same file
        if (this.$refs.importFile) this.$refs.importFile.value = ''
      }
    },
    async importRepositories() {
      if (!this.parsedImportUrls.length || this.importing) return

      this.importing = true
      this.importStatus = null
      try {
        const response = await axios.post('/api/imports/github', {
          repositories: this.parsedImportUrls
        })
        this.importResults = response.data.results || []
        this.importStatus = {
          success: response.data.imported > 0,
          message: `Imported ${response.data.imported} repositories, skipped ${response.data.skipped}.`
        }
        this.importInput = ''
        this.importFileName = ''
        await this.loadImports()
      } catch (error) {
        console.error('Error importing GitHub repositories:', error)
        this.importStatus = {
          success: false,
          message: error.response?.data?.detail || 'Failed to import GitHub repositories'
        }
      } finally {
        this.importing = false
      }
    },
    async exportGitHubImports(format) {
      try {
        const response = await axios.get(`/api/imports/github/export?format=${format}`, {
          responseType: 'blob'
        })
        const blob = new Blob([response.data], {
          type: format === 'json' ? 'application/json' : 'text/plain'
        })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = format === 'json' ? 'github-imports.json' : 'github-imports.txt'
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
      } catch (error) {
        console.error('Error exporting GitHub imports:', error)
        alert('Failed to export imported GitHub repositories')
      }
    },
    async resyncGitHubImport(importId) {
      this.githubImportBusy[importId] = true
      try {
        await axios.post(`/api/imports/github/${importId}/resync`)
        await this.loadImports()
      } catch (error) {
        console.error('Error resyncing GitHub import:', error)
        alert(error.response?.data?.detail || 'Failed to resync GitHub import')
      } finally {
        this.githubImportBusy[importId] = false
      }
    },
    async deleteGitHubImport(importId) {
      if (!confirm('Delete this imported GitHub app?')) {
        return
      }

      this.githubImportBusy[importId] = true
      try {
        await axios.delete(`/api/imports/github/${importId}`)
        this.githubImports = this.githubImports.filter(app => app.id !== importId)
      } catch (error) {
        console.error('Error deleting GitHub import:', error)
        alert(error.response?.data?.detail || 'Failed to delete GitHub import')
      } finally {
        this.githubImportBusy[importId] = false
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
      if (importDebug.import_strategy === 'dockerfile-fallback') {
        return 'Imported via Dockerfile fallback'
      }
      if (importDebug.import_strategy === 'git-fallback') {
        return 'Imported via git fallback'
      }
      return 'Imported via GitHub API'
    },
    importDebugClass(importDebug) {
      if (!importDebug) return ''
      if (importDebug.import_strategy === 'dockerfile-fallback') return 'dockerfile-fallback'
      if (importDebug.import_strategy === 'git-fallback') return 'git-fallback'
      return 'github-api'
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
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.page-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.text-muted {
  color: var(--color-text-secondary);
}

.toolbar {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-test,
.btn-secondary,
.btn-sync,
.btn-delete {
  padding: 0.75rem 1.25rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
}

.btn-test {
  background: var(--color-info);
  color: white;
}

.btn-secondary {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-sync {
  background: var(--color-warning);
  color: #333;
}

.btn-delete {
  background: var(--color-error);
  color: white;
}

.btn-test:hover,
.btn-secondary:hover,
.btn-sync:hover,
.btn-delete:hover {
  opacity: 0.92;
}

.btn-sync:disabled,
.btn-delete:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.import-debug-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.import-debug-legend-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.import-debug-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid transparent;
}

.import-debug-badge.github-api {
  background: rgba(34, 197, 94, 0.14);
  border-color: rgba(34, 197, 94, 0.28);
  color: #15803d;
}

.import-debug-badge.git-fallback {
  background: rgba(245, 158, 11, 0.14);
  border-color: rgba(245, 158, 11, 0.28);
  color: #b45309;
}

.import-debug-badge.dockerfile-fallback {
  background: rgba(59, 130, 246, 0.14);
  border-color: rgba(59, 130, 246, 0.28);
  color: #1d4ed8;
}

.warning-text {
  color: #b45309;
  font-weight: 600;
}

.empty-state {
  background: var(--color-bg-secondary);
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  color: var(--color-text-secondary);
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
  border-radius: 8px;
  background: var(--color-bg-secondary);
}

.repo-info {
  display: grid;
  gap: 0.5rem;
}

.repo-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--color-text-primary);
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
  grid-template-columns: auto auto;
  gap: 0.5rem;
}

.import-section {
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-secondary);
}

.import-section h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-text-primary);
}

.import-controls {
  display: grid;
  gap: 0.75rem;
}

.import-controls textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  resize: vertical;
}

.import-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.file-label {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.file-input {
  display: none;
}

.file-name {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.status {
  padding: 0.75rem 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.status.success {
  background: rgba(34, 197, 94, 0.14);
  color: #15803d;
}

.status.error {
  background: rgba(239, 68, 68, 0.14);
  color: #b91c1c;
}

.error-text {
  color: #b91c1c;
  font-size: 0.9rem;
}

.import-results {
  display: grid;
  gap: 0.75rem;
}

.import-result-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-tertiary);
}

.import-result-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-shrink: 0;
}

.btn-link {
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-info);
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: underline;
}

.btn-link:hover {
  opacity: 0.8;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.55);
}

.modal {
  width: 100%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
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
  font-size: 1.1rem;
  color: var(--color-text-primary);
}

.modal-close {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-text-secondary);
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
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  word-break: break-all;
}

.modal-message {
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-tertiary);
  font-family: monospace;
  font-size: 0.9rem;
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

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-pill.imported {
  background: rgba(34, 197, 94, 0.14);
  color: #15803d;
}

.status-pill.skipped {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

@media (max-width: 768px) {
  .page-header,
  .repo-item {
    grid-template-columns: 1fr;
    display: grid;
  }

  .repo-actions {
    grid-template-columns: 1fr;
  }
}
</style>
