<template>
  <div class="home-page">
    <!-- Hero -->
    <section class="hero reveal">
      <div class="hero-glow" aria-hidden="true"></div>
      <div class="hero-copy">
        <span class="hero-eyebrow badge badge-primary">Container AppStore Bridge</span>
        <h1 class="hero-title">Curated apps,<br />ready to deploy.</h1>
        <p class="hero-sub">
          Browse, inspect and deploy containerized applications from CasaOS-compatible
          repositories straight to your stacks.
        </p>
      </div>

      <div class="hero-controls">
        <div class="search-wrap">
          <svg class="search-icon" viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search apps, developers, keywords…"
            class="search-input"
            @input="handleSearch"
          >
          <span v-if="searchQuery" class="search-clear" @click="clearSearch">✕</span>
        </div>

        <div class="category-chips">
          <button
            :class="['chip', { active: selectedCategory === '' }]"
            @click="selectCategory('')"
          >
            All
          </button>
          <button
            v-for="cat in categories"
            :key="cat.name"
            :class="['chip', { active: selectedCategory === cat.name }]"
            @click="selectCategory(cat.name)"
          >
            {{ cat.name }}
            <span class="chip-count">{{ cat.count }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Toolbar -->
    <div class="home-toolbar reveal" :style="{ animationDelay: '60ms' }">
      <div class="view-toggle">
        <button
          :class="['seg-btn', { active: viewMode === 'all' }]"
          @click="switchView('all')"
        >
          <span class="seg-dot"></span>
          All Apps
          <span class="seg-count">{{ filteredTotal }}</span>
        </button>
        <button
          :class="['seg-btn', { active: viewMode === 'favorites' }]"
          @click="switchView('favorites')"
        >
          <span class="seg-dot"></span>
          My List
          <span class="seg-count">{{ favoriteIds.size }}</span>
        </button>
      </div>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="apps-grid" aria-label="Loading apps">
      <div v-for="n in 12" :key="n" class="app-card skeleton-card">
        <div class="skeleton skeleton-icon"></div>
        <div class="skeleton skeleton-line w-80"></div>
        <div class="skeleton skeleton-line w-50"></div>
        <div class="skeleton skeleton-line w-90"></div>
        <div class="skeleton-card-footer">
          <div class="skeleton skeleton-line w-40"></div>
          <div class="skeleton skeleton-btn"></div>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="displayApps.length === 0" class="empty-state reveal">
      <div class="empty-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
      </div>
      <h3 v-if="viewMode === 'favorites'">Nothing saved yet</h3>
      <h3 v-else>No apps found</h3>
      <p v-if="viewMode === 'favorites'" class="text-muted">
        Tap the heart on any app to add it to your personal list.
      </p>
      <p v-else class="text-muted">Try a different search term or category.</p>
    </div>

    <!-- Grid -->
    <div v-else class="apps-grid">
      <div
        v-for="(app, idx) in displayApps"
        :key="app.app_id"
        class="app-card reveal"
        :style="{ animationDelay: `${Math.min(idx * 45, 450)}ms` }"
      >
        <button
          class="fav-btn"
          :class="{ favorited: favoriteIds.has(app.app_id) }"
          @click="toggleFavorite(app.app_id)"
          :title="favoriteIds.has(app.app_id) ? 'Remove from My List' : 'Add to My List'"
          :aria-label="favoriteIds.has(app.app_id) ? 'Remove from My List' : 'Add to My List'"
        >
          <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" stroke="currentColor" stroke-width="1.6">
            <path d="M12 21s-7.5-4.7-10-9.3C.5 8.5 2 5 5.3 5c2 0 3.4 1.1 4.2 2.4.6-1.3 2-2.4 4.2-2.4C17 5 18.5 8.5 17 11.7 14.5 16.3 12 21 12 21z" />
          </svg>
        </button>

        <div class="card-icon">
          <img :src="app.icon" :alt="app.title" class="app-icon" loading="lazy" v-img-fallback>
        </div>

        <h3 class="app-title">{{ app.title }}</h3>
        <p class="app-dev">{{ app.developer }}</p>

        <p v-if="app.compatibility_status === 'warning'" class="arch-warning">
          No {{ app.host_architecture }} image
        </p>

        <p class="app-desc">{{ truncate(app.description, 100) }}</p>

        <div class="app-footer">
          <span class="badge category-badge">{{ app.category }}</span>
          <router-link :to="`/app/${app.app_id}`" class="btn btn-primary btn-sm details-btn">
            Details
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </router-link>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="viewMode === 'all' && hasMore" class="pagination reveal">
      <button @click="loadMore" class="btn btn-accent load-more-btn">
        Load more apps
      </button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Home',
  data() {
    return {
      apps: [],
      allApps: [],
      categories: [],
      searchQuery: '',
      selectedCategory: '',
      viewMode: 'all',
      favoriteIds: new Set(),
      loading: true,
      totalApps: 0,
      offset: 0,
      limit: 12,
      pageSize: 12
    }
  },
  computed: {
    filteredApps() {
      if (this.viewMode === 'favorites') {
        return this.allApps.filter(a => this.favoriteIds.has(a.app_id))
      }
      return this.allApps
    },
    displayApps() {
      if (this.viewMode === 'favorites') {
        return this.filteredApps
      }
      return this.apps
    },
    filteredTotal() {
      return this.allApps.length
    },
    hasMore() {
      return this.offset < this.allApps.length
    }
  },
  mounted() {
    this.loadDisplaySettings()
    this.loadCategories()
    this.loadFavorites()
    this.loadApps()
  },
  watch: {
    '$route'(to, from) {
      if (to.path === '/' && from.path !== '/') {
        this.loadFavorites()
        const previousLimit = this.limit
        this.loadDisplaySettings()
        if (previousLimit !== this.limit) {
          this.loadApps()
        }
      }
    }
  },
  methods: {
    loadDisplaySettings() {
      const saved = localStorage.getItem('appDisplaySettings')
      if (saved) {
        try {
          const settings = JSON.parse(saved)
          if (settings.appsPerPage) {
            this.limit = settings.appsPerPage
          }
        } catch (e) {
          console.error('Error parsing display settings:', e)
        }
      }
    },
    async loadCategories() {
      try {
        const response = await axios.get('/api/categories')
        this.categories = response.data.categories
      } catch (error) {
        console.error('Error loading categories:', error)
        this.categories = []
      }
    },
    async loadFavorites() {
      try {
        const response = await axios.get('/api/favorites/ids')
        this.favoriteIds = new Set(response.data.ids)
      } catch (error) {
        console.error('Error loading favorites:', error)
      }
    },
    async loadApps() {
      this.loading = true
      this.offset = 0
      try {
        let url = `/apps?limit=1000&offset=0&random=true`
        if (this.selectedCategory) {
          url += `&category=${this.selectedCategory}`
        }

        const response = await axios.get(url)
        this.allApps = response.data.apps
        this.totalApps = response.data.total
        this.pageSize = this.limit
        this.apps = this.allApps.slice(0, this.pageSize)
        this.offset = this.pageSize
      } catch (error) {
        console.error('Error loading apps:', error)
        this.allApps = []
        this.apps = []
      } finally {
        this.loading = false
      }
    },
    async handleSearch() {
      if (!this.searchQuery) {
        this.loadApps()
        return
      }

      this.loading = true
      try {
        const response = await axios.get(`/apps/search?q=${this.searchQuery}`)
        this.allApps = response.data.apps
        this.totalApps = response.data.results_count
        this.apps = this.allApps.slice(0, this.limit)
        this.offset = this.limit
      } catch (error) {
        console.error('Error searching apps:', error)
        this.allApps = []
        this.apps = []
      } finally {
        this.loading = false
      }
    },
    clearSearch() {
      this.searchQuery = ''
      this.loadApps()
    },
    selectCategory(cat) {
      this.selectedCategory = cat
      this.loadApps()
    },
    switchView(mode) {
      this.viewMode = mode
      if (mode === 'favorites') {
        this.loadFavorites()
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
    },
    loadMore() {
      const nextBatch = this.allApps.slice(this.offset, this.offset + this.limit)
      this.apps = [...this.apps, ...nextBatch]
      this.offset += this.limit
    },
    truncate(text, length) {
      if (!text) return ''
      if (text.length <= length) return text
      return text.substring(0, length) + '…'
    }
  }
}
</script>

<style scoped>
.home-page {
  display: grid;
  gap: 1.75rem;
}

/* ---------- Hero ---------- */
.hero {
  position: relative;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 2.5rem;
  align-items: center;
  padding: 2.75rem 0 1.5rem;
}

.hero-glow {
  position: absolute;
  inset: -3rem -6rem auto auto;
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, var(--glow-ambient-a) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.hero-copy,
.hero-controls {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  margin-bottom: 1.1rem;
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(2.3rem, 5vw, 3.6rem);
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.02;
  margin-bottom: 1rem;
  background: linear-gradient(150deg, var(--color-text-primary) 30%, var(--color-primary-light) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-sub {
  color: var(--color-text-secondary);
  font-size: 1.05rem;
  max-width: 34rem;
}

.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 1rem;
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 1.05rem 3rem 1.05rem 2.9rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  color: var(--color-text-primary);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.search-clear {
  position: absolute;
  right: 1rem;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  background: var(--color-bg-tertiary);
  transition: all var(--transition-fast);
}

.search-clear:hover {
  color: var(--color-text-primary);
  background: var(--color-border-strong);
}

.category-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-glass);
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.chip:hover {
  color: var(--color-text-primary);
  border-color: var(--color-border-strong);
  transform: translateY(-1px);
}

.chip.active {
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-color: transparent;
  box-shadow: var(--glow-primary);
}

.chip-count {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.05rem 0.4rem;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.14);
}

/* ---------- Toolbar ---------- */
.home-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--color-border-light);
}

.view-toggle {
  display: inline-flex;
  padding: 0.25rem;
  gap: 0.15rem;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
}

.seg-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.15rem;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.seg-btn:hover {
  color: var(--color-text-primary);
}

.seg-btn.active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #fff;
  box-shadow: var(--glow-primary);
}

.seg-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.6;
}

.seg-count {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.05rem 0.45rem;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.16);
}

/* ---------- Grid ---------- */
.apps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(235px, 1fr));
  gap: 1.25rem;
}

.app-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 1.15rem;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-base), box-shadow var(--transition-base),
    border-color var(--transition-base);
}

.app-card:hover {
  transform: translateY(-6px);
  border-color: rgba(109, 124, 255, 0.35);
  box-shadow: var(--glow-primary);
}

.card-icon {
  width: 76px;
  height: 76px;
  border-radius: 18px;
  overflow: hidden;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  margin-bottom: 0.9rem;
}

.app-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform var(--transition-base);
}

.app-card:hover .app-icon {
  transform: scale(1.06);
}

.app-title {
  font-size: 1.06rem;
  font-weight: 700;
  margin-bottom: 0.15rem;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.app-dev {
  font-size: 0.82rem;
  color: var(--color-text-muted);
  margin-bottom: 0.6rem;
}

.arch-warning {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
  color: var(--color-warning);
  font-size: 0.78rem;
  font-weight: 700;
}

.arch-warning::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 10px currentColor;
}

.app-desc {
  font-size: 0.86rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  flex: 1;
  margin-bottom: 1rem;
}

.app-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--color-border-light);
}

.category-badge {
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.details-btn {
  gap: 0.35rem;
}

/* Favorite button */
.fav-btn {
  position: absolute;
  top: 0.85rem;
  right: 0.85rem;
  z-index: 2;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: var(--color-text-muted);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all var(--transition-fast);
}

.fav-btn:hover {
  transform: scale(1.12);
  color: var(--color-error);
  border-color: rgba(239, 68, 68, 0.5);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.25);
}

.fav-btn.favorited {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.14);
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.28);
}

/* ---------- Skeleton ---------- */
.skeleton-card {
  gap: 0.7rem;
  background: var(--color-glass);
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
.skeleton-line.w-40 { width: 40%; }

.skeleton-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.6rem;
  border-top: 1px solid var(--color-border-light);
}

.skeleton-btn {
  width: 88px;
  height: 34px;
  border-radius: var(--radius-sm);
}

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

/* ---------- Pagination ---------- */
.pagination {
  display: flex;
  justify-content: center;
  padding-top: 1rem;
}

.load-more-btn {
  padding: 0.85rem 2rem;
}

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 1.75rem;
  }

  .hero-glow {
    width: 280px;
    height: 280px;
  }
}

@media (max-width: 560px) {
  .apps-grid {
    grid-template-columns: 1fr;
  }

  .home-toolbar {
    justify-content: center;
  }
}
</style>