<template>
  <AdminShell @open-settings="panelOpen = true">
    <slot />
  </AdminShell>

  <AdminUserCenterPanel :open="panelOpen" @update:open="panelOpen = $event" />
</template>

<script setup lang="ts">
const panelOpen = ref(false)
import AdminUserCenterPanel from '~/components/admin/profile/AdminUserCenterPanel.vue'
</script>
