<template>
  <div class="room-list">
    <div class="room-list-header">
      <h3>Raeume</h3>
      <Button
        icon="pi pi-user"
        text
        rounded
        size="small"
        @click="$emit('start-dm')"
        v-tooltip="'Direktnachricht'"
      />
      <Button
        icon="pi pi-plus"
        text
        rounded
        size="small"
        @click="$emit('create')"
        v-tooltip="'Neuer Raum'"
      />
    </div>
    <div class="room-list-items">
      <div
        v-for="room in rooms"
        :key="room.matrix_room_id"
        class="room-item"
        :class="{ active: room.matrix_room_id === currentRoomId }"
        @click="$emit('select', room.matrix_room_id)"
      >
        <i :class="roomIcon(room)" class="room-icon"></i>
        <div class="room-info">
          <span class="room-name">{{ room.display_name || room.matrix_room_id }}</span>
          <span v-if="room.last_message" class="room-last-msg">{{ room.last_message }}</span>
        </div>
        <span v-if="room.unread_count > 0" class="room-badge">{{ room.unread_count }}</span>
      </div>
      <div v-if="rooms.length === 0" class="room-empty">
        Keine Raeume vorhanden
      </div>
    </div>
  </div>
</template>

<script setup>
import Button from 'primevue/button'

defineProps({
  rooms: { type: Array, default: () => [] },
  currentRoomId: { type: String, default: null },
})

defineEmits(['select', 'create', 'start-dm'])

function roomIcon(room) {
  switch (room.room_type) {
    case 'dm': return 'pi pi-user'
    case 'entity': return 'pi pi-box'
    case 'space': return 'pi pi-folder'
    default: return 'pi pi-comments'
  }
}
</script>

<style scoped>
.room-list {
  width: 280px;
  min-width: 280px;
  border-right: 1px solid var(--surface-border);
  background: var(--surface-section);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.room-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.room-list-header h3 {
  margin: 0;
  font-size: 1rem;
}

.room-list-items {
  flex: 1;
  overflow-y: auto;
}

.room-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
}

.room-item:hover {
  background: var(--surface-overlay);
}

.room-item.active {
  background: var(--surface-card);
  border-left: 3px solid var(--primary-color);
}

.room-icon {
  font-size: 1rem;
  color: var(--text-color-secondary);
  min-width: 1.25rem;
  text-align: center;
}

.room-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.room-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-last-msg {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-badge {
  background: var(--primary-color);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 8px;
  min-width: 1.2rem;
  text-align: center;
}

.room-empty {
  padding: 1rem;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}
</style>
