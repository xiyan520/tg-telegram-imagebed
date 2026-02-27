<template>
  <div
    class="min-h-screen bg-[radial-gradient(circle_at_20%_20%,rgba(251,191,36,0.14),transparent_38%),radial-gradient(circle_at_80%_0%,rgba(249,115,22,0.10),transparent_40%),linear-gradient(180deg,#fafaf9_0%,#f5f5f4_100%)] dark:bg-[radial-gradient(circle_at_20%_20%,rgba(251,191,36,0.12),transparent_38%),radial-gradient(circle_at_80%_0%,rgba(249,115,22,0.10),transparent_40%),linear-gradient(180deg,#0c0a09_0%,#171717_100%)]"
    :style="themeColor ? `--gallery-accent: ${themeColor}` : '--gallery-accent: #f59e0b'"
  >
    <div class="fixed inset-0 pointer-events-none opacity-40 [background-size:28px_28px] [background-image:linear-gradient(to_right,rgba(120,113,108,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(120,113,108,0.08)_1px,transparent_1px)] dark:opacity-25" />

    <div class="relative z-10 mx-auto max-w-7xl px-3 pb-10 pt-4 sm:px-6 sm:pb-14 sm:pt-6 lg:px-8">
      <header class="sticky top-3 z-40 mb-5 rounded-2xl border border-stone-200/75 bg-white/88 px-3 py-2.5 shadow-xl shadow-stone-200/60 backdrop-blur-xl dark:border-stone-700/70 dark:bg-neutral-900/86 dark:shadow-black/35 sm:px-4 sm:py-3">
        <div class="flex items-start gap-2 sm:items-center sm:gap-3">
          <NuxtLink
            v-if="backLink"
            :to="backLink"
            class="mt-0.5 shrink-0 rounded-xl p-2 text-stone-500 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:text-stone-400 dark:hover:bg-amber-900/20 dark:hover:text-amber-400 sm:mt-0"
            title="返回列表"
          >
            <UIcon name="heroicons:arrow-left" class="h-5 w-5" />
          </NuxtLink>

          <div class="min-w-0 flex-1">
            <p class="text-[10px] font-semibold uppercase tracking-[0.24em] text-stone-500 dark:text-stone-400">Gallery Share</p>
            <h1 class="truncate text-sm font-bold text-stone-900 dark:text-white sm:text-base">
              {{ galleryTitle }}
            </h1>
          </div>

          <div class="shrink-0 flex items-center gap-1.5">
            <UButton
              variant="ghost"
              size="sm"
              :icon="copied ? 'heroicons:check' : 'heroicons:link'"
              class="text-stone-600 hover:bg-amber-50 hover:text-amber-600 dark:text-stone-300 dark:hover:bg-amber-900/20 dark:hover:text-amber-400"
              aria-label="复制分享链接"
              @click="copyShareLink"
            >
              <span class="hidden text-xs sm:inline">{{ copied ? '已复制' : '复制' }}</span>
            </UButton>
            <UButton
              v-if="allowDownload"
              variant="ghost"
              size="sm"
              icon="heroicons:arrow-down-tray"
              :loading="downloadingAll"
              :disabled="!galleryData || galleryData.images.length === 0"
              class="text-stone-600 hover:bg-amber-50 hover:text-amber-600 dark:text-stone-300 dark:hover:bg-amber-900/20 dark:hover:text-amber-400"
              aria-label="下载全部图片"
              @click="downloadAllImages"
            >
              <span class="hidden text-xs sm:inline">下载</span>
            </UButton>
          </div>
        </div>
      </header>

      <main>
        <div v-if="loading" class="space-y-5 sm:space-y-6">
          <div class="h-44 animate-pulse rounded-3xl border border-stone-200 bg-stone-200/80 dark:border-stone-700 dark:bg-neutral-800/80 sm:h-56" />
          <div class="columns-1 [column-gap:0.75rem] sm:columns-2 lg:columns-3 xl:columns-4 sm:[column-gap:1rem]">
            <div
              v-for="i in 12"
              :key="i"
              class="mb-3 break-inside-avoid animate-pulse rounded-2xl bg-stone-200 dark:bg-neutral-800 sm:mb-4"
              :style="`height: ${[170, 220, 195, 150, 210, 260, 185, 205, 165, 230, 215, 182][i - 1]}px`"
            />
          </div>
        </div>

        <div v-else-if="requiresPassword" class="mx-auto mt-8 max-w-md rounded-3xl border border-amber-200/70 bg-white/90 p-6 text-center shadow-2xl shadow-amber-100/70 backdrop-blur-sm dark:border-amber-700/40 dark:bg-neutral-900/88 dark:shadow-black/40 sm:mt-12 sm:p-8">
          <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg">
            <UIcon name="heroicons:lock-closed" class="h-8 w-8" />
          </div>
          <h2 class="mb-1 text-2xl font-bold text-stone-900 dark:text-white">{{ lockedGalleryName || '受保护画集' }}</h2>
          <p class="mb-6 text-sm text-stone-500 dark:text-stone-400">请输入访问密码继续查看</p>
          <div class="space-y-3">
            <UInput v-model="passwordInput" type="password" placeholder="请输入访问密码" size="lg" @keyup.enter="submitPassword" />
            <UButton block size="lg" :loading="unlocking" :disabled="!passwordInput" class="bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600" @click="submitPassword">
              解锁画集
            </UButton>
            <p v-if="unlockError" class="text-sm text-red-500">{{ unlockError }}</p>
          </div>
        </div>

        <div v-else-if="requiresToken" class="mx-auto mt-8 max-w-md rounded-3xl border border-amber-200/70 bg-white/90 p-6 text-center shadow-2xl shadow-amber-100/70 backdrop-blur-sm dark:border-amber-700/40 dark:bg-neutral-900/88 dark:shadow-black/40 sm:mt-12 sm:p-8">
          <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg">
            <UIcon name="heroicons:key" class="h-8 w-8" />
          </div>
          <h2 class="mb-1 text-2xl font-bold text-stone-900 dark:text-white">{{ lockedGalleryName || '受保护画集' }}</h2>
          <p class="mb-6 text-sm text-stone-500 dark:text-stone-400">需要授权 Token 才能访问此画集</p>
          <UButton block size="lg" class="bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600" @click="showLoginModal = true">
            验证身份
          </UButton>
        </div>

        <div v-else-if="error" class="mx-auto mt-8 max-w-md rounded-3xl border border-red-200/70 bg-white/90 p-6 text-center shadow-2xl shadow-red-100/70 backdrop-blur-sm dark:border-red-700/40 dark:bg-neutral-900/88 dark:shadow-black/40 sm:mt-12 sm:p-8">
          <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-400 to-orange-500 text-white shadow-lg">
            <UIcon name="heroicons:exclamation-triangle" class="h-8 w-8" />
          </div>
          <h2 class="mb-1 text-2xl font-bold text-stone-900 dark:text-white">无法访问</h2>
          <p class="mb-6 text-sm text-stone-500 dark:text-stone-400">{{ error }}</p>
          <UButton :to="errorBackLink" class="bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600">
            {{ errorBackLabel }}
          </UButton>
        </div>

        <div v-else-if="galleryData" class="space-y-5 sm:space-y-7">
          <Transition name="fade">
            <div
              v-if="nsfwWarning && !nsfwConfirmed"
              class="fixed inset-0 z-[120] flex items-center justify-center bg-black/85 px-4 backdrop-blur-lg"
            >
              <div class="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-7 text-center shadow-2xl dark:border-neutral-700/60 dark:bg-neutral-900">
                <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500 to-orange-500 text-white shadow-lg">
                  <UIcon name="heroicons:eye-slash" class="h-8 w-8" />
                </div>
                <h3 class="mb-2 text-xl font-bold text-stone-900 dark:text-white">内容警告</h3>
                <p class="mb-6 text-sm leading-relaxed text-stone-500 dark:text-stone-400">
                  此画集可能包含敏感内容，请确认您已年满 18 岁并愿意继续浏览。
                </p>
                <div class="flex gap-3">
                  <UButton block variant="outline" class="border-stone-300 text-stone-600 dark:border-neutral-600 dark:text-stone-300" @click="leaveNsfw">
                    离开
                  </UButton>
                  <UButton block class="bg-gradient-to-r from-red-500 to-orange-500 text-white hover:from-red-600 hover:to-orange-600" @click="confirmNsfw">
                    继续浏览
                  </UButton>
                </div>
              </div>
            </div>
          </Transition>

          <section class="relative overflow-hidden rounded-3xl border border-stone-200/70 bg-white/90 shadow-xl shadow-stone-200/70 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/86 dark:shadow-black/35">
            <div v-if="coverSrc" class="absolute inset-0">
              <img :src="coverSrc" alt="" aria-hidden="true" class="h-full w-full object-cover blur-sm scale-110">
              <div class="absolute inset-0 bg-gradient-to-br from-black/55 via-black/35 to-black/65" />
            </div>
            <div v-else class="absolute inset-0 bg-gradient-to-br from-amber-400/25 via-orange-400/18 to-stone-400/18 dark:from-amber-500/18 dark:via-orange-500/12 dark:to-stone-900/35" />

            <div class="relative p-5 sm:p-7">
              <div>
                <h2 class="text-3xl font-black leading-tight text-white drop-shadow-lg sm:text-4xl">
                  {{ galleryTitle }}
                </h2>
                <p v-if="galleryData.gallery.description" class="mt-3 max-w-2xl text-sm leading-relaxed text-white/90 sm:text-base">
                  {{ galleryData.gallery.description }}
                </p>
                <p v-if="customHeaderText" class="mt-2 max-w-2xl text-xs leading-relaxed text-white/75 sm:text-sm">
                  {{ customHeaderText }}
                </p>

                <div class="mt-5 flex flex-wrap gap-2">
                  <span class="rounded-full border border-white/30 bg-white/15 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                    {{ galleryData.gallery.image_count }} 张图片
                  </span>
                  <span class="rounded-full border border-white/30 bg-white/15 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                    布局：{{ layoutModeLabel }}
                  </span>
                  <span class="rounded-full border border-white/30 bg-white/15 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                    {{ allowDownload ? '允许下载' : '仅浏览' }}
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section class="rounded-3xl border border-stone-200/70 bg-white/86 p-3 shadow-xl shadow-stone-200/60 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/82 dark:shadow-black/35 sm:p-4">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-2 px-1 sm:px-2">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">Content Stream</p>
                <p class="text-sm text-stone-600 dark:text-stone-300">点击任意图片可进入沉浸式浏览</p>
              </div>
              <span class="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-xs text-stone-500 dark:border-stone-700 dark:bg-neutral-800 dark:text-stone-400">
                第 {{ page }} 页
              </span>
            </div>

            <div v-if="galleryData.images.length === 0" class="py-16 text-center">
              <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-stone-100 dark:bg-neutral-800">
                <UIcon name="heroicons:photo" class="h-8 w-8 text-stone-400" />
              </div>
              <p class="text-base font-medium text-stone-900 dark:text-white">画集暂无图片</p>
            </div>

            <div v-else>
              <div
                v-if="layoutMode === 'masonry'"
                class="columns-1 [column-gap:0.75rem] sm:columns-2 lg:columns-3 xl:columns-4 sm:[column-gap:1rem]"
              >
                <button
                  v-for="(image, index) in galleryData.images"
                  :key="image.encrypted_id"
                  type="button"
                  class="group relative mb-3 block w-full break-inside-avoid overflow-hidden rounded-2xl border border-stone-200/80 bg-white text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/80 dark:bg-neutral-900 dark:hover:shadow-black/35 sm:mb-4"
                  style="content-visibility: auto; contain-intrinsic-size: 360px 240px;"
                  @click="openLightbox(index)"
                >
                  <img :src="image.image_url" :alt="image.original_filename" loading="lazy" decoding="async" class="block h-auto w-full" />
                  <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/18" />
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2.5 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                  </div>
                </button>
              </div>

              <div
                v-else-if="layoutMode === 'grid'"
                class="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5"
              >
                <button
                  v-for="(image, index) in galleryData.images"
                  :key="image.encrypted_id"
                  type="button"
                  class="group relative block aspect-square overflow-hidden rounded-2xl border border-stone-200/80 bg-stone-200 text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/80 dark:bg-neutral-800 dark:hover:shadow-black/35"
                  @click="openLightbox(index)"
                >
                  <img :src="image.image_url" :alt="image.original_filename" loading="lazy" decoding="async" class="h-full w-full object-cover" />
                  <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/18" />
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                  </div>
                </button>
              </div>

              <div v-else class="flex flex-wrap gap-2.5">
                <button
                  v-for="(image, index) in galleryData.images"
                  :key="image.encrypted_id"
                  type="button"
                  class="group relative block min-w-[42%] flex-grow overflow-hidden rounded-2xl border border-stone-200/80 bg-stone-200 text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/80 dark:bg-neutral-800 dark:hover:shadow-black/35 sm:min-w-[150px] sm:max-w-[380px]"
                  style="height: 180px;"
                  @click="openLightbox(index)"
                >
                  <img :src="image.image_url" :alt="image.original_filename" loading="lazy" decoding="async" class="h-full w-full object-cover" />
                  <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/18" />
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                  </div>
                </button>
              </div>
            </div>

            <div v-if="loadingMore" class="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4 sm:gap-3">
              <div v-for="i in 4" :key="i" class="aspect-square animate-pulse rounded-2xl bg-stone-200 dark:bg-neutral-800" />
            </div>

            <div v-if="galleryData.has_more && !loadingMore" class="pt-6 text-center">
              <UButton
                variant="outline"
                class="border-stone-300 text-stone-600 hover:border-amber-400 hover:text-amber-600 dark:border-neutral-600 dark:text-stone-300 dark:hover:border-amber-500 dark:hover:text-amber-400"
                @click="loadMore"
              >
                加载更多
              </UButton>
            </div>
          </section>
        </div>
      </main>
    </div>

    <footer class="relative z-10 border-t border-stone-200/60 dark:border-stone-700/60">
      <div class="mx-auto max-w-7xl px-3 py-6 text-center sm:px-6 lg:px-8">
        <NuxtLink :to="footerLink" class="inline-flex items-center gap-1.5 text-xs text-stone-500 transition-colors hover:text-amber-600 dark:text-stone-400 dark:hover:text-amber-400">
          <UIcon :name="footerIcon" class="h-3.5 w-3.5" />
          <span>{{ footerLabel }}</span>
        </NuxtLink>
      </div>
    </footer>

    <Transition name="slide-up">
      <button
        v-if="showBackToTop"
        type="button"
        class="fixed bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full text-white shadow-lg transition-all duration-200 hover:scale-110 active:scale-95"
        :style="`background: var(--gallery-accent)`"
        aria-label="回到顶部"
        @click="scrollToTop"
      >
        <UIcon name="heroicons:arrow-up" class="h-5 w-5" />
      </button>
    </Transition>

    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="galleryData?.images || []"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
    />

    <AuthLoginModal
      v-model="showLoginModal"
      title="验证身份"
      :subtitle="lockedGalleryName ? `访问画集「${lockedGalleryName}」` : undefined"
      mode="token"
      :gallery-share-token="shareToken"
      @success="onLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'
import { useInfiniteScroll, useWindowScroll } from '@vueuse/core'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()
const requestURL = useRequestURL()
const { copy: clipboardCopy } = useClipboardCopy()
const toast = useLightToast()
const { displayName } = useSeoSettings()

const siteMode = useState<{ mode: string; site_name?: string } | null>('gallery-site-mode', () => null)
const isGalleryMode = computed(() => siteMode.value?.mode === 'gallery')
const gallerySiteName = computed(() => siteMode.value?.site_name || '画集')

const shareToken = computed(() => String(route.params.token || ''))
const fromGalleries = computed(() => {
  const value = route.query.from
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
})

const loading = ref(true)
const error = ref('')
const galleryData = ref<{
  gallery: {
    name: string
    description?: string
    image_count: number
    cover_image?: string
    cover_url?: string
    layout_mode?: 'masonry' | 'grid' | 'justified'
    theme_color?: string
    show_image_info?: boolean
    allow_download?: boolean
    sort_order?: 'newest' | 'oldest' | 'filename'
    nsfw_warning?: boolean
    custom_header_text?: string
  }
  images: GalleryImage[]
  total: number
  page: number
  limit: number
  has_more: boolean
} | null>(null)

const requiresPassword = ref(false)
const lockedGalleryName = ref('')
const passwordInput = ref('')
const unlocking = ref(false)
const unlockError = ref('')

const requiresToken = ref(false)
const showLoginModal = ref(false)

const page = ref(1)
const loadingMore = ref(false)
let loadSeq = 0

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined
const downloadingAll = ref(false)

const nsfwConfirmed = ref(false)

const galleryTitle = computed(() => {
  const name = (galleryData.value?.gallery?.name || '').trim()
  return name || '分享画集'
})
const layoutMode = computed(() => galleryData.value?.gallery?.layout_mode || 'masonry')
const layoutModeLabel = computed(() => {
  if (layoutMode.value === 'grid') return '网格'
  if (layoutMode.value === 'justified') return '等高'
  return '瀑布流'
})
const themeColor = computed(() => galleryData.value?.gallery?.theme_color || '')
const showImageInfo = computed(() => galleryData.value?.gallery?.show_image_info !== false)
const allowDownload = computed(() => galleryData.value?.gallery?.allow_download !== false)
const nsfwWarning = computed(() => galleryData.value?.gallery?.nsfw_warning === true)
const customHeaderText = computed(() => galleryData.value?.gallery?.custom_header_text || '')

const coverSrc = computed(() => {
  const gallery = galleryData.value?.gallery
  if (!gallery) return ''
  if (gallery.cover_url) return gallery.cover_url
  if (gallery.cover_image) {
    return `${String(useRuntimeConfig().public.apiBase || '').replace(/\/$/, '')}/image/${gallery.cover_image}`
  }
  return ''
})

const backLink = computed(() => (fromGalleries.value ? `/galleries/${fromGalleries.value}` : undefined))
const errorBackLink = computed(() => (isGalleryMode.value ? '/gallery-site/' : '/'))
const errorBackLabel = computed(() => (isGalleryMode.value ? '返回画集首页' : '返回首页'))
const footerLink = computed(() => (isGalleryMode.value ? '/gallery-site/' : '/'))
const footerLabel = computed(() => isGalleryMode.value ? `© ${new Date().getFullYear()} ${gallerySiteName.value}` : `Powered by ${displayName.value}`)
const footerIcon = computed(() => (isGalleryMode.value ? 'heroicons:photo' : 'heroicons:cloud-arrow-up'))

const canonicalUrl = computed(() => {
  if (import.meta.client) return `${window.location.origin}/g/${shareToken.value}`
  return `${requestURL.origin}/g/${shareToken.value}`
})

const shareDescription = computed(() => {
  const description = galleryData.value?.gallery?.description?.trim()
  if (description) return description
  return `${galleryTitle.value}，共 ${galleryData.value?.gallery?.image_count || 0} 张图片`
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl.value }],
  meta: [
    { name: 'robots', content: 'noindex,nofollow,noarchive' },
    { name: 'googlebot', content: 'noindex,nofollow,noarchive' },
    { name: 'referrer', content: 'no-referrer-when-downgrade' }
  ]
}))

useSeoMeta(() => ({
  title: `${galleryTitle.value} - 分享画集`,
  description: shareDescription.value,
  ogTitle: galleryTitle.value,
  ogDescription: shareDescription.value,
  ogImage: coverSrc.value || undefined,
  ogUrl: canonicalUrl.value,
  twitterTitle: galleryTitle.value,
  twitterDescription: shareDescription.value,
  twitterImage: coverSrc.value || undefined,
  twitterCard: coverSrc.value ? 'summary_large_image' : 'summary'
}))

const syncNsfwSession = () => {
  if (typeof sessionStorage === 'undefined') return
  nsfwConfirmed.value = sessionStorage.getItem(`nsfw_confirmed_${shareToken.value}`) === '1'
}

const confirmNsfw = () => {
  nsfwConfirmed.value = true
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(`nsfw_confirmed_${shareToken.value}`, '1')
  }
}

const leaveNsfw = () => {
  if (typeof window !== 'undefined') window.history.back()
}

const loadGallery = async () => {
  const seq = ++loadSeq
  const token = shareToken.value

  loading.value = true
  error.value = ''
  requiresPassword.value = false
  requiresToken.value = false
  unlockError.value = ''
  lockedGalleryName.value = ''
  syncNsfwSession()

  try {
    const data = await galleryApi.getSharedGallery(token, 1, 50)
    if (seq !== loadSeq || token !== shareToken.value) return
    galleryData.value = data
    page.value = 1
  } catch (e: any) {
    if (seq !== loadSeq || token !== shareToken.value) return

    galleryData.value = null
    if (e.requires_password) {
      requiresPassword.value = true
      lockedGalleryName.value = e.gallery_name || ''
      return
    }
    if (e.requires_token) {
      requiresToken.value = true
      lockedGalleryName.value = e.gallery_name || ''
      return
    }
    error.value = e.message || '画集不存在或分享已关闭'
  } finally {
    if (seq === loadSeq && token === shareToken.value) {
      loading.value = false
    }
  }
}

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

const onLoginSuccess = async () => {
  requiresToken.value = false
  await loadGallery()
}

const loadMore = async () => {
  if (!galleryData.value?.has_more || loadingMore.value) return
  const seq = loadSeq
  const token = shareToken.value
  loadingMore.value = true
  try {
    const nextPage = page.value + 1
    const result = await galleryApi.getSharedGallery(token, nextPage, 50)
    if (seq !== loadSeq || token !== shareToken.value || !galleryData.value) return
    galleryData.value.images.push(...result.images)
    galleryData.value.has_more = result.has_more
    page.value = nextPage
  } finally {
    if (seq === loadSeq && token === shareToken.value) {
      loadingMore.value = false
    }
  }
}

const openLightbox = (index: number) => {
  const count = galleryData.value?.images?.length || 0
  if (!count) return
  lightboxIndex.value = Math.min(Math.max(index, 0), count - 1)
  lightboxOpen.value = true
}

const copyShareLink = async () => {
  const ok = await clipboardCopy(canonicalUrl.value, '链接已复制到剪贴板')
  if (!ok) return
  copied.value = true
  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => { copied.value = false }, 1400)
}

const downloadAllImages = async () => {
  if (typeof window === 'undefined') return
  if (downloadingAll.value || !galleryData.value?.images?.length) return

  const count = galleryData.value.images.length
  if (!window.confirm(`将下载 ${count} 张图片，浏览器可能会拦截多个下载，是否继续？`)) return

  downloadingAll.value = true
  let failed = 0
  try {
    for (const image of galleryData.value.images) {
      try {
        const link = document.createElement('a')
        link.href = image.image_url
        link.download = image.original_filename || 'image'
        link.target = '_blank'
        document.body.appendChild(link)
        link.click()
        link.remove()
      } catch {
        failed += 1
      }
      await new Promise(resolve => setTimeout(resolve, 140))
    }
  } finally {
    downloadingAll.value = false
    if (failed > 0) {
      toast.warning(`下载完成，${failed} 张被浏览器拦截`)
    }
  }
}

const { y: scrollY } = useWindowScroll()
const showBackToTop = computed(() => scrollY.value > 500)
const scrollToTop = () => {
  if (typeof window !== 'undefined') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

watch(requiresToken, (needsToken) => {
  if (needsToken) showLoginModal.value = true
})

watch(shareToken, () => {
  lightboxOpen.value = false
  loadGallery()
})

if (import.meta.client) {
  useInfiniteScroll(window, loadMore, {
    distance: 800,
    canLoadMore: () => !!galleryData.value?.has_more && !loadingMore.value && !loading.value && !error.value
  })
}

onMounted(loadGallery)

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
