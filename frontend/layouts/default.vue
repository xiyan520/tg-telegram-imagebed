<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-neutral-950 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none bg-gray-50 dark:bg-neutral-950" style="z-index: 0;">
      <!-- 完整网格背景 -->
      <div class="absolute inset-0 grid-background-full"></div>

      <!-- 网格装饰点 - 突出显示某些网格交叉点 -->
      <div class="absolute top-20 left-20 w-2 h-2 bg-amber-400/60 dark:bg-amber-500/40 rounded-full animate-pulse-slow"></div>
      <div class="absolute top-40 right-32 w-2 h-2 bg-orange-400/50 dark:bg-orange-500/35 rounded-full animate-pulse-slow animation-delay-1000"></div>
      <div class="absolute bottom-32 left-40 w-2 h-2 bg-amber-400/55 dark:bg-amber-500/38 rounded-full animate-pulse-slow animation-delay-2000"></div>
      <div class="absolute top-1/3 right-1/4 w-2 h-2 bg-orange-400/50 dark:bg-orange-500/35 rounded-full animate-pulse-slow animation-delay-3000"></div>
      <div class="absolute bottom-1/4 right-1/3 w-2 h-2 bg-amber-400/60 dark:bg-amber-500/40 rounded-full animate-pulse-slow animation-delay-4000"></div>

      <!-- 网格区域高亮 - 矩形高亮区域 -->
      <div class="absolute top-10 right-10 w-96 h-64 border-2 border-amber-300/20 dark:border-amber-600/15 bg-amber-50/5 dark:bg-amber-900/5 rounded-lg animate-float"></div>
      <div class="absolute bottom-20 left-10 w-80 h-56 border-2 border-orange-300/15 dark:border-orange-600/12 bg-orange-50/5 dark:bg-orange-900/5 rounded-lg rotate-3 animate-float animation-delay-2000"></div>
      <div class="absolute top-1/2 left-1/4 w-72 h-48 border border-amber-300/15 dark:border-amber-600/12 bg-amber-50/3 dark:bg-amber-900/3 rounded-lg -rotate-2 animate-float animation-delay-4000"></div>

      <!-- 网格线条强调 - 垂直和水平线 -->
      <div class="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-amber-300/20 dark:via-amber-600/15 to-transparent"></div>
      <div class="absolute top-0 right-1/3 w-px h-full bg-gradient-to-b from-transparent via-orange-300/15 dark:via-orange-600/12 to-transparent"></div>
      <div class="absolute top-1/4 left-0 w-full h-px bg-gradient-to-r from-transparent via-amber-300/20 dark:via-amber-600/15 to-transparent"></div>
      <div class="absolute bottom-1/3 left-0 w-full h-px bg-gradient-to-r from-transparent via-orange-300/15 dark:via-orange-600/12 to-transparent"></div>

      <!-- 网格节点装饰 - 大型节点 -->
      <div class="absolute top-1/4 left-1/4 w-4 h-4 border-2 border-amber-400/40 dark:border-amber-500/30 bg-amber-100/20 dark:bg-amber-900/15 rounded-full animate-pulse-slow"></div>
      <div class="absolute top-1/3 right-1/3 w-3 h-3 border-2 border-orange-400/35 dark:border-orange-500/25 bg-orange-100/20 dark:bg-orange-900/15 rounded-full animate-pulse-slow animation-delay-2000"></div>
      <div class="absolute bottom-1/4 right-1/4 w-4 h-4 border-2 border-amber-400/40 dark:border-amber-500/30 bg-amber-100/20 dark:bg-amber-900/15 rounded-full animate-pulse-slow animation-delay-4000"></div>
    </div>

    <!-- 顶部导航栏 -->
    <header class="sticky top-0 backdrop-blur-xl bg-white/80 dark:bg-neutral-900/80 border-b border-gray-200/60 dark:border-gray-700/60 relative shadow-sm" style="z-index: 100;">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <!-- Logo -->
          <NuxtLink to="/" class="flex items-center gap-3 group">
            <div class="relative">
              <div class="absolute inset-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl blur opacity-50 group-hover:opacity-75 transition-opacity"></div>
              <div class="relative w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center transform group-hover:scale-105 group-hover:rotate-3 transition-all shadow-lg">
                <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
              </div>
            </div>
            <div>
              <span class="text-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent">
                图床 Pro
              </span>
            </div>
          </NuxtLink>

          <!-- 导航菜单 -->
          <nav class="hidden md:flex items-center gap-2">
            <NuxtLink to="/" class="relative px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-all group">
              <span class="relative z-10">首页</span>
              <div class="absolute inset-0 bg-amber-50 dark:bg-amber-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </NuxtLink>
            <NuxtLink to="/gallery" class="relative px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-all group">
              <span class="relative z-10">画廊</span>
              <div class="absolute inset-0 bg-amber-50 dark:bg-amber-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </NuxtLink>
            <NuxtLink to="/guest" class="relative px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-all group">
              <span class="relative z-10">Token</span>
              <div class="absolute inset-0 bg-amber-50 dark:bg-amber-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </NuxtLink>
            <NuxtLink to="/docs" class="relative px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg transition-all group">
              <span class="relative z-10">文档</span>
              <div class="absolute inset-0 bg-amber-50 dark:bg-amber-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </NuxtLink>
            <div class="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-2"></div>
            <NuxtLink to="/admin" class="relative px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 rounded-lg transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5">
              管理
            </NuxtLink>
          </nav>

          <!-- 移动端菜单按钮 -->
          <button
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="md:hidden p-2.5 text-stone-600 dark:text-stone-300 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all"
          >
            <UIcon :name="mobileMenuOpen ? 'heroicons:x-mark' : 'heroicons:bars-3'" class="w-6 h-6" />
          </button>
        </div>

        <!-- 移动端菜单 -->
        <div v-if="mobileMenuOpen" class="md:hidden mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
          <NuxtLink to="/" class="block px-4 py-2.5 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all">
            首页
          </NuxtLink>
          <NuxtLink to="/gallery" class="block px-4 py-2.5 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all">
            画廊
          </NuxtLink>
          <NuxtLink to="/guest" class="block px-4 py-2.5 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all">
            Token
          </NuxtLink>
          <NuxtLink to="/docs" class="block px-4 py-2.5 text-sm font-medium text-stone-700 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all">
            文档
          </NuxtLink>
          <NuxtLink to="/admin" class="block px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 rounded-lg transition-all text-center shadow-md">
            管理
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1 container mx-auto px-4 py-8 relative" style="z-index: 10;">
      <slot />
    </main>

    <!-- 实时统计 - 位于页脚上方 -->
    <section class="relative container mx-auto px-4 pb-8" style="z-index: 10;">
      <div class="space-y-4">
        <h2 class="text-xl font-bold text-stone-900 dark:text-white">实时统计</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <!-- 总文件 -->
          <div class="group relative overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 hover:border-amber-300 dark:hover:border-amber-600 transition-all hover:shadow-lg">
            <div class="absolute top-0 right-0 w-20 h-20 bg-amber-500/5 dark:bg-amber-500/10 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"></div>
            <div class="relative">
              <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">总文件</p>
              <p class="text-3xl font-bold text-stone-900 dark:text-white">
                {{ stats.totalFiles || "--" }}
              </p>
            </div>
          </div>

          <!-- 存储空间 -->
          <div class="group relative overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 hover:border-amber-300 dark:hover:border-amber-600 transition-all hover:shadow-lg">
            <div class="absolute top-0 right-0 w-20 h-20 bg-amber-500/5 dark:bg-amber-500/10 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"></div>
            <div class="relative">
              <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">存储空间</p>
              <p class="text-3xl font-bold text-stone-900 dark:text-white">
                {{ stats.totalSize || "--" }}
              </p>
            </div>
          </div>

          <!-- 今日上传 -->
          <div class="group relative overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 hover:border-amber-300 dark:hover:border-amber-600 transition-all hover:shadow-lg">
            <div class="absolute top-0 right-0 w-20 h-20 bg-amber-500/5 dark:bg-amber-500/10 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"></div>
            <div class="relative">
              <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">今日上传</p>
              <p class="text-3xl font-bold text-stone-900 dark:text-white">
                {{ stats.todayUploads || "--" }}
              </p>
            </div>
          </div>

          <!-- 运行时间 -->
          <div class="group relative overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 hover:border-amber-300 dark:hover:border-amber-600 transition-all hover:shadow-lg">
            <div class="absolute top-0 right-0 w-20 h-20 bg-amber-500/5 dark:bg-amber-500/10 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"></div>
            <div class="relative">
              <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">运行时间</p>
              <p class="text-3xl font-bold text-stone-900 dark:text-white">
                {{ stats.uptime || "--" }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="relative" style="z-index: 10;">
      <div class="container mx-auto px-4 py-6">
        <div class="text-center text-sm text-stone-400 dark:text-neutral-500">
          &copy; {{ new Date().getFullYear() }} 图床 Pro
        </div>
      </div>
    </footer>

    <!-- 公告弹窗 -->
    <AnnouncementModal />
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const mobileMenuOpen = ref(false)
const guestStore = useGuestTokenStore()
const { getStats } = useImageApi()
const { onStatsRefresh } = useStatsRefresh()

// 统计数据
const stats = ref<any>({})

// 加载统计信息
const loadStats = async () => {
  try {
    stats.value = await getStats()
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 定时刷新统计数据
let statsRefreshInterval: NodeJS.Timeout | null = null

// 页面加载时恢复游客token和加载统计
onMounted(async () => {
  guestStore.restoreToken()
  await loadStats()

  // 监听全局统计刷新事件
  onStatsRefresh(() => {
    loadStats()
  })

  // 每30秒自动刷新统计数据
  statsRefreshInterval = setInterval(() => {
    loadStats()
  }, 30000)
})

// 页面卸载时清除定时器
onUnmounted(() => {
  if (statsRefreshInterval) {
    clearInterval(statsRefreshInterval)
  }
})
</script>

<style scoped>
/* 完整网格背景 - 覆盖整个页面 */
.grid-background-full {
  background-color: rgb(249 250 251 / 1); /* matches Tailwind bg-gray-50 */
  background-image:
    linear-gradient(to right, rgb(209 213 219 / 0.8) 1px, transparent 1px),
    linear-gradient(to bottom, rgb(209 213 219 / 0.8) 1px, transparent 1px);
  background-size: 3rem 3rem;
  /* 移除遮罩,显示完整网格 */
}

:global(.dark) .grid-background-full {
  background-color: rgb(10 10 10 / 1); /* matches Tailwind dark:bg-neutral-950 */
  background-image:
    linear-gradient(to right, rgb(82 82 91 / 0.6) 1px, transparent 1px),
    linear-gradient(to bottom, rgb(82 82 91 / 0.6) 1px, transparent 1px);
}

/* 光晕动画 - 更流畅 */
@keyframes blob {
  0%, 100% {
    transform: translate(0px, 0px) scale(1);
  }
  25% {
    transform: translate(40px, -60px) scale(1.15);
  }
  50% {
    transform: translate(-30px, 40px) scale(0.95);
  }
  75% {
    transform: translate(20px, 30px) scale(1.05);
  }
}

.animate-blob {
  animation: blob 12s ease-in-out infinite;
}

/* 浮动动画 */
@keyframes float {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(5deg);
  }
}

.animate-float {
  animation: float 8s ease-in-out infinite;
}

/* 慢速旋转 */
@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 30s linear infinite;
}

/* 慢速脉冲 */
@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.05);
  }
}

.animate-pulse-slow {
  animation: pulse-slow 4s ease-in-out infinite;
}

/* 动画延迟 */
.animation-delay-1000 {
  animation-delay: 1s;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

.animation-delay-3000 {
  animation-delay: 3s;
}

.animation-delay-4000 {
  animation-delay: 4s;
}

.animation-delay-6000 {
  animation-delay: 6s;
}
</style>
