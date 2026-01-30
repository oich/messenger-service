import { ref, computed } from 'vue'
import api from '../api'

const rooms = ref([])
const currentRoomId = ref(null)
const messages = ref([])
const loading = ref(false)
const endToken = ref(null)
const hasMore = ref(false)

export function useMessenger() {
  const currentRoom = computed(() =>
    rooms.value.find(r => r.matrix_room_id === currentRoomId.value)
  )

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
    if (msg.room_id === currentRoomId.value) {
      const exists = messages.value.some(m => m.event_id === msg.event_id)
      if (!exists) {
        messages.value.push(msg)
      }
    }
  }

  return {
    rooms,
    currentRoomId,
    currentRoom,
    messages,
    loading,
    hasMore,
    fetchRooms,
    selectRoom,
    sendMessage,
    createRoom,
    joinRoom,
    loadMoreMessages,
    addIncomingMessage,
  }
}
