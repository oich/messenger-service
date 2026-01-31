<template>
  <div class="chat-layout">
    <RoomList
      :rooms="rooms"
      :currentRoomId="currentRoomId"
      :currentUser="currentUser"
      @select="handleSelectRoom"
      @create="openCreateRoom"
      @new-message="showNewMessage = true"
      @open-external-client="showExternalClient = true"
    />
    <div class="chat-main">
      <div v-if="currentRoom" class="chat-header">
        <div class="chat-header-left">
          <h3>{{ currentRoom.display_name }}</h3>
          <span v-if="currentRoom.room_type === 'entity'" class="chat-header-badge">
            {{ currentRoom.entity_type }} #{{ currentRoom.entity_id }}
          </span>
        </div>
        <div class="chat-header-right">
          <div class="member-avatars" v-if="roomMembers.length > 0" @click="showMemberList = true">
            <span
              v-for="member in roomMembers.slice(0, 5)"
              :key="member.matrix_user_id"
              class="member-avatar"
              :title="member.display_name"
            >{{ memberInitials(member) }}</span>
            <span v-if="roomMembers.length > 5" class="member-avatar member-more">
              +{{ roomMembers.length - 5 }}
            </span>
          </div>
          <button
            v-if="currentRoom.room_type !== 'dm'"
            class="header-action-btn"
            @click="openInviteDialog"
            title="Mitglied hinzufuegen"
          >
            <i class="pi pi-user-plus"></i>
          </button>
        </div>
      </div>
      <div v-else class="chat-header">
        <div class="chat-header-left"><h3>Messenger</h3></div>
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

    <!-- Create Room Dialog -->
    <Dialog
      v-model:visible="showCreateRoom"
      header="Neuen Raum erstellen"
      modal
      :style="{ width: '480px' }"
      @hide="resetCreateRoom"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label>Name</label>
          <InputText v-model="newRoomName" placeholder="Raum-Name" class="w-full" />
        </div>
        <div class="form-field">
          <label>Thema (optional)</label>
          <InputText v-model="newRoomTopic" placeholder="Thema" class="w-full" />
        </div>
        <div class="form-field">
          <label>Mitglieder einladen</label>
          <div class="invite-area">
            <div class="invite-chips">
              <span v-for="user in newRoomInvites" :key="user.hub_user_id" class="invite-chip">
                {{ user.display_name || user.hub_user_id }}
                <button class="chip-remove" @click="removeNewRoomInvite(user)">
                  <i class="pi pi-times"></i>
                </button>
              </span>
              <input
                v-model="newRoomUserSearch"
                type="text"
                class="invite-input"
                placeholder="Nutzer suchen..."
                @input="onNewRoomUserSearch"
                @focus="newRoomShowSuggestions = true"
                ref="newRoomSearchRef"
              />
            </div>
            <div v-if="newRoomShowSuggestions && newRoomFilteredUsers.length > 0" class="user-suggestions">
              <div
                v-for="user in newRoomFilteredUsers"
                :key="user.hub_user_id"
                class="suggestion-item"
                @mousedown.prevent="addNewRoomInvite(user)"
              >
                <i class="pi pi-user"></i>
                <span>{{ user.display_name || user.hub_user_id }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showCreateRoom = false" />
        <Button label="Erstellen" @click="handleCreateRoom" :disabled="!newRoomName.trim()" />
      </template>
    </Dialog>

    <!-- Invite to Room Dialog -->
    <Dialog
      v-model:visible="showInviteDialog"
      header="Mitglied hinzufuegen"
      modal
      :style="{ width: '400px' }"
      @hide="resetInvite"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label>Nutzer suchen</label>
          <div class="invite-area">
            <input
              v-model="inviteSearch"
              type="text"
              class="invite-input-solo"
              placeholder="Name oder ID..."
              @input="onInviteSearch"
              @focus="inviteShowSuggestions = true"
              ref="inviteSearchRef"
            />
            <div v-if="inviteShowSuggestions && inviteFilteredUsers.length > 0" class="user-suggestions">
              <div
                v-for="user in inviteFilteredUsers"
                :key="user.hub_user_id"
                class="suggestion-item"
                @mousedown.prevent="handleInviteUser(user)"
              >
                <i class="pi pi-user"></i>
                <span>{{ user.display_name || user.hub_user_id }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Dialog>

    <!-- Member List Dialog -->
    <Dialog
      v-model:visible="showMemberList"
      header="Raum-Mitglieder"
      modal
      :style="{ width: '360px' }"
    >
      <div class="member-list">
        <div v-for="member in roomMembers" :key="member.matrix_user_id" class="member-item">
          <span class="member-avatar-lg">{{ memberInitials(member) }}</span>
          <div class="member-info">
            <span class="member-name">{{ member.display_name }}</span>
            <span v-if="member.hub_user_id" class="member-id">{{ member.hub_user_id }}</span>
          </div>
        </div>
        <div v-if="roomMembers.length === 0" class="member-empty">
          Keine Mitglieder gefunden
        </div>
      </div>
    </Dialog>

    <NewMessageDialog
      v-model="showNewMessage"
      @send="handleNewMessage"
    />

    <ExternalClientDialog v-model="showExternalClient" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessenger } from '../../composables/useMessenger'
import { useSSE } from '../../composables/useSSE'
import RoomList from './RoomList.vue'
import MessageArea from './MessageArea.vue'
import MessageCompose from './MessageCompose.vue'
import NewMessageDialog from './NewMessageDialog.vue'
import ExternalClientDialog from './ExternalClientDialog.vue'
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
  inviteToRoom,
  fetchRoomMembers,
} = useMessenger()

// --- Room members ---
const roomMembers = ref([])
const showMemberList = ref(false)

async function loadRoomMembers(roomId) {
  if (!roomId) { roomMembers.value = []; return }
  roomMembers.value = await fetchRoomMembers(roomId)
}

function memberInitials(member) {
  const name = member.display_name || '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

// --- Create room ---
const showCreateRoom = ref(false)
const newRoomName = ref('')
const newRoomTopic = ref('')
const newRoomInvites = ref([])
const newRoomUserSearch = ref('')
const newRoomShowSuggestions = ref(false)
const newRoomSearchRef = ref(null)
const allUsers = ref([])

const newRoomFilteredUsers = computed(() => {
  const selectedIds = new Set(newRoomInvites.value.map(u => u.hub_user_id))
  if (currentUser.value) selectedIds.add(currentUser.value.hub_user_id)
  let users = allUsers.value.filter(u => !selectedIds.has(u.hub_user_id))
  if (newRoomUserSearch.value.trim()) {
    const q = newRoomUserSearch.value.toLowerCase()
    users = users.filter(u =>
      (u.display_name || '').toLowerCase().includes(q) ||
      u.hub_user_id.toLowerCase().includes(q)
    )
  }
  return users.slice(0, 10)
})

async function loadAllUsers() {
  if (allUsers.value.length === 0) {
    allUsers.value = await fetchUsers()
  }
}

function onNewRoomUserSearch() {
  newRoomShowSuggestions.value = true
  loadAllUsers()
}

function addNewRoomInvite(user) {
  if (!newRoomInvites.value.some(u => u.hub_user_id === user.hub_user_id)) {
    newRoomInvites.value.push(user)
  }
  newRoomUserSearch.value = ''
  newRoomShowSuggestions.value = false
}

function removeNewRoomInvite(user) {
  newRoomInvites.value = newRoomInvites.value.filter(u => u.hub_user_id !== user.hub_user_id)
}

function openCreateRoom() {
  loadAllUsers()
  showCreateRoom.value = true
}

function resetCreateRoom() {
  newRoomName.value = ''
  newRoomTopic.value = ''
  newRoomInvites.value = []
  newRoomUserSearch.value = ''
  newRoomShowSuggestions.value = false
}

// --- Invite to existing room ---
const showInviteDialog = ref(false)
const inviteSearch = ref('')
const inviteShowSuggestions = ref(false)
const inviteSearchRef = ref(null)

const inviteFilteredUsers = computed(() => {
  const memberIds = new Set(roomMembers.value.map(m => m.hub_user_id).filter(Boolean))
  let users = allUsers.value.filter(u => !memberIds.has(u.hub_user_id))
  if (inviteSearch.value.trim()) {
    const q = inviteSearch.value.toLowerCase()
    users = users.filter(u =>
      (u.display_name || '').toLowerCase().includes(q) ||
      u.hub_user_id.toLowerCase().includes(q)
    )
  }
  return users.slice(0, 10)
})

function openInviteDialog() {
  loadAllUsers()
  showInviteDialog.value = true
}

function onInviteSearch() {
  inviteShowSuggestions.value = true
  loadAllUsers()
}

function resetInvite() {
  inviteSearch.value = ''
  inviteShowSuggestions.value = false
}

async function handleInviteUser(user) {
  if (!currentRoomId.value) return
  try {
    await inviteToRoom(currentRoomId.value, user.hub_user_id)
    toast.add({ severity: 'success', summary: 'Eingeladen', detail: `${user.display_name || user.hub_user_id} wurde hinzugefuegt`, life: 3000 })
    showInviteDialog.value = false
    await loadRoomMembers(currentRoomId.value)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Nutzer konnte nicht eingeladen werden', life: 3000 })
  }
}

// --- New message ---
const showNewMessage = ref(false)

// --- External client ---
const showExternalClient = ref(false)

// --- Notifications ---
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

// --- SSE ---
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

// --- Handlers ---
async function handleSelectRoom(roomId) {
  selectRoom(roomId)
  loadRoomMembers(roomId)
}

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
    const inviteIds = newRoomInvites.value.map(u => u.matrix_user_id).filter(Boolean)
    const room = await createRoom(
      newRoomName.value.trim(),
      newRoomTopic.value.trim() || null,
      inviteIds.length > 0 ? inviteIds : null,
    )
    showCreateRoom.value = false
    resetCreateRoom()
    selectRoom(room.matrix_room_id)
    loadRoomMembers(room.matrix_room_id)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Raum konnte nicht erstellt werden', life: 3000 })
  }
}

async function handleNewMessage({ recipients, groupName, message, file }) {
  try {
    let room
    if (recipients.length === 1) {
      room = await createDM(recipients[0].hub_user_id)
    } else {
      const inviteIds = recipients.map(u => u.matrix_user_id).filter(Boolean)
      room = await createRoom(
        groupName || recipients.map(u => u.display_name || u.hub_user_id).join(', '),
        null,
        inviteIds,
      )
    }

    selectRoom(room.matrix_room_id)
    loadRoomMembers(room.matrix_room_id)

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
    handleSelectRoom(route.params.roomId)
  } else if (rooms.value.length > 0) {
    handleSelectRoom(rooms.value[0].matrix_room_id)
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
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-section);
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.chat-header-left h3 {
  margin: 0;
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.chat-header-badge {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-overlay);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

/* Member avatars in header */
.member-avatars {
  display: flex;
  cursor: pointer;
}

.member-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--primary-100, #e0e7ff);
  color: var(--primary-700, #4338ca);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
  border: 2px solid var(--surface-section);
  margin-left: -8px;
}

.member-avatar:first-child {
  margin-left: 0;
}

.member-more {
  background: var(--surface-200, #e5e7eb);
  color: var(--text-color-secondary);
  font-size: 0.55rem;
}

.header-action-btn {
  background: none;
  border: 1px solid var(--surface-border);
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
  display: flex;
  align-items: center;
  font-size: 0.9rem;
  transition: all 0.15s;
}

.header-action-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: var(--primary-50, rgba(59, 130, 246, 0.05));
}

/* Dialog form styles */
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.form-field label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.invite-area {
  position: relative;
}

.invite-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-ground);
  min-height: 38px;
  align-items: center;
}

.invite-chips:focus-within {
  border-color: var(--primary-color);
}

.invite-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--primary-color);
  color: #fff;
  font-size: 0.8rem;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
}

.chip-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  padding: 0;
  font-size: 0.7rem;
  display: flex;
  align-items: center;
}

.chip-remove:hover {
  color: #fff;
}

.invite-input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.85rem;
  color: var(--text-color);
  flex: 1;
  min-width: 100px;
  padding: 0.1rem 0;
}

.invite-input::placeholder {
  color: var(--text-color-secondary);
}

.invite-input-solo {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-ground);
  font-size: 0.85rem;
  color: var(--text-color);
  outline: none;
  box-sizing: border-box;
}

.invite-input-solo:focus {
  border-color: var(--primary-color);
}

.user-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  margin-top: 2px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.1s;
}

.suggestion-item:hover {
  background: var(--surface-hover);
}

.suggestion-item i {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

/* Member list dialog */
.member-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0;
}

.member-avatar-lg {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-100, #e0e7ff);
  color: var(--primary-700, #4338ca);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.member-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.member-name {
  font-size: 0.875rem;
  font-weight: 500;
}

.member-id {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.member-empty {
  text-align: center;
  color: var(--text-color-secondary);
  padding: 1rem;
  font-size: 0.875rem;
}
</style>
