import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import AppDetail from './views/AppDetail.vue'
import Settings from './views/Settings.vue'
import './styles/theme.css'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Home
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
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

createApp(App).use(router).mount('#app')
