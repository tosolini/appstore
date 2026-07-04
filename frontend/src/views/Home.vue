<template>
  <div class="home-page">
    <div class="filters">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="Search apps..." 
        class="search-input"
        @input="handleSearch"
      >
      <select v-model="selectedCategory" class="filter-select" @change="loadApps">
        <option value="">All Categories</option>
        <option v-for="cat in categories" :key="cat.name" :value="cat.name">
          {{ cat.name }} ({{ cat.count }})
        </option>
      </select>
    </div>

    <div class="view-toggle">
      <button 
        :class="['toggle-btn', { active: viewMode === 'all' }]" 
        @click="switchView('all')">
        All Apps ({{ filteredTotal }})
      </button>
      <button 
        :class="['toggle-btn', { active: viewMode === 'favorites' }]" 
        @click="switchView('favorites')">
        My List ({{ favoriteIds.size }})
      </button>
    </div>

    <div v-if="loading" class="loading">Loading apps...</div>
    
    <div v-else-if="displayApps.length === 0" class="no-results">
      <template v-if="viewMode === 'favorites'">No favorited apps yet. Browse and add some!</template>
      <template v-else>No apps found</template>
    </div>
    
    <div v-else class="apps-grid">
      <div v-for="app in displayApps" :key="app.app_id" class="app-card">
        <button 
          class="fav-btn" 
          :class="{ favorited: favoriteIds.has(app.app_id) }"
          @click="toggleFavorite(app.app_id)"
          :title="favoriteIds.has(app.app_id) ? 'Remove from My List' : 'Add to My List'">
          {{ favoriteIds.has(app.app_id) ? '♥' : '♡' }}
        </button>
        <img :src="app.icon" :alt="app.title" class="app-icon">
        <h3>{{ app.title }}</h3>
        <p class="app-dev">{{ app.developer }}</p>
        <p class="app-desc">{{ truncate(app.description, 100) }}</p>
        <div class="app-footer">
          <span class="category">{{ app.category }}</span>
          <router-link :to="`/app/${app.app_id}`" class="btn-primary">Details</router-link>
        </div>
      </div>
    </div>

    <div v-if="viewMode === 'all' && hasMore" class="pagination">
      <button @click="loadMore" class="btn-load-more">Load More</button>
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
      if (text.length <= length) return text
      return text.substring(0, length) + '...'
    }
  }
}
</script>

<style scoped>
.home-page {
  padding: 1rem 0;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.view-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.toggle-btn {
  padding: 0.5rem 1.25rem;
  border: 2px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-text-primary);
}

.toggle-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.search-input,
.filter-select {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 1rem;
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  transition: all 0.3s ease;
}

.search-input:focus,
.filter-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.filter-select {
  min-width: 150px;
}

.loading,
.no-results {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--color-text-secondary);
  font-size: 1.1rem;
}

.apps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.app-card {
  background: var(--color-bg-secondary);
  border-radius: 8px;
  padding: 1rem;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  position: relative;
}

.app-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.fav-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  z-index: 2;
  line-height: 1;
}

.fav-btn:hover {
  transform: scale(1.15);
  background: rgba(0, 0, 0, 0.6);
}

.fav-btn.favorited {
  color: #ff4757;
  background: rgba(255, 71, 87, 0.25);
}

.fav-btn.favorited:hover {
  background: rgba(255, 71, 87, 0.4);
}

.app-icon {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 0.75rem;
}

.app-card h3 {
  font-size: 1.1rem;
  margin-bottom: 0.25rem;
  color: var(--color-text-primary);
}

.app-dev {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.app-desc {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
  flex: 1;
  line-height: 1.4;
}

.app-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.category {
  display: inline-block;
  background: var(--color-bg-tertiary);
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background 0.2s;
  border: none;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.pagination {
  text-align: center;
  margin-top: 2rem;
}

.btn-load-more {
  background: var(--color-primary);
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-load-more:hover {
  background: var(--color-primary-dark);
}
</style>
