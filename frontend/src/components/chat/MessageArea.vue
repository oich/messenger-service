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
      class="message-item"
    >
      <div class="message-header">
        <span class="message-sender">{{ msg.sender_display_name || msg.sender }}</span>
        <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
      </div>
      <div class="message-body">{{ msg.body }}</div>
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
})

defineEmits(['load-more'])

const messageAreaRef = ref(null)

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
</script>

<style scoped>
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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

.message-item {
  padding: 0.4rem 0;
}

.message-header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.15rem;
}

.message-sender {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--primary-color);
}

.message-time {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.message-body {
  font-size: 0.875rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
