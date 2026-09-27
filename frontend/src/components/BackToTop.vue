<template>
  <transition name="back-to-top">
    <button
      v-show="visible"
      type="button"
      class="back-to-top"
      :title="title"
      aria-label="Back to top"
      @click="scrollToTop"
    >
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 19V5m0 0-6 6m6-6 6 6" />
      </svg>
    </button>
  </transition>
</template>

<script>
export default {
  name: 'BackToTop',
  props: {
    threshold: {
      type: Number,
      default: 600
    },
    title: {
      type: String,
      default: 'Back to top'
    }
  },
  data() {
    return {
      visible: false
    }
  },
  mounted() {
    this.onScroll()
    window.addEventListener('scroll', this.onScroll, { passive: true })
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.onScroll)
  },
  methods: {
    onScroll() {
      this.visible = window.scrollY > this.threshold
    },
    scrollToTop() {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }
}
</script>

<style scoped>
.back-to-top {
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  z-index: 900;
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-glass);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  color: var(--color-text-primary);
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
}

.back-to-top:hover {
  transform: translateY(-3px);
  border-color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.back-to-top-enter-active,
.back-to-top-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}

.back-to-top-enter-from,
.back-to-top-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 560px) {
  .back-to-top {
    right: 1rem;
    bottom: 1rem;
  }
}
</style>
