import { ref, computed } from 'vue'
import api from '../api'

const rooms = ref([])
const currentRoomId = ref(null)
const messages = ref([])
const loading = ref(false)
const endToken = ref(null)
const hasMore = ref(false)
const currentUser = ref(null)

export function useMessenger() {
  const currentRoom = computed(() =>
    rooms.value.find(r => r.matrix_room_id === currentRoomId.value)
  )

  async function fetchCurrentUser() {
    try {
      const { data } = await api.get('/api/v1/users/me')
      currentUser.value = data
    } catch (err) {
      console.error('Failed to fetch current user:', err)
    }
  }

  async function fetchRooms() {
    try {
      const { data } = await api.get('/api/v1/rooms')
      rooms.value = data.rooms
    } catch (err) {
      console.error('Failed to fetch rooms:', err)
    }
  }

  async function selectRoom(roomId) {
    currentRoomId.value = roomId
    messages.value = []
    endToken.value = null
    hasMore.value = false
    // Reset unread count for this room
    const room = rooms.value.find(r => r.matrix_room_id === roomId)
    if (room) room.unread_count = 0
    await fetchMessages(roomId)
  }

  async function fetchMessages(roomId, fromToken = null) {
    loading.value = true
    try {
      const params = { limit: 50 }
      if (fromToken) params.from_token = fromToken
      const { data } = await api.get(`/api/v1/messages/history/${encodeURIComponent(roomId)}`, { params })
      if (fromToken) {
        messages.value = [...data.messages.reverse(), ...messages.value]
      } else {
        messages.value = data.messages.reverse()
      }
      endToken.value = data.end_token
      hasMore.value = data.has_more
    } catch (err) {
      console.error('Failed to fetch messages:', err)
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(body) {
    if (!currentRoomId.value || !body.trim()) return
    try {
      const { data } = await api.post('/api/v1/messages/send', {
        room_id: currentRoomId.value,
        body: body.trim(),
      })
      messages.value.push(data)
    } catch (err) {
      console.error('Failed to send message:', err)
      throw err
    }
  }

  async function uploadFile(roomId, file, body = '') {
    const formData = new FormData()
    formData.append('room_id', roomId)
    formData.append('file', file)
    if (body) formData.append('body', body)
    try {
      const { data } = await api.post('/api/v1/messages/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (roomId === currentRoomId.value) {
        messages.value.push(data)
      }
      return data
    } catch (err) {
      console.error('Failed to upload file:', err)
      throw err
    }
  }

  async function createRoom(name, topic = null, inviteUsers = null) {
    try {
      const { data } = await api.post('/api/v1/rooms', {
        name,
        topic,
        invite_users: inviteUsers,
      })
      rooms.value.push(data)
      return data
    } catch (err) {
      console.error('Failed to create room:', err)
      throw err
    }
  }

  async function fetchUsers(query = null) {
    try {
      const params = {}
      if (query) params.q = query
      const { data } = await api.get('/api/v1/users', { params })
      return data
    } catch (err) {
      console.error('Failed to fetch users:', err)
      return []
    }
  }

  async function createDM(targetUserId) {
    try {
      const { data } = await api.post(`/api/v1/rooms/dm/${encodeURIComponent(targetUserId)}`)
      const exists = rooms.value.some(r => r.matrix_room_id === data.matrix_room_id)
      if (!exists) {
        rooms.value.push(data)
      }
      return data
    } catch (err) {
      console.error('Failed to create DM:', err)
      throw err
    }
  }

  async function joinRoom(roomId) {
    try {
      await api.post(`/api/v1/rooms/${encodeURIComponent(roomId)}/join`)
      await fetchRooms()
    } catch (err) {
      console.error('Failed to join room:', err)
      throw err
    }
  }

  async function loadMoreMessages() {
    if (!hasMore.value || !endToken.value || !currentRoomId.value) return
    await fetchMessages(currentRoomId.value, endToken.value)
  }

  function addIncomingMessage(msg) {
    // Always add to current room's messages if it matches
    if (msg.room_id === currentRoomId.value) {
      const exists = messages.value.some(m => m.event_id === msg.event_id)
      if (!exists) {
        messages.value.push(msg)
      }
    }

    // Update room list: last_message, unread_count
    const room = rooms.value.find(r => r.matrix_room_id === msg.room_id)
    if (room) {
      room.last_message = msg.body
      room.last_message_ts = msg.timestamp
      if (msg.room_id !== currentRoomId.value) {
        room.unread_count = (room.unread_count || 0) + 1
      }
    } else {
      // Unknown room — reload rooms and then auto-select if no room is active
      fetchRooms().then(() => {
        const newRoom = rooms.value.find(r => r.matrix_room_id === msg.room_id)
        if (newRoom) {
          newRoom.last_message = msg.body
          newRoom.unread_count = 1
        }
      })
    }
  }

  return {
    rooms,
    currentRoomId,
    currentRoom,
    currentUser,
    messages,
    loading,
    hasMore,
    fetchCurrentUser,
    fetchRooms,
    selectRoom,
    sendMessage,
    uploadFile,
    createRoom,
    createDM,
    fetchUsers,
    joinRoom,
    loadMoreMessages,
    addIncomingMessage,
  }
}
