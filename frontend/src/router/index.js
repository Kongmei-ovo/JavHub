import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Search from '../views/Search.vue'
import Genres from '../views/Genres.vue'
import MagnetParse from '../views/MagnetParse.vue'
import Subscription from '../views/Subscription.vue'
import Library from '../views/Library.vue'
import Logs from '../views/Logs.vue'
import Config from '../views/Config.vue'
import Actor from '../views/Actor.vue'
import Favorites from '../views/Favorites.vue'

const routes = [
  { path: '/', component: Genres },
  { path: '/downloads', component: Home },
  { path: '/search', component: Search },
  { path: '/genres', component: Genres },
  { path: '/genres/:categoryId', name: 'GenreDetail', component: () => import('../views/GenreDetail.vue') },
  { path: '/parse', component: MagnetParse },
  { path: '/subscription', component: Subscription },
  { path: '/library', component: Library },
  { path: '/logs', component: Logs },
  { path: '/settings', component: Config },
  { path: '/config', redirect: '/settings' },
  { path: '/actor/:name', component: Actor },
  { path: '/favorites', component: Favorites },
  { path: '/missing', name: 'Missing', component: () => import('../views/Missing.vue') },
  { path: '/missing/:id', name: 'MissingDetail', component: () => import('../views/MissingDetail.vue') },
  { path: '/duplicates', name: 'Duplicates', component: () => import('../views/Duplicates.vue') },
  { path: '/tasks', redirect: '/downloads' },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
