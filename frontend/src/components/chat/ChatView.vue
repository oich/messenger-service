<template>
  <div class="chat-layout">
    <RoomList
      :rooms="rooms"
      :currentRoomId="currentRoomId"
      :currentUser="currentUser"
      @select="selectRoom"
      @create="showCreateRoom = true"
      @new-message="showNewMessage = true"
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
        :currentUserMatrixId="currentUser?.matrix_user_id"
        @load-more="loadMoreMessages"
      />
      <MessageCompose
        v-if="currentRoomId"
        @send="handleSend"
        @upload="handleUpload"
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

    <NewMessageDialog
      v-model="showNewMessage"
      @send="handleNewMessage"
    />
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
import NewMessageDialog from './NewMessageDialog.vue'
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
  currentUser,
  messages,
  loading,
  hasMore,
  fetchCurrentUser,
  fetchRooms,
  selectRoom,
  sendMessage,
  uploadFile,
  createRoom,
  createDM,
  fetchUsers,
  loadMoreMessages,
  addIncomingMessage,
} = useMessenger()

const showCreateRoom = ref(false)
const newRoomName = ref('')
const newRoomTopic = ref('')
const showNewMessage = ref(false)

function showBrowserNotification(event) {
  if (Notification.permission !== 'granted') return
  if (!document.hidden) return
  if (event.sender === currentUser.value?.matrix_user_id) return

  const senderName = event.sender_display_name || event.sender || 'Neue Nachricht'
  const body = event.msg_type === 'm.image' ? 'Bild gesendet'
    : event.msg_type === 'm.file' ? 'Datei gesendet'
    : event.body || ''

  const notification = new Notification(senderName, {
    body,
    tag: event.event_id,
    icon: '/favicon.ico',
  })

  notification.onclick = () => {
    window.focus()
    if (event.room_id) selectRoom(event.room_id)
    notification.close()
  }
}

const { connect } = useSSE((event) => {
  if (event.type === 'new_message') {
    addIncomingMessage({
      event_id: event.event_id,
      room_id: event.room_id,
      sender: event.sender,
      sender_display_name: event.sender_display_name,
      body: event.body,
      msg_type: event.msg_type || 'm.text',
      timestamp: new Date().toISOString(),
      file_url: event.file_url || null,
      filename: event.filename || null,
      file_size: event.file_size || null,
    })
    showBrowserNotification(event)
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

async function handleUpload({ file, body }) {
  if (!currentRoomId.value) return
  try {
    await uploadFile(currentRoomId.value, file, body)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Datei konnte nicht hochgeladen werden', life: 3000 })
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

async function handleNewMessage({ recipients, groupName, message, file }) {
  try {
    let room
    if (recipients.length === 1) {
      // DM
      room = await createDM(recipients[0].hub_user_id)
    } else {
      // Group — create room with all recipients
      const inviteIds = recipients.map(u => u.matrix_user_id).filter(Boolean)
      room = await createRoom(
        groupName || recipients.map(u => u.display_name || u.hub_user_id).join(', '),
        null,
        inviteIds,
      )
    }

    selectRoom(room.matrix_room_id)

    // Send the first message
    if (file) {
      await uploadFile(room.matrix_room_id, file, message)
    } else if (message) {
      await sendMessage(message)
    }
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Nachricht konnte nicht gesendet werden', life: 3000 })
  }
}

onMounted(async () => {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }

  await Promise.all([fetchCurrentUser(), fetchRooms()])
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
