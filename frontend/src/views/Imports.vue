<template>
  <div class="imports-page">
    <nav class="imports-tabs reveal" aria-label="Import sources">
      <router-link to="/imports/github" class="tab">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
        </svg>
        GitHub
      </router-link>
      <router-link to="/imports/dockerhub" class="tab">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 11h16v3H4zM6 8h4v3H6zM14 8h4v3h-4zM10 14h4v3h-4zM6 14h2v3H6z" />
          <path d="M7 17h10v3H7z" />
        </svg>
        Docker Hub
      </router-link>
    </nav>

    <router-view />
  </div>
</template>

<script>
export default {
  name: 'Imports'
}
</script>

<style scoped>
.imports-page {
  display: grid;
  gap: 1.25rem;
}

.imports-tabs {
  display: inline-flex;
  gap: 0.35rem;
  padding: 0.3rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-glass);
  width: fit-content;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.1rem;
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 700;
  transition: all var(--transition-fast);
}

.tab:hover {
  color: var(--color-text-primary);
}

.tab.router-link-active {
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  box-shadow: var(--glow-primary);
}
</style>
