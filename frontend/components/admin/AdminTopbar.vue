<template>
  <header
    class="sticky top-0 z-30 border-b border-stone-200/65 bg-white/82 backdrop-blur-xl dark:border-neutral-700/70 dark:bg-neutral-900/82"
  >
    <div class="flex h-16 items-center justify-between gap-3 px-3 sm:px-4 lg:px-6">
      <div class="flex min-w-0 items-center gap-2 sm:gap-3">
        <!-- 移动端菜单按钮 -->
        <button
          class="rounded-lg p-2 text-stone-600 transition-colors hover:bg-stone-100/70 dark:text-stone-300 dark:hover:bg-neutral-800/70 lg:hidden"
          @click="adminUiStore.openMobileSidebar()"
        >
          <UIcon name="heroicons:bars-3" class="h-5 w-5" />
        </button>

        <div class="hidden h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 shadow-sm shadow-amber-500/20 sm:flex">
          <UIcon name="heroicons:command-line" class="h-4.5 w-4.5 text-white" />
        </div>

        <div class="min-w-0">
          <slot name="title">
            <p class="truncate text-sm font-semibold text-stone-800 dark:text-stone-100 sm:text-base">
              {{ resolvedTitle }}
            </p>
          </slot>
          <p class="truncate text-xs text-stone-500 dark:text-stone-400">
            {{ activeGroupLabel }} · Admin Console
          </p>
        </div>
      </div>

      <div class="flex items-center gap-1.5 sm:gap-2">
        <!-- 额外操作插槽 -->
        <slot name="actions" />

        <UButton
          class="hidden sm:inline-flex"
          color="gray"
          variant="ghost"
          size="sm"
          :icon="adminUiStore.densityMode === 'compact' ? 'heroicons:rectangle-stack' : 'heroicons:squares-2x2'"
          :title="adminUiStore.densityMode === 'compact' ? '切换为舒适模式' : '切换为紧凑模式'"
          @click="toggleDensity"
        />

        <UButton
          class="hidden lg:inline-flex"
          color="gray"
          variant="ghost"
          size="sm"
          :icon="adminUiStore.sidebarCollapsed ? 'heroicons:chevron-double-right' : 'heroicons:chevron-double-left'"
          :title="adminUiStore.sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
          @click="adminUiStore.toggleSidebar()"
        />

        <!-- 用户入口 -->
        <button
          v-if="authStore.isAuthenticated"
          class="flex items-center gap-2 rounded-xl px-2 py-1.5 text-stone-600 transition-colors hover:bg-stone-100/70 dark:text-stone-300 dark:hover:bg-neutral-800/70 sm:px-3"
          @click="$emit('openSettings')"
        >
          <div class="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-amber-500 to-orange-500">
            <UIcon name="heroicons:user" class="h-4 w-4 text-white" />
          </div>
          <span class="hidden max-w-[120px] truncate text-sm font-medium sm:inline">{{ authStore.username }}</span>
          <UIcon name="heroicons:chevron-down" class="h-4 w-4 text-stone-400" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const props = defineProps<{
  pageTitle?: string
}>()

defineEmits<{
  openSettings: []
}>()

const adminUiStore = useAdminUiStore()
const authStore = useAuthStore()
const { menu, activeKey } = useAdminMenu()

const activeItem = computed(() => menu.value.find(item => item.key === activeKey.value))

const resolvedTitle = computed(() => {
  if (props.pageTitle?.trim()) return props.pageTitle
  return activeItem.value?.label || '管理后台'
})

const activeGroupLabel = computed(() => {
  const groupKey = activeItem.value?.groupKey
  return adminMenuGroupsMeta.find(group => group.key === groupKey)?.label || '总览'
})

const toggleDensity = () => {
  adminUiStore.setDensityMode(adminUiStore.densityMode === 'compact' ? 'comfortable' : 'compact')
}
</script>
