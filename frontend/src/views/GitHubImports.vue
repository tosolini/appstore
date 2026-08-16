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
      loading: true
    }
  },
  mounted() {
    this.loadImports()
  },
  methods: {
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
