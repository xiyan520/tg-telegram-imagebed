<template>
  <nav class="fixed inset-x-0 bottom-0 z-40 border-t border-stone-200/80 bg-white/95 px-1 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-1.5 backdrop-blur-xl dark:border-neutral-700/80 dark:bg-neutral-900/95 lg:hidden">
    <div class="grid grid-cols-5 gap-1">
      <NuxtLink
        v-for="item in mobilePrimaryMenu"
        :key="item.key"
        :to="item.to"
        class="flex flex-col items-center justify-center rounded-xl px-1 py-1.5 text-[11px] font-medium transition-all"
        :class="isActive(item) ? 'bg-amber-100/80 text-amber-700 dark:bg-amber-900/35 dark:text-amber-300' : 'text-stone-500 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-neutral-800'"
        @click="handleNavigate(item.key)"
      >
        <UIcon :name="item.icon" class="mb-0.5 h-4 w-4" />
        <span class="truncate">{{ item.label }}</span>
      </NuxtLink>

      <button
        type="button"
        class="flex flex-col items-center justify-center rounded-xl px-1 py-1.5 text-[11px] font-medium transition-all"
        :class="overflowActive ? 'bg-amber-100/80 text-amber-700 dark:bg-amber-900/35 dark:text-amber-300' : 'text-stone-500 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-neutral-800'"
        @click="adminUiStore.openMobileSidebar()"
      >
        <UIcon name="heroicons:bars-3-bottom-left" class="mb-0.5 h-4 w-4" />
        <span>更多</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
const route = useRoute()
const adminUiStore = useAdminUiStore()
const { mobilePrimaryMenu, mobileSecondaryMenu, isActive } = useAdminMenu()

const overflowActive = computed(() =>
  mobileSecondaryMenu.value.some(item => route.path === item.to || route.path.startsWith(`${item.to}/`))
)

const handleNavigate = (key: string) => {
  adminUiStore.setMobilePrimaryTab(key)
  adminUiStore.closeMobileSidebar()
}
</script>
