<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-950">
    <!-- 画集标题栏 -->
    <header class="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-b border-stone-200/50 dark:border-neutral-700/50 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <!-- 左侧：画集信息 -->
          <div class="flex items-center gap-3 min-w-0">
            <NuxtLink
              v-if="fromGalleries"
              :to="`/galleries/${fromGalleries}`"
              class="shrink-0 p-1.5 -ml-1.5 rounded-lg text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-neutral-800 transition-colors"
              title="返回全部画集"
            >
              <UIcon name="heroicons:arrow-left" class="w-5 h-5" />
            </NuxtLink>
            <div class="min-w-0">
              <h1 class="text-base sm:text-lg font-semibold text-stone-900 dark:text-white truncate">
                {{ galleryTitle }}
              </h1>
              <p class="text-xs sm:text-sm text-stone-500 dark:text-stone-400 truncate">
                <template v-if="galleryData">
                  共 {{ galleryData.gallery.image_count }} 张
                  <span v-if="galleryData.gallery.description" class="hidden md:inline"> · {{ galleryData.gallery.description }}</span>
                </template>
                <template v-else>加载中...</template>
              </p>
            </div>
          </div>

          <!-- 右侧：操作按钮 -->
          <div class="shrink-0 flex items-center gap-2">
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              :icon="copied ? 'heroicons:check' : 'heroicons:link'"
              aria-label="复制分享链接"
              @click="copyShareLink"
            >
              <span class="hidden sm:inline">{{ copied ? '已复制' : '复制链接' }}</span>
            </UButton>
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="heroicons:arrow-down-tray"
              :loading="downloadingAll"
              :disabled="!galleryData || galleryData.images.length === 0"
              aria-label="下载全部图片"
              @click="downloadAllImages"
            >
              <span class="hidden sm:inline">下载全部</span>
            </UButton>
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

      <!-- 密码解锁状态 -->
      <div v-else-if="requiresPassword" class="text-center py-32">
        <div class="w-24 h-24 bg-amber-100 dark:bg-amber-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <UIcon name="heroicons:lock-closed" class="w-12 h-12 text-amber-500" />
        </div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">{{ lockedGalleryName || '受保护的画集' }}</h1>
        <p class="text-stone-600 dark:text-stone-400 mb-6">此画集需要密码才能访问</p>
        <div class="max-w-xs mx-auto space-y-4">
          <UInput
            v-model="passwordInput"
            type="password"
            placeholder="请输入访问密码"
            size="lg"
            @keyup.enter="submitPassword"
          />
          <UButton color="primary" block :loading="unlocking" :disabled="!passwordInput" @click="submitPassword">
            解锁
          </UButton>
          <p v-if="unlockError" class="text-sm text-red-500">{{ unlockError }}</p>
        </div>
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
        <!-- 空状态 -->
        <div v-if="galleryData.images.length === 0" class="text-center py-16">
          <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-400" />
          </div>
          <p class="text-lg font-medium text-stone-900 dark:text-white">画集暂无图片</p>
        </div>

        <!-- 瀑布流布局 -->
        <div v-else class="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 [column-gap:1rem]">
          <button
            v-for="(image, index) in galleryData.images"
            :key="image.encrypted_id"
            type="button"
            class="group mb-4 w-full break-inside-avoid rounded-xl overflow-hidden border border-stone-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:shadow-lg transition-shadow text-left block"
            @click="openLightbox(index)"
          >
            <div class="relative">
              <img
                :src="image.image_url"
                :alt="image.original_filename"
                loading="lazy"
                decoding="async"
                class="block w-full h-auto"
              />
              <div class="absolute inset-0 bg-black/0 group-hover:bg-black/15 transition-colors" />
              <div class="absolute inset-0 flex items-center justify-center">
                <UIcon name="heroicons:magnifying-glass-plus" class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
              </div>
              <div class="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                <p class="text-white/90 text-xs truncate">{{ image.original_filename }}</p>
              </div>
            </div>
          </button>
        </div>

        <!-- 加载更多 -->
        <div v-if="galleryData.has_more" class="text-center pt-4">
          <UButton color="gray" variant="outline" :loading="loadingMore" @click="loadMore">
            加载更多
          </UButton>
        </div>
      </div>
    </main>

    <!-- 全屏灯箱 -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="lightboxOpen"
          ref="lightboxEl"
          class="fixed inset-0 z-[100] bg-black/95 overscroll-contain"
          :style="{ paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)' }"
          role="dialog"
          aria-modal="true"
          aria-label="图片查看器"
          tabindex="-1"
          @click.self="onBackdropClick"
        >
          <div class="h-full flex flex-col">
            <!-- 顶部栏 -->
            <div class="shrink-0 bg-black/50 backdrop-blur px-4 py-3 text-white">
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium truncate">{{ currentImage?.original_filename }}</p>
                  <p v-if="galleryData" class="text-xs text-white/60">{{ lightboxIndex + 1 }} / {{ galleryData.images.length }}</p>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <UButton icon="heroicons:arrow-down-tray" color="white" variant="solid" size="sm" aria-label="下载图片" @click="downloadImage" />
                  <UButton icon="heroicons:x-mark" color="white" variant="solid" size="sm" aria-label="关闭" @click="closeLightbox" />
                </div>
              </div>
            </div>

            <!-- 图片区域 -->
            <div
              ref="swipeAreaEl"
              class="relative flex-1 flex items-center justify-center px-2 py-4 select-none touch-none overflow-hidden"
            >
              <!-- 左右切换按钮 -->
              <div class="absolute inset-y-0 left-0 flex items-center px-1 sm:px-2 z-10">
                <UButton
                  icon="heroicons:chevron-left"
                  color="white"
                  variant="ghost"
                  size="lg"
                  aria-label="上一张"
                  :disabled="!hasPrev"
                  :class="{ 'opacity-30': !hasPrev }"
                  @click.stop="goPrev"
                />
              </div>
              <div class="absolute inset-y-0 right-0 flex items-center px-1 sm:px-2 z-10">
                <UButton
                  icon="heroicons:chevron-right"
                  color="white"
                  variant="ghost"
                  size="lg"
                  aria-label="下一张"
                  :disabled="!hasNext"
                  :class="{ 'opacity-30': !hasNext }"
                  @click.stop="goNext"
                />
              </div>

              <!-- 图片 -->
              <Transition
                mode="out-in"
                enter-active-class="transition duration-200 ease-out"
                enter-from-class="opacity-0 scale-[0.98]"
                enter-to-class="opacity-100 scale-100"
                leave-active-class="transition duration-150 ease-in"
                leave-from-class="opacity-100 scale-100"
                leave-to-class="opacity-0 scale-[0.98]"
              >
                <img
                  v-if="currentImage"
                  :key="currentImage.encrypted_id"
                  :src="currentImage.image_url"
                  :alt="currentImage.original_filename"
                  class="max-h-full max-w-full object-contain"
                  draggable="false"
                />
              </Transition>

              <!-- 操作提示 -->
              <div class="absolute bottom-3 inset-x-0 text-center pointer-events-none">
                <p class="text-xs text-white/50 hidden sm:block">← → 切换图片 · ESC 关闭</p>
                <p class="text-xs text-white/50 sm:hidden">滑动切换 · 向下滑动关闭</p>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 底部 -->
    <footer class="py-6 text-center">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-1.5 text-xs text-stone-400 dark:text-stone-500 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
      >
        <UIcon name="heroicons:cloud-arrow-up" class="w-3.5 h-3.5" />
        <span>Powered by 图床 Pro</span>
      </NuxtLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'
import { usePointerSwipe } from '@vueuse/core'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()

const shareToken = computed(() => route.params.token as string)
const fromGalleries = computed(() => route.query.from as string | undefined)

// 数据状态
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

// 密码解锁状态
const requiresPassword = ref(false)
const lockedGalleryName = ref('')
const passwordInput = ref('')
const unlocking = ref(false)
const unlockError = ref('')

const page = ref(1)
const loadingMore = ref(false)

// 页头状态
const galleryTitle = computed(() => {
  const name = (galleryData.value?.gallery?.name || '').trim()
  return name || '分享画集'
})

const copied = ref(false)
const downloadingAll = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

const copyShareLink = async () => {
  if (typeof window === 'undefined') return
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    const el = document.createElement('textarea')
    el.value = url
    el.style.cssText = 'position:fixed;left:-9999px;top:0'
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  }
  copied.value = true
  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => { copied.value = false }, 1500)
}

const downloadAllImages = async () => {
  if (typeof window === 'undefined') return
  if (downloadingAll.value || !galleryData.value?.images?.length) return

  const count = galleryData.value.images.length
  if (!window.confirm(`将下载 ${count} 张图片，浏览器可能会拦截多个下载，是否继续？`)) return

  downloadingAll.value = true
  try {
    for (const image of galleryData.value.images) {
      const link = document.createElement('a')
      link.href = image.image_url
      link.download = image.original_filename || 'image'
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      link.remove()
      await new Promise(r => setTimeout(r, 150))
    }
  } finally {
    downloadingAll.value = false
  }
}

// 灯箱状态
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxEl = ref<HTMLElement | null>(null)
const swipeAreaEl = ref<HTMLElement | null>(null)

const currentImage = computed(() => {
  if (!galleryData.value) return null
  const idx = lightboxIndex.value
  if (idx < 0 || idx >= galleryData.value.images.length) return null
  return galleryData.value.images[idx]
})

const hasPrev = computed(() => lightboxIndex.value > 0)
const hasNext = computed(() => {
  if (!galleryData.value) return false
  return lightboxIndex.value < galleryData.value.images.length - 1
})

// 加载画集
const loadGallery = async () => {
  loading.value = true
  error.value = ''
  requiresPassword.value = false
  try {
    galleryData.value = await galleryApi.getSharedGallery(shareToken.value, 1, 50)
    page.value = 1
  } catch (e: any) {
    if (e.requires_password) {
      requiresPassword.value = true
      lockedGalleryName.value = e.gallery_name || ''
    } else {
      error.value = e.message || '画集不存在或分享已关闭'
    }
  } finally {
    loading.value = false
  }
}

// 提交密码解锁
const submitPassword = async () => {
  if (!passwordInput.value || unlocking.value) return
  unlocking.value = true
  unlockError.value = ''
  try {
    await galleryApi.unlockGallery(shareToken.value, passwordInput.value)
    passwordInput.value = ''
    requiresPassword.value = false
    await loadGallery()
  } catch (e: any) {
    unlockError.value = e.message || '密码错误'
  } finally {
    unlocking.value = false
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

// 灯箱操作
const openLightbox = (index: number) => {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const closeLightbox = () => {
  lightboxOpen.value = false
}

const goPrev = () => {
  if (hasPrev.value) lightboxIndex.value--
}

const goNext = () => {
  if (hasNext.value) lightboxIndex.value++
}

const downloadImage = () => {
  if (!currentImage.value) return
  const link = document.createElement('a')
  link.href = currentImage.value.image_url
  link.download = currentImage.value.original_filename || 'image'
  link.target = '_blank'
  link.click()
}

// 键盘导航
const onKeydown = (e: KeyboardEvent) => {
  if (!lightboxOpen.value) return
  switch (e.key) {
    case 'Escape':
      e.preventDefault()
      closeLightbox()
      break
    case 'ArrowLeft':
      e.preventDefault()
      goPrev()
      break
    case 'ArrowRight':
      e.preventDefault()
      goNext()
      break
  }
}

// 触摸手势
const { isSwiping } = usePointerSwipe(swipeAreaEl, {
  threshold: 60,
  onSwipeEnd: (_e, direction) => {
    if (!lightboxOpen.value) return
    if (direction === 'left') goNext()
    else if (direction === 'right') goPrev()
    else if (direction === 'down') closeLightbox()
  }
})

const onBackdropClick = () => {
  if (isSwiping.value) return
  closeLightbox()
}

// 锁定背景滚动
watch(lightboxOpen, async (open) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    await nextTick()
    lightboxEl.value?.focus()
  }
})

// 监听路由参数变化
watch(shareToken, () => {
  closeLightbox()
  loadGallery()
})

onMounted(() => {
  loadGallery()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>
