<template>
  <div class="admin-panel">
    <div class="admin-header">
      <router-link to="/" class="back-link">
        <i class="pi pi-arrow-left"></i>
      </router-link>
      <h2>Messenger Admin</h2>
    </div>

    <div class="admin-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <i :class="tab.icon"></i>
        {{ tab.label }}
      </button>
    </div>

    <!-- Users Tab -->
    <div v-if="activeTab === 'users'" class="tab-content">
      <div class="toolbar">
        <input
          v-model="userSearch"
          type="text"
          class="search-input"
          placeholder="Nutzer suchen..."
        />
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Anzeigename</th>
              <th>Hub-ID</th>
              <th>Rolle</th>
              <th>Matrix-ID</th>
              <th>Provisioniert</th>
              <th>Ext. Client</th>
              <th>Erstellt am</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.hub_user_id">
              <td>{{ user.display_name || '-' }}</td>
              <td class="monospace">{{ user.hub_user_id }}</td>
              <td>
                <span class="role-badge" :class="'role-' + user.role">{{ user.role }}</span>
              </td>
              <td class="monospace small">{{ user.matrix_user_id }}</td>
              <td>
                <i :class="user.provisioned ? 'pi pi-check-circle status-ok' : 'pi pi-times-circle status-no'"></i>
              </td>
              <td>
                <button
                  v-if="user.provisioned"
                  class="toggle-btn"
                  :class="{ active: user.external_client_enabled }"
                  @click="toggleExternalAccess(user)"
                  :title="user.external_client_enabled ? 'Ext. Client deaktivieren' : 'Ext. Client aktivieren'"
                >
                  <i :class="user.external_client_enabled ? 'pi pi-check' : 'pi pi-times'"></i>
                </button>
                <span v-else class="small">-</span>
              </td>
              <td class="small">{{ formatDate(user.created_at) }}</td>
              <td>
                <button class="icon-btn" @click="openEditUser(user)" title="Bearbeiten">
                  <i class="pi pi-pencil"></i>
                </button>
              </td>
            </tr>
            <tr v-if="filteredUsers.length === 0">
              <td colspan="8" class="empty-row">Keine Nutzer gefunden</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Rooms Tab -->
    <div v-if="activeTab === 'rooms'" class="tab-content">
      <div class="toolbar">
        <input
          v-model="roomSearch"
          type="text"
          class="search-input"
          placeholder="Raum suchen..."
        />
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Typ</th>
              <th>Mitglieder</th>
              <th>Room-ID</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="room in filteredRooms" :key="room.matrix_room_id">
              <td>{{ room.display_name || '-' }}</td>
              <td>
                <span class="type-badge" :class="'type-' + room.room_type">{{ roomTypeLabel(room.room_type) }}</span>
              </td>
              <td>{{ room.member_count }}</td>
              <td class="monospace small">{{ room.matrix_room_id }}</td>
              <td>
                <button class="icon-btn danger" @click="confirmDeleteRoom(room)" title="Loeschen">
                  <i class="pi pi-trash"></i>
                </button>
              </td>
            </tr>
            <tr v-if="filteredRooms.length === 0">
              <td colspan="5" class="empty-row">Keine Raeume gefunden</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Teams Tab -->
    <div v-if="activeTab === 'teams'" class="tab-content">
      <div class="toolbar">
        <Button label="Neues Team" icon="pi pi-plus" size="small" @click="openCreateTeam" />
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Mitglieder</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="team in teams" :key="team.id">
              <td>{{ team.name }}</td>
              <td class="small">
                {{ team.members.map(m => m.display_name || m.hub_user_id).join(', ') || '-' }}
              </td>
              <td>
                <button class="icon-btn" @click="openEditTeam(team)" title="Bearbeiten">
                  <i class="pi pi-pencil"></i>
                </button>
                <button class="icon-btn danger" @click="confirmDeleteTeam(team)" title="Loeschen">
                  <i class="pi pi-trash"></i>
                </button>
              </td>
            </tr>
            <tr v-if="teams.length === 0">
              <td colspan="3" class="empty-row">Keine Teams angelegt</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- System Tab -->
    <div v-if="activeTab === 'system'" class="tab-content">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon"><i class="pi pi-users"></i></div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.total_users }}</span>
            <span class="stat-label">Nutzer gesamt</span>
            <span class="stat-sub">{{ stats.provisioned_users }} provisioniert</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon"><i class="pi pi-comments"></i></div>
          <div class="stat-body">
            <span class="stat-value">{{ totalRooms }}</span>
            <span class="stat-label">Raeume</span>
            <span class="stat-sub">
              <template v-for="(count, type) in stats.rooms_by_type" :key="type">
                {{ type }}: {{ count }}&nbsp;
              </template>
            </span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon"><i class="pi pi-wifi"></i></div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.sse_connections }}</span>
            <span class="stat-label">SSE-Verbindungen</span>
          </div>
        </div>
        <div class="stat-card" :class="{ 'status-online': stats.conduit_status === 'online', 'status-offline': stats.conduit_status !== 'online' }">
          <div class="stat-icon"><i class="pi pi-server"></i></div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.conduit_status }}</span>
            <span class="stat-label">Conduit-Status</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit User Dialog -->
    <Dialog
      v-model:visible="showEditUser"
      header="Anzeigename aendern"
      modal
      :style="{ width: '400px' }"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label>Anzeigename</label>
          <InputText v-model="editDisplayName" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showEditUser = false" />
        <Button label="Speichern" @click="saveEditUser" :disabled="!editDisplayName.trim()" />
      </template>
    </Dialog>

    <!-- Create/Edit Team Dialog -->
    <Dialog
      v-model:visible="showTeamDialog"
      :header="editTeamTarget ? 'Team bearbeiten' : 'Neues Team'"
      modal
      :style="{ width: '460px' }"
      @hide="resetTeamDialog"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label>Name</label>
          <InputText v-model="teamName" class="w-full" placeholder="z.B. Konstruktion" />
        </div>
        <div class="form-field">
          <label>Mitglieder</label>
          <div class="invite-area">
            <div class="invite-chips">
              <span v-for="user in teamMembers" :key="user.hub_user_id" class="invite-chip">
                {{ user.display_name || user.hub_user_id }}
                <button class="chip-remove" @click="removeTeamMember(user)">
                  <i class="pi pi-times"></i>
                </button>
              </span>
              <input
                v-model="teamMemberSearch"
                type="text"
                class="invite-input"
                placeholder="Nutzer suchen..."
                @focus="teamMemberShowSuggestions = true"
              />
            </div>
            <div v-if="teamMemberShowSuggestions && teamMemberFilteredUsers.length > 0" class="user-suggestions">
              <div
                v-for="user in teamMemberFilteredUsers"
                :key="user.hub_user_id"
                class="suggestion-item"
                @mousedown.prevent="addTeamMember(user)"
              >
                <i class="pi pi-user"></i>
                <span>{{ user.display_name || user.hub_user_id }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showTeamDialog = false" />
        <Button label="Speichern" @click="saveTeam" :disabled="!teamName.trim()" />
      </template>
    </Dialog>

    <!-- Delete Team Confirmation Dialog -->
    <Dialog
      v-model:visible="showDeleteTeamConfirm"
      header="Team loeschen"
      modal
      :style="{ width: '400px' }"
    >
      <p>Soll das Team <strong>{{ deleteTeamTarget?.name }}</strong> wirklich geloescht werden?</p>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showDeleteTeamConfirm = false" />
        <Button label="Loeschen" severity="danger" @click="executeDeleteTeam" />
      </template>
    </Dialog>

    <!-- Delete Room Confirmation Dialog -->
    <Dialog
      v-model:visible="showDeleteConfirm"
      header="Raum loeschen"
      modal
      :style="{ width: '400px' }"
    >
      <p>Soll das Raum-Mapping <strong>{{ deleteTarget?.display_name || deleteTarget?.matrix_room_id }}</strong> wirklich geloescht werden?</p>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" @click="showDeleteConfirm = false" />
        <Button label="Loeschen" severity="danger" @click="executeDeleteRoom" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const tabs = [
  { key: 'users', label: 'Nutzer', icon: 'pi pi-users' },
  { key: 'rooms', label: 'Raeume', icon: 'pi pi-comments' },
  { key: 'teams', label: 'Teams', icon: 'pi pi-sitemap' },
  { key: 'system', label: 'System', icon: 'pi pi-server' },
]

const activeTab = ref('users')

// ── Users ──────────────────────────────────────────────
const users = ref([])
const userSearch = ref('')

const filteredUsers = computed(() => {
  if (!userSearch.value.trim()) return users.value
  const q = userSearch.value.toLowerCase()
  return users.value.filter(u =>
    (u.display_name || '').toLowerCase().includes(q) ||
    u.hub_user_id.toLowerCase().includes(q) ||
    u.matrix_user_id.toLowerCase().includes(q)
  )
})

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
const roomSearch = ref('')

const filteredRooms = computed(() => {
  if (!roomSearch.value.trim()) return rooms.value
  const q = roomSearch.value.toLowerCase()
  return rooms.value.filter(r =>
    (r.display_name || '').toLowerCase().includes(q) ||
    r.matrix_room_id.toLowerCase().includes(q) ||
    r.room_type.toLowerCase().includes(q)
  )
})

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

// Delete room
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)

function confirmDeleteRoom(room) {
  deleteTarget.value = room
  showDeleteConfirm.value = true
}

async function executeDeleteRoom() {
  try {
    await api.delete(`/api/v1/admin/rooms/${encodeURIComponent(deleteTarget.value.matrix_room_id)}`)
    rooms.value = rooms.value.filter(r => r.matrix_room_id !== deleteTarget.value.matrix_room_id)
    showDeleteConfirm.value = false
    toast.add({ severity: 'success', summary: 'Raum geloescht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Raum konnte nicht geloescht werden', life: 3000 })
  }
}

// ── Teams ──────────────────────────────────────────────
const teams = ref([])
const allUsers = ref([])

async function fetchTeams() {
  try {
    const { data } = await api.get('/api/v1/teams')
    teams.value = data
  } catch {}
}

async function loadAllUsers() {
  if (allUsers.value.length === 0) {
    try {
      const { data } = await api.get('/api/v1/users')
      allUsers.value = data
    } catch {}
  }
}

const showTeamDialog = ref(false)
const editTeamTarget = ref(null)
const teamName = ref('')
const teamMembers = ref([])
const teamMemberSearch = ref('')
const teamMemberShowSuggestions = ref(false)

const teamMemberFilteredUsers = computed(() => {
  const selectedIds = new Set(teamMembers.value.map(u => u.hub_user_id))
  let users = allUsers.value.filter(u => !selectedIds.has(u.hub_user_id))
  if (teamMemberSearch.value.trim()) {
    const q = teamMemberSearch.value.toLowerCase()
    users = users.filter(u =>
      (u.display_name || '').toLowerCase().includes(q) ||
      u.hub_user_id.toLowerCase().includes(q)
    )
  }
  return users.slice(0, 10)
})

function addTeamMember(user) {
  if (!teamMembers.value.some(u => u.hub_user_id === user.hub_user_id)) {
    teamMembers.value.push(user)
  }
  teamMemberSearch.value = ''
  teamMemberShowSuggestions.value = false
}

function removeTeamMember(user) {
  teamMembers.value = teamMembers.value.filter(u => u.hub_user_id !== user.hub_user_id)
}

function openCreateTeam() {
  loadAllUsers()
  editTeamTarget.value = null
  showTeamDialog.value = true
}

function openEditTeam(team) {
  loadAllUsers()
  editTeamTarget.value = team
  teamName.value = team.name
  teamMembers.value = team.members.map(m => ({ hub_user_id: m.hub_user_id, display_name: m.display_name }))
  showTeamDialog.value = true
}

function resetTeamDialog() {
  editTeamTarget.value = null
  teamName.value = ''
  teamMembers.value = []
  teamMemberSearch.value = ''
  teamMemberShowSuggestions.value = false
}

async function saveTeam() {
  const payload = {
    name: teamName.value.trim(),
    member_hub_user_ids: teamMembers.value.map(u => u.hub_user_id),
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

const showDeleteTeamConfirm = ref(false)
const deleteTeamTarget = ref(null)

function confirmDeleteTeam(team) {
  deleteTeamTarget.value = team
  showDeleteTeamConfirm.value = true
}

async function executeDeleteTeam() {
  try {
    await api.delete(`/api/v1/teams/${deleteTeamTarget.value.id}`)
    teams.value = teams.value.filter(t => t.id !== deleteTeamTarget.value.id)
    showDeleteTeamConfirm.value = false
    toast.add({ severity: 'success', summary: 'Team geloescht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Team konnte nicht geloescht werden', life: 3000 })
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

const totalRooms = computed(() =>
  Object.values(stats.value.rooms_by_type).reduce((a, b) => a + b, 0)
)

async function fetchStats() {
  try {
    const { data } = await api.get('/api/v1/admin/stats')
    stats.value = data
  } catch {}
}

// Auto-refresh stats every 30s
let statsInterval = null

function formatDate(iso) {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('de-DE')
  } catch {
    return iso
  }
}

onMounted(async () => {
  await Promise.all([fetchUsers(), fetchRooms(), fetchTeams(), fetchStats()])
  statsInterval = setInterval(fetchStats, 30000)
})

onUnmounted(() => {
  if (statsInterval) clearInterval(statsInterval)
})
</script>

<style scoped>
.admin-panel {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
  overflow: hidden;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: var(--surface-section);
  border-bottom: 1px solid var(--surface-border);
}

.admin-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.back-link {
  color: var(--text-color-secondary);
  text-decoration: none;
  display: flex;
  align-items: center;
  padding: 0.3rem;
  border-radius: 6px;
  transition: color 0.15s;
}

.back-link:hover {
  color: var(--primary-color);
}

.admin-tabs {
  display: flex;
  gap: 0;
  background: var(--surface-section);
  border-bottom: 1px solid var(--surface-border);
  padding: 0 1.25rem;
}

.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.6rem 1rem;
  cursor: pointer;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}

.tab-btn:hover {
  color: var(--text-color);
}

.tab-btn.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

/* Toolbar */
.toolbar {
  margin-bottom: 0.75rem;
}

.search-input {
  width: 100%;
  max-width: 360px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-card);
  color: var(--text-color);
  font-size: 0.85rem;
  outline: none;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: var(--primary-color);
}

/* Table */
.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.data-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 2px solid var(--surface-border);
  color: var(--text-color-secondary);
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
}

.data-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--surface-border);
  vertical-align: middle;
}

.data-table tbody tr:hover {
  background: var(--surface-hover, rgba(0,0,0,0.02));
}

.monospace {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
}

.small {
  font-size: 0.78rem;
  color: var(--text-color-secondary);
}

.empty-row {
  text-align: center;
  color: var(--text-color-secondary);
  padding: 2rem 0.75rem !important;
}

/* Badges */
.role-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-weight: 600;
}

.role-admin {
  background: var(--red-100, #fee2e2);
  color: var(--red-700, #b91c1c);
}

.role-user {
  background: var(--blue-100, #dbeafe);
  color: var(--blue-700, #1d4ed8);
}

.role-viewer {
  background: var(--surface-200, #e5e7eb);
  color: var(--text-color-secondary);
}

.type-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-weight: 600;
}

.type-dm {
  background: var(--green-100, #dcfce7);
  color: var(--green-700, #15803d);
}

.type-general {
  background: var(--blue-100, #dbeafe);
  color: var(--blue-700, #1d4ed8);
}

.type-entity {
  background: var(--orange-100, #ffedd5);
  color: var(--orange-700, #c2410c);
}

.type-space {
  background: var(--purple-100, #f3e8ff);
  color: var(--purple-700, #7e22ce);
}

/* Status icons */
.status-ok {
  color: var(--green-500, #22c55e);
  font-size: 1rem;
}

.status-no {
  color: var(--text-color-secondary);
  opacity: 0.4;
  font-size: 1rem;
}

/* Toggle button */
.toggle-btn {
  background: var(--surface-200, #e5e7eb);
  border: 1px solid var(--surface-border);
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
}

.toggle-btn.active {
  background: var(--green-100, #dcfce7);
  border-color: var(--green-300, #86efac);
  color: var(--green-700, #15803d);
}

.toggle-btn:hover {
  opacity: 0.8;
}

/* Icon buttons */
.icon-btn {
  background: none;
  border: 1px solid var(--surface-border);
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 0.3rem 0.45rem;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  font-size: 0.85rem;
  transition: all 0.15s;
}

.icon-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.icon-btn.danger:hover {
  color: var(--red-500, #ef4444);
  border-color: var(--red-500, #ef4444);
}

.icon-btn + .icon-btn {
  margin-left: 0.3rem;
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.stat-card.status-online {
  border-color: var(--green-300, #86efac);
}

.stat-card.status-offline {
  border-color: var(--red-300, #fca5a5);
}

.stat-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
  padding-top: 0.1rem;
}

.stat-body {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.stat-sub {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  opacity: 0.7;
  margin-top: 0.15rem;
}

/* Dialog overrides */
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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
</style>
