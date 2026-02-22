<template>
  <div class="app-detail-page">
    <div v-if="loading" class="loading">Loading app details...</div>
    
    <div v-else-if="!app" class="not-found">App not found</div>
    
    <div v-else class="app-detail">
      <div class="app-header">
        <img :src="app.icon" :alt="app.title" class="app-icon">
        <div class="app-info">
          <h1>{{ app.title }}</h1>
          <p class="developer">by {{ app.developer }}</p>
          <p class="category">{{ app.category }}</p>
          <p class="description">{{ app.description }}</p>
        </div>
      </div>

      <div class="screenshots" v-if="app.screenshot_links && app.screenshot_links.length">
        <h2>Screenshots</h2>
        <div class="screenshots-grid">
          <div 
            v-for="(img, idx) in app.screenshot_links.slice(0, 3)" 
            :key="idx"
            class="screenshot-wrapper"
            @click="openLightbox(idx)"
          >
            <img 
              :src="img" 
              :alt="`Screenshot ${idx + 1}`"
              class="screenshot">
            <div class="screenshot-overlay">
              <span class="magnifier">🔍</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Lightbox -->
      <div v-if="lightboxOpen" class="lightbox-overlay" @click="closeLightbox">
        <div class="lightbox-content" @click.stop>
          <button class="lightbox-close" @click="closeLightbox">✕</button>
          <button class="lightbox-prev" @click="prevImage" v-if="currentImageIndex > 0">❮</button>
          <img 
            :src="app.screenshot_links[currentImageIndex]" 
            :alt="`Screenshot ${currentImageIndex + 1}`"
            class="lightbox-image">
          <button class="lightbox-next" @click="nextImage" v-if="currentImageIndex < app.screenshot_links.length - 1">❯</button>
          <div class="lightbox-counter">{{ currentImageIndex + 1 }} / {{ app.screenshot_links.length }}</div>
        </div>
      </div>

      <div class="deployment-section">
        <h2>Deploy to Portainer</h2>
        <DeployForm 
          :app-id="app.app_id"
          :schema="parameters"
          :volumes="volumes"
          @deploy-success="onDeploySuccess"
          @deploy-error="onDeployError"
        />
      </div>

      <div class="compose-section">
        <h2>Docker Compose</h2>
        <p class="text-muted">Get the docker-compose.yml for this application</p>
        <div class="compose-container">
          <pre class="compose-code"><code>{{ cleanedCompose }}</code></pre>
          <button class="btn-copy" @click="copyCompose" :class="{ 'copied': copyMessage }">
            {{ copyMessage ? '✓ Copied!' : '📋 Copy' }}
          </button>
        </div>
      </div>

      <div class="metadata">
        <h2>Information</h2>
        <p><strong>App ID:</strong> {{ app.app_id }}</p>
        <p><strong>Repository:</strong> {{ app.repository_source }}</p>
        <p><strong>Main Service:</strong> {{ app.main_service }}</p>
        <p><strong>Port Map:</strong> {{ app.port_map }}</p>
        <p><strong>Architectures:</strong> {{ app.architectures.join(', ') }}</p>
      </div>

      <router-link to="/" class="btn-back">← Back to Browse</router-link>
    </div>
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
      currentImageIndex: 0
    }
  },
  mounted() {
    this.loadAppDetail()
  },
  computed: {
    cleanedCompose() {
      if (!this.app || !this.app.compose_content) return ''
      try {
        let cleaned = this.removeXCasaosSection(this.app.compose_content)
        cleaned = this.normalizeCompose(cleaned)
        return cleaned
      } catch (error) {
        console.error('Error cleaning compose:', error)
        // Se c'è un errore, ritorna almeno il compose senza x-casaos
        return this.removeXCasaosSection(this.app.compose_content)
      }
    }
  },
  methods: {
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
      } catch (error) {
        console.error('Error loading app details:', error)
      } finally {
        this.loading = false
      }
    },
    onDeploySuccess(result) {
      console.log('Deploy successful:', result)
      // Opzionale: redirect o notifica
    },
    onDeployError(error) {
      console.error('Deploy error:', error)
      // Opzionale: mostrar errore
    },
    async copyCompose() {
      try {
        await navigator.clipboard.writeText(this.cleanedCompose)
        this.copyMessage = true
        // Reset message after 2 seconds
        setTimeout(() => {
          this.copyMessage = false
        }, 2000)
      } catch (error) {
        console.error('Failed to copy:', error)
        alert('Failed to copy to clipboard')
      }
    },
    removeXCasaosSection(yaml) {
      /**
       * Rimuove la sezione x-casaos: e tutto il contenuto indentato
       * dal docker-compose.yml
       */
      const lines = yaml.split('\n')
      const filtered = []
      let skipUntilNextKey = false
      
      for (const line of lines) {
        // Se troviamo x-casaos al livello principale
        if (line.trim().startsWith('x-casaos:')) {
          skipUntilNextKey = true
          continue
        }
        
        // Se siamo in modalità skip (dentro x-casaos)
        if (skipUntilNextKey) {
          // Se la linea è una chiave al livello principale (non indentata)
          if (line && !line.startsWith(' ') && !line.startsWith('\t')) {
            skipUntilNextKey = false
            filtered.push(line)
            continue
          }
          // Se è una riga vuota, la saltiamo comunque
          if (!line.trim()) {
            continue
          }
          // Altrimenti continua a skippare
          continue
        }
        
        filtered.push(line)
      }
      
      return filtered.join('\n').trim()
    },
    normalizeCompose(yaml) {
      /**
       * Normalizza il docker-compose.yml per correggere errori comuni:
       * - Converte long syntax ports a short syntax: "port:port/protocol"
       * - Mantieni le porte già in short syntax come sono
       */
      try {
        // Usa regex per trovare e convertire i blocchi porta in long format
        // Pattern: - target: NUM\n  published: NUM\n  protocol: PROTO
        const portBlockRegex = /- target:\s*["']?(\d+)["']?\r?\n\s+published:\s*["']?(\d+)["']?\r?\n\s+protocol:\s*["']?(\w+)["']?(?:\r?\n)?/gm
        
        let replaced = yaml.replace(portBlockRegex, (match, target, published, protocol) => {
          // Se manca il protocol, usa tcp come default
          protocol = protocol || 'tcp'
          // Formato short: "target:published/protocol"
          return `- "${target}:${published}/${protocol}"\n`
        })
        
        return replaced.trim()
      } catch (error) {
        console.error('Error normalizing compose:', error)
        return yaml // Ritorna l'originale se c'è un errore
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
  padding: 1rem 0;
}

.loading,
.not-found {
  text-align: center;
  padding: 2rem;
  font-size: 1.1rem;
  color: var(--color-text-secondary);
}

.app-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
  background: var(--color-bg-secondary);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.app-icon {
  width: 200px;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.app-info {
  flex: 1;
}

.app-info h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.developer {
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
}

.category {
  display: inline-block;
  background: var(--color-primary);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.description {
  line-height: 1.6;
  color: var(--color-text-primary);
}

.screenshots {
  margin-bottom: 2rem;
}

.screenshots h2,
.deployment-section h2,
.metadata h2 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: var(--color-text-primary);
}

.screenshots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.screenshot-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.screenshot {
  width: 100%;
  max-height: 400px;
  object-fit: cover;
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.screenshot-wrapper:hover .screenshot {
  transform: scale(1.05);
}

.screenshot-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  border-radius: 8px;
}

.screenshot-wrapper:hover .screenshot-overlay {
  opacity: 1;
}

.magnifier {
  font-size: 2rem;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Lightbox */
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.lightbox-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-image {
  max-width: 85vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 8px;
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  color: white;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  font-size: 1.5rem;
  cursor: pointer;
  z-index: 10001;
  transition: all 0.2s ease;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.4);
  transform: scale(1.1);
}

.lightbox-prev,
.lightbox-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  color: white;
  width: 50px;
  height: 50px;
  border-radius: 4px;
  font-size: 1.5rem;
  cursor: pointer;
  z-index: 10000;
  transition: all 0.2s ease;
}

.lightbox-prev:hover,
.lightbox-next:hover {
  background: rgba(255, 255, 255, 0.4);
  transform: translateY(-50%) scale(1.1);
}

.lightbox-prev {
  left: 20px;
}

.lightbox-next {
  right: 20px;
}

.lightbox-counter {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.deployment-section {
  background: var(--color-bg-secondary);
  padding: 2rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  border: 1px solid var(--color-border);
}

.compose-section {
  background: var(--color-bg-secondary);
  padding: 2rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  border: 1px solid var(--color-border);
}

.compose-section h2 {
  color: var(--color-text-primary);
  margin-bottom: 0.5rem;
}

.text-muted {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}

.compose-container {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.compose-code {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 1.5rem;
  overflow-x: auto;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-text-primary);
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}

.compose-code code {
  color: var(--color-text-primary);
  word-break: break-word;
  white-space: pre-wrap;
}

.btn-copy {
  padding: 0.75rem 1.5rem;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  font-size: 1rem;
  transition: all 0.3s ease;
  align-self: flex-start;
}

.btn-copy:hover:not(.copied) {
  background: var(--color-primary-dark);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-copy.copied {
  background: var(--color-success);
  cursor: default;
}

.metadata {
  background: var(--color-bg-secondary);
  padding: 2rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  border: 1px solid var(--color-border);
}

.metadata p {
  margin-bottom: 0.75rem;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.metadata strong {
  color: var(--color-text-primary);
  font-weight: 600;
}

.btn-back {
  display: inline-block;
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  text-decoration: none;
  transition: background 0.2s;
  border: 1px solid var(--color-border);
}

.btn-back:hover {
  background: var(--color-border);
}
</style>
