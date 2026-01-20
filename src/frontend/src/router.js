import { createRouter, createWebHistory } from 'vue-router'
import NegotiationsView from './views/NegotiationsView.vue'
import ScenariosView from './views/ScenariosView.vue'
import NegotiatorsView from './views/NegotiatorsView.vue'
import TournamentsView from './views/TournamentsView.vue'

const routes = [
  {
    path: '/',
    redirect: '/negotiations',
  },
  {
    path: '/negotiations',
    name: 'negotiations',
    component: NegotiationsView,
  },
  {
    path: '/scenarios',
    name: 'scenarios',
    component: ScenariosView,
  },
  {
    path: '/negotiators',
    name: 'negotiators',
    component: NegotiatorsView,
  },
  {
    path: '/tournaments',
    name: 'tournaments',
    component: TournamentsView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
