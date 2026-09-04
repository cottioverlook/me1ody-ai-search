import { createRouter, createWebHistory } from 'vue-router'
import SearchHome from '../components/SearchHome.vue'

const ConversationView = () => import('../components/ConversationView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: SearchHome },
    { path: '/search/:id?', component: ConversationView },
    { path: '/share/:shareId', component: ConversationView },
  ],
})

export default router
