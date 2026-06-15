import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Today', component: () => import('../views/Today.vue') },
  { path: '/today', redirect: '/' },
  { path: '/downloads', name: 'Downloads', component: () => import('../views/Downloads.vue') },
  { path: '/candidates', name: 'Candidates', component: () => import('../views/Candidates.vue') },
  { path: '/search', component: () => import('../views/Search.vue') },
  { path: '/watch/:movieId', name: 'Watch', component: () => import('../views/Watch.vue') },
  { path: '/genres', component: () => import('../views/Genres.vue') },
  { path: '/discovery/:type/:value', name: 'DiscoveryDetail', component: () => import('../views/DiscoveryDetail.vue') },
  { path: '/parse', component: () => import('../views/MagnetParse.vue') },
  { path: '/entities', name: 'Entities', component: () => import('../views/Entities.vue') },
  { path: '/subscription', component: () => import('../views/Subscription.vue') },
  { path: '/library', redirect: '/search' },
  { path: '/logs', component: () => import('../views/Logs.vue') },
  { path: '/settings', component: () => import('../views/Config.vue') },
  { path: '/config', redirect: '/settings' },
  { path: '/actor/:name', component: () => import('../views/Actor.vue') },
  { path: '/favorites', component: () => import('../views/Favorites.vue') },
  { path: '/translations', name: 'TranslationJobs', component: () => import('../views/TranslationJobs.vue') },
  { path: '/tasks', redirect: '/downloads' },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
