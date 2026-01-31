<template>
  <div class="message-area" ref="messageAreaRef">
    <div v-if="hasMore" class="load-more">
      <Button
        label="Aeltere Nachrichten laden"
        text
        size="small"
        :loading="loading"
        @click="$emit('load-more')"
      />
    </div>
    <div v-if="loading && messages.length === 0" class="message-loading">
      <i class="pi pi-spin pi-spinner"></i> Nachrichten werden geladen...
    </div>
    <div v-if="!loading && messages.length === 0" class="message-empty">
      Noch keine Nachrichten in diesem Raum.
    </div>
    <div
      v-for="msg in messages"
      :key="msg.event_id"
      class="message-row"
      :class="{ 'message-row-own': isOwn(msg), 'message-row-other': !isOwn(msg) }"
    >
      <div class="message-bubble" :class="{ 'bubble-own': isOwn(msg), 'bubble-other': !isOwn(msg) }">
        <div v-if="!isOwn(msg)" class="message-sender">{{ displayName(msg) }}</div>
        <div class="message-body">
          <!-- Image message -->
          <div v-if="msg.msg_type === 'm.image' && msg.file_url" class="message-image">
            <img
              :src="resolveMediaUrl(msg.file_url)"
              :alt="msg.filename || msg.body"
              class="message-img"
              loading="lazy"
              @click="openImage(resolveMediaUrl(msg.file_url))"
            />
            <div v-if="msg.body && msg.body !== msg.filename" class="message-text">{{ msg.body }}</div>
          </div>
          <!-- File message -->
          <div v-else-if="isFileMessage(msg.msg_type) && msg.file_url" class="message-file">
            <a
              :href="resolveMediaUrl(msg.file_url)"
              target="_blank"
              class="file-download"
              :download="msg.filename"
            >
              <i class="pi pi-file"></i>
              <div class="file-info">
                <span class="file-name">{{ msg.filename || msg.body }}</span>
                <span v-if="msg.file_size" class="file-size">{{ formatFileSize(msg.file_size) }}</span>
              </div>
              <i class="pi pi-download"></i>
            </a>
            <div v-if="msg.body && msg.body !== msg.filename" class="message-text">{{ msg.body }}</div>
          </div>
          <!-- Text message -->
          <template v-else>{{ msg.body }}</template>
        </div>
        <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
      </div>
    </div>

    <!-- Image lightbox -->
    <div v-if="lightboxUrl" class="lightbox" @click="lightboxUrl = null">
      <img :src="lightboxUrl" class="lightbox-img" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import Button from 'primevue/button'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
  currentUserMatrixId: { type: String, default: null },
})

defineEmits(['load-more'])

const messageAreaRef = ref(null)
const lightboxUrl = ref(null)

function isOwn(msg) {
  if (!props.currentUserMatrixId) return false
  return msg.sender === props.currentUserMatrixId
}

function displayName(msg) {
  if (msg.sender_display_name) return msg.sender_display_name
  // Extract readable name from Matrix ID: @username:server -> username
  if (msg.sender && msg.sender.startsWith('@')) {
    return msg.sender.split(':')[0].substring(1)
  }
  return msg.sender || ''
}

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (messageAreaRef.value) {
      messageAreaRef.value.scrollTop = messageAreaRef.value.scrollHeight
    }
  }
)

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const time = d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  if (isToday) return time
  return `${d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })} ${time}`
}

function resolveMediaUrl(mxcUrl) {
  if (!mxcUrl) return ''
  if (!mxcUrl.startsWith('mxc://')) return mxcUrl
  const parts = mxcUrl.replace('mxc://', '').split('/')
  if (parts.length >= 2) {
    const baseUrl = import.meta.env.VITE_API_TARGET || ''
    const token = localStorage.getItem('token') || ''
    return `${baseUrl}/api/v1/messages/media/${parts[0]}/${parts.slice(1).join('/')}?token=${encodeURIComponent(token)}`
  }
  return mxcUrl
}

function isFileMessage(msgType) {
  return ['m.file', 'm.audio', 'm.video'].includes(msgType)
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function openImage(url) {
  lightboxUrl.value = url
}
</script>

<style scoped>
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  position: relative;
  background: var(--surface-ground);
}

.load-more {
  text-align: center;
  padding: 0.5rem;
}

.message-loading,
.message-empty {
  text-align: center;
  color: var(--text-color-secondary);
  padding: 2rem;
}

/* Row alignment */
.message-row {
  display: flex;
  padding: 0.15rem 0;
}

.message-row-own {
  justify-content: flex-end;
}

.message-row-other {
  justify-content: flex-start;
}

/* Bubble styles */
.message-bubble {
  max-width: 70%;
  padding: 0.5rem 0.75rem;
  border-radius: 12px;
  position: relative;
}

.bubble-own {
  background: var(--primary-color);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-other {
  background: var(--surface-card);
  color: var(--text-color);
  border: 1px solid var(--surface-border);
  border-bottom-left-radius: 4px;
}

.message-sender {
  font-weight: 600;
  font-size: 0.75rem;
  margin-bottom: 0.15rem;
  color: var(--primary-color);
}

.message-body {
  font-size: 0.875rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-time {
  font-size: 0.65rem;
  opacity: 0.6;
  text-align: right;
  margin-top: 0.2rem;
}

.bubble-own .message-time {
  color: rgba(255, 255, 255, 0.7);
}

/* Image */
.message-image {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.message-img {
  max-width: 350px;
  max-height: 260px;
  border-radius: 6px;
  cursor: pointer;
  object-fit: contain;
  transition: opacity 0.15s;
}

.bubble-other .message-img {
  border: 1px solid var(--surface-border);
}

.message-img:hover {
  opacity: 0.9;
}

/* File */
.message-file {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.file-download {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  text-decoration: none;
  color: inherit;
  max-width: 300px;
  transition: background 0.15s;
}

.bubble-other .file-download {
  background: var(--surface-overlay);
  border: 1px solid var(--surface-border);
}

.file-download:hover {
  background: rgba(255, 255, 255, 0.25);
}

.bubble-other .file-download:hover {
  background: var(--surface-hover);
}

.file-download .pi-file {
  font-size: 1.1rem;
}

.file-download .pi-download {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-left: auto;
}

.file-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.file-name {
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 0.65rem;
  opacity: 0.7;
}

.message-text {
  font-size: 0.875rem;
  white-space: pre-wrap;
}

/* Lightbox */
.lightbox {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  cursor: pointer;
}

.lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}
</style>
