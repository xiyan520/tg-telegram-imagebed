<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">游客控制台</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">管理你的 Token、上传和画集</p>
      </div>
      <UButton color="red" variant="ghost" size="sm" icon="heroicons:arrow-right-start-on-rectangle" @click="handleLogout">
        登出
      </UButton>
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
      <div class="flex gap-1 p-1 bg-stone-100 dark:bg-neutral-800 rounded-xl">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all flex-1 justify-center"
          :class="activeTab === tab.key
            ? 'bg-white dark:bg-neutral-700 text-stone-900 dark:text-white shadow-sm'
            : 'text-stone-500 dark:text-stone-400 hover:text-stone-700 dark:hover:text-stone-300'"
          @click="activeTab = tab.key"
        >
          <UIcon :name="tab.icon" class="w-4 h-4" />
          <span class="hidden sm:inline">{{ tab.label }}</span>
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
          :upload-count="tokenStore.uploadCount"
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
  }
  // 无 Token 且未 TG 登录 → 跳转首页
  if (!tokenStore.hasToken && !tgAuth.isLoggedIn) {
    navigateTo('/')
    return
  }
})
</script>
