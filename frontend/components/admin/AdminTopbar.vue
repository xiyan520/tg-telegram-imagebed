<template>
  <header
    class="sticky top-0 z-30 h-16 flex items-center justify-between px-4 lg:px-6 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-b border-stone-200/50 dark:border-neutral-700/50"
  >
    <!-- 左侧：移动端菜单按钮 + 页面标题 -->
    <div class="flex items-center gap-4">
      <!-- 移动端菜单按钮 -->
      <button
        class="lg:hidden p-2 -ml-2 text-stone-600 dark:text-stone-300 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50 rounded-lg transition-colors"
        @click="adminUiStore.openMobileSidebar()"
      >
        <UIcon name="heroicons:bars-3" class="w-6 h-6" />
      </button>

      <!-- 页面标题插槽 -->
      <div class="flex items-center gap-3">
        <slot name="title">
          <h1 class="text-lg font-semibold text-stone-800 dark:text-stone-100">
            {{ pageTitle }}
          </h1>
        </slot>
      </div>
    </div>

    <!-- 右侧：用户操作 -->
    <div class="flex items-center gap-2">
      <!-- 额外操作插槽 -->
      <slot name="actions" />

      <!-- 用户信息 -->
      <div v-if="authStore.isAuthenticated" class="flex items-center">
        <!-- 用户名 + 设置按钮合并为一个可点击区域 -->
        <button
          class="flex items-center gap-2 px-3 py-1.5 text-stone-600 dark:text-stone-300 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50 rounded-lg transition-colors"
          @click="$emit('openSettings')"
        >
          <div class="w-7 h-7 bg-gradient-to-br from-amber-500 to-orange-500 rounded-full flex items-center justify-center">
            <UIcon name="heroicons:user" class="w-4 h-4 text-white" />
          </div>
          <span class="hidden sm:inline text-sm font-medium">{{ authStore.username }}</span>
          <UIcon name="heroicons:chevron-down" class="w-4 h-4 text-stone-400" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  pageTitle?: string
}>()

defineEmits<{
  openSettings: []
}>()

const adminUiStore = useAdminUiStore()
const authStore = useAuthStore()
</script>
