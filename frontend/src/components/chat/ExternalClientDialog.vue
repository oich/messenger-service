<template>
  <Dialog
    :visible="modelValue"
    @update:visible="$emit('update:modelValue', $event)"
    header="Mit Matrix-Client verbinden"
    modal
    :style="{ width: '440px' }"
  >
    <div v-if="loading" class="ext-loading">
      <i class="pi pi-spin pi-spinner"></i> Lade Zugangsdaten...
    </div>
    <div v-else-if="error" class="ext-error">
      <i class="pi pi-exclamation-circle"></i>
      <span>{{ error }}</span>
    </div>
    <div v-else-if="clientInfo" class="ext-content">
      <p class="ext-intro">
        Verbinde dich mit Element, FluffyChat oder einem anderen Matrix-Client.
        Kopiere die Zugangsdaten und gib sie im Client ein.
      </p>

      <div class="credentials">
        <div class="credential-row">
          <label>Homeserver</label>
          <div class="credential-value">
            <code>{{ clientInfo.homeserver }}</code>
            <button class="copy-btn" @click="copy(clientInfo.homeserver)" title="Kopieren">
              <i class="pi pi-copy"></i>
            </button>
          </div>
        </div>
        <div class="credential-row">
          <label>Benutzer</label>
          <div class="credential-value">
            <code>{{ clientInfo.username }}</code>
            <button class="copy-btn" @click="copy(clientInfo.username)" title="Kopieren">
              <i class="pi pi-copy"></i>
            </button>
          </div>
        </div>
        <div class="credential-row">
          <label>Passwort</label>
          <div class="credential-value">
            <code class="password-field">{{ showPassword ? clientInfo.password : '••••••••••••' }}</code>
            <button class="copy-btn" @click="togglePassword" :title="showPassword ? 'Verbergen' : 'Anzeigen'">
              <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
            </button>
            <button class="copy-btn" @click="copy(clientInfo.password)" title="Kopieren">
              <i class="pi pi-copy"></i>
            </button>
          </div>
        </div>
      </div>

      <div class="ext-hint">
        <i class="pi pi-info-circle"></i>
        In Element: Anmelden &rarr; Homeserver bearbeiten &rarr; obige URL eingeben
      </div>
    </div>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import api from '../../api'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const loading = ref(false)
const error = ref(null)
const clientInfo = ref(null)
const showPassword = ref(false)

function togglePassword() {
  showPassword.value = !showPassword.value
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: 'Kopiert', life: 1500 })
  } catch {
    // Fallback
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
    toast.add({ severity: 'success', summary: 'Kopiert', life: 1500 })
  }
}

async function fetchClientInfo() {
  loading.value = true
  error.value = null
  clientInfo.value = null
  showPassword.value = false

  try {
    const { data } = await api.get('/api/v1/users/me/external-client')
    clientInfo.value = data
  } catch (err) {
    if (err.response?.status === 403) {
      error.value = 'Externer Client-Zugang ist fuer dein Konto nicht aktiviert. Bitte kontaktiere einen Admin.'
    } else if (err.response?.status === 404) {
      error.value = 'Kein Matrix-Passwort vorhanden. Bitte kontaktiere einen Admin.'
    } else {
      error.value = 'Zugangsdaten konnten nicht geladen werden.'
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) fetchClientInfo()
})
</script>

<style scoped>
.ext-loading, .ext-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem 0;
  justify-content: center;
  color: var(--text-color-secondary);
}

.ext-error {
  color: var(--red-500, #ef4444);
}

.ext-intro {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin: 0 0 1rem 0;
  line-height: 1.4;
}

.credentials {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--surface-ground);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 0.75rem;
}

.credential-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.credential-row label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.credential-value {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.credential-value code {
  flex: 1;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.82rem;
  color: var(--text-color);
  word-break: break-all;
}

.password-field {
  letter-spacing: 1px;
}

.copy-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.2rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  transition: color 0.15s;
  flex-shrink: 0;
}

.copy-btn:hover {
  color: var(--primary-color);
}

.ext-hint {
  margin-top: 0.75rem;
  font-size: 0.78rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  line-height: 1.3;
}

.ext-hint i {
  margin-top: 0.1rem;
  flex-shrink: 0;
}
</style>
