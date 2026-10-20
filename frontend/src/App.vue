<template>
  <!-- Chat layout fills the content area (room list + messages scroll inside) -->
  <HubAppShell
    app-name="Messenger"
    :menu="menuItems"
    :user="currentUser?.display_name || currentUser?.hub_user_id || ''"
    :full-height="isChat"
    :flush="isChat"
    show-feedback
    :show-logout="false"
    @feedback="feedbackVisible = true"
  >
    <router-view />
    <FeedbackDialog v-model:visible="feedbackVisible" />
  </HubAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { HubAppShell } from '@hub/ui'
import FeedbackDialog from './components/chat/FeedbackDialog.vue'
import { useMessenger } from './composables/useMessenger'

const { currentUser, fetchCurrentUser } = useMessenger()
const feedbackVisible = ref(false)
const route = useRoute()
// The chat view loads the user too; other pages (admin, info) need it for the menu
onMounted(() => { if (!currentUser.value) fetchCurrentUser() })
const isChat = computed(() => route.name === 'chat' || route.name === 'room')

// `to` lets the shell highlight the active page (docs/ui-designsystem-konzept.md 4)
const menuItems = computed(() => [
  { label: 'Chat', icon: 'pi pi-comments', to: '/', match: '/room' },
  { label: 'Admin', icon: 'pi pi-cog', to: '/admin', visible: currentUser.value?.role === 'admin' },
  { label: 'Info', icon: 'pi pi-info-circle', to: '/info' },
])
</script>
