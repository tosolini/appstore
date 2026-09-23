<template>
  <div class="app-card reveal">
    <span v-if="isNew" class="new-badge" title="New since the previous version">NEW</span>

    <button
      class="fav-btn"
      :class="{ favorited: isFavorite }"
      @click="$emit('toggle-favorite', app.app_id)"
      :title="isFavorite ? 'Remove from My List' : 'Add to My List'"
      :aria-label="isFavorite ? 'Remove from My List' : 'Add to My List'"
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
</template>

<script>
export default {
  name: 'AppCard',
  props: {
    app: {
      type: Object,
      required: true
    },
    isNew: {
      type: Boolean,
      default: false
    },
    isFavorite: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle-favorite'],
  methods: {
    truncate(text, length) {
      if (!text) return ''
      if (text.length <= length) return text
      return text.substring(0, length) + '…'
    }
  }
}
</script>

<style scoped>
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

.new-badge {
  position: absolute;
  top: 0.85rem;
  left: 0.85rem;
  z-index: 2;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #fff;
  background: linear-gradient(135deg, var(--color-accent), var(--color-primary));
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
</style>
