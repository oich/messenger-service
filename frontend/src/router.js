import { createRouter, createWebHistory } from 'vue-router'
import ChatView from './components/chat/ChatView.vue'
import AdminPanel from './components/admin/AdminPanel.vue'

const routes = [
  {
    path: '/',
    name: 'chat',
    component: ChatView,
  },
  {
    path: '/room/:roomId',
    name: 'room',
    component: ChatView,
    props: true,
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminPanel,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
