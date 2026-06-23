import { createRouter, createWebHistory } from 'vue-router'

const supplementPanelRedirect = (tab) => (to) => ({
  path: '/supplement',
  query: { ...to.query, tab },
})

const routes = [
  { path: '/', name: 'Today', component: () => import('../views/Today.vue') },
  { path: '/today', redirect: '/' },
  { path: '/downloads', name: 'Downloads', component: () => import('../views/Downloads.vue') },
  { path: '/candidates', name: 'Candidates', component: () => import('../views/Candidates.vue') },
  { path: '/search', component: () => import('../views/Search.vue') },
  { path: '/watch/:movieId', name: 'Watch', component: () => import('../views/Watch.vue') },
  { path: '/discovery/:type/:value', name: 'DiscoveryDetail', component: () => import('../views/DiscoveryDetail.vue') },
  { path: '/parse', redirect: '/downloads' },
  { path: '/entities', name: 'Entities', component: () => import('../views/Entities.vue') },
  { path: '/subscription', component: () => import('../views/Subscription.vue') },
  { path: '/library', redirect: '/search' },
  { path: '/logs', redirect: (to) => ({ path: '/operations', query: { ...to.query, tab: 'logs' } }) },
  { path: '/settings', component: () => import('../views/Config.vue') },
  { path: '/config', redirect: '/settings' },
  { path: '/actor/:name', component: () => import('../views/Actor.vue') },
  { path: '/favorites', component: () => import('../views/Favorites.vue') },
  { path: '/translations', name: 'TranslationJobs', component: () => import('../views/TranslationJobs.vue') },
  { path: '/drive', name: 'Drive115', component: () => import('../views/Drive115.vue') },
  { path: '/operations', name: 'SystemMonitor', component: () => import('../views/SystemMonitor.vue') },
  { path: '/system-jobs', name: 'SystemJobs', component: () => import('../views/SystemJobs.vue') },
  { path: '/supplement', name: 'Supplement', component: () => import('../views/SupplementManagement.vue') },
  { path: '/supplement/movies', redirect: supplementPanelRedirect('movies') },
  { path: '/supplement/jobs', redirect: supplementPanelRedirect('jobs') },
  { path: '/supplement/sources', redirect: supplementPanelRedirect('sources') },
  { path: '/supplement/stats', redirect: supplementPanelRedirect('stats') },
  { path: '/tasks', redirect: '/downloads' },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
