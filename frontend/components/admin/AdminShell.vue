<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-900">
    <!-- 侧边栏 -->
    <AdminSidebar />

    <!-- 主内容区 -->
    <div
      class="transition-all duration-300"
      :class="{
        'lg:ml-16': adminUiStore.sidebarCollapsed,
        'lg:ml-64': !adminUiStore.sidebarCollapsed
      }"
    >
      <!-- 顶栏 -->
      <AdminTopbar
        :page-title="pageTitle"
        @open-settings="$emit('openSettings')"
      >
        <template #title>
          <slot name="title" />
        </template>
        <template #actions>
          <slot name="actions" />
        </template>
      </AdminTopbar>

      <!-- 页面内容 -->
      <main class="p-4 lg:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  pageTitle?: string
}>()

defineEmits<{
  openSettings: []
}>()

const adminUiStore = useAdminUiStore()
</script>
