import { createRouter, createWebHistory } from 'vue-router'
import NegotiationsListView from './views/NegotiationsListView.vue'
import SingleNegotiationView from './views/SingleNegotiationView.vue'
import ScenariosView from './views/ScenariosView.vue'
import NegotiatorsView from './views/NegotiatorsView.vue'
import TournamentsListView from './views/TournamentsListView.vue'
import SingleTournamentView from './views/SingleTournamentView.vue'
import ConfigsView from './views/ConfigsView.vue'

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
    path: '/tournaments/:tournamentId/negotiations',
    name: 'TournamentNegotiationsList',
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
  {
    path: '/configs',
    name: 'Configs',
    component: ConfigsView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
