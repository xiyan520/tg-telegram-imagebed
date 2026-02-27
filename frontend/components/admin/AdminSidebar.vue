<template>
  <aside
    class="fixed left-0 top-0 z-40 hidden h-screen flex-col border-r border-stone-200/70 bg-white/94 backdrop-blur-xl transition-all duration-300 dark:border-neutral-700/80 dark:bg-neutral-900/90 lg:flex"
    :class="adminUiStore.sidebarCollapsed ? 'w-16' : 'w-64'"
  >
    <div class="flex h-16 items-center border-b border-stone-200/70 px-3 dark:border-neutral-700/80">
      <NuxtLink to="/" class="flex min-w-0 items-center gap-2.5">
        <template v-if="seoSettings.logoMode === 'custom' && seoSettings.logoUrl">
          <img :src="seoSettings.logoUrl" :alt="displayName" class="h-9 w-9 rounded-lg object-contain" />
        </template>
        <template v-else>
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 shadow-sm shadow-amber-500/25">
            <UIcon name="heroicons:cloud-arrow-up" class="h-5 w-5 text-white" />
          </div>
        </template>
        <Transition name="fade">
          <div v-if="!adminUiStore.sidebarCollapsed" class="min-w-0">
            <p class="truncate text-sm font-semibold text-stone-900 dark:text-stone-100">{{ displayName }}</p>
            <p class="text-[11px] text-stone-500 dark:text-stone-400">Admin Console</p>
          </div>
        </Transition>
      </NuxtLink>
    </div>

    <nav class="flex-1 overflow-y-auto py-3">
      <div v-for="group in groupedMenu" :key="group.key" class="mb-4 px-2">
        <p v-if="!adminUiStore.sidebarCollapsed" class="mb-1 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-stone-400 dark:text-stone-500">
          {{ group.label }}
        </p>
        <ul class="space-y-1">
          <li v-for="item in group.items" :key="item.key">
            <NuxtLink
              :to="item.to"
              class="group flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm transition-all"
              :class="isActive(item)
                ? 'bg-amber-100/80 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800/80'"
              :title="item.label"
            >
              <UIcon
                :name="item.icon"
                class="h-4.5 w-4.5 shrink-0"
                :class="isActive(item) ? 'text-amber-600 dark:text-amber-300' : 'text-stone-500 dark:text-stone-400'"
              />
              <Transition name="fade">
                <span v-if="!adminUiStore.sidebarCollapsed" class="truncate font-medium">{{ item.label }}</span>
              </Transition>
            </NuxtLink>
          </li>
        </ul>
      </div>
    </nav>

    <div class="border-t border-stone-200/70 p-2.5 dark:border-neutral-700/80">
      <button
        type="button"
        class="flex w-full items-center justify-center gap-2 rounded-xl px-2 py-2 text-sm text-stone-500 transition-colors hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800"
        @click="adminUiStore.toggleSidebar()"
      >
        <UIcon :name="adminUiStore.sidebarCollapsed ? 'heroicons:chevron-double-right' : 'heroicons:chevron-double-left'" class="h-4.5 w-4.5" />
        <Transition name="fade">
          <span v-if="!adminUiStore.sidebarCollapsed">收起菜单</span>
        </Transition>
      </button>
    </div>
  </aside>

  <USlideover v-model="adminUiStore.mobileSidebarOpen" side="left">
    <div class="flex h-full flex-col bg-white dark:bg-neutral-900">
      <div class="flex h-16 items-center justify-between border-b border-stone-200 px-4 dark:border-neutral-700">
        <NuxtLink to="/" class="flex items-center gap-2.5" @click="adminUiStore.closeMobileSidebar()">
          <template v-if="seoSettings.logoMode === 'custom' && seoSettings.logoUrl">
            <img :src="seoSettings.logoUrl" :alt="displayName" class="h-9 w-9 rounded-lg object-contain" />
          </template>
          <template v-else>
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 shadow-sm shadow-amber-500/25">
              <UIcon name="heroicons:cloud-arrow-up" class="h-5 w-5 text-white" />
            </div>
          </template>
          <div>
            <p class="text-sm font-semibold text-stone-900 dark:text-stone-100">{{ displayName }}</p>
            <p class="text-[11px] text-stone-500 dark:text-stone-400">Admin Console</p>
          </div>
        </NuxtLink>
        <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="adminUiStore.closeMobileSidebar()" />
      </div>

      <nav class="flex-1 overflow-y-auto px-3 py-3">
        <section v-for="group in groupedMenu" :key="group.key" class="mb-4">
          <p class="mb-1.5 px-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-400 dark:text-stone-500">
            {{ group.label }}
          </p>
          <ul class="space-y-1">
            <li v-for="item in group.items" :key="item.key">
              <NuxtLink
                :to="item.to"
                class="flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all"
                :class="isActive(item)
                  ? 'bg-amber-100/80 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                  : 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800/80'"
                @click="adminUiStore.closeMobileSidebar()"
              >
                <UIcon :name="item.icon" class="h-4.5 w-4.5 shrink-0" />
                <span class="font-medium">{{ item.label }}</span>
              </NuxtLink>
            </li>
          </ul>
        </section>
      </nav>
    </div>
  </USlideover>
</template>

<script setup lang="ts">
const route = useRoute()
const adminUiStore = useAdminUiStore()
const { groupedMenu, isActive, activeKey } = useAdminMenu()
const { seoSettings, displayName } = useSeoSettings()

watch(
  () => route.path,
  () => {
    adminUiStore.closeMobileSidebar()
  }
)

watch(activeKey, (key) => {
  if (key) adminUiStore.setMobilePrimaryTab(key)
}, { immediate: true })

onMounted(() => {
  adminUiStore.restore()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
