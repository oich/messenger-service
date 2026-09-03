<script setup>
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Message from 'primevue/message'
import apiClient from '../../api'

const props = defineProps({
  visible: Boolean,
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const typeOptions = [
  { label: 'Bug melden', value: 'bug' },
  { label: 'Feature vorschlagen', value: 'feature' },
]
const severityOptions = [
  { label: 'Niedrig', value: 'low' },
  { label: 'Mittel', value: 'medium' },
  { label: 'Hoch', value: 'high' },
]
const impactOptions = [
  { label: 'Gering', value: 'low' },
  { label: 'Mittel', value: 'medium' },
  { label: 'Gross', value: 'high' },
]

const type = ref('bug')
const subject = ref('')
const body = ref('')
const severity = ref(null)
const impact = ref(null)
const submitting = ref(false)
const error = ref('')

const isBug = computed(() => type.value === 'bug')

function resetForm() {
  type.value = 'bug'
  subject.value = ''
  body.value = ''
  severity.value = null
  impact.value = null
  error.value = ''
}

async function submit() {
  if (submitting.value) return
  if (!body.value?.trim()) {
    error.value = 'Bitte eine Beschreibung eingeben.'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await apiClient.post('/api/v1/feedback', {
      type: type.value,
      subject: subject.value || undefined,
      body: body.value,
      severity: isBug.value ? severity.value || undefined : undefined,
      impact: !isBug.value ? impact.value || undefined : undefined,
    })
    dialogVisible.value = false
    resetForm()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Senden fehlgeschlagen.'
  } finally {
    submitting.value = false
  }
}

function closeDialog() {
  dialogVisible.value = false
  error.value = ''
}
</script>

<template>
  <Dialog
    v-model:visible="dialogVisible"
    :modal="true"
    header="Feedback"
    :style="{ width: '480px' }"
    :dismissable-mask="true"
    @hide="closeDialog"
  >
    <div class="flex flex-col gap-4 pt-2">
      <SelectButton v-model="type" :options="typeOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />

      <div class="field">
        <label class="block mb-2 font-medium">Titel</label>
        <InputText v-model="subject" class="w-full" placeholder="Kurze Zusammenfassung" />
      </div>

      <div v-if="isBug" class="field">
        <label class="block mb-2 font-medium">Schweregrad</label>
        <Select v-model="severity" :options="severityOptions" optionLabel="label" optionValue="value" class="w-full" placeholder="Bitte waehlen" />
      </div>
      <div v-else class="field">
        <label class="block mb-2 font-medium">Nutzen</label>
        <Select v-model="impact" :options="impactOptions" optionLabel="label" optionValue="value" class="w-full" placeholder="Bitte waehlen" />
      </div>

      <div class="field">
        <label class="block mb-2 font-medium">Beschreibung *</label>
        <Textarea v-model="body" rows="6" auto-resize class="w-full" placeholder="Was ist passiert bzw. was schlagen Sie vor?" />
      </div>

      <Message v-if="error" severity="error" :closable="false">
        {{ error }}
      </Message>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="closeDialog" />
      <Button label="Absenden" icon="pi pi-send" :loading="submitting" @click="submit" />
    </template>
  </Dialog>
</template>
