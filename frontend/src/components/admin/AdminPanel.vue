<template>
  <div>
    <HubPageHeader title="Messenger-Administration" />

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab v-for="tab in tabs" :key="tab.key" :value="tab.key">
          <i :class="tab.icon" class="mr-[0.5rem]" />{{ tab.label }}
        </Tab>
      </TabList>
      <TabPanels>
        <!-- Users -->
        <TabPanel value="users">
          <HubDataTable
            :paginator="false"
            flat
            :value="users"
            data-key="hub_user_id"
            :global-filter-fields="['display_name', 'hub_user_id', 'matrix_user_id']"
            search-placeholder="Nutzer suchen…"
            empty-title="Keine Nutzer gefunden"
          >
            <Column field="display_name" header="Anzeigename" sortable>
              <template #body="{ data }">{{ data.display_name || '–' }}</template>
            </Column>
            <Column field="hub_user_id" header="Hub-ID" sortable body-class="font-mono" />
            <Column field="role" header="Rolle" sortable>
              <template #body="{ data }">
                <Tag :value="data.role" :severity="data.role === 'admin' ? 'danger' : 'secondary'" />
              </template>
            </Column>
            <Column field="matrix_user_id" header="Matrix-ID" body-class="font-mono text-sm" />
            <Column field="provisioned" header="Provisioniert" sortable>
              <template #body="{ data }">
                <i :class="data.provisioned ? 'pi pi-check-circle text-hub-success' : 'pi pi-times-circle text-hub-muted'" />
              </template>
            </Column>
            <Column header="Ext. Client">
              <template #body="{ data }">
                <ToggleSwitch
                  v-if="data.provisioned"
                  :model-value="data.external_client_enabled"
                  :aria-label="data.external_client_enabled ? 'Ext. Client deaktivieren' : 'Ext. Client aktivieren'"
                  @update:model-value="toggleExternalAccess(data)"
                />
                <span v-else class="text-hub-muted">–</span>
              </template>
            </Column>
            <Column field="created_at" header="Erstellt am" sortable>
              <template #body="{ data }">{{ formatDateTime(data.created_at) }}</template>
            </Column>
            <Column header="" body-class="text-right">
              <template #body="{ data }">
                <Button v-tooltip.left="'Bearbeiten'" icon="pi pi-pencil" text rounded aria-label="Bearbeiten" @click="openEditUser(data)" />
              </template>
            </Column>
          </HubDataTable>
        </TabPanel>

        <!-- Rooms -->
        <TabPanel value="rooms">
          <HubDataTable
            :paginator="false"
            flat
            :value="rooms"
            data-key="matrix_room_id"
            :global-filter-fields="['display_name', 'matrix_room_id', 'room_type']"
            search-placeholder="Raum suchen…"
            empty-title="Keine Räume gefunden"
          >
            <Column field="display_name" header="Name" sortable>
              <template #body="{ data }">{{ data.display_name || '–' }}</template>
            </Column>
            <Column field="room_type" header="Typ" sortable>
              <template #body="{ data }">
                <Tag :value="roomTypeLabel(data.room_type)" severity="info" />
              </template>
            </Column>
            <Column field="member_count" header="Mitglieder" sortable body-class="hub-num" header-class="hub-num" />
            <Column field="matrix_room_id" header="Room-ID" body-class="font-mono text-sm" />
            <Column header="" body-class="text-right">
              <template #body="{ data }">
                <Button v-tooltip.left="'Löschen'" icon="pi pi-trash" text rounded severity="danger" aria-label="Löschen" @click="deleteRoom(data)" />
              </template>
            </Column>
          </HubDataTable>
        </TabPanel>

        <!-- Teams -->
        <TabPanel value="teams">
          <HubDataTable
            :paginator="false"
            flat
            :value="teams"
            data-key="id"
            empty-title="Keine Teams angelegt"
            empty-text="Teams lassen sich mit einem Klick in einen Chat einladen."
          >
            <template #toolbar-end>
              <Button label="Neues Team" icon="pi pi-plus" @click="openCreateTeam" />
            </template>
            <Column field="name" header="Name" sortable />
            <Column header="Mitglieder">
              <template #body="{ data }">
                <span class="text-sm">{{ data.members.map((m) => m.display_name || m.hub_user_id).join(', ') || '–' }}</span>
              </template>
            </Column>
            <Column header="" body-class="text-right whitespace-nowrap">
              <template #body="{ data }">
                <Button v-tooltip.left="'Bearbeiten'" icon="pi pi-pencil" text rounded aria-label="Bearbeiten" @click="openEditTeam(data)" />
                <Button v-tooltip.left="'Löschen'" icon="pi pi-trash" text rounded severity="danger" aria-label="Löschen" @click="deleteTeam(data)" />
              </template>
            </Column>
          </HubDataTable>
        </TabPanel>

        <!-- System -->
        <TabPanel value="system">
          <div class="stat-grid">
            <div v-for="card in statCards" :key="card.label" class="hub-card flex items-center gap-[1rem] p-[1rem]">
              <i :class="[card.icon, card.tone]" class="text-2xl" />
              <div class="flex min-w-0 flex-col">
                <span class="text-xl font-semibold" :class="card.tone">{{ card.value }}</span>
                <span class="text-sm text-hub-muted">{{ card.label }}</span>
                <span v-if="card.sub" class="truncate text-xs text-hub-muted">{{ card.sub }}</span>
              </div>
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Edit user -->
    <HubDialog v-model:visible="showEditUser" header="Anzeigename ändern" size="sm" submit-on-enter @submit="saveEditUser">
      <HubField v-slot="{ id }" label="Anzeigename" required>
        <InputText :id="id" v-model="editDisplayName" fluid />
      </HubField>
      <template #footer>
        <Button severity="secondary" text label="Abbrechen" @click="showEditUser = false" />
        <Button label="Speichern" icon="pi pi-check" :disabled="!editDisplayName.trim()" @click="saveEditUser" />
      </template>
    </HubDialog>

    <!-- Create / edit team -->
    <HubDialog
      v-model:visible="showTeamDialog"
      :header="editTeamTarget ? 'Team bearbeiten' : 'Neues Team'"
      size="md"
      @hide="resetTeamDialog"
    >
      <div class="flex flex-col gap-[1rem]">
        <HubField v-slot="{ id }" label="Name" required>
          <InputText :id="id" v-model="teamName" placeholder="z.B. Konstruktion" fluid />
        </HubField>
        <HubField v-slot="{ id }" label="Mitglieder">
          <MultiSelect
            :id="id"
            v-model="teamMemberIds"
            :options="memberOptions"
            option-label="label"
            option-value="hub_user_id"
            display="chip"
            filter
            filter-placeholder="Nutzer suchen…"
            placeholder="Mitglieder wählen"
            :loading="loadingUsers"
            fluid
          />
        </HubField>
      </div>
      <template #footer>
        <Button severity="secondary" text label="Abbrechen" @click="showTeamDialog = false" />
        <Button label="Speichern" icon="pi pi-check" :disabled="!teamName.trim()" @click="saveTeam" />
      </template>
    </HubDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import MultiSelect from 'primevue/multiselect'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import {
  HubDataTable, HubDialog, HubField, HubPageHeader, hubConfirm, formatDateTime,
} from '@hub/ui'

const toast = useToast()

const tabs = [
  { key: 'users', label: 'Nutzer', icon: 'pi pi-users' },
  { key: 'rooms', label: 'Räume', icon: 'pi pi-comments' },
  { key: 'teams', label: 'Teams', icon: 'pi pi-sitemap' },
  { key: 'system', label: 'System', icon: 'pi pi-server' },
]

const activeTab = ref('users')

// ── Users ──────────────────────────────────────────────
const users = ref([])

async function fetchUsers() {
  try {
    const { data } = await api.get('/api/v1/admin/users')
    users.value = data
  } catch (err) {
    if (err.response?.status === 403) {
      toast.add({ severity: 'error', summary: 'Zugriff verweigert', detail: 'Admin-Rechte erforderlich', life: 5000 })
    }
  }
}

// Edit user
const showEditUser = ref(false)
const editTarget = ref(null)
const editDisplayName = ref('')

function openEditUser(user) {
  editTarget.value = user
  editDisplayName.value = user.display_name || ''
  showEditUser.value = true
}

async function saveEditUser() {
  if (!editDisplayName.value.trim()) return
  try {
    await api.patch(`/api/v1/admin/users/${encodeURIComponent(editTarget.value.hub_user_id)}`, {
      display_name: editDisplayName.value.trim(),
    })
    editTarget.value.display_name = editDisplayName.value.trim()
    showEditUser.value = false
    toast.add({ severity: 'success', summary: 'Gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht gespeichert werden', life: 3000 })
  }
}

// External client access toggle
async function toggleExternalAccess(user) {
  const newState = !user.external_client_enabled
  try {
    await api.post(`/api/v1/admin/users/${encodeURIComponent(user.hub_user_id)}/external-access`, {
      enabled: newState,
    })
    user.external_client_enabled = newState
    toast.add({
      severity: 'success',
      summary: newState ? 'Ext. Client aktiviert' : 'Ext. Client deaktiviert',
      detail: user.display_name || user.hub_user_id,
      life: 3000,
    })
  } catch (err) {
    const detail = err.response?.data?.detail || 'Fehler beim Umschalten'
    toast.add({ severity: 'error', summary: 'Fehler', detail, life: 5000 })
  }
}

// ── Rooms ──────────────────────────────────────────────
const rooms = ref([])

async function fetchRooms() {
  try {
    const { data } = await api.get('/api/v1/admin/rooms')
    rooms.value = data
  } catch {}
}

function roomTypeLabel(type) {
  const map = { dm: 'DM', general: 'Gruppe', entity: 'Entity', space: 'Space' }
  return map[type] || type
}

async function deleteRoom(room) {
  const name = room.display_name || room.matrix_room_id
  if (!(await hubConfirm(`Soll das Raum-Mapping "${name}" wirklich gelöscht werden?`))) return
  try {
    await api.delete(`/api/v1/admin/rooms/${encodeURIComponent(room.matrix_room_id)}`)
    rooms.value = rooms.value.filter((r) => r.matrix_room_id !== room.matrix_room_id)
    toast.add({ severity: 'success', summary: 'Raum gelöscht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Raum konnte nicht gelöscht werden', life: 3000 })
  }
}

// ── Teams ──────────────────────────────────────────────
const teams = ref([])
const allUsers = ref([])
const loadingUsers = ref(false)

async function fetchTeams() {
  try {
    const { data } = await api.get('/api/v1/teams')
    teams.value = data
  } catch {}
}

async function loadAllUsers() {
  if (allUsers.value.length > 0) return
  loadingUsers.value = true
  try {
    const { data } = await api.get('/api/v1/users')
    allUsers.value = data
  } catch {} finally {
    loadingUsers.value = false
  }
}

const showTeamDialog = ref(false)
const editTeamTarget = ref(null)
const teamName = ref('')
const teamMemberIds = ref([])

// Current members stay selectable even before the user list has loaded
const memberOptions = computed(() => {
  const byId = new Map()
  for (const m of editTeamTarget.value?.members || []) byId.set(m.hub_user_id, m)
  for (const u of allUsers.value) byId.set(u.hub_user_id, u)
  return [...byId.values()].map((u) => ({ hub_user_id: u.hub_user_id, label: u.display_name || u.hub_user_id }))
})

function openCreateTeam() {
  loadAllUsers()
  editTeamTarget.value = null
  showTeamDialog.value = true
}

function openEditTeam(team) {
  loadAllUsers()
  editTeamTarget.value = team
  teamName.value = team.name
  teamMemberIds.value = team.members.map((m) => m.hub_user_id)
  showTeamDialog.value = true
}

function resetTeamDialog() {
  editTeamTarget.value = null
  teamName.value = ''
  teamMemberIds.value = []
}

async function saveTeam() {
  const payload = {
    name: teamName.value.trim(),
    member_hub_user_ids: teamMemberIds.value,
  }
  try {
    if (editTeamTarget.value) {
      await api.patch(`/api/v1/teams/${editTeamTarget.value.id}`, payload)
    } else {
      await api.post('/api/v1/teams', payload)
    }
    showTeamDialog.value = false
    await fetchTeams()
    toast.add({ severity: 'success', summary: 'Gespeichert', life: 3000 })
  } catch (err) {
    const detail = err.response?.data?.detail || 'Team konnte nicht gespeichert werden'
    toast.add({ severity: 'error', summary: 'Fehler', detail, life: 4000 })
  }
}

async function deleteTeam(team) {
  if (!(await hubConfirm(`Soll das Team "${team.name}" wirklich gelöscht werden?`))) return
  try {
    await api.delete(`/api/v1/teams/${team.id}`)
    teams.value = teams.value.filter((t) => t.id !== team.id)
    toast.add({ severity: 'success', summary: 'Team gelöscht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Team konnte nicht gelöscht werden', life: 3000 })
  }
}

// ── System Stats ───────────────────────────────────────
const stats = ref({
  total_users: 0,
  provisioned_users: 0,
  rooms_by_type: {},
  sse_connections: 0,
  conduit_status: 'unknown',
})

const statCards = computed(() => {
  const s = stats.value
  const roomsByType = s.rooms_by_type || {}
  const online = s.conduit_status === 'online'
  return [
    { icon: 'pi pi-users', label: 'Nutzer gesamt', value: s.total_users, sub: `${s.provisioned_users} provisioniert` },
    {
      icon: 'pi pi-comments',
      label: 'Räume',
      value: Object.values(roomsByType).reduce((a, b) => a + b, 0),
      sub: Object.entries(roomsByType).map(([type, count]) => `${roomTypeLabel(type)}: ${count}`).join(' · '),
    },
    { icon: 'pi pi-wifi', label: 'SSE-Verbindungen', value: s.sse_connections },
    {
      icon: 'pi pi-server',
      label: 'Conduit-Status',
      value: s.conduit_status,
      tone: online ? 'text-hub-success' : 'text-hub-danger',
    },
  ]
})

async function fetchStats() {
  try {
    const { data } = await api.get('/api/v1/admin/stats')
    stats.value = data
  } catch {}
}

// Auto-refresh stats every 30s
let statsInterval = null

onMounted(async () => {
  await Promise.all([fetchUsers(), fetchRooms(), fetchTeams(), fetchStats()])
  statsInterval = setInterval(fetchStats, 30000)
})

onUnmounted(() => {
  if (statsInterval) clearInterval(statsInterval)
})
</script>

<style scoped>
/* own grid class: PrimeFlex (still loaded) redefines `grid` */
.stat-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
}
</style>
