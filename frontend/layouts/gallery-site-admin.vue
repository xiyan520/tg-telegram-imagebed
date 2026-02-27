<template>
  <div class="min-h-screen bg-stone-50 text-stone-900 dark:bg-neutral-950 dark:text-white">
    <div class="pointer-events-none fixed inset-0 overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-stone-100/70 via-transparent to-amber-50/45 dark:from-neutral-900/60 dark:to-amber-950/20" />
      <div class="absolute -left-24 top-0 h-64 w-64 rounded-full bg-amber-300/20 blur-3xl dark:bg-amber-700/10" />
      <div class="absolute right-0 top-1/3 h-72 w-72 rounded-full bg-orange-300/15 blur-3xl dark:bg-orange-700/10" />
    </div>

    <header class="sticky top-0 z-50 border-b border-stone-200/70 bg-white/85 backdrop-blur-2xl dark:border-stone-700/70 dark:bg-neutral-900/85">
      <div class="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between gap-3">
          <NuxtLink to="/gallery-site/" class="group flex min-w-0 items-center gap-3">
            <div class="relative">
              <div class="absolute inset-0 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 blur opacity-40 transition-opacity group-hover:opacity-60" />
              <div class="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 shadow-lg transition-transform group-hover:scale-105">
                <UIcon name="heroicons:cog-6-tooth" class="h-5 w-5 text-white" />
              </div>
            </div>
            <div class="min-w-0">
              <p class="truncate text-base font-bold font-serif bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent dark:from-amber-400 dark:to-orange-400 sm:text-lg">
                {{ siteName }} · 管理
              </p>
              <p class="hidden text-xs text-stone-500 dark:text-stone-400 sm:block">Gallery Site Admin Console</p>
            </div>
          </NuxtLink>

          <nav class="hidden items-center gap-1 md:flex">
            <NuxtLink
              to="/gallery-site/admin"
              :class="navLinkClass"
              active-class="!text-amber-700 dark:!text-amber-300 bg-amber-50/80 dark:bg-amber-900/30"
              :exact="true"
            >
              仪表板
            </NuxtLink>
            <NuxtLink
              to="/gallery-site/admin/settings"
              :class="navLinkClass"
              active-class="!text-amber-700 dark:!text-amber-300 bg-amber-50/80 dark:bg-amber-900/30"
            >
              站点设置
            </NuxtLink>
            <NuxtLink
              to="/gallery-site/admin/galleries"
              :class="navLinkClass"
              active-class="!text-amber-700 dark:!text-amber-300 bg-amber-50/80 dark:bg-amber-900/30"
            >
              画集管理
            </NuxtLink>
          </nav>

          <div class="flex items-center gap-1.5 sm:gap-2">
            <span class="hidden rounded-full border border-stone-200 bg-stone-100 px-2.5 py-1 text-xs text-stone-500 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300 lg:inline">
              {{ adminUsername || '管理员' }}
            </span>
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
              class="rounded-lg p-2 text-stone-600 transition-colors hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800 md:hidden"
              @click="mobileMenuOpen = !mobileMenuOpen"
            >
              <UIcon :name="mobileMenuOpen ? 'heroicons:x-mark' : 'heroicons:bars-3'" class="h-5 w-5" />
            </button>
          </div>
        </div>

        <div v-if="mobileMenuOpen" class="mt-3 space-y-1 border-t border-stone-200 pt-3 dark:border-stone-700 md:hidden">
          <NuxtLink
            to="/gallery-site/admin"
            class="block rounded-xl px-4 py-2.5 text-sm font-medium text-stone-600 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:text-stone-300 dark:hover:bg-amber-900/25 dark:hover:text-amber-400"
            @click="mobileMenuOpen = false"
          >
            仪表板
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/admin/settings"
            class="block rounded-xl px-4 py-2.5 text-sm font-medium text-stone-600 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:text-stone-300 dark:hover:bg-amber-900/25 dark:hover:text-amber-400"
            @click="mobileMenuOpen = false"
          >
            站点设置
          </NuxtLink>
          <NuxtLink
            to="/gallery-site/admin/galleries"
            class="block rounded-xl px-4 py-2.5 text-sm font-medium text-stone-600 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:text-stone-300 dark:hover:bg-amber-900/25 dark:hover:text-amber-400"
            @click="mobileMenuOpen = false"
          >
            画集管理
          </NuxtLink>
        </div>
      </div>
    </header>

    <main class="relative z-10 flex-1">
      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <slot />
      </div>
    </main>

    <footer class="relative z-10 border-t border-stone-200/70 dark:border-stone-700/70">
      <div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <p class="text-center text-xs text-stone-400 dark:text-stone-500">
          {{ siteName }} · Admin Console
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

const navLinkClass = 'rounded-lg px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-amber-50/80 hover:text-amber-700 dark:text-stone-300 dark:hover:bg-amber-900/25 dark:hover:text-amber-300'

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
