<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-950">
    <!-- 头部 -->
    <header class="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-b border-stone-200/50 dark:border-neutral-700/50 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <NuxtLink to="/" class="flex items-center gap-2">
              <div class="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
              </div>
              <span class="text-lg font-semibold text-stone-800 dark:text-stone-100">图床 Pro</span>
            </NuxtLink>
            <span class="text-stone-400 dark:text-stone-500">/</span>
            <span class="text-stone-600 dark:text-stone-300">分享画集</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="max-w-7xl mx-auto px-4 py-8">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex flex-col justify-center items-center py-32">
        <div class="w-16 h-16 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-stone-600 dark:text-stone-400">加载中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="text-center py-32">
        <div class="w-24 h-24 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-500" />
        </div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">无法访问</h1>
        <p class="text-stone-600 dark:text-stone-400 mb-6">{{ error }}</p>
        <UButton to="/" color="primary">返回首页</UButton>
      </div>

      <!-- 画集内容 -->
      <div v-else-if="galleryData" class="space-y-6">
        <!-- 画集信息 -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-stone-900 dark:text-white mb-2">{{ galleryData.gallery.name }}</h1>
          <p v-if="galleryData.gallery.description" class="text-stone-600 dark:text-stone-400 max-w-2xl mx-auto">
            {{ galleryData.gallery.description }}
          </p>
          <p class="text-sm text-stone-500 dark:text-stone-500 mt-2">
            共 {{ galleryData.gallery.image_count }} 张图片
          </p>
        </div>

        <!-- 图片网格 -->
        <div v-if="galleryData.images.length === 0" class="text-center py-16">
          <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-400" />
          </div>
          <p class="text-lg font-medium text-stone-900 dark:text-white">画集暂无图片</p>
        </div>

        <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          <div
            v-for="(image, index) in galleryData.images"
            :key="image.encrypted_id"
            class="group relative aspect-square rounded-xl overflow-hidden border border-stone-200 dark:border-neutral-700 hover:shadow-lg transition-all cursor-pointer"
            @click="openLightbox(index)"
          >
            <img
              :src="image.image_url"
              :alt="image.original_filename"
              loading="lazy"
              class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
            />
            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <UIcon name="heroicons:magnifying-glass-plus" class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="galleryData.has_more" class="text-center pt-4">
          <UButton color="gray" variant="outline" :loading="loadingMore" @click="loadMore">
            加载更多
          </UButton>
        </div>
      </div>
    </main>

    <!-- 图片灯箱 -->
    <UModal v-model="lightboxOpen" :ui="{ width: 'sm:max-w-5xl' }">
      <div class="relative bg-black rounded-lg overflow-hidden">
        <img
          v-if="currentImage"
          :src="currentImage.image_url"
          :alt="currentImage.original_filename"
          class="w-full max-h-[80vh] object-contain"
        />
        <div class="absolute top-4 right-4 flex gap-2">
          <UButton
            icon="heroicons:arrow-down-tray"
            color="white"
            variant="solid"
            size="sm"
            @click="downloadImage"
          />
          <UButton
            icon="heroicons:x-mark"
            color="white"
            variant="solid"
            size="sm"
            @click="lightboxOpen = false"
          />
        </div>
        <div v-if="galleryData && galleryData.images.length > 1" class="absolute inset-y-0 left-0 flex items-center">
          <UButton
            icon="heroicons:chevron-left"
            color="white"
            variant="ghost"
            size="lg"
            :disabled="lightboxIndex === 0"
            @click="lightboxIndex--"
          />
        </div>
        <div v-if="galleryData && galleryData.images.length > 1" class="absolute inset-y-0 right-0 flex items-center">
          <UButton
            icon="heroicons:chevron-right"
            color="white"
            variant="ghost"
            size="lg"
            :disabled="lightboxIndex >= galleryData.images.length - 1"
            @click="lightboxIndex++"
          />
        </div>
        <div class="absolute bottom-4 left-0 right-0 text-center">
          <p class="text-white/80 text-sm">{{ currentImage?.original_filename }}</p>
          <p v-if="galleryData" class="text-white/60 text-xs mt-1">{{ lightboxIndex + 1 }} / {{ galleryData.images.length }}</p>
        </div>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()

const shareToken = computed(() => route.params.token as string)

const loading = ref(true)
const error = ref('')
const galleryData = ref<{
  gallery: { name: string; description?: string; image_count: number }
  images: GalleryImage[]
  total: number
  page: number
  limit: number
  has_more: boolean
} | null>(null)

const page = ref(1)
const loadingMore = ref(false)

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

const currentImage = computed(() => {
  if (!galleryData.value || lightboxIndex.value < 0) return null
  return galleryData.value.images[lightboxIndex.value]
})

const loadGallery = async () => {
  loading.value = true
  error.value = ''
  try {
    galleryData.value = await galleryApi.getSharedGallery(shareToken.value, 1, 50)
    page.value = 1
  } catch (e: any) {
    error.value = e.message || '画集不存在或分享已关闭'
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (!galleryData.value?.has_more || loadingMore.value) return
  loadingMore.value = true
  try {
    const nextPage = page.value + 1
    const result = await galleryApi.getSharedGallery(shareToken.value, nextPage, 50)
    galleryData.value.images.push(...result.images)
    galleryData.value.has_more = result.has_more
    page.value = nextPage
  } catch (e: any) {
    console.error('加载更多失败:', e)
  } finally {
    loadingMore.value = false
  }
}

const openLightbox = (index: number) => {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const downloadImage = () => {
  if (!currentImage.value) return
  const link = document.createElement('a')
  link.href = currentImage.value.image_url
  link.download = currentImage.value.original_filename || 'image'
  link.target = '_blank'
  link.click()
}

onMounted(loadGallery)
</script>
