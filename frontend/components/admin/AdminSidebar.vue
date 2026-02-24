<template>
  <!-- 桌面端侧边栏 -->
  <aside
    class="hidden lg:flex flex-col fixed left-0 top-0 h-screen z-40 transition-all duration-300 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-r border-stone-200/50 dark:border-neutral-700/50"
    :class="{
      'w-16': adminUiStore.sidebarCollapsed,
      'w-64': !adminUiStore.sidebarCollapsed
    }"
  >
    <!-- Logo 区域 -->
    <div class="h-16 flex items-center px-4 border-b border-stone-200/50 dark:border-neutral-700/50">
      <NuxtLink to="/" class="flex items-center gap-2.5 overflow-hidden">
        <template v-if="seoSettings.logoMode === 'custom' && seoSettings.logoUrl">
          <img :src="seoSettings.logoUrl" :alt="displayName" class="w-9 h-9 flex-shrink-0 rounded-lg object-contain" />
        </template>
        <template v-else>
          <div class="w-9 h-9 flex-shrink-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
            <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
          </div>
        </template>
        <Transition name="fade">
          <div v-if="!adminUiStore.sidebarCollapsed" class="flex items-center gap-2">
            <span class="text-lg font-semibold text-stone-800 dark:text-stone-100 whitespace-nowrap">{{ displayName }}</span>
            <UBadge color="red" variant="subtle" size="xs">管理</UBadge>
          </div>
        </Transition>
      </NuxtLink>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 py-4 overflow-y-auto">
      <ul class="space-y-1 px-3">
        <li v-for="item in menu" :key="item.key">
          <NuxtLink
            :to="item.to"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group"
            :class="[
              isActive(item)
                ? 'bg-gradient-to-r from-amber-500/10 to-orange-500/10 text-amber-600 dark:text-amber-400'
                : 'text-stone-600 dark:text-stone-400 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50'
            ]"
          >
            <UIcon
              :name="item.icon"
              class="w-5 h-5 flex-shrink-0 transition-colors"
              :class="[
                isActive(item)
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-stone-500 dark:text-stone-400 group-hover:text-stone-700 dark:group-hover:text-stone-300'
              ]"
            />
            <Transition name="fade">
              <span
                v-if="!adminUiStore.sidebarCollapsed"
                class="font-medium whitespace-nowrap"
              >
                {{ item.label }}
              </span>
            </Transition>
            <!-- 徽章 -->
            <Transition name="fade">
              <UBadge
                v-if="!adminUiStore.sidebarCollapsed && item.badge"
                color="red"
                variant="solid"
                size="xs"
                class="ml-auto"
              >
                {{ item.badge }}
              </UBadge>
            </Transition>
          </NuxtLink>
        </li>
      </ul>
    </nav>

    <!-- 折叠按钮 -->
    <div class="p-3 border-t border-stone-200/50 dark:border-neutral-700/50">
      <button
        @click="adminUiStore.toggleSidebar()"
        class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-stone-500 dark:text-stone-400 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50 transition-colors"
      >
        <UIcon
          :name="adminUiStore.sidebarCollapsed ? 'heroicons:chevron-double-right' : 'heroicons:chevron-double-left'"
          class="w-5 h-5"
        />
        <Transition name="fade">
          <span v-if="!adminUiStore.sidebarCollapsed" class="text-sm">收起菜单</span>
        </Transition>
      </button>
    </div>
  </aside>

  <!-- 移动端侧边栏（抽屉） -->
  <USlideover v-model="adminUiStore.mobileSidebarOpen" side="left">
    <div class="flex flex-col h-full bg-white dark:bg-neutral-900">
      <!-- Logo 区域 -->
      <div class="h-16 flex items-center justify-between px-4 border-b border-stone-200 dark:border-neutral-700">
        <NuxtLink to="/" class="flex items-center gap-2.5" @click="adminUiStore.closeMobileSidebar()">
          <template v-if="seoSettings.logoMode === 'custom' && seoSettings.logoUrl">
            <img :src="seoSettings.logoUrl" :alt="displayName" class="w-9 h-9 rounded-lg object-contain" />
          </template>
          <template v-else>
            <div class="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
            </div>
          </template>
          <div class="flex items-center gap-2">
            <span class="text-lg font-semibold text-stone-800 dark:text-stone-100">{{ displayName }}</span>
            <UBadge color="red" variant="subtle" size="xs">管理</UBadge>
          </div>
        </NuxtLink>
        <UButton
          icon="heroicons:x-mark"
          color="gray"
          variant="ghost"
          @click="adminUiStore.closeMobileSidebar()"
        />
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 py-4 overflow-y-auto">
        <ul class="space-y-1 px-3">
          <li v-for="item in menu" :key="item.key">
            <NuxtLink
              :to="item.to"
              class="flex items-center gap-3 px-3 py-3 rounded-lg transition-all"
              :class="[
                isActive(item)
                  ? 'bg-gradient-to-r from-amber-500/10 to-orange-500/10 text-amber-600 dark:text-amber-400'
                  : 'text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-neutral-800'
              ]"
              @click="adminUiStore.closeMobileSidebar()"
            >
              <UIcon
                :name="item.icon"
                class="w-5 h-5"
                :class="[
                  isActive(item)
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-stone-500 dark:text-stone-400'
                ]"
              />
              <span class="font-medium">{{ item.label }}</span>
              <UBadge
                v-if="item.badge"
                color="red"
                variant="solid"
                size="xs"
                class="ml-auto"
              >
                {{ item.badge }}
              </UBadge>
            </NuxtLink>
          </li>
        </ul>
      </nav>
    </div>
  </USlideover>
</template>

<script setup lang="ts">
const adminUiStore = useAdminUiStore()
const { menu, isActive } = useAdminMenu()
const { seoSettings, displayName } = useSeoSettings()

// 路由变化时关闭移动端侧边栏
const route = useRoute()
watch(() => route.path, () => {
  adminUiStore.closeMobileSidebar()
})

// 恢复侧边栏状态
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
