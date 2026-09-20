<template>
  <div class="app-detail-page">
    <div v-if="loading" class="detail-loading">
      <div class="skeleton detail-hero-skeleton"></div>
      <div class="skeleton detail-line w-70"></div>
      <div class="skeleton detail-line w-100"></div>
      <div class="skeleton detail-line w-90"></div>
    </div>

    <div v-else-if="!app" class="not-found">
      <div class="empty-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 12h18M12 3l9 9-9 9" />
        </svg>
      </div>
      <h2>App not found</h2>
      <p class="text-muted">It may have been removed or renamed.</p>
    </div>

    <template v-else>
      <router-link to="/" class="back-link">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5M11 18l-6-6 6-6" />
        </svg>
        Back to Browse
      </router-link>

      <section class="detail-hero reveal">
        <div class="hero-icon-wrap">
          <img :src="app.icon" :alt="app.title" class="hero-icon" v-img-fallback>
        </div>
        <div class="hero-info">
          <div class="hero-title-row">
            <h1>{{ app.title }}</h1>
            <button
              class="fav-btn-detail"
              :class="{ favorited: isFavorite }"
              @click="toggleFavorite"
              :title="isFavorite ? 'Remove from My List' : 'Add to My List'"
              :aria-label="isFavorite ? 'Remove from My List' : 'Add to My List'"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="currentColor" stroke-width="1.6">
                <path d="M12 21s-7.5-4.7-10-9.3C.5 8.5 2 5 5.3 5c2 0 3.4 1.1 4.2 2.4.6-1.3 2-2.4 4.2-2.4C17 5 18.5 8.5 17 11.7 14.5 16.3 12 21 12 21z" />
              </svg>
            </button>
          </div>
          <p class="developer">by {{ app.developer }}</p>
          <div class="hero-badges">
            <span class="badge badge-primary">{{ app.category }}</span>
            <span v-if="app.source_type" class="badge">{{ app.source_type }}</span>
            <span class="badge"><span class="arch-label">arch</span> {{ app.architectures.join(', ') }}</span>
          </div>
        </div>
      </section>

      <div v-if="app.compatibility_warning" class="compatibility-banner warning reveal">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
        </svg>
        <span>{{ app.compatibility_warning }}</span>
      </div>
      <div v-else-if="app.compatibility_status === 'buildable'" class="compatibility-banner info reveal">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <span>
          This app is generated from a Dockerfile and should build on the current host architecture
          ({{ app.host_architecture }}).
        </span>
      </div>

      <section v-if="app.screenshot_links && app.screenshot_links.length" class="screenshots reveal">
        <div class="screenshots-grid">
          <div
            v-for="(img, idx) in app.screenshot_links.slice(0, 3)"
            :key="idx"
            class="screenshot-wrapper"
            @click="openLightbox(idx)"
            role="button"
            tabindex="0"
            @keydown.enter="openLightbox(idx)"
            :aria-label="`Open screenshot ${idx + 1}`"
          >
            <img :src="img" :alt="`Screenshot ${idx + 1}`" class="screenshot" loading="lazy" v-img-fallback>
            <div class="screenshot-overlay">
              <span class="magnifier">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m21 21-4.3-4.3M8 11h6M11 8v6" />
                </svg>
              </span>
            </div>
          </div>
        </div>
      </section>

      <div v-if="lightboxOpen" class="lightbox-overlay" @click="closeLightbox">
        <div class="lightbox-content" @click.stop>
          <button class="lightbox-close" @click="closeLightbox" aria-label="Close">✕</button>
          <button class="lightbox-prev" @click="prevImage" v-if="currentImageIndex > 0" aria-label="Previous">❮</button>
          <img
            :src="app.screenshot_links[currentImageIndex]"
            :alt="`Screenshot ${currentImageIndex + 1}`"
            class="lightbox-image"
            v-img-fallback
          >
          <button class="lightbox-next" @click="nextImage" v-if="currentImageIndex < app.screenshot_links.length - 1" aria-label="Next">❯</button>
          <div class="lightbox-counter">{{ currentImageIndex + 1 }} / {{ app.screenshot_links.length }}</div>
        </div>
      </div>

      <div class="detail-layout">
        <div class="detail-main">
          <section class="panel about-panel reveal">
            <h2 class="panel-title">About</h2>
            <p class="about-text">{{ app.description }}</p>
            <div class="about-links">
              <a v-if="app.source_url" :href="app.source_url" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
                  <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
                </svg>
                Source
              </a>
              <a v-if="app.homepage" :href="app.homepage" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 12h4l2 7 4-14 2 7h4" />
                </svg>
                Homepage
              </a>
            </div>
          </section>

          <section class="panel compose-panel reveal">
            <div class="compose-header">
              <h2 class="panel-title">Docker Compose</h2>
              <button class="btn btn-ghost btn-sm" @click="copyCompose" :class="{ copied: copyMessage }">
                <span v-if="copyMessage" class="copied-mark">✓</span>
                <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="12" height="12" rx="2" />
                  <path d="M5 15V5a2 2 0 0 1 2-2h10" />
                </svg>
                {{ copyMessage ? 'Copied!' : 'Copy' }}
              </button>
            </div>
            <p class="text-muted panel-sub">Get the docker-compose.yml for this application</p>
            <pre class="compose-code"><code>{{ cleanedCompose }}</code></pre>
          </section>
        </div>

        <aside class="detail-side">
          <section class="panel deploy-panel reveal">
            <div class="deploy-head">
              <h2 class="panel-title">Deploy</h2>
              <span class="badge badge-primary backend-badge">{{ activeBackendLabel }}</span>
            </div>
            <p class="text-muted panel-sub">Configure and deploy this stack to your {{ activeBackendLabel }} endpoint.</p>
            <DeployForm
              :app-id="app.app_id"
              :schema="parameters"
              :volumes="volumes"
              @deploy-success="onDeploySuccess"
              @deploy-error="onDeployError"
            />
          </section>

          <section class="panel info-panel reveal">
            <h2 class="panel-title">Information</h2>
            <dl class="info-list">
              <div class="info-item">
                <dt>App ID</dt>
                <dd class="mono">{{ app.app_id }}</dd>
              </div>
              <div class="info-item">
                <dt>Repository</dt>
                <dd class="mono">{{ app.repository_source }}</dd>
              </div>
              <div class="info-item">
                <dt>Main Service</dt>
                <dd class="mono">{{ app.main_service }}</dd>
              </div>
              <div class="info-item">
                <dt>Port Map</dt>
                <dd class="mono">{{ app.port_map }}</dd>
              </div>
              <div class="info-item">
                <dt>Architectures</dt>
                <dd class="mono">{{ app.architectures.join(', ') }}</dd>
              </div>
              <div class="info-item" v-if="app.host_architecture">
                <dt>Host Architecture</dt>
                <dd class="mono">{{ app.host_architecture }}</dd>
              </div>
              <div class="info-item" v-if="app.source_type">
                <dt>Source Type</dt>
                <dd class="mono">{{ app.source_type }}</dd>
              </div>
              <div class="info-item" v-if="app.import_debug">
                <dt>Import</dt>
                <dd>
                  <span :class="['badge', importDebugClass(app.import_debug)]">
                    {{ formatImportDebug(app.import_debug) }}
                  </span>
                </dd>
              </div>
              <div class="info-item" v-if="app.unsupported_services && app.unsupported_services.length">
                <dt>Unsupported</dt>
                <dd class="mono">{{ app.unsupported_services.join(', ') }}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script>
import axios from 'axios'
import DeployForm from '../components/DeployForm.vue'

export default {
  name: 'AppDetail',
  components: {
    DeployForm
  },
  data() {
    return {
      app: null,
      parameters: [],
      volumes: [],
      loading: true,
      copyMessage: false,
      lightboxOpen: false,
      currentImageIndex: 0,
      activeBackend: 'Portainer',
      isFavorite: false
    }
  },
  mounted() {
    this.loadAppDetail()
    this.loadBackendStatus()
  },
  computed: {
    activeBackendLabel() {
      return this.activeBackend.charAt(0).toUpperCase() + this.activeBackend.slice(1)
    },
    cleanedCompose() {
      if (!this.app || !this.app.compose_content) return ''
      try {
        let cleaned = this.removeXCasaosSection(this.app.compose_content)
        cleaned = this.normalizeCompose(cleaned)
        return cleaned
      } catch (error) {
        console.error('Error cleaning compose:', error)
        return this.removeXCasaosSection(this.app.compose_content)
      }
    }
  },
  methods: {
    formatImportDebug(importDebug) {
      if (!importDebug) return ''

      const composeSource = importDebug.compose_path ? ` (${importDebug.compose_path})` : ''
      if (importDebug.import_strategy === 'dockerfile-fallback') {
        return `Dockerfile fallback${importDebug.dockerfile_path ? ` (${importDebug.dockerfile_path})` : ''}`
      }
      if (importDebug.import_strategy === 'git-fallback') {
        return `git fallback${composeSource}`
      }
      return `GitHub API${composeSource}`
    },

    importDebugClass(importDebug) {
      if (!importDebug) return ''
      if (importDebug.import_strategy === 'dockerfile-fallback') return 'badge-info'
      if (importDebug.import_strategy === 'git-fallback') return 'badge-warning'
      return 'badge-success'
    },

    async loadBackendStatus() {
      try {
        const response = await axios.get('/api/settings/backend')
        this.activeBackend = response.data.active_backend
      } catch (error) {
        console.error('Error loading backend status:', error)
      }
    },
    async loadAppDetail() {
      const appId = this.$route.params.id
      try {
        const [appResponse, schemaResponse] = await Promise.all([
          axios.get(`/apps/${appId}`),
          axios.get(`/apps/${appId}/schema`)
        ])

        this.app = appResponse.data
        this.parameters = schemaResponse.data.parameters
        this.volumes = schemaResponse.data.volumes || []
        await this.loadFavoriteStatus()
      } catch (error) {
        console.error('Error loading app details:', error)
      } finally {
        this.loading = false
      }
    },
    async loadFavoriteStatus() {
      try {
        const response = await axios.get('/api/favorites/ids')
        this.isFavorite = response.data.ids.includes(this.app?.app_id)
      } catch (error) {
        console.error('Error loading favorite status:', error)
      }
    },
    async toggleFavorite() {
      try {
        if (this.isFavorite) {
          await axios.delete(`/api/favorites/${this.app.app_id}`)
        } else {
          await axios.post(`/api/favorites/${this.app.app_id}`)
        }
        this.isFavorite = !this.isFavorite
      } catch (error) {
        console.error('Error toggling favorite:', error)
      }
    },
    onDeploySuccess(result) {
      console.log('Deploy successful:', result)
    },
    onDeployError(error) {
      console.error('Deploy error:', error)
    },
    async copyCompose() {
      try {
        await navigator.clipboard.writeText(this.cleanedCompose)
        this.copyMessage = true
        setTimeout(() => {
          this.copyMessage = false
        }, 2000)
      } catch (error) {
        console.error('Failed to copy:', error)
        alert('Failed to copy to clipboard')
      }
    },
    removeXCasaosSection(yaml) {
      const lines = yaml.split('\n')
      const filtered = []
      let skipUntilNextKey = false

      for (const line of lines) {
        if (line.trim().startsWith('x-casaos:')) {
          skipUntilNextKey = true
          continue
        }

        if (skipUntilNextKey) {
          if (line && !line.startsWith(' ') && !line.startsWith('\t')) {
            skipUntilNextKey = false
            filtered.push(line)
            continue
          }
          if (!line.trim()) {
            continue
          }
          continue
        }

        filtered.push(line)
      }

      return filtered.join('\n').trim()
    },
    normalizeCompose(yaml) {
      try {
        const portBlockRegex = /- target:\s*["']?(\d+)["']?\r?\n\s+published:\s*["']?(\d+)["']?\r?\n\s+protocol:\s*["']?(\w+)["']?(?:\r?\n)?/gm

        let replaced = yaml.replace(portBlockRegex, (match, target, published, protocol) => {
          protocol = protocol || 'tcp'
          return `- "${target}:${published}/${protocol}"\n`
        })

        return replaced.trim()
      } catch (error) {
        console.error('Error normalizing compose:', error)
        return yaml
      }
    },
    openLightbox(index) {
      this.currentImageIndex = index
      this.lightboxOpen = true
      document.body.style.overflow = 'hidden'
    },
    closeLightbox() {
      this.lightboxOpen = false
      document.body.style.overflow = 'auto'
    },
    nextImage() {
      if (this.currentImageIndex < this.app.screenshot_links.length - 1) {
        this.currentImageIndex++
      }
    },
    prevImage() {
      if (this.currentImageIndex > 0) {
        this.currentImageIndex--
      }
    }
  }
}
</script>

<style scoped>
.app-detail-page {
  display: grid;
  gap: 1.25rem;
}

/* ---------- Loading / not found ---------- */
.detail-loading {
  display: grid;
  gap: 0.9rem;
}

.detail-hero-skeleton {
  height: 180px;
  border-radius: var(--radius-lg);
}

.detail-line { height: 16px; }
.detail-line.w-70 { width: 70%; }
.detail-line.w-100 { width: 100%; }
.detail-line.w-90 { width: 90%; }

.not-found {
  text-align: center;
  padding: 5rem 2rem;
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

.not-found h2 {
  font-size: 1.5rem;
  margin-bottom: 0.35rem;
}

/* ---------- Back ---------- */
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  width: fit-content;
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-size: 0.88rem;
  font-weight: 600;
  transition: all var(--transition-fast);
}

.back-link:hover {
  color: var(--color-text-primary);
  background: var(--color-glass);
}

/* ---------- Hero ---------- */
.detail-hero {
  display: flex;
  gap: 1.75rem;
  align-items: flex-start;
  padding: 1.75rem;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.detail-hero::before {
  content: '';
  position: absolute;
  inset: auto -80px -120px auto;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, var(--glow-ambient-a), transparent 65%);
  pointer-events: none;
}

.hero-icon-wrap {
  width: 108px;
  height: 108px;
  flex-shrink: 0;
  border-radius: 24px;
  overflow: hidden;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.hero-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-info {
  flex: 1;
  position: relative;
  z-index: 1;
  min-width: 0;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.hero-title-row h1 {
  font-size: clamp(1.6rem, 3.5vw, 2.3rem);
  font-weight: 750;
  letter-spacing: -0.03em;
  overflow-wrap: anywhere;
}

.developer {
  color: var(--color-text-secondary);
  margin: 0.3rem 0 0.9rem;
  font-size: 0.95rem;
}

.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.arch-label {
  opacity: 0.7;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.04em;
}

/* Favorite */
.fav-btn-detail {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-glass);
  color: var(--color-text-muted);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all var(--transition-fast);
}

.fav-btn-detail:hover {
  transform: scale(1.1);
  color: var(--color-error);
  border-color: rgba(239, 68, 68, 0.5);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.25);
}

.fav-btn-detail.favorited {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.14);
  border-color: rgba(239, 68, 68, 0.4);
}

/* ---------- Compatibility banner ---------- */
.compatibility-banner {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.95rem 1.15rem;
  border-radius: var(--radius-md);
  border: 1px solid;
  font-size: 0.93rem;
  font-weight: 500;
  line-height: 1.5;
}

.compatibility-banner svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.compatibility-banner.warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  color: var(--color-warning);
}

.compatibility-banner.info {
  background: rgba(14, 165, 233, 0.1);
  border-color: rgba(14, 165, 233, 0.28);
  color: var(--color-info);
}

/* ---------- Screenshots ---------- */
.screenshots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.screenshot-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.screenshot {
  width: 100%;
  max-height: 420px;
  object-fit: cover;
  display: block;
  transition: transform 500ms cubic-bezier(0.22, 1, 0.36, 1);
}

.screenshot-wrapper:hover .screenshot {
  transform: scale(1.05);
}

.screenshot-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.15) 50%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--transition-base);
}

.screenshot-wrapper:hover .screenshot-overlay {
  opacity: 1;
}

.magnifier {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

/* ---------- Lightbox ---------- */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 6, 14, 0.94);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 220ms ease;
}

.lightbox-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: popIn 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.lightbox-image {
  max-width: 85vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: var(--radius-md);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6);
}

.lightbox-close,
.lightbox-prev,
.lightbox-next {
  position: absolute;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: #fff;
  cursor: pointer;
  z-index: 10001;
  transition: all var(--transition-fast);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.lightbox-close {
  top: 20px;
  right: 20px;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  font-size: 1.2rem;
}

.lightbox-prev,
.lightbox-next {
  top: 50%;
  transform: translateY(-50%);
  width: 50px;
  height: 50px;
  border-radius: 50%;
  font-size: 1.2rem;
}

.lightbox-close:hover,
.lightbox-prev:hover,
.lightbox-next:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.4);
}

.lightbox-prev:hover,
.lightbox-next:hover {
  transform: translateY(-50%) scale(1.1);
}

.lightbox-prev { left: 20px; }
.lightbox-next { right: 20px; }

.lightbox-counter {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 0.4rem 0.9rem;
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

/* ---------- Layout ---------- */
.detail-layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 1.25rem;
  align-items: start;
}

.detail-main {
  display: grid;
  gap: 1.25rem;
}

.detail-side {
  display: grid;
  gap: 1.25rem;
  position: sticky;
  top: 92px;
}

.panel {
  padding: 1.5rem;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.panel-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}

.panel-sub {
  font-size: 0.9rem;
  margin: 0.3rem 0 1.25rem;
}

/* About */
.about-text {
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 1.1rem;
  font-size: 0.96rem;
}

.about-links {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

/* Compose */
.compose-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.copied-mark {
  color: var(--color-success);
  font-weight: 800;
}

.compose-code {
  background: var(--color-code-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--color-code-text);
  margin: 0;
  max-height: 420px;
}

.compose-code code {
  color: var(--color-code-text);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Deploy */
.deploy-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.25rem;
}

.backend-badge {
  letter-spacing: 0.04em;
}

/* Information */
.info-list {
  display: grid;
  gap: 0;
  margin: 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--color-border-light);
}

.info-item:last-child {
  border-bottom: none;
}

.info-item dt {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding-top: 0.15rem;
  flex-shrink: 0;
}

.info-item dd {
  margin: 0;
  font-size: 0.88rem;
  color: var(--color-text-secondary);
  text-align: right;
  overflow-wrap: anywhere;
}

.info-item dd.mono {
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .detail-side {
    position: static;
  }
}

@media (max-width: 560px) {
  .detail-hero {
    flex-direction: column;
  }

  .hero-icon-wrap {
    width: 88px;
    height: 88px;
  }
}
</style>