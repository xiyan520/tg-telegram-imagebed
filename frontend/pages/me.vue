<template>
  <div class="space-y-6">
    <!-- 用户信息卡片 -->
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500 p-6 text-white shadow-lg">
      <div class="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg%20width%3D%2220%22%20height%3D%2220%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Ccircle%20cx%3D%2210%22%20cy%3D%2210%22%20r%3D%221.5%22%20fill%3D%22white%22%2F%3E%3C%2Fsvg%3E')] opacity-10" />
      <div class="relative flex items-center gap-4">
        <!-- TG 头像或 Token 图标 -->
        <div v-if="tgAuth.isLoggedIn && tgAuth.user" class="w-14 h-14 rounded-full bg-white/20 backdrop-blur flex items-center justify-center text-2xl font-bold flex-shrink-0">
          {{ (tgAuth.user.first_name || 'U')[0] }}
        </div>
        <div v-else class="w-14 h-14 rounded-full bg-white/20 backdrop-blur flex items-center justify-center flex-shrink-0">
          <UIcon name="heroicons:key" class="w-7 h-7" />
        </div>
        <div class="flex-1 min-w-0">
          <h1 class="text-xl font-bold truncate">
            {{ tgAuth.isLoggedIn && tgAuth.user ? tgAuth.user.first_name : '游客控制台' }}
            <span v-if="tgAuth.isLoggedIn && tgAuth.user?.username" class="text-white/70 text-sm font-normal ml-1">@{{ tgAuth.user.username }}</span>
          </h1>
          <p class="text-white/80 text-sm mt-0.5">
            {{ tokenStore.vaultItems.length }} 个 Token · {{ tokenStore.uploadCount }} 次上传
          </p>
          <!-- 配额进度条 -->
          <div v-if="tokenStore.hasToken && tokenStore.uploadLimit > 0" class="mt-2">
            <div class="flex justify-between text-xs text-white/70 mb-1">
              <span>配额使用</span>
              <span>{{ tokenStore.uploadCount }} / {{ tokenStore.uploadLimit }}</span>
            </div>
            <div class="h-1.5 bg-white/20 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="quotaPercent > 90 ? 'bg-red-300' : quotaPercent > 70 ? 'bg-orange-300' : 'bg-white/80'"
                :style="{ width: `${Math.min(100, quotaPercent)}%` }"
              />
            </div>
          </div>
        </div>
        <UButton color="white" variant="ghost" size="sm" icon="heroicons:arrow-right-start-on-rectangle" @click="handleLogout" class="flex-shrink-0 text-white/80 hover:text-white" />
      </div>
    </div>

    <!-- 无 Token 引导 -->
    <UCard v-if="!tokenStore.hasToken" class="shadow-lg">
      <div class="text-center py-8 space-y-4">
        <div class="w-16 h-16 mx-auto bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl flex items-center justify-center">
          <UIcon name="heroicons:key" class="w-8 h-8 text-white" />
        </div>
        <div v-if="tgAuth.isLoggedIn">
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">暂无 Token</h2>
          <p class="text-gray-600 dark:text-gray-400 mb-4">生成一个 Token 开始使用</p>
          <UButton color="primary" :loading="generatingToken" @click="handleQuickGenerate">生成 Token</UButton>
        </div>
        <div v-else>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">尚未登录</h2>
          <p class="text-gray-600 dark:text-gray-400 mb-4">请先登录以使用控制台功能</p>
          <UButton color="primary" @click="navigateTo('/')">返回首页登录</UButton>
        </div>
      </div>
    </UCard>

    <!-- 主内容 -->
    <template v-if="tokenStore.hasToken">
      <!-- Tab 导航 -->
      <div class="flex gap-1 p-1 bg-white/60 dark:bg-neutral-800/60 backdrop-blur-sm rounded-xl border border-stone-200/50 dark:border-neutral-700/50">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="relative flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all flex-1 justify-center"
          :class="activeTab === tab.key
            ? 'bg-amber-500 text-white shadow-sm shadow-amber-500/25'
            : 'text-stone-500 dark:text-stone-400 hover:text-stone-700 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-700/50'"
          @click="activeTab = tab.key"
        >
          <UIcon :name="tab.icon" class="w-4 h-4" />
          <span class="hidden sm:inline">{{ tab.label }}</span>
          <!-- TG 未绑定红点 -->
          <span
            v-if="tab.key === 'tg' && tgAuth.isLoggedIn && hasUnboundTokens"
            class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full"
          />
        </button>
      </div>

      <!-- Token 管理 -->
      <MeTokenPanel v-if="activeTab === 'tokens'" />

      <!-- 我的上传 -->
      <template v-if="activeTab === 'uploads'">
        <AlbumMyUploads :key="'uploads-' + refreshKey" @view-image="openLightbox" @navigate="() => {}" />
      </template>

      <!-- 画集 -->
      <template v-if="activeTab === 'galleries'">
        <AlbumGalleryList
          v-if="galleryView === 'list'"
          :key="'gallery-list-' + refreshKey"
          @navigate="handleGalleryNavigate"
        />
        <AlbumGalleryDetail
          v-else-if="galleryView === 'detail' && activeGalleryId"
          :key="'gallery-detail-' + activeGalleryId + '-' + refreshKey"
          :gallery-id="activeGalleryId"
          @navigate="handleGalleryNavigate"
          @view-image="openLightbox"
        />
      </template>

      <!-- TG 绑定 -->
      <MeTgBindPanel v-if="activeTab === 'tg'" />
    </template>

    <!-- 灯箱 -->
    <GalleryLightbox v-model:open="lightboxOpen" v-model:index="lightboxIndex" :images="lightboxImages" />
  </div>
</template>

<!-- PLACEHOLDER_SCRIPT -->
<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'

const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const { publicSettings, loadSettings, logout } = useGuestAuth()

// Tab 配置（TG 绑定 tab 仅在有实际意义时显示）
const allTabs = [
  { key: 'tokens', label: 'Token 管理', icon: 'heroicons:key' },
  { key: 'uploads', label: '我的上传', icon: 'heroicons:cloud-arrow-up' },
  { key: 'galleries', label: '画集', icon: 'heroicons:photo' },
  { key: 'tg', label: 'TG 绑定', icon: 'heroicons:chat-bubble-left-right' },
] as const

type TabKey = typeof allTabs[number]['key']
const activeTab = ref<TabKey>('tokens')

const tabs = computed(() =>
  allTabs.filter(t => t.key !== 'tg' || publicSettings.value.tgBindEnabled || publicSettings.value.tgAuthRequired)
)

// 配额百分比
const quotaPercent = computed(() => {
  if (!tokenStore.uploadLimit) return 0
  return Math.round((tokenStore.uploadCount / tokenStore.uploadLimit) * 100)
})

// 是否有未绑定 TG 的 Token
const hasUnboundTokens = computed(() =>
  tgAuth.isLoggedIn && tokenStore.vaultItems.some(i => !i.tokenInfo?.tg_user_id)
)

// 灯箱
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxImages = ref<GalleryImage[]>([])

// 画集子视图
const galleryView = ref<'list' | 'detail'>('list')
const activeGalleryId = ref<number | null>(null)

// 刷新 key
const refreshKey = ref(0)

// 快速生成 Token（TG 已登录但无 Token 时使用）
const generatingToken = ref(false)
const toast = useLightToast()
const handleQuickGenerate = async () => {
  generatingToken.value = true
  try {
    await tokenStore.generateToken()
    tgAuth.checkSession()
    toast.success('Token 已生成')
  } catch (e: any) {
    toast.error(e.message || '生成 Token 失败')
  } finally {
    generatingToken.value = false
  }
}

const handleGalleryNavigate = (view: string, galleryId?: number) => {
  if (view === 'detail' && galleryId) {
    activeGalleryId.value = galleryId
    galleryView.value = 'detail'
  } else {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
}

const openLightbox = (images: GalleryImage[], index: number) => {
  lightboxImages.value = images
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const handleLogout = async () => {
  await logout()
  navigateTo('/')
}

// Token 切换时刷新
watch(() => tokenStore.token, (n, o) => {
  if (n === o) return
  galleryView.value = 'list'
  activeGalleryId.value = null
  refreshKey.value++
})

// 切换画集 tab 时重置子视图
watch(activeTab, (tab) => {
  if (tab === 'galleries') {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
})

// 删除最后一个 Token 后：TG 已登录用户留在控制台，否则跳转首页
watch(() => tokenStore.hasToken, (has) => {
  if (!has && !tgAuth.isLoggedIn) navigateTo('/')
})

onMounted(async () => {
  await tokenStore.restoreToken()
  // 加载公共设置
  await loadSettings()
  // TG 认证启用时恢复会话
  if (publicSettings.value.tgAuthEnabled) {
    await tgAuth.checkSession()
    // TG 已登录时，自动同步该用户下所有 Token 到本地 vault
    if (tgAuth.isLoggedIn) {
      await tgAuth.syncTokensToVault()
    }
  }
  // 无 Token 且未 TG 登录 → 跳转首页
  if (!tokenStore.hasToken && !tgAuth.isLoggedIn) {
    navigateTo('/')
    return
  }
})
</script>
