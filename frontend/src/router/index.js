import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/search' },
  { path: '/operations', name: 'Operations', component: () => import('../views/Operations.vue') },
  { path: '/downloads', component: () => import('../views/Home.vue') },
  { path: '/search', component: () => import('../views/Search.vue') },
  { path: '/genres', component: () => import('../views/Genres.vue') },
  { path: '/discovery/:type/:value', name: 'DiscoveryDetail', component: () => import('../views/DiscoveryDetail.vue') },
  { path: '/parse', component: () => import('../views/MagnetParse.vue') },
  { path: '/entities', name: 'Entities', component: () => import('../views/Entities.vue') },
  { path: '/subscription', component: () => import('../views/Subscription.vue') },
  { path: '/library-organize', name: 'LibraryOrganize', component: () => import('../views/LibraryOrganize.vue') },
  { path: '/library', redirect: { path: '/library-organize', query: { tab: 'check' } } },
  { path: '/logs', component: () => import('../views/Logs.vue') },
  { path: '/settings', component: () => import('../views/Config.vue') },
  { path: '/config', redirect: '/settings' },
  { path: '/actor/:name', component: () => import('../views/Actor.vue') },
  { path: '/favorites', component: () => import('../views/Favorites.vue') },
  { path: '/duplicates', name: 'Duplicates', redirect: { path: '/library-organize', query: { tab: 'duplicates' } } },
  { path: '/inventory', name: 'Inventory', redirect: { path: '/library-organize', query: { tab: 'inventory' } } },
  {
    path: '/inventory/actors/:id',
    name: 'InventoryActor',
    redirect: to => ({ path: '/library-organize', query: { tab: 'inventory', actor_id: to.params.id } })
  },
  { path: '/normalize', name: 'Normalize', redirect: { path: '/library-organize', query: { tab: 'mapping' } } },
  { path: '/translations', name: 'TranslationJobs', component: () => import('../views/TranslationJobs.vue') },
  { path: '/supplement', name: 'Supplement', component: () => import('../views/SupplementManagement.vue') },
  { path: '/tasks', redirect: '/downloads' },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
