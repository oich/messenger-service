<template>
  <div class="compose-bar">
    <InputText
      v-model="text"
      placeholder="Nachricht schreiben..."
      class="compose-input"
      @keydown.enter.exact="handleSend"
    />
    <Button
      icon="pi pi-send"
      @click="handleSend"
      :disabled="!text.trim()"
      rounded
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const emit = defineEmits(['send'])
const text = ref('')

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value)
  text.value = ''
}
</script>

<style scoped>
.compose-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--surface-border);
  background: var(--surface-section);
}

.compose-input {
  flex: 1;
}
</style>
