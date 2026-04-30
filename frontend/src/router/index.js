import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('../views/Genres.vue') },
  { path: '/downloads', component: () => import('../views/Home.vue') },
  { path: '/search', component: () => import('../views/Search.vue') },
  { path: '/genres', component: () => import('../views/Genres.vue') },
  { path: '/discovery/:type/:value', name: 'DiscoveryDetail', component: () => import('../views/DiscoveryDetail.vue') },
  { path: '/parse', component: () => import('../views/MagnetParse.vue') },
  { path: '/subscription', component: () => import('../views/Subscription.vue') },
  { path: '/library', component: () => import('../views/Library.vue') },
  { path: '/logs', component: () => import('../views/Logs.vue') },
  { path: '/settings', component: () => import('../views/Config.vue') },
  { path: '/config', redirect: '/settings' },
  { path: '/actor/:name', component: () => import('../views/Actor.vue') },
  { path: '/favorites', component: () => import('../views/Favorites.vue') },
  { path: '/duplicates', name: 'Duplicates', component: () => import('../views/Duplicates.vue') },
  { path: '/inventory', name: 'Inventory', component: () => import('../views/Inventory.vue') },
  { path: '/inventory/actors/:id', name: 'InventoryActor', component: () => import('../views/InventoryActor.vue') },
  { path: '/normalize', name: 'Normalize', component: () => import('../views/Normalize.vue') },
  { path: '/tasks', redirect: '/downloads' },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
