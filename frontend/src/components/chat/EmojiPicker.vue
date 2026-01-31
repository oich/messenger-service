<template>
  <div class="emoji-picker">
    <div class="emoji-search">
      <input
        v-model="search"
        type="text"
        placeholder="Emoji suchen..."
        class="emoji-search-input"
        ref="searchInput"
      />
    </div>
    <div class="emoji-categories">
      <button
        v-for="cat in categories"
        :key="cat.name"
        class="emoji-cat-btn"
        :class="{ active: activeCategory === cat.name }"
        @click="activeCategory = cat.name"
        :title="cat.label"
      >
        {{ cat.icon }}
      </button>
    </div>
    <div class="emoji-grid">
      <button
        v-for="emoji in filteredEmojis"
        :key="emoji.e"
        class="emoji-btn"
        @click="$emit('select', emoji.e)"
        :title="emoji.n"
      >
        {{ emoji.e }}
      </button>
      <div v-if="filteredEmojis.length === 0" class="emoji-empty">
        Kein Emoji gefunden
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'

defineEmits(['select'])

const search = ref('')
const activeCategory = ref('smileys')
const searchInput = ref(null)

onMounted(() => {
  nextTick(() => searchInput.value?.focus())
})

const categories = [
  { name: 'smileys', label: 'Smileys', icon: '😀' },
  { name: 'gestures', label: 'Gesten', icon: '👋' },
  { name: 'hearts', label: 'Herzen', icon: '❤️' },
  { name: 'animals', label: 'Tiere', icon: '🐱' },
  { name: 'food', label: 'Essen', icon: '🍕' },
  { name: 'activities', label: 'Aktivitäten', icon: '⚽' },
  { name: 'objects', label: 'Objekte', icon: '💡' },
]

const emojiData = {
  smileys: [
    { e: '😀', n: 'grinsen' }, { e: '😃', n: 'lachen' }, { e: '😄', n: 'breit lachen' },
    { e: '😁', n: 'strahlen' }, { e: '😅', n: 'schwitzen' }, { e: '😂', n: 'traenen lachen' },
    { e: '🤣', n: 'auf boden lachen' }, { e: '😊', n: 'laecheln' }, { e: '😇', n: 'engel' },
    { e: '🙂', n: 'leicht laecheln' }, { e: '😉', n: 'zwinkern' }, { e: '😍', n: 'herzaugen' },
    { e: '🥰', n: 'verliebt' }, { e: '😘', n: 'kussmund' }, { e: '😋', n: 'lecker' },
    { e: '😜', n: 'zunge raus zwinkern' }, { e: '🤪', n: 'verrückt' }, { e: '😎', n: 'cool' },
    { e: '🤩', n: 'sternaugen' }, { e: '🥳', n: 'party' }, { e: '😏', n: 'schmunzeln' },
    { e: '😒', n: 'genervt' }, { e: '😞', n: 'enttaeuscht' }, { e: '😔', n: 'nachdenklich' },
    { e: '😟', n: 'besorgt' }, { e: '😕', n: 'verwirrt' }, { e: '😢', n: 'weinen' },
    { e: '😭', n: 'heulen' }, { e: '😤', n: 'wuetend' }, { e: '😠', n: 'aergerlich' },
    { e: '🤔', n: 'nachdenken' }, { e: '🤫', n: 'psst' }, { e: '🤭', n: 'kichern' },
    { e: '🥱', n: 'gaehnen' }, { e: '😴', n: 'schlafen' }, { e: '🤮', n: 'uebelkeit' },
    { e: '🤒', n: 'krank' }, { e: '😱', n: 'schockiert' }, { e: '😳', n: 'erroeten' },
    { e: '🥺', n: 'bittend' }, { e: '🤯', n: 'explodiert' },
  ],
  gestures: [
    { e: '👋', n: 'winken' }, { e: '🤚', n: 'hand heben' }, { e: '✋', n: 'stopp' },
    { e: '🖖', n: 'vulkanier' }, { e: '👌', n: 'ok' }, { e: '🤌', n: 'italienisch' },
    { e: '✌️', n: 'peace' }, { e: '🤞', n: 'daumen druecken' }, { e: '🤟', n: 'liebe' },
    { e: '🤘', n: 'rock' }, { e: '👍', n: 'daumen hoch' }, { e: '👎', n: 'daumen runter' },
    { e: '👏', n: 'klatschen' }, { e: '🙌', n: 'haende hoch' }, { e: '🤝', n: 'haendeschuetteln' },
    { e: '🙏', n: 'beten' }, { e: '💪', n: 'muskel' }, { e: '👈', n: 'links zeigen' },
    { e: '👉', n: 'rechts zeigen' }, { e: '👆', n: 'oben zeigen' }, { e: '👇', n: 'unten zeigen' },
    { e: '☝️', n: 'zeigefinger' }, { e: '🫶', n: 'herz haende' }, { e: '🤙', n: 'ruf mich an' },
  ],
  hearts: [
    { e: '❤️', n: 'rotes herz' }, { e: '🧡', n: 'oranges herz' }, { e: '💛', n: 'gelbes herz' },
    { e: '💚', n: 'gruenes herz' }, { e: '💙', n: 'blaues herz' }, { e: '💜', n: 'lila herz' },
    { e: '🖤', n: 'schwarzes herz' }, { e: '🤍', n: 'weisses herz' }, { e: '💕', n: 'zwei herzen' },
    { e: '💞', n: 'kreisende herzen' }, { e: '💓', n: 'klopfendes herz' }, { e: '💗', n: 'wachsendes herz' },
    { e: '💖', n: 'funkelndes herz' }, { e: '💘', n: 'pfeilherz' }, { e: '💝', n: 'geschenkherz' },
    { e: '💔', n: 'gebrochenes herz' }, { e: '🔥', n: 'feuer' }, { e: '⭐', n: 'stern' },
    { e: '✨', n: 'funkeln' }, { e: '🌟', n: 'leuchtender stern' },
  ],
  animals: [
    { e: '🐱', n: 'katze' }, { e: '🐶', n: 'hund' }, { e: '🐭', n: 'maus' },
    { e: '🐹', n: 'hamster' }, { e: '🐰', n: 'hase' }, { e: '🦊', n: 'fuchs' },
    { e: '🐻', n: 'baer' }, { e: '🐼', n: 'panda' }, { e: '🐨', n: 'koala' },
    { e: '🦁', n: 'loewe' }, { e: '🐮', n: 'kuh' }, { e: '🐷', n: 'schwein' },
    { e: '🐸', n: 'frosch' }, { e: '🐵', n: 'affe' }, { e: '🐔', n: 'huhn' },
    { e: '🦄', n: 'einhorn' }, { e: '🐝', n: 'biene' }, { e: '🦋', n: 'schmetterling' },
    { e: '🐢', n: 'schildkroete' }, { e: '🐍', n: 'schlange' }, { e: '🐠', n: 'fisch' },
    { e: '🐬', n: 'delfin' }, { e: '🦅', n: 'adler' }, { e: '🦉', n: 'eule' },
  ],
  food: [
    { e: '🍕', n: 'pizza' }, { e: '🍔', n: 'burger' }, { e: '🍟', n: 'pommes' },
    { e: '🌭', n: 'hotdog' }, { e: '🍿', n: 'popcorn' }, { e: '🍩', n: 'donut' },
    { e: '🍰', n: 'kuchen' }, { e: '🎂', n: 'geburtstagskuchen' }, { e: '🍫', n: 'schokolade' },
    { e: '🍪', n: 'keks' }, { e: '☕', n: 'kaffee' }, { e: '🍺', n: 'bier' },
    { e: '🍷', n: 'wein' }, { e: '🥂', n: 'anstossen' }, { e: '🍎', n: 'apfel' },
    { e: '🍌', n: 'banane' }, { e: '🍇', n: 'trauben' }, { e: '🍓', n: 'erdbeere' },
    { e: '🥑', n: 'avocado' }, { e: '🌮', n: 'taco' }, { e: '🍣', n: 'sushi' },
    { e: '🥗', n: 'salat' }, { e: '🍝', n: 'spaghetti' }, { e: '🧁', n: 'cupcake' },
  ],
  activities: [
    { e: '⚽', n: 'fussball' }, { e: '🏀', n: 'basketball' }, { e: '🏈', n: 'football' },
    { e: '⚾', n: 'baseball' }, { e: '🎾', n: 'tennis' }, { e: '🏐', n: 'volleyball' },
    { e: '🎱', n: 'billard' }, { e: '🏓', n: 'tischtennis' }, { e: '🎯', n: 'zielscheibe' },
    { e: '🎮', n: 'controller' }, { e: '🎲', n: 'wuerfel' }, { e: '🧩', n: 'puzzle' },
    { e: '🎵', n: 'musik' }, { e: '🎶', n: 'noten' }, { e: '🎤', n: 'mikrofon' },
    { e: '🎸', n: 'gitarre' }, { e: '🎹', n: 'klavier' }, { e: '🎨', n: 'palette' },
    { e: '🏆', n: 'pokal' }, { e: '🥇', n: 'goldmedaille' }, { e: '🏅', n: 'medaille' },
    { e: '🚴', n: 'radfahren' }, { e: '🏊', n: 'schwimmen' }, { e: '⛷️', n: 'skifahren' },
  ],
  objects: [
    { e: '💡', n: 'gluehbirne' }, { e: '🔧', n: 'schraubenschluessel' }, { e: '🔨', n: 'hammer' },
    { e: '⚙️', n: 'zahnrad' }, { e: '📎', n: 'bueroklammer' }, { e: '📌', n: 'stecknadel' },
    { e: '📁', n: 'ordner' }, { e: '📂', n: 'offener ordner' }, { e: '📝', n: 'notiz' },
    { e: '📊', n: 'diagramm' }, { e: '📈', n: 'aufwaerts' }, { e: '📉', n: 'abwaerts' },
    { e: '💻', n: 'laptop' }, { e: '🖥️', n: 'desktop' }, { e: '📱', n: 'smartphone' },
    { e: '⌨️', n: 'tastatur' }, { e: '🖨️', n: 'drucker' }, { e: '📷', n: 'kamera' },
    { e: '🔑', n: 'schluessel' }, { e: '🔒', n: 'schloss' }, { e: '📦', n: 'paket' },
    { e: '🗑️', n: 'papierkorb' }, { e: '✉️', n: 'brief' }, { e: '📅', n: 'kalender' },
  ],
}

const filteredEmojis = computed(() => {
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    const all = Object.values(emojiData).flat()
    return all.filter(e => e.n.includes(q) || e.e === q)
  }
  return emojiData[activeCategory.value] || []
})
</script>

<style scoped>
.emoji-picker {
  width: 320px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.emoji-search {
  padding: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.emoji-search-input {
  width: 100%;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-ground);
  color: var(--text-color);
  font-size: 0.85rem;
  outline: none;
}

.emoji-search-input:focus {
  border-color: var(--primary-color);
}

.emoji-categories {
  display: flex;
  gap: 2px;
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid var(--surface-border);
  overflow-x: auto;
}

.emoji-cat-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0.25rem 0.4rem;
  border-radius: 4px;
  opacity: 0.6;
  transition: opacity 0.15s, background 0.15s;
}

.emoji-cat-btn:hover {
  opacity: 1;
  background: var(--surface-hover);
}

.emoji-cat-btn.active {
  opacity: 1;
  background: var(--surface-overlay);
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 2px;
  padding: 0.5rem;
  max-height: 220px;
  overflow-y: auto;
}

.emoji-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.3rem;
  padding: 0.2rem;
  border-radius: 4px;
  text-align: center;
  line-height: 1.4;
  transition: background 0.1s;
}

.emoji-btn:hover {
  background: var(--surface-hover);
}

.emoji-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
  padding: 1rem;
}
</style>
