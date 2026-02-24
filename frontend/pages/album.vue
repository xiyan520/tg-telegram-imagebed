<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="text-center space-y-3">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        相册
      </h1>
      <p class="text-stone-600 dark:text-stone-400">
        通过 Token 管理你的图片和画集
      </p>
    </div>

    <!-- 无 Token 引导提示 -->
    <UCard v-if="!store.hasToken" class="shadow-lg">
      <div class="text-center py-8 space-y-4">
        <div class="w-16 h-16 mx-auto bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl flex items-center justify-center">
          <UIcon name="heroicons:photo" class="w-8 h-8 text-white" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">开始使用相册</h2>
          <p class="text-gray-600 dark:text-gray-400">
            请点击右上角「游客登录」按钮登录后使用相册功能
          </p>
        </div>
      </div>
    </UCard>

    <!-- 视图路由 -->
    <template v-if="store.hasToken">
      <AlbumGalleryList
        v-if="currentView === 'list'"
        ref="galleryListRef"
        :key="'gallery-list-' + refreshKey"
        @navigate="handleNavigate"
      />
      <AlbumGalleryDetail
        v-else-if="currentView === 'detail' && activeGalleryId"
        :key="'gallery-detail-' + activeGalleryId + '-' + refreshKey"
        :gallery-id="activeGalleryId"
        @navigate="handleNavigate"
        @view-image="openLightbox"
      />
    </template>

    <!-- 灯箱 -->
    <GalleryLightbox
      v-model:open="lightboxOpen"
      v-model:index="lightboxIndex"
      :images="lightboxImages"
    />
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'

const store = useTokenStore()

// 视图状态
const currentView = ref<'list' | 'detail'>('list')
const activeGalleryId = ref<number | null>(null)

// 子组件引用
const galleryListRef = ref<{ refresh: () => Promise<void> } | null>(null)

// 灯箱状态
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxImages = ref<GalleryImage[]>([])

// 刷新计数器：每次 +1 强制子组件重建
const refreshKey = ref(0)

const handleNavigate = (view: string, galleryId?: number) => {
  if (view === 'detail' && galleryId) {
    activeGalleryId.value = galleryId
    currentView.value = 'detail'
  } else {
    currentView.value = 'list'
    activeGalleryId.value = null
  }
}

const openLightbox = (images: GalleryImage[], index: number) => {
  lightboxImages.value = images
  lightboxIndex.value = index
  lightboxOpen.value = true
}

// Token 切换时：重置视图 + 强制刷新子组件
watch(() => store.token, (newToken, oldToken) => {
  if (newToken === oldToken) return
  currentView.value = 'list'
  activeGalleryId.value = null
  // 递增 key 强制子组件重建，确保 onMounted 重新触发
  refreshKey.value++
})

// 页面加载时恢复 Token
onMounted(async () => {
  await store.restoreToken()
})
</script>
