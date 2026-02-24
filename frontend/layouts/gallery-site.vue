<template>
  <div class="min-h-screen flex flex-col bg-stone-50 dark:bg-neutral-950">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none" style="z-index: 0;">
      <div class="absolute inset-0 bg-gradient-to-br from-stone-100/50 via-transparent to-amber-50/30 dark:from-neutral-900/50 dark:via-transparent dark:to-amber-950/20"></div>
      <div class="absolute top-0 right-1/4 w-px h-full bg-gradient-to-b from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent"></div>
      <div class="absolute top-1/3 left-0 w-full h-px bg-gradient-to-r from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent"></div>
    </div>

    <!-- 顶部导航栏 -->
    <header class="sticky top-0 backdrop-blur-xl bg-white/80 dark:bg-neutral-900/80 border-b border-stone-200/60 dark:border-stone-700/60 shadow-sm" style="z-index: 100;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <!-- 站点名称 -->
          <NuxtLink to="/gallery-site/" class="flex items-center gap-3 group">
            <div class="relative">
              <div class="absolute inset-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl blur opacity-40 group-hover:opacity-60 transition-opacity"></div>
              <div class="relative w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center transform group-hover:scale-105 transition-all shadow-lg">
                <UIcon name="heroicons:photo" class="w-5 h-5 text-white" />
              </div>
            </div>
            <span class="text-xl font-bold font-serif bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent">
              {{ siteName }}
            </span>
          </NuxtLink>

          <!-- 导航链接 -->
          <nav class="hidden md:flex items-center gap-1">
            <NuxtLink
              to="/gallery-site/"
              class="px-4 py-2 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-colors hover:bg-amber-50 dark:hover:bg-amber-900/20"
              active-class="!text-amber-600 dark:!text-amber-400 bg-amber-50 dark:bg-amber-900/20"
            >
              首页
            </NuxtLink>
            <NuxtLink
              to="/gallery-site/galleries"
              class="px-4 py-2 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-colors hover:bg-amber-50 dark:hover:bg-amber-900/20"
              active-class="!text-amber-600 dark:!text-amber-400 bg-amber-50 dark:bg-amber-900/20"
            >
              画集
            </NuxtLink>
          </nav>

          <!-- 右侧：管理按钮 + 深色模式切换 + 移动端菜单 -->
          <div class="flex items-center gap-2">
            <!-- 管理后台入口 -->
            <NuxtLink
              to="/gallery-site/admin"
              class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30 rounded-lg transition-colors"
            >
              <UIcon name="heroicons:cog-6-tooth" class="w-4 h-4" />
              管理
            </NuxtLink>
            <UButton
              :icon="colorMode.value === 'dark' ? 'heroicons:sun' : 'heroicons:moon'"
              color="gray"
              variant="ghost"
              size="sm"
              aria-label="切换深色模式"
              @click="toggleColorMode"
            />
            <button
              class="md:hidden p-2 text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors"
              @click="mobileMenuOpen = !mobileMenuOpen"
            >
              <UIcon :name="mobileMenuOpen ? 'heroicons:x-mark' : 'heroicons:bars-3'" class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- 移动端菜单 -->
        <div v-if="mobileMenuOpen" class="md:hidden mt-4 pt-4 border-t border-stone-200 dark:border-stone-700 space-y-1">
          <NuxtLink
            to="/gallery-site/"
            class="block px-4 py-2.5 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            首页
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/galleries"
            class="block px-4 py-2.5 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            画集
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/admin"
            class="block px-4 py-2.5 text-sm font-medium text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            <span class="flex items-center gap-1.5">
              <UIcon name="heroicons:cog-6-tooth" class="w-4 h-4" />
              管理后台
            </span>
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1 relative" style="z-index: 10;">
      <slot />
    </main>

    <!-- 页脚 -->
    <footer class="relative border-t border-stone-200/60 dark:border-stone-700/60" style="z-index: 10;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <p class="text-center text-sm text-stone-400 dark:text-stone-500">
          &copy; {{ new Date().getFullYear() }} {{ siteName }}
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const colorMode = useColorMode()
const mobileMenuOpen = ref(false)

// 从缓存的站点模式中获取站点名称
const siteMode = useState<{ mode: string; site_name?: string } | null>('gallery-site-mode', () => null)
const siteName = computed(() => siteMode.value?.site_name || '画集')

/** 切换深色/浅色模式 */
const toggleColorMode = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>
