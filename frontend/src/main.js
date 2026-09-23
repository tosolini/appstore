import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import AppDetail from './views/AppDetail.vue'
import Settings from './views/Settings.vue'
import GitHubImports from './views/GitHubImports.vue'
import NewApps from './views/NewApps.vue'
import imageFallback from './directives/imageFallback'
import './styles/theme.css'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Home
    },
    {
        path: '/new',
        name: 'NewApps',
        component: NewApps
    },
    {
        path: '/app/:id',
        name: 'AppDetail',
        component: AppDetail
    },
    {
        path: '/settings',
        name: 'Settings',
        component: Settings
    },
    {
        path: '/imports/github',
        name: 'GitHubImports',
        component: GitHubImports
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

const app = createApp(App)
app.use(router)
app.directive('img-fallback', imageFallback)
app.mount('#app')
