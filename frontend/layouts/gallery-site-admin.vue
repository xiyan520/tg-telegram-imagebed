<template>
  <div class="min-h-screen flex flex-col bg-stone-50 dark:bg-neutral-950">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none" style="z-index: 0;">
      <div class="absolute inset-0 bg-gradient-to-br from-stone-100/50 via-transparent to-amber-50/30 dark:from-neutral-900/50 dark:via-transparent dark:to-amber-950/20"></div>
    </div>

    <!-- 顶部导航栏 -->
    <header class="sticky top-0 backdrop-blur-xl bg-white/80 dark:bg-neutral-900/80 border-b border-stone-200/60 dark:border-stone-700/60 shadow-sm" style="z-index: 100;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div class="flex items-center justify-between">
          <!-- 左侧：Logo + 标题 -->
          <NuxtLink to="/gallery-site/admin" class="flex items-center gap-3 group">
            <div class="relative">
              <div class="absolute inset-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl blur opacity-40 group-hover:opacity-60 transition-opacity"></div>
              <div class="relative w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center transform group-hover:scale-105 transition-all shadow-lg">
                <UIcon name="heroicons:cog-6-tooth" class="w-5 h-5 text-white" />
              </div>
            </div>
            <span class="text-lg font-bold font-serif bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent">
              {{ siteName }} · 管理
            </span>
          </NuxtLink>

          <!-- 中间导航链接 -->
          <nav class="hidden md:flex items-center gap-1">
            <NuxtLink
              to="/gallery-site/admin"
              :class="navLinkClass"
              active-class="!text-amber-600 dark:!text-amber-400 bg-amber-50 dark:bg-amber-900/20"
              :exact="true"
            >
              仪表板
            </NuxtLink>
            <NuxtLink
              to="/gallery-site/admin/settings"
              :class="navLinkClass"
              active-class="!text-amber-600 dark:!text-amber-400 bg-amber-50 dark:bg-amber-900/20"
            >
              站点设置
            </NuxtLink>
            <NuxtLink
              to="/gallery-site/admin/galleries"
              :class="navLinkClass"
              active-class="!text-amber-600 dark:!text-amber-400 bg-amber-50 dark:bg-amber-900/20"
            >
              画集管理
            </NuxtLink>
          </nav>

          <!-- 右侧：用户名 + 登出 + 暗色模式 + 移动端菜单 -->
          <div class="flex items-center gap-2">
            <span class="hidden sm:inline text-sm text-stone-500 dark:text-stone-400">{{ adminUsername }}</span>
            <UButton
              icon="heroicons:arrow-right-on-rectangle"
              color="gray"
              variant="ghost"
              size="sm"
              title="登出"
              @click="handleLogout"
            />
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
        <div v-if="mobileMenuOpen" class="md:hidden mt-3 pt-3 border-t border-stone-200 dark:border-stone-700 space-y-1">
          <NuxtLink
            to="/gallery-site/admin"
            class="block px-4 py-2.5 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            仪表板
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/admin/settings"
            class="block px-4 py-2.5 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            站点设置
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/admin/galleries"
            class="block px-4 py-2.5 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            @click="mobileMenuOpen = false"
          >
            画集管理
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1 relative" style="z-index: 10;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <slot />
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="relative border-t border-stone-200/60 dark:border-stone-700/60" style="z-index: 10;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <p class="text-center text-xs text-stone-400 dark:text-stone-500">
          {{ siteName }} · 管理
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const colorMode = useColorMode()
const mobileMenuOpen = ref(false)
const router = useRouter()

const adminUsername = useState<string>('gallery-site-admin-username', () => '')

// 从缓存的站点模式中获取画集站点名称
const siteMode = useState<{ mode: string; site_name?: string } | null>('gallery-site-mode', () => null)
const siteName = computed(() => siteMode.value?.site_name || '画集')

// 画集管理后台独立的浏览器标题，不跟随主站
useHead(computed(() => ({
  title: `${siteName.value} · 管理`,
})))

const navLinkClass = 'px-4 py-2 text-sm font-medium text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-colors hover:bg-amber-50 dark:hover:bg-amber-900/20'

/** 切换深色/浅色模式 */
const toggleColorMode = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}

/** 登出 */
const handleLogout = async () => {
  try {
    const { logout } = useGallerySiteAdmin()
    await logout()
  } catch {
    // 忽略登出错误
  }
  adminUsername.value = ''
  router.push('/gallery-site/')
}
</script>
