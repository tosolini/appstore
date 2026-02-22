import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
    plugins: [vue()],
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
    },
    server: {
        proxy: {
            '/api': 'http://localhost:8888',
            '/apps': 'http://localhost:8888'
        }
    }
})
