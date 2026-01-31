<template>
  <Dialog
    v-model:visible="visible"
    header="Neue Nachricht"
    modal
    :style="{ width: '520px' }"
    :closable="true"
    @hide="resetForm"
  >
    <div class="new-msg-form">
      <!-- Recipient field -->
      <div class="form-field">
        <label>Empfaenger</label>
        <div class="recipient-area">
          <div class="recipient-chips">
            <span
              v-for="user in selectedUsers"
              :key="user.hub_user_id"
              class="recipient-chip"
            >
              {{ user.display_name || user.hub_user_id }}
              <button class="chip-remove" @click="removeRecipient(user)">
                <i class="pi pi-times"></i>
              </button>
            </span>
            <input
              v-model="userSearch"
              type="text"
              class="recipient-input"
              placeholder="Nutzer suchen..."
              @input="onUserSearch"
              @focus="showSuggestions = true"
              ref="recipientInputRef"
            />
          </div>
          <div v-if="showSuggestions && filteredUsers.length > 0" class="user-suggestions">
            <div
              v-for="user in filteredUsers"
              :key="user.hub_user_id"
              class="suggestion-item"
              @mousedown.prevent="addRecipient(user)"
            >
              <i class="pi pi-user"></i>
              <span>{{ user.display_name || user.hub_user_id }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Room name for groups -->
      <div v-if="selectedUsers.length > 1" class="form-field">
        <label>Gruppenname (optional)</label>
        <input
          v-model="groupName"
          type="text"
          class="form-input"
          placeholder="Name der Gruppe..."
        />
      </div>

      <!-- Message field -->
      <div class="form-field">
        <label>Nachricht</label>
        <div class="msg-compose-area">
          <textarea
            ref="msgTextareaRef"
            v-model="messageText"
            class="msg-textarea"
            placeholder="Nachricht schreiben..."
            rows="4"
            @keydown="onKeydown"
          ></textarea>
          <div class="msg-actions">
            <div class="emoji-container">
              <button class="msg-action-btn" @click="toggleEmojiPicker" title="Emoji">
                <i class="pi pi-face-smile"></i>
              </button>
              <div v-if="showEmojiPicker" class="emoji-popover" ref="emojiPopoverRef">
                <EmojiPicker @select="insertEmoji" />
              </div>
            </div>
            <button class="msg-action-btn" @click="triggerFileInput" title="Datei anhaengen">
              <i class="pi pi-paperclip"></i>
            </button>
            <input
              ref="fileInputRef"
              type="file"
              class="hidden-file-input"
              @change="onFileSelect"
            />
          </div>
        </div>
      </div>

      <!-- File preview -->
      <div v-if="filePreview" class="file-preview">
        <div class="file-preview-item">
          <img v-if="filePreview.isImage" :src="filePreview.url" class="file-preview-img" />
          <div v-else class="file-preview-icon">
            <i class="pi pi-file"></i>
          </div>
          <span class="file-preview-name">{{ filePreview.name }}</span>
          <button class="file-preview-remove" @click="removeFile">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="visible = false" />
      <Button
        label="Senden"
        icon="pi pi-send"
        @click="handleSend"
        :disabled="!canSend"
        :loading="sending"
      />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import EmojiPicker from './EmojiPicker.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'send'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const userSearch = ref('')
const selectedUsers = ref([])
const allUsers = ref([])
const showSuggestions = ref(false)
const groupName = ref('')
const messageText = ref('')
const selectedFile = ref(null)
const filePreview = ref(null)
const showEmojiPicker = ref(false)
const sending = ref(false)
const recipientInputRef = ref(null)
const msgTextareaRef = ref(null)
const fileInputRef = ref(null)
const emojiPopoverRef = ref(null)

let searchTimeout = null

const filteredUsers = computed(() => {
  const selectedIds = new Set(selectedUsers.value.map(u => u.hub_user_id))
  let users = allUsers.value.filter(u => !selectedIds.has(u.hub_user_id))
  if (userSearch.value.trim()) {
    const q = userSearch.value.toLowerCase()
    users = users.filter(u =>
      (u.display_name || '').toLowerCase().includes(q) ||
      u.hub_user_id.toLowerCase().includes(q)
    )
  }
  return users.slice(0, 10)
})

const canSend = computed(() =>
  selectedUsers.value.length > 0 && (messageText.value.trim() || selectedFile.value)
)

function onUserSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    showSuggestions.value = true
    if (allUsers.value.length === 0) {
      await loadUsers()
    }
  }, 200)
}

async function loadUsers() {
  try {
    const api = (await import('../../api')).default
    const { data } = await api.get('/api/v1/users')
    allUsers.value = data
  } catch {
    allUsers.value = []
  }
}

function addRecipient(user) {
  if (!selectedUsers.value.some(u => u.hub_user_id === user.hub_user_id)) {
    selectedUsers.value.push(user)
  }
  userSearch.value = ''
  showSuggestions.value = false
  recipientInputRef.value?.focus()
}

function removeRecipient(user) {
  selectedUsers.value = selectedUsers.value.filter(u => u.hub_user_id !== user.hub_user_id)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

async function handleSend() {
  if (!canSend.value || sending.value) return
  sending.value = true
  try {
    emit('send', {
      recipients: selectedUsers.value,
      groupName: groupName.value.trim() || null,
      message: messageText.value.trim(),
      file: selectedFile.value,
    })
    visible.value = false
  } finally {
    sending.value = false
  }
}

function toggleEmojiPicker() {
  showEmojiPicker.value = !showEmojiPicker.value
}

function insertEmoji(emoji) {
  const el = msgTextareaRef.value
  if (el) {
    const start = el.selectionStart
    const end = el.selectionEnd
    messageText.value = messageText.value.slice(0, start) + emoji + messageText.value.slice(end)
    nextTick(() => {
      el.selectionStart = el.selectionEnd = start + emoji.length
      el.focus()
    })
  } else {
    messageText.value += emoji
  }
  showEmojiPicker.value = false
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    selectedFile.value = file
    const isImage = file.type.startsWith('image/')
    filePreview.value = {
      name: file.name,
      isImage,
      url: isImage ? URL.createObjectURL(file) : null,
    }
  }
  e.target.value = ''
}

function removeFile() {
  if (filePreview.value?.url) URL.revokeObjectURL(filePreview.value.url)
  selectedFile.value = null
  filePreview.value = null
}

function resetForm() {
  userSearch.value = ''
  selectedUsers.value = []
  groupName.value = ''
  messageText.value = ''
  removeFile()
  showEmojiPicker.value = false
  showSuggestions.value = false
}

function onClickOutside(e) {
  if (showEmojiPicker.value && emojiPopoverRef.value && !emojiPopoverRef.value.contains(e.target)) {
    const btn = e.target.closest('.emoji-container')
    if (!btn) showEmojiPicker.value = false
  }
  if (showSuggestions.value && recipientInputRef.value && !recipientInputRef.value.contains(e.target)) {
    const area = e.target.closest('.recipient-area')
    if (!area) showSuggestions.value = false
  }
}

watch(visible, async (v) => {
  if (v) {
    await loadUsers()
    nextTick(() => recipientInputRef.value?.focus())
  }
})

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.new-msg-form {
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
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recipient-area {
  position: relative;
}

.recipient-chips {
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

.recipient-chips:focus-within {
  border-color: var(--primary-color);
}

.recipient-chip {
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

.recipient-input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.85rem;
  color: var(--text-color);
  flex: 1;
  min-width: 100px;
  padding: 0.1rem 0;
}

.recipient-input::placeholder {
  color: var(--text-color-secondary);
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

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-ground);
  color: var(--text-color);
  font-size: 0.85rem;
  outline: none;
}

.form-input:focus {
  border-color: var(--primary-color);
}

.msg-compose-area {
  position: relative;
}

.msg-textarea {
  width: 100%;
  resize: none;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  padding-bottom: 2rem;
  font-family: inherit;
  font-size: 0.85rem;
  line-height: 1.4;
  background: var(--surface-ground);
  color: var(--text-color);
  outline: none;
  box-sizing: border-box;
}

.msg-textarea:focus {
  border-color: var(--primary-color);
}

.msg-textarea::placeholder {
  color: var(--text-color-secondary);
}

.msg-actions {
  position: absolute;
  bottom: 0.4rem;
  left: 0.5rem;
  display: flex;
  gap: 0.25rem;
}

.msg-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.25rem;
  border-radius: 4px;
  font-size: 1rem;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}

.msg-action-btn:hover {
  color: var(--primary-color);
}

.emoji-container {
  position: relative;
}

.emoji-popover {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 0.5rem;
  z-index: 1000;
}

.file-preview {
  padding: 0;
}

.file-preview-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--surface-overlay);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 0.3rem 0.6rem;
  max-width: 300px;
}

.file-preview-img {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

.file-preview-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-ground);
  border-radius: 4px;
  color: var(--text-color-secondary);
}

.file-preview-name {
  font-size: 0.8rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.file-preview-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
}

.file-preview-remove:hover {
  color: var(--red-500);
}

.hidden-file-input {
  display: none;
}
</style>
