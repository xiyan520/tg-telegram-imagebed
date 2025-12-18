<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-950">
    <!-- 画集标题栏 -->
    <header class="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-b border-stone-200/50 dark:border-neutral-700/50 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <!-- 左侧：画集信息 -->
          <div class="flex items-center gap-3 min-w-0">
            <NuxtLink
              :to="`/galleries/${shareAllToken}`"
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

      <!-- Token 验证状态 -->
      <div v-else-if="requiresToken" class="text-center py-32">
        <div class="w-24 h-24 bg-amber-100 dark:bg-amber-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <UIcon name="heroicons:key" class="w-12 h-12 text-amber-500" />
        </div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">{{ lockedGalleryName || '受保护的画集' }}</h1>
        <p class="text-stone-600 dark:text-stone-400 mb-6">此画集需要授权 Token 才能访问</p>
        <div class="max-w-sm mx-auto">
          <UButton color="primary" block @click="showLoginModal = true">
            验证身份
          </UButton>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="text-center py-32">
        <div class="w-24 h-24 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-500" />
        </div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">无法访问</h1>
        <p class="text-stone-600 dark:text-stone-400 mb-6">{{ error }}</p>
        <UButton :to="`/galleries/${shareAllToken}`" color="primary">返回画集列表</UButton>
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
            style="content-visibility: auto; contain-intrinsic-size: 360px 240px;"
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
    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="galleryData?.images || []"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
    />

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

    <!-- 登录弹窗 -->
    <AuthLoginModal
      v-model="showLoginModal"
      title="验证身份"
      :subtitle="lockedGalleryName ? `访问画集「${lockedGalleryName}」` : undefined"
      mode="token"
      @success="onLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'
import { useInfiniteScroll } from '@vueuse/core'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()

const shareAllToken = computed(() => route.params.token as string)
const galleryId = computed(() => parseInt(route.params.id as string, 10))

// 数据状态
const loading = ref(true)
const error = ref('')
const galleryData = ref<{
  gallery: { id: number; name: string; description?: string; image_count: number; access_mode: string }
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

// Token 验证状态
const requiresToken = ref(false)
const showLoginModal = ref(false)

const page = ref(1)
const loadingMore = ref(false)
let loadSeq = 0

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

// 加载画集
const loadGallery = async () => {
  const seq = ++loadSeq
  const token = shareAllToken.value
  const id = galleryId.value
  loading.value = true
  error.value = ''
  requiresPassword.value = false
  requiresToken.value = false

  // 验证 galleryId 有效性
  if (isNaN(id) || id <= 0) {
    error.value = '无效的画集 ID'
    loading.value = false
    return
  }

  try {
    const data = await galleryApi.getShareAllGallery(token, id, 1, 50)
    if (seq !== loadSeq || token !== shareAllToken.value || id !== galleryId.value) return
    galleryData.value = data
    page.value = 1
  } catch (e: any) {
    if (seq !== loadSeq) return
    if (e.requires_password) {
      requiresPassword.value = true
      lockedGalleryName.value = e.gallery_name || ''
    } else if (e.requires_token) {
      requiresToken.value = true
      lockedGalleryName.value = e.gallery_name || ''
    } else {
      error.value = e.message || '画集不存在或分享已关闭'
    }
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// 提交密码解锁
const submitPassword = async () => {
  if (!passwordInput.value || unlocking.value) return
  unlocking.value = true
  unlockError.value = ''
  try {
    await galleryApi.unlockShareAllGallery(shareAllToken.value, galleryId.value, passwordInput.value)
    passwordInput.value = ''
    requiresPassword.value = false
    await loadGallery()
  } catch (e: any) {
    unlockError.value = e.message || '密码错误'
  } finally {
    unlocking.value = false
  }
}

// Token 验证成功回调
const onLoginSuccess = async () => {
  requiresToken.value = false
  await loadGallery()
}

const loadMore = async () => {
  if (!galleryData.value?.has_more || loadingMore.value) return
  const seq = loadSeq
  const token = shareAllToken.value
  const id = galleryId.value
  loadingMore.value = true
  try {
    const nextPage = page.value + 1
    const result = await galleryApi.getShareAllGallery(token, id, nextPage, 50)
    if (seq !== loadSeq || token !== shareAllToken.value || id !== galleryId.value || !galleryData.value) return
    galleryData.value.images.push(...result.images)
    galleryData.value.has_more = result.has_more
    page.value = nextPage
  } catch (e: any) {
    console.error('加载更多失败:', e)
  } finally {
    if (seq === loadSeq) loadingMore.value = false
  }
}

// 灯箱操作
const openLightbox = (index: number) => {
  const count = galleryData.value?.images?.length || 0
  if (!count) return
  lightboxIndex.value = Math.min(Math.max(index, 0), count - 1)
  lightboxOpen.value = true
}

// 当需要 Token 验证时自动弹出登录弹窗
watch(requiresToken, (needsToken) => {
  if (needsToken) showLoginModal.value = true
})

// 监听路由参数变化
watch([shareAllToken, galleryId], () => {
  lightboxOpen.value = false
  loadGallery()
})

// 无限滚动
if (import.meta.client) {
  useInfiniteScroll(window, loadMore, {
    distance: 800,
    canLoadMore: () => !!galleryData.value?.has_more && !loadingMore.value && !loading.value && !error.value
  })
}

onMounted(() => {
  loadGallery()
})

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})
</script>
