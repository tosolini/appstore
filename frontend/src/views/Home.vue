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

    <div v-if="loading" class="loading">Loading apps...</div>
    
    <div v-else-if="apps.length === 0" class="no-results">
      No apps found
    </div>
    
    <div v-else class="apps-grid">
      <div v-for="app in apps" :key="app.app_id" class="app-card">
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

    <div v-if="totalApps > apps.length" class="pagination">
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
      categories: [],
      searchQuery: '',
      selectedCategory: '',
      loading: true,
      totalApps: 0,
      offset: 0,
      limit: 12
    }
  },
  mounted() {
    this.loadCategories()
    this.loadApps()
  },
  methods: {
    async loadCategories() {
      try {
        const response = await axios.get('/api/categories')
        this.categories = response.data.categories
      } catch (error) {
        console.error('Error loading categories:', error)
        this.categories = []
      }
    },
    async loadApps() {
      this.loading = true
      this.offset = 0
      try {
        let url = `/apps?limit=${this.limit}&offset=${this.offset}`
        if (this.selectedCategory) {
          url += `&category=${this.selectedCategory}`
        }
        
        const response = await axios.get(url)
        this.apps = response.data.apps
        this.totalApps = response.data.total
      } catch (error) {
        console.error('Error loading apps:', error)
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
        this.apps = response.data.apps
        this.totalApps = response.data.results_count
      } catch (error) {
        console.error('Error searching apps:', error)
        this.apps = []
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      this.offset += this.limit
      try {
        let url = `/apps?limit=${this.limit}&offset=${this.offset}`
        if (this.selectedCategory) {
          url += `&category=${this.selectedCategory}`
        }
        
        const response = await axios.get(url)
        this.apps = [...this.apps, ...response.data.apps]
      } catch (error) {
        console.error('Error loading more apps:', error)
      }
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
  margin-bottom: 2rem;
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
  padding: 2rem;
  color: var(--color-text-secondary);
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
}

.app-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
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
