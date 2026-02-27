<template>
  <div
    class="min-h-screen flex flex-col bg-stone-50 dark:bg-neutral-950"
    :style="themeColor ? `--gallery-accent: ${themeColor}` : '--gallery-accent: #f59e0b'"
  >
    <div class="fixed inset-0 overflow-hidden pointer-events-none" style="z-index: 0;">
      <div
        class="absolute inset-0"
        :style="themeColor
          ? `background: linear-gradient(145deg, ${themeColor}10 0%, transparent 55%, ${themeColor}08 100%)`
          : 'background: linear-gradient(145deg, rgb(231 229 228 / 0.45) 0%, transparent 55%, rgb(255 251 235 / 0.35) 100%)'"
      />
      <div class="absolute top-0 right-1/4 h-full w-px bg-gradient-to-b from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent" />
      <div class="absolute top-1/3 left-0 h-px w-full bg-gradient-to-r from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent" />
    </div>

    <header
      class="sticky top-0 border-b border-stone-200/65 bg-white/85 shadow-sm backdrop-blur-xl dark:border-stone-700/65 dark:bg-neutral-900/85"
      style="z-index: 110;"
    >
      <div class="mx-auto max-w-7xl px-3 py-3 sm:px-6 sm:py-4 lg:px-8">
        <div class="flex items-start justify-between gap-2 sm:items-center sm:gap-3">
          <div class="flex min-w-0 items-start gap-2 sm:items-center sm:gap-3">
            <NuxtLink
              v-if="backLink"
              :to="backLink"
              class="mt-0.5 shrink-0 rounded-xl p-2 text-stone-500 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:text-stone-400 dark:hover:bg-amber-900/20 dark:hover:text-amber-400 sm:mt-0"
              title="返回"
            >
              <UIcon name="heroicons:arrow-left" class="h-5 w-5" />
            </NuxtLink>

            <div class="relative shrink-0 mt-0.5 sm:mt-0">
              <div class="absolute inset-0 rounded-xl opacity-30 blur" :style="`background: var(--gallery-accent)`" />
              <div
                class="relative flex h-9 w-9 items-center justify-center rounded-xl shadow-lg sm:h-10 sm:w-10"
                :style="`background: linear-gradient(135deg, var(--gallery-accent), color-mix(in srgb, var(--gallery-accent) 78%, #000))`"
              >
                <UIcon name="heroicons:photo" class="h-4 w-4 text-white sm:h-5 sm:w-5" />
              </div>
            </div>

            <div class="min-w-0">
              <h1 class="truncate text-base font-bold leading-tight sm:text-xl">
                <span
                  v-if="!themeColor"
                  class="bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent dark:from-amber-400 dark:to-orange-400"
                >{{ galleryTitle }}</span>
                <span v-else :style="`color: var(--gallery-accent)`">{{ galleryTitle }}</span>
              </h1>
              <div v-if="galleryData" class="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-stone-500 dark:text-stone-400 sm:text-xs">
                <span class="inline-flex items-center gap-1">
                  <UIcon name="heroicons:photo" class="h-3 w-3" />
                  {{ galleryData.gallery.image_count }} 张
                </span>
                <span class="hidden sm:inline text-stone-300 dark:text-stone-600">·</span>
                <span class="max-w-[11rem] truncate sm:max-w-none">{{ galleryData.gallery.description || '分享画集' }}</span>
              </div>
            </div>
          </div>

          <div class="shrink-0 flex items-center gap-1 sm:gap-2">
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
      </div>
    </header>

    <main class="relative flex-1" style="z-index: 10;">
      <div v-if="loading">
        <div class="h-40 w-full animate-pulse bg-stone-200 dark:bg-neutral-800 sm:h-56" />
        <div class="mx-auto max-w-7xl px-3 py-6 sm:px-6 sm:py-8 lg:px-8">
          <div class="columns-1 [column-gap:0.75rem] sm:columns-2 lg:columns-3 xl:columns-4 sm:[column-gap:1rem]">
            <div
              v-for="i in 12"
              :key="i"
              class="mb-3 break-inside-avoid animate-pulse rounded-2xl bg-stone-200 dark:bg-neutral-800 sm:mb-4"
              :style="`height: ${[180, 240, 200, 160, 220, 280, 190, 210, 170, 250, 230, 195][i - 1]}px`"
            />
          </div>
        </div>
      </div>

      <div v-else-if="requiresPassword" class="flex min-h-[62vh] items-center justify-center px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative mx-auto mb-6 h-24 w-24">
            <div class="absolute inset-0 rounded-full blur-xl opacity-20" :style="`background: var(--gallery-accent)`" />
            <div class="relative flex h-full w-full items-center justify-center rounded-full border border-amber-200/50 bg-amber-50 dark:border-amber-700/30 dark:bg-amber-900/20">
              <UIcon name="heroicons:lock-closed" class="h-12 w-12 text-amber-500" />
            </div>
          </div>
          <h2 class="mb-2 bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-2xl font-bold text-transparent dark:from-amber-400 dark:to-orange-400">
            {{ lockedGalleryName || '受保护的画集' }}
          </h2>
          <p class="mb-7 text-sm text-stone-500 dark:text-stone-400">此画集需要密码才能访问</p>
          <div class="space-y-3">
            <UInput
              v-model="passwordInput"
              type="password"
              placeholder="请输入访问密码"
              size="lg"
              @keyup.enter="submitPassword"
            />
            <UButton
              block
              size="lg"
              :loading="unlocking"
              :disabled="!passwordInput"
              class="bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25 hover:from-amber-600 hover:to-orange-600"
              @click="submitPassword"
            >
              解锁画集
            </UButton>
            <p v-if="unlockError" class="text-sm text-red-500">{{ unlockError }}</p>
          </div>
        </div>
      </div>

      <div v-else-if="requiresToken" class="flex min-h-[62vh] items-center justify-center px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative mx-auto mb-6 h-24 w-24">
            <div class="absolute inset-0 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 blur-xl opacity-20" />
            <div class="relative flex h-full w-full items-center justify-center rounded-full border border-amber-200/50 bg-amber-50 dark:border-amber-700/30 dark:bg-amber-900/20">
              <UIcon name="heroicons:key" class="h-12 w-12 text-amber-500" />
            </div>
          </div>
          <h2 class="mb-2 bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-2xl font-bold text-transparent dark:from-amber-400 dark:to-orange-400">
            {{ lockedGalleryName || '受保护的画集' }}
          </h2>
          <p class="mb-7 text-sm text-stone-500 dark:text-stone-400">此画集需要授权 Token 才能访问</p>
          <UButton
            block
            size="lg"
            class="bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25 hover:from-amber-600 hover:to-orange-600"
            @click="showLoginModal = true"
          >
            验证身份
          </UButton>
        </div>
      </div>

      <div v-else-if="error" class="flex min-h-[62vh] items-center justify-center px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative mx-auto mb-6 h-24 w-24">
            <div class="absolute inset-0 rounded-full bg-gradient-to-br from-red-400 to-orange-400 blur-xl opacity-20" />
            <div class="relative flex h-full w-full items-center justify-center rounded-full border border-red-200/50 bg-red-50 dark:border-red-700/30 dark:bg-red-900/20">
              <UIcon name="heroicons:exclamation-triangle" class="h-12 w-12 text-red-500" />
            </div>
          </div>
          <h2 class="mb-2 text-2xl font-bold text-stone-900 dark:text-white">无法访问</h2>
          <p class="mb-8 text-sm text-stone-500 dark:text-stone-400">{{ error }}</p>
          <UButton
            :to="errorBackLink"
            class="bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25 hover:from-amber-600 hover:to-orange-600"
          >
            {{ errorBackLabel }}
          </UButton>
        </div>
      </div>

      <div v-else-if="galleryData">
        <Transition name="fade">
          <div
            v-if="nsfwWarning && !nsfwConfirmed"
            class="fixed inset-0 flex items-center justify-center bg-black/85 backdrop-blur-lg"
            style="z-index: 200;"
          >
            <div class="mx-4 w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-8 text-center shadow-2xl dark:border-neutral-700/60 dark:bg-neutral-900">
              <div class="relative mx-auto mb-5 h-20 w-20">
                <div class="absolute inset-0 rounded-full bg-gradient-to-br from-red-500 to-orange-500 blur-xl opacity-30" />
                <div class="relative flex h-full w-full items-center justify-center rounded-full border border-red-200/50 bg-red-50 dark:border-red-700/30 dark:bg-red-900/20">
                  <UIcon name="heroicons:eye-slash" class="h-10 w-10 text-red-500" />
                </div>
              </div>
              <h3 class="mb-2 text-xl font-bold text-stone-900 dark:text-white">内容警告</h3>
              <p class="mb-6 text-sm leading-relaxed text-stone-500 dark:text-stone-400">
                此画集可能包含敏感内容，不适合所有人查看。<br>请确认您已年满 18 岁且愿意继续。
              </p>
              <div class="flex gap-3">
                <UButton block variant="outline" class="border-stone-300 text-stone-600 dark:border-neutral-600 dark:text-stone-300" @click="leaveNsfw">
                  离开
                </UButton>
                <UButton block class="bg-gradient-to-r from-red-500 to-orange-500 text-white hover:from-red-600 hover:to-orange-600" @click="confirmNsfw">
                  我已了解，继续
                </UButton>
              </div>
            </div>
          </div>
        </Transition>

        <div class="relative w-full overflow-hidden" :class="hasCover ? 'h-44 sm:h-64' : 'h-32 sm:h-44'">
          <img
            v-if="hasCover && coverSrc"
            :src="coverSrc"
            alt=""
            aria-hidden="true"
            class="absolute inset-0 h-full w-full scale-110 object-cover blur-sm"
          >
          <div
            v-else
            class="absolute inset-0"
            :style="themeColor
              ? `background: linear-gradient(135deg, ${themeColor}42, ${themeColor}18)`
              : 'background: linear-gradient(135deg, rgb(245 158 11 / 0.24), rgb(249 115 22 / 0.15))'"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/35 to-black/10" />
          <div class="absolute inset-0 mx-auto flex w-full max-w-7xl flex-col justify-end px-3 pb-5 sm:px-8 sm:pb-8">
            <h2 class="line-clamp-2 text-2xl font-bold text-white drop-shadow-lg sm:text-4xl">
              {{ galleryTitle }}
            </h2>
            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-white/85">
              <span class="inline-flex items-center gap-1">
                <UIcon name="heroicons:photo" class="h-4 w-4" />
                {{ galleryData.gallery.image_count }} 张图片
              </span>
              <span v-if="galleryData.gallery.description" class="hidden opacity-60 sm:inline">·</span>
              <span v-if="galleryData.gallery.description" class="line-clamp-1 hidden sm:inline">{{ galleryData.gallery.description }}</span>
            </div>
            <p v-if="customHeaderText" class="mt-2 line-clamp-2 text-xs leading-relaxed text-white/75 sm:text-sm">
              {{ customHeaderText }}
            </p>
          </div>
        </div>

        <section class="mx-auto w-full max-w-7xl px-3 py-5 sm:px-6 sm:py-8 lg:px-8">
          <div v-if="galleryData.images.length === 0" class="py-20 text-center">
            <div class="relative mx-auto mb-4 h-20 w-20">
              <div class="absolute inset-0 rounded-full blur-xl opacity-15" :style="`background: var(--gallery-accent)`" />
              <div class="relative flex h-full w-full items-center justify-center rounded-full border border-stone-200/50 bg-stone-100 dark:border-neutral-700/50 dark:bg-neutral-800">
                <UIcon name="heroicons:photo" class="h-10 w-10 text-stone-400" />
              </div>
            </div>
            <p class="text-lg font-medium text-stone-900 dark:text-white">画集暂无图片</p>
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
                style="content-visibility: auto; contain-intrinsic-size: 360px 240px;"
                class="group mb-3 block w-full break-inside-avoid overflow-hidden rounded-2xl border border-stone-200/65 bg-white text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/65 dark:bg-neutral-900 dark:hover:shadow-black/30 sm:mb-4"
                @click="openLightbox(index)"
              >
                <div class="relative">
                  <div class="absolute inset-0 animate-pulse bg-stone-200 dark:bg-neutral-800" />
                  <img
                    :src="image.image_url"
                    :alt="image.original_filename"
                    loading="lazy"
                    decoding="async"
                    class="relative block h-auto w-full"
                    @load="(e) => (e.target as HTMLElement).previousElementSibling?.remove()"
                  >
                  <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/15" />
                  <div class="absolute inset-0 flex items-center justify-center">
                    <UIcon name="heroicons:magnifying-glass-plus" class="h-8 w-8 text-white opacity-0 drop-shadow-lg transition-opacity duration-300 group-hover:opacity-100" />
                  </div>
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/25 to-transparent p-3 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                  </div>
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
                class="group block aspect-square overflow-hidden rounded-2xl border border-stone-200/65 bg-stone-200 text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/65 dark:bg-neutral-800 dark:hover:shadow-black/30"
                @click="openLightbox(index)"
              >
                <div class="relative h-full w-full">
                  <img :src="image.image_url" :alt="image.original_filename" loading="lazy" decoding="async" class="h-full w-full object-cover">
                  <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/20" />
                  <div class="absolute inset-0 flex items-center justify-center">
                    <UIcon name="heroicons:magnifying-glass-plus" class="h-7 w-7 text-white opacity-0 drop-shadow-lg transition-opacity duration-300 group-hover:opacity-100" />
                  </div>
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                  </div>
                </div>
              </button>
            </div>

            <div v-else class="flex flex-wrap gap-2">
              <button
                v-for="(image, index) in galleryData.images"
                :key="image.encrypted_id"
                type="button"
                class="group relative block min-w-[42%] flex-grow overflow-hidden rounded-2xl border border-stone-200/65 bg-stone-200 text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10 dark:border-neutral-700/65 dark:bg-neutral-800 dark:hover:shadow-black/30 sm:min-w-[150px] sm:max-w-[380px]"
                style="height: 180px;"
                @click="openLightbox(index)"
              >
                <img :src="image.image_url" :alt="image.original_filename" loading="lazy" decoding="async" class="h-full w-full object-cover">
                <div class="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/20" />
                <div class="absolute inset-0 flex items-center justify-center">
                  <UIcon name="heroicons:magnifying-glass-plus" class="h-7 w-7 text-white opacity-0 drop-shadow-lg transition-opacity duration-300 group-hover:opacity-100" />
                </div>
                <div
                  v-if="showImageInfo"
                  class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2 opacity-95 transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100"
                >
                  <p class="truncate text-xs text-white/90">{{ image.original_filename }}</p>
                </div>
              </button>
            </div>
          </div>

          <div v-if="loadingMore" class="mt-4">
            <div
              v-if="layoutMode === 'masonry'"
              class="columns-1 [column-gap:0.75rem] sm:columns-2 lg:columns-3 xl:columns-4 sm:[column-gap:1rem]"
            >
              <div
                v-for="i in 4"
                :key="i"
                class="mb-3 break-inside-avoid animate-pulse rounded-2xl bg-stone-200 dark:bg-neutral-800 sm:mb-4"
                :style="`height: ${[180, 220, 160, 200][i - 1]}px`"
              />
            </div>
            <div v-else class="mt-0 grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4">
              <div v-for="i in 4" :key="i" class="aspect-square animate-pulse rounded-2xl bg-stone-200 dark:bg-neutral-800" />
            </div>
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

    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="galleryData?.images || []"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
    />

    <footer class="relative border-t border-stone-200/60 dark:border-stone-700/60" style="z-index: 10;">
      <div class="mx-auto max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
        <div class="flex items-center justify-center gap-2 text-center text-xs text-stone-400 dark:text-stone-500">
          <NuxtLink :to="footerLink" class="inline-flex items-center gap-1.5 transition-colors hover:text-amber-600 dark:hover:text-amber-400">
            <UIcon :name="footerIcon" class="h-3.5 w-3.5" />
            <span>{{ footerLabel }}</span>
          </NuxtLink>
        </div>
      </div>
    </footer>

    <Transition name="slide-up">
      <button
        v-if="showBackToTop"
        type="button"
        class="fixed bottom-6 right-6 flex h-10 w-10 items-center justify-center rounded-full text-white shadow-lg transition-all duration-200 hover:scale-110 active:scale-95"
        :style="`background: var(--gallery-accent); box-shadow: 0 4px 14px color-mix(in srgb, var(--gallery-accent) 40%, transparent)`"
        style="z-index: 50;"
        aria-label="回到顶部"
        @click="scrollToTop"
      >
        <UIcon name="heroicons:arrow-up" class="h-5 w-5" />
      </button>
    </Transition>

    <AuthLoginModal
      v-model="showLoginModal"
      title="验证身份"
      :subtitle="lockedGalleryName ? `访问画集「${lockedGalleryName}」` : undefined"
      :mode="loginMode"
      :gallery-share-token="loginShareToken"
      @success="onLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { useInfiniteScroll, useWindowScroll } from '@vueuse/core'
import type { SharedGalleryAdapter, SharedGalleryData } from '~/composables/gallery-share/adapters'

interface AccessLikeError extends Error {
  requires_password?: boolean
  requires_token?: boolean
  gallery_name?: string
}

const props = defineProps<{ adapter: SharedGalleryAdapter }>()

const route = useRoute()
const config = useRuntimeConfig()
const requestURL = useRequestURL()
const { copy: clipboardCopy } = useClipboardCopy()
const toast = useLightToast()

const PAGE_SIZE = 50

const loading = ref(true)
const error = ref('')
const galleryData = ref<SharedGalleryData | null>(null)

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
const downloadingAll = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

const nsfwConfirmed = ref(false)

const galleryTitle = computed(() => {
  const name = (galleryData.value?.gallery?.name || '').trim()
  return name || '分享画集'
})

const layoutMode = computed(() => galleryData.value?.gallery?.layout_mode || 'masonry')
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
    return `${String(config.public.apiBase || '').replace(/\/$/, '')}/image/${gallery.cover_image}`
  }
  return ''
})
const hasCover = computed(() => Boolean(coverSrc.value))

const backLink = computed(() => props.adapter.getBackLink())
const errorBackLink = computed(() => props.adapter.getErrorBackLink())
const errorBackLabel = computed(() => props.adapter.getErrorBackLabel())
const footerLink = computed(() => props.adapter.getFooterLink())
const footerLabel = computed(() => props.adapter.getFooterLabel())
const footerIcon = computed(() => props.adapter.getFooterIcon())
const loginMode = computed(() => props.adapter.getLoginMode())
const loginShareToken = computed(() => props.adapter.getLoginShareToken())

const canonicalUrl = computed(() => {
  const path = props.adapter.getCanonicalPath()
  if (import.meta.client) return `${window.location.origin}${path}`
  return `${requestURL.origin}${path}`
})

const shareUrl = computed(() => {
  const path = props.adapter.getSharePath()
  if (import.meta.client) return `${window.location.origin}${path}`
  return `${requestURL.origin}${path}`
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

const resetAccessState = () => {
  requiresPassword.value = false
  requiresToken.value = false
  unlockError.value = ''
  lockedGalleryName.value = ''
}

const syncNsfwSession = () => {
  if (typeof sessionStorage === 'undefined') return
  nsfwConfirmed.value = sessionStorage.getItem(props.adapter.getNsfwStorageKey()) === '1'
}

const confirmNsfw = () => {
  nsfwConfirmed.value = true
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(props.adapter.getNsfwStorageKey(), '1')
  }
}

const leaveNsfw = () => {
  if (typeof window !== 'undefined') window.history.back()
}

const loadGallery = async () => {
  const seq = ++loadSeq
  const adapterKey = props.adapter.key

  loading.value = true
  error.value = ''
  resetAccessState()
  syncNsfwSession()

  try {
    const data = await props.adapter.fetchPage(1, PAGE_SIZE)
    if (seq !== loadSeq || adapterKey !== props.adapter.key) return
    galleryData.value = data
    page.value = 1
  } catch (rawError: any) {
    if (seq !== loadSeq || adapterKey !== props.adapter.key) return

    const e = rawError as AccessLikeError
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
    if (seq === loadSeq && adapterKey === props.adapter.key) {
      loading.value = false
    }
  }
}

const submitPassword = async () => {
  if (!passwordInput.value || unlocking.value) return
  unlocking.value = true
  unlockError.value = ''
  try {
    await props.adapter.unlockPassword(passwordInput.value)
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
  const adapterKey = props.adapter.key
  loadingMore.value = true

  try {
    const nextPage = page.value + 1
    const result = await props.adapter.fetchPage(nextPage, PAGE_SIZE)
    if (seq !== loadSeq || adapterKey !== props.adapter.key || !galleryData.value) return
    galleryData.value.images.push(...result.images)
    galleryData.value.has_more = result.has_more
    page.value = nextPage
  } catch {
    // 静默失败，保留手动加载入口
  } finally {
    if (seq === loadSeq && adapterKey === props.adapter.key) {
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
  const copiedOk = await clipboardCopy(shareUrl.value, '链接已复制到剪贴板')
  if (!copiedOk) return

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
  if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch(requiresToken, (needsToken) => {
  if (needsToken) showLoginModal.value = true
})

watch(() => props.adapter.key, () => {
  lightboxOpen.value = false
  loadGallery()
}, { immediate: true })

if (import.meta.client) {
  useInfiniteScroll(window, loadMore, {
    distance: 800,
    canLoadMore: () => !!galleryData.value?.has_more && !loadingMore.value && !loading.value && !error.value
  })
}

watch(() => route.fullPath, () => {
  if (copied.value) copied.value = false
})

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
  transform: translateY(12px);
}
</style>
