import { createRouter, createWebHistory } from 'vue-router'
import NegotiationsListView from './views/NegotiationsListView.vue'
import SingleNegotiationView from './views/SingleNegotiationView.vue'
import ScenariosView from './views/ScenariosView.vue'
import NegotiatorsView from './views/NegotiatorsView.vue'
import TournamentsListView from './views/TournamentsListView.vue'
import SingleTournamentView from './views/SingleTournamentView.vue'

const routes = [
  {
    path: '/',
    redirect: '/negotiations',
  },
  {
    path: '/negotiations',
    name: 'NegotiationsList',
    component: NegotiationsListView,
  },
  {
    path: '/negotiations/:id',
    name: 'SingleNegotiation',
    component: SingleNegotiationView,
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
    name: 'TournamentsList',
    component: TournamentsListView,
  },
  {
    path: '/tournaments/:id',
    name: 'SingleTournament',
    component: SingleTournamentView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
