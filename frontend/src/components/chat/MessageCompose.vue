<template>
  <div
    class="compose-bar"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
    :class="{ 'drag-over': isDragOver }"
  >
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
    <div class="compose-row">
      <div class="compose-actions-left">
        <button class="compose-action-btn" @click="triggerFileInput" title="Datei anhaengen">
          <i class="pi pi-paperclip"></i>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          class="hidden-file-input"
          @change="onFileSelect"
        />
        <div class="emoji-container">
          <button class="compose-action-btn" @click="toggleEmojiPicker" title="Emoji">
            <i class="pi pi-face-smile"></i>
          </button>
          <div v-if="showEmojiPicker" class="emoji-popover" ref="emojiPopoverRef">
            <EmojiPicker @select="insertEmoji" />
          </div>
        </div>
      </div>
      <textarea
        ref="textareaRef"
        v-model="text"
        placeholder="Nachricht schreiben..."
        class="compose-textarea"
        rows="1"
        @keydown="onKeydown"
        @input="autoResize"
      ></textarea>
      <Button
        icon="pi pi-send"
        @click="handleSend"
        :disabled="!canSend"
        :loading="sending"
        rounded
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import EmojiPicker from './EmojiPicker.vue'

const emit = defineEmits(['send', 'upload'])
const text = ref('')
const showEmojiPicker = ref(false)
const selectedFile = ref(null)
const filePreview = ref(null)
const isDragOver = ref(false)
const sending = ref(false)
const textareaRef = ref(null)
const fileInputRef = ref(null)
const emojiPopoverRef = ref(null)

const canSend = computed(() => text.value.trim() || selectedFile.value)

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
    if (selectedFile.value) {
      emit('upload', { file: selectedFile.value, body: text.value.trim() })
      removeFile()
    } else {
      emit('send', text.value)
    }
    text.value = ''
    await nextTick()
    autoResize()
  } finally {
    sending.value = false
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

function toggleEmojiPicker() {
  showEmojiPicker.value = !showEmojiPicker.value
}

function insertEmoji(emoji) {
  const el = textareaRef.value
  if (el) {
    const start = el.selectionStart
    const end = el.selectionEnd
    text.value = text.value.slice(0, start) + emoji + text.value.slice(end)
    nextTick(() => {
      el.selectionStart = el.selectionEnd = start + emoji.length
      el.focus()
    })
  } else {
    text.value += emoji
  }
  showEmojiPicker.value = false
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) setFile(file)
  e.target.value = ''
}

function setFile(file) {
  selectedFile.value = file
  const isImage = file.type.startsWith('image/')
  filePreview.value = {
    name: file.name,
    isImage,
    url: isImage ? URL.createObjectURL(file) : null,
  }
}

function removeFile() {
  if (filePreview.value?.url) URL.revokeObjectURL(filePreview.value.url)
  selectedFile.value = null
  filePreview.value = null
}

function onDragOver() {
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) setFile(file)
}

function onClickOutside(e) {
  if (showEmojiPicker.value && emojiPopoverRef.value && !emojiPopoverRef.value.contains(e.target)) {
    const btn = e.target.closest('.emoji-container')
    if (!btn) showEmojiPicker.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.compose-bar {
  border-top: 1px solid var(--surface-border);
  background: var(--surface-section);
  padding: 0.5rem 1rem;
  transition: background 0.2s;
}

.compose-bar.drag-over {
  background: var(--primary-50, rgba(59, 130, 246, 0.05));
  border-top-color: var(--primary-color);
}

.file-preview {
  padding: 0.4rem 0;
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
  background: var(--surface-hover);
}

.compose-row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.compose-actions-left {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding-bottom: 0.2rem;
}

.compose-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.4rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  transition: color 0.15s, background 0.15s;
}

.compose-action-btn:hover {
  color: var(--primary-color);
  background: var(--surface-hover);
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

.compose-textarea {
  flex: 1;
  resize: none;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.4;
  background: var(--surface-ground);
  color: var(--text-color);
  outline: none;
  max-height: 150px;
  overflow-y: auto;
}

.compose-textarea:focus {
  border-color: var(--primary-color);
}

.compose-textarea::placeholder {
  color: var(--text-color-secondary);
}

.hidden-file-input {
  display: none;
}
</style>
