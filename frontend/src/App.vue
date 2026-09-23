<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <router-link to="/" class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="6" rx="1.6" />
              <rect x="3" y="14" width="18" height="6" rx="1.6" />
              <path d="M8 7h.01M8 17h.01" />
            </svg>
          </span>
          <span class="brand-text">
            Container<span class="brand-accent">AppStore</span>
          </span>
        </router-link>

        <nav class="header-nav">
          <router-link to="/" class="nav-link">Browse</router-link>
          <router-link to="/new" class="nav-link nav-link-new">
            New
            <span v-if="newCount > 0" class="new-count">{{ newCount }}</span>
          </router-link>
          <router-link to="/imports/github" class="nav-link">Imports</router-link>
          <router-link to="/settings" class="nav-link">Settings</router-link>
          <button
            class="theme-toggle"
            @click="toggleTheme"
            :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            aria-label="Toggle theme"
          >
            <span class="theme-track">
              <span class="theme-thumb" :class="{ dark: isDark }"></span>
            </span>
            <span class="theme-icon" aria-hidden="true">{{ themeIcon }}</span>
          </button>
        </nav>
      </div>
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </transition>
      </router-view>
    </main>

    <footer class="app-footer">
      <div class="footer-content">
        <span class="footer-brand">Container AppStore Bridge</span>
        <span class="footer-divider" aria-hidden="true">•</span>
        <a href="https://www.tosolini.info" target="_blank" rel="noopener noreferrer">Tosolini.info</a>
        <span class="footer-version badge badge-primary">v{{ appVersion }}</span>
        <a href="/docs" target="_blank" rel="noopener noreferrer" class="footer-docs">Backend API</a>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useTheme } from './composables/useTheme'
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import packageJson from '../package.json'

const { currentTheme, toggleTheme } = useTheme()

const isDark = computed(() => currentTheme.value === 'dark')
const themeIcon = computed(() => isDark.value ? '☀️' : '🌙')
const appVersion = packageJson.version
const newCount = ref(0)

onMounted(async () => {
  // Record the catalog baseline for this frontend version (idempotent),
  // then refresh the "new apps" badge count.
  try {
    await axios.post('/api/imports/github/snapshot', {
      frontend_version: packageJson.version
    })
  } catch (e) {
    console.error('Error recording catalog snapshot:', e)
  }
  try {
    const response = await axios.get('/api/imports/github/new-ids')
    newCount.value = (response.data.ids || []).length
  } catch (e) {
    console.error('Error loading new apps count:', e)
  }
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: background-color 0.4s ease, color 0.4s ease;
}

/* ---------- Header ---------- */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.85rem 0;
  background: color-mix(in srgb, var(--color-bg-primary) 62%, transparent);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  backdrop-filter: blur(18px) saturate(160%);
  border-bottom: 1px solid var(--color-border-light);
}

.header-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  color: var(--color-text-primary);
}

.brand:hover {
  color: var(--color-text-primary);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 55%, var(--color-accent) 130%);
  box-shadow: var(--glow-primary);
}

.brand-text {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-accent {
  background: linear-gradient(120deg, var(--color-primary-light), var(--color-accent));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.header-nav {
  display: flex;
  gap: 0.35rem;
  align-items: center;
}

.nav-link {
  position: relative;
  padding: 0.5rem 0.95rem;
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-size: 0.92rem;
  font-weight: 600;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-glass);
}

.nav-link.router-link-active {
  color: var(--color-text-primary);
  background: linear-gradient(135deg, rgba(109, 124, 255, 0.16), rgba(34, 211, 238, 0.12));
  box-shadow: inset 0 0 0 1px rgba(109, 124, 255, 0.28);
}

.nav-link-new {
  gap: 0.4rem;
}

.new-count {
  font-size: 0.7rem;
  font-weight: 800;
  padding: 0.1rem 0.45rem;
  border-radius: var(--radius-pill);
  color: #fff;
  background: linear-gradient(135deg, var(--color-accent), var(--color-primary));
}

/* Theme toggle */
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 0.5rem;
  padding: 0.35rem 0.55rem 0.35rem 0.35rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-glass);
  cursor: pointer;
  transition: all var(--transition-base);
}

.theme-toggle:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.theme-track {
  position: relative;
  width: 30px;
  height: 18px;
  border-radius: var(--radius-pill);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
}

.theme-thumb {
  position: absolute;
  top: 1.5px;
  left: 2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-warning), #f97316);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  transition: transform var(--transition-base), background var(--transition-base);
}

.theme-thumb.dark {
  transform: translateX(12px);
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-accent));
}

.theme-icon {
  font-size: 0.9rem;
  line-height: 1;
}

/* ---------- Main ---------- */
.app-main {
  flex: 1;
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 2.25rem 1.5rem 4rem;
  background-color: var(--color-bg-primary);
  transition: background-color 0.4s ease;
}

/* ---------- Footer ---------- */
.app-footer {
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  border-top: 1px solid var(--color-border-light);
  padding: 1.25rem 1.5rem;
}

.footer-content {
  max-width: 1240px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 0.88rem;
}

.footer-brand {
  font-weight: 600;
  color: var(--color-text-secondary);
}

.footer-divider {
  opacity: 0.5;
}

.footer-version {
  margin-left: 0.15rem;
}

.footer-docs {
  margin-left: 0.25rem;
}

/* ---------- Page transition ---------- */
.page-enter-active,
.page-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ---------- Responsive ---------- */
@media (max-width: 700px) {
  .brand-text {
    font-size: 1.05rem;
  }

  .nav-link {
    padding: 0.45rem 0.7rem;
    font-size: 0.85rem;
  }

  .app-main {
    padding: 1.5rem 1rem 3rem;
  }
}
</style>