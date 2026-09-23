<template>
  <div class="new-page">
    <header class="page-head reveal">
      <div>
        <span class="hero-eyebrow badge badge-primary">Fresh in the catalog</span>
        <h1>New apps</h1>
        <p v-if="previousVersion" class="text-muted">
          Added since <strong>v{{ previousVersion }}</strong>
          <span v-if="currentVersion"> — you're on <strong>v{{ currentVersion }}</strong></span>
          · {{ total }} app{{ total === 1 ? '' : 's' }}
        </p>
        <p v-else class="text-muted">Recently added GitHub imports.</p>
      </div>
      <router-link to="/" class="btn btn-ghost">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5M11 18l-6-6 6-6" />
        </svg>
        Back to Browse
      </router-link>
    </header>

    <!-- Loading skeletons -->
    <div v-if="loading" class="apps-grid" aria-label="Loading new apps">
      <div v-for="n in 6" :key="n" class="app-card skeleton-card">
        <div class="skeleton skeleton-icon"></div>
        <div class="skeleton skeleton-line w-80"></div>
        <div class="skeleton skeleton-line w-50"></div>
        <div class="skeleton skeleton-line w-90"></div>
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="apps.length === 0" class="empty-state reveal">
      <div class="empty-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
          <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
      </div>
      <h3>Nothing new here</h3>
      <p class="text-muted">
        No apps were added since the previous version.
        Import a repository from Settings → Imports to see it show up here.
      </p>
    </div>

    <!-- Grid -->
    <div v-else class="apps-grid">
      <AppCard
        v-for="(app, idx) in apps"
        :key="app.app_id"
        :app="app"
        :style="{ animationDelay: `${Math.min(idx * 45, 450)}ms` }"
        :is-new="true"
        :is-favorite="favoriteIds.has(app.app_id)"
        @toggle-favorite="toggleFavorite"
      />
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import AppCard from '../components/AppCard.vue'

export default {
  name: 'NewApps',
  components: { AppCard },
  data() {
    return {
      apps: [],
      total: 0,
      currentVersion: null,
      previousVersion: null,
      favoriteIds: new Set(),
      loading: true
    }
  },
  mounted() {
    this.loadFavorites()
    this.loadNewApps()
  },
  methods: {
    async loadFavorites() {
      try {
        const response = await axios.get('/api/favorites/ids')
        this.favoriteIds = new Set(response.data.ids)
      } catch (error) {
        console.error('Error loading favorites:', error)
      }
    },
    async loadNewApps() {
      this.loading = true
      try {
        const response = await axios.get('/api/imports/github/new')
        this.apps = response.data.apps || []
        this.total = response.data.total || 0
        this.currentVersion = response.data.current_version
        this.previousVersion = response.data.previous_version
      } catch (error) {
        console.error('Error loading new apps:', error)
        this.apps = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    async toggleFavorite(appId) {
      try {
        if (this.favoriteIds.has(appId)) {
          await axios.delete(`/api/favorites/${appId}`)
          this.favoriteIds.delete(appId)
        } else {
          await axios.post(`/api/favorites/${appId}`)
          this.favoriteIds.add(appId)
        }
        this.favoriteIds = new Set(this.favoriteIds)
      } catch (error) {
        console.error('Error toggling favorite:', error)
      }
    }
  }
}
</script>

<style scoped>
.new-page {
  display: grid;
  gap: 1.75rem;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem 0 0.5rem;
}

.page-head h1 {
  font-family: var(--font-display);
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  font-weight: 750;
  letter-spacing: -0.02em;
  margin: 0.6rem 0 0.4rem;
}

.hero-eyebrow {
  margin-bottom: 0.4rem;
}

.apps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(235px, 1fr));
  gap: 1.25rem;
}

/* ---------- Skeleton ---------- */
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 1.15rem;
  background: var(--color-glass);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.skeleton-icon {
  width: 76px;
  height: 76px;
  border-radius: 18px;
}

.skeleton-line {
  height: 13px;
}

.skeleton-line.w-80 { width: 80%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-90 { width: 90%; }

/* ---------- Empty ---------- */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: var(--color-glass);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1rem;
  display: grid;
  place-items: center;
  border-radius: 18px;
  color: var(--color-text-muted);
  background: var(--color-bg-tertiary);
}

.empty-state h3 {
  font-size: 1.35rem;
  margin-bottom: 0.35rem;
}

.empty-state p {
  font-size: 0.95rem;
}

@media (max-width: 560px) {
  .apps-grid {
    grid-template-columns: 1fr;
  }

  .page-head {
    flex-direction: column;
  }
}
</style>
