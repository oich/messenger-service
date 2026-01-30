<template>
  <div class="chat-layout">
    <RoomList
      :rooms="rooms"
      :currentRoomId="currentRoomId"
      @select="selectRoom"
      @create="showCreateRoom = true"
    />
    <div class="chat-main">
      <div v-if="currentRoom" class="chat-header">
        <h3>{{ currentRoom.display_name }}</h3>
        <span v-if="currentRoom.room_type === 'entity'" class="chat-header-badge">
          {{ currentRoom.entity_type }} #{{ currentRoom.entity_id }}
        </span>
      </div>
      <div v-else class="chat-header">
        <h3>Messenger</h3>
      </div>
      <MessageArea
        :messages="messages"
        :loading="loading"
        :hasMore="hasMore"
        @load-more="loadMoreMessages"
      />
      <MessageCompose
        v-if="currentRoomId"
        @send="handleSend"
      />
    </div>

    <Dialog
      v-model:visible="showCreateRoom"
      header="Neuen Raum erstellen"
      modal
      :style="{ width: '400px' }"
    >
      <div class="flex flex-column gap-3">
        <div class="flex flex-column gap-1">
          <label>Name</label>
          <InputText v-model="newRoomName" placeholder="Raum-Name" />
        </div>
        <div class="flex flex-column gap-1">
          <label>Thema (optional)</label>
          <InputText v-model="newRoomTopic" placeholder="Thema" />
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showCreateRoom = false" />
        <Button label="Erstellen" @click="handleCreateRoom" :disabled="!newRoomName.trim()" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessenger } from '../../composables/useMessenger'
import { useSSE } from '../../composables/useSSE'
import RoomList from './RoomList.vue'
import MessageArea from './MessageArea.vue'
import MessageCompose from './MessageCompose.vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const toast = useToast()
const route = useRoute()
const {
  rooms,
  currentRoomId,
  currentRoom,
  messages,
  loading,
  hasMore,
  fetchRooms,
  selectRoom,
  sendMessage,
  createRoom,
  loadMoreMessages,
  addIncomingMessage,
} = useMessenger()

const showCreateRoom = ref(false)
const newRoomName = ref('')
const newRoomTopic = ref('')

const { connect } = useSSE((event) => {
  if (event.type === 'new_message') {
    addIncomingMessage({
      event_id: event.event_id,
      room_id: event.room_id,
      sender: event.sender,
      sender_display_name: event.sender_display_name,
      body: event.body,
      msg_type: 'm.text',
      timestamp: new Date().toISOString(),
    })
  }
  if (event.type === 'notification') {
    toast.add({
      severity: event.priority === 'urgent' ? 'error' : 'info',
      summary: `[${event.source_app}] ${event.title}`,
      detail: event.body,
      life: 5000,
    })
  }
})

async function handleSend(body) {
  try {
    await sendMessage(body)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Nachricht konnte nicht gesendet werden', life: 3000 })
  }
}

async function handleCreateRoom() {
  try {
    const room = await createRoom(newRoomName.value.trim(), newRoomTopic.value.trim() || null)
    showCreateRoom.value = false
    newRoomName.value = ''
    newRoomTopic.value = ''
    selectRoom(room.matrix_room_id)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Raum konnte nicht erstellt werden', life: 3000 })
  }
}

onMounted(async () => {
  await fetchRooms()
  connect()
  if (route.params.roomId) {
    selectRoom(route.params.roomId)
  } else if (rooms.value.length > 0) {
    selectRoom(rooms.value[0].matrix_room_id)
  }
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-section);
}

.chat-header h3 {
  margin: 0;
  font-size: 1rem;
}

.chat-header-badge {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-overlay);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}
</style>
