<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <h1>Container AppStore</h1>
        <nav class="header-nav">
          <router-link to="/">Browse</router-link>
          <router-link to="/settings">Settings</router-link>
          <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'Light Mode' : 'Dark Mode'">
            {{ themeIcon }}
          </button>
        </nav>
      </div>
    </header>
    
    <main class="app-main">
      <router-view></router-view>
    </main>
    
    <footer class="app-footer">
      <p>
        Container AppStore Bridge by 
        <a href="https://www.tosolini.info" target="_blank" rel="noopener noreferrer">Tosolini.info</a>
        v0.2.0 | 
        <a href="/docs" target="_blank" rel="noopener noreferrer">Backend API</a>
      </p>
    </footer>
  </div>
</template>

<script setup>
import { useTheme } from './composables/useTheme'
import { computed } from 'vue'

const { currentTheme, toggleTheme } = useTheme()

const isDark = computed(() => currentTheme.value === 'dark')
const themeIcon = computed(() => isDark.value ? '☀️' : '🌙')
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
}

.app-header {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  padding: 1rem 0;
  box-shadow: var(--shadow-md);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  font-size: 1.8rem;
  font-weight: 700;
}

.header-nav {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.header-nav a {
  color: white;
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.3s;
  border-bottom: 2px solid transparent;
  padding-bottom: 0.25rem;
}

.header-nav a:hover,
.header-nav a.router-link-active {
  opacity: 0.8;
  border-bottom-color: white;
}

.theme-toggle {
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  color: white;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  padding: 0;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.app-main {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
  width: 100%;
  background-color: var(--color-bg-primary);
}

.app-footer {
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border);
  padding: 1rem;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.app-footer a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.app-footer a:hover {
  opacity: 0.8;
  text-decoration: underline;
}
</style>
