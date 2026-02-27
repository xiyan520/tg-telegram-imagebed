<template>
  <div class="min-h-screen bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.08),transparent_38%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.08),transparent_35%),linear-gradient(180deg,#f8fafc_0%,#f5f5f4_100%)] dark:bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.09),transparent_42%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.10),transparent_38%),linear-gradient(180deg,#0b0b0c_0%,#121214_100%)]">
    <div class="pointer-events-none fixed inset-0 opacity-[0.18] [background-size:26px_26px] [background-image:linear-gradient(to_right,rgba(120,113,108,0.10)_1px,transparent_1px),linear-gradient(to_bottom,rgba(120,113,108,0.10)_1px,transparent_1px)] dark:opacity-[0.12]" />

    <!-- 侧边栏 -->
    <AdminSidebar />

    <!-- 主内容区 -->
    <div
      class="relative z-10 transition-all duration-300"
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
      <main
        class="px-3 pb-24 sm:px-4 lg:px-6 lg:pb-6"
        :class="adminUiStore.densityMode === 'compact' ? 'pt-2 sm:pt-3 lg:pt-4' : 'pt-3 sm:pt-4 lg:pt-5'"
      >
        <div
          class="mx-auto max-w-[1520px]"
          :class="adminUiStore.densityMode === 'compact' ? 'space-y-3' : 'space-y-4'"
        >
          <slot />
        </div>
      </main>
    </div>

    <AdminMobileNav />
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
