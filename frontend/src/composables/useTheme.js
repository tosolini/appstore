import { ref, watch, onMounted } from 'vue'

const currentTheme = ref('light')

export function useTheme() {
    const setTheme = (theme) => {
        currentTheme.value = theme
        document.documentElement.setAttribute('data-theme', theme)
        localStorage.setItem('appstore-theme', theme)

        // Aggiorna meta theme-color per mobile
        const metaThemeColor = document.querySelector('meta[name="theme-color"]')
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', theme === 'dark' ? '#1a1a1a' : '#667eea')
        }
    }

    const toggleTheme = () => {
        const newTheme = currentTheme.value === 'light' ? 'dark' : 'light'
        setTheme(newTheme)
    }

    onMounted(() => {
        // Carica tema dal localStorage o usa preferenza di sistema
        const saved = localStorage.getItem('appstore-theme')
        if (saved) {
            setTheme(saved)
        } else {
            // Controlla preferenza di sistema
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
            setTheme(prefersDark ? 'dark' : 'light')
        }
    })

    return {
        currentTheme,
        setTheme,
        toggleTheme
    }
}
