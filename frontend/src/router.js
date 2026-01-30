import { createRouter, createWebHistory } from 'vue-router'
import ChatView from './components/chat/ChatView.vue'

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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
