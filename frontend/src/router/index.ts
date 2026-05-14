import { createRouter, createWebHistory } from 'vue-router'
import SearchHome from '../components/SearchHome.vue'
import ConversationView from '../components/ConversationView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: SearchHome },
    { path: '/search/:id?', component: ConversationView },
  ],
})

export default router
