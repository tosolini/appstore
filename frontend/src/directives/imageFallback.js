export const IMAGE_PLACEHOLDER =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1c2536"/>
      <stop offset="1" stop-color="#0b101d"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="44" fill="url(#bg)"/>
  <g fill="none" stroke="#55607a" stroke-width="13" stroke-linecap="round" stroke-linejoin="round">
    <rect x="52" y="70" width="152" height="116" rx="16"/>
    <path d="M52 150l40-40 30 30 26-26 56 54"/>
    <circle cx="124" cy="110" r="11"/>
  </g>
  <path d="M88 78l80 100M168 78L88 178" stroke="#f87171" stroke-width="13" stroke-linecap="round" opacity="0.85"/>
</svg>`)

export default {
  mounted(el, binding) {
    el.addEventListener('error', function handler() {
      if (el.dataset.imgFallback === '1') return
      el.dataset.imgFallback = '1'
      el.src = binding.value || IMAGE_PLACEHOLDER
      el.removeEventListener('error', handler)
    })
  }
}