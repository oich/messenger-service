<template>
  <span class="build-stamp" :title="tooltip">{{ label }}</span>
</template>

<script setup>
// Build-Stempel (Version + Build-Zeit, siehe vite.config.js __APP_VERSION__/
// __BUILD_TIME__): aendert sich bei jedem Rebuild, damit im Menue sichtbar
// ist, ob der Browser gerade den aktuellen oder einen alten (gecachten) Stand
// zeigt. Vorlage: ruest-app/frontend/src/App.vue.
const built = new Date(__BUILD_TIME__)
const label = `v${__APP_VERSION__} · ${built.toLocaleString('de-DE', {
  day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
})}`
const tooltip = `Version ${__APP_VERSION__}\nGebaut: ${built.toLocaleString('de-DE')}`
</script>

<style scoped>
.build-stamp {
  font-size: 0.72rem;
  color: #8b95a1;
  white-space: nowrap;
  margin-right: 0.5rem;
  cursor: default;
}
</style>
