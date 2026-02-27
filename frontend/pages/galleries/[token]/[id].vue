<template>
  <!-- 根容器：通过 CSS 变量注入主题色 -->
  <div
    class="min-h-screen flex flex-col bg-stone-50 dark:bg-neutral-950"
    :style="themeColor ? `--gallery-accent: ${themeColor}` : '--gallery-accent: #f59e0b'"
  >
    <!-- 固定背景装饰层 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none" style="z-index: 0;">
      <div
        class="absolute inset-0"
        :style="themeColor
          ? `background: linear-gradient(135deg, ${themeColor}08 0%, transparent 50%, ${themeColor}05 100%)`
          : 'background: linear-gradient(135deg, rgb(231 229 228 / 0.5) 0%, transparent 50%, rgb(255 251 235 / 0.3) 100%)'"
      ></div>
      <div class="absolute top-0 right-1/4 w-px h-full bg-gradient-to-b from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent"></div>
      <div class="absolute top-1/3 left-0 w-full h-px bg-gradient-to-r from-transparent via-stone-300/20 dark:via-stone-700/15 to-transparent"></div>
    </div>

    <!-- 顶部导航栏（sticky） -->
    <header
      class="sticky top-0 backdrop-blur-xl bg-white/80 dark:bg-neutral-900/80 border-b border-stone-200/60 dark:border-stone-700/60 shadow-sm"
      style="z-index: 100;"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
        <div class="flex items-center justify-between gap-3">
          <!-- 左侧：返回 + 画集标识 -->
          <div class="flex items-center gap-2 sm:gap-3 min-w-0">
            <NuxtLink
              :to="`/galleries/${shareAllToken}`"
              class="shrink-0 p-2 -ml-2 rounded-xl text-stone-500 hover:text-amber-600 dark:text-stone-400 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors"
              title="返回全部画集"
            >
              <UIcon name="heroicons:arrow-left" class="w-5 h-5" />
            </NuxtLink>
            <!-- 画集图标 -->
            <div class="shrink-0 relative">
              <div
                class="absolute inset-0 rounded-xl blur opacity-30"
                :style="`background: var(--gallery-accent)`"
              ></div>
              <div
                class="relative w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shadow-lg"
                :style="`background: linear-gradient(135deg, var(--gallery-accent), color-mix(in srgb, var(--gallery-accent) 80%, #000))`"
              >
                <UIcon name="heroicons:photo" class="w-4 h-4 sm:w-5 sm:h-5 text-white" />
              </div>
            </div>
            <div class="min-w-0">
              <h1 class="text-base sm:text-xl font-bold font-serif truncate leading-tight">
                <span
                  v-if="!themeColor"
                  class="bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent"
                >{{ galleryTitle }}</span>
                <span v-else :style="`color: var(--gallery-accent)`">{{ galleryTitle }}</span>
              </h1>
              <p v-if="galleryData" class="text-xs text-stone-500 dark:text-stone-400 truncate mt-0.5">
                <span class="inline-flex items-center gap-1">
                  <UIcon name="heroicons:photo" class="w-3 h-3" />
                  {{ galleryData.gallery.image_count }} 张图片
                </span>
                <span v-if="galleryData.gallery.description" class="hidden sm:inline text-stone-300 dark:text-stone-600 mx-1.5">·</span>
                <span v-if="galleryData.gallery.description" class="hidden sm:inline">{{ galleryData.gallery.description }}</span>
              </p>
            </div>
          </div>

          <!-- 右侧操作按钮 -->
          <div class="shrink-0 flex items-center gap-1 sm:gap-2">
            <UButton
              variant="ghost"
              size="sm"
              :icon="copied ? 'heroicons:check' : 'heroicons:link'"
              class="text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20"
              aria-label="复制分享链接"
              @click="copyShareLink"
            >
              <span class="hidden sm:inline text-xs">{{ copied ? '已复制' : '复制链接' }}</span>
            </UButton>
            <UButton
              v-if="allowDownload"
              variant="ghost"
              size="sm"
              icon="heroicons:arrow-down-tray"
              :loading="downloadingAll"
              :disabled="!galleryData || galleryData.images.length === 0"
              class="text-stone-600 dark:text-stone-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20"
              aria-label="下载全部图片"
              @click="downloadAllImages"
            >
              <span class="hidden sm:inline text-xs">下载全部</span>
            </UButton>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1 relative" style="z-index: 10;">

      <!-- 骨架屏：首次加载时显示 -->
      <div v-if="loading">
        <div class="w-full h-48 sm:h-64 bg-stone-200 dark:bg-neutral-800 animate-pulse"></div>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div class="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 [column-gap:1rem]">
            <div
              v-for="i in 12"
              :key="i"
              class="mb-4 break-inside-avoid rounded-2xl bg-stone-200 dark:bg-neutral-800 animate-pulse"
              :style="`height: ${[180, 240, 200, 160, 220, 280, 190, 210, 170, 250, 230, 195][i-1]}px`"
            ></div>
          </div>
        </div>
      </div>

      <!-- 密码解锁 -->
      <div v-else-if="requiresPassword" class="flex items-center justify-center min-h-[60vh] px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative w-24 h-24 mx-auto mb-6">
            <div class="absolute inset-0 rounded-full blur-xl opacity-20" :style="`background: var(--gallery-accent)`"></div>
            <div class="relative w-full h-full bg-amber-50 dark:bg-amber-900/20 rounded-full flex items-center justify-center border border-amber-200/50 dark:border-amber-700/30">
              <UIcon name="heroicons:lock-closed" class="w-12 h-12 text-amber-500" />
            </div>
          </div>
          <h1 class="text-2xl font-bold font-serif mb-2 bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent">
            {{ lockedGalleryName || '受保护的画集' }}
          </h1>
          <p class="text-stone-500 dark:text-stone-400 mb-8 text-sm">此画集需要密码才能访问</p>
          <div class="space-y-3">
            <UInput v-model="passwordInput" type="password" placeholder="请输入访问密码" size="lg" @keyup.enter="submitPassword" />
            <UButton
              block size="lg" :loading="unlocking" :disabled="!passwordInput"
              class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-lg shadow-amber-500/25"
              @click="submitPassword"
            >解锁画集</UButton>
            <p v-if="unlockError" class="text-sm text-red-500">{{ unlockError }}</p>
          </div>
        </div>
      </div>

      <!-- Token 验证 -->
      <div v-else-if="requiresToken" class="flex items-center justify-center min-h-[60vh] px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative w-24 h-24 mx-auto mb-6">
            <div class="absolute inset-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-full blur-xl opacity-20"></div>
            <div class="relative w-full h-full bg-amber-50 dark:bg-amber-900/20 rounded-full flex items-center justify-center border border-amber-200/50 dark:border-amber-700/30">
              <UIcon name="heroicons:key" class="w-12 h-12 text-amber-500" />
            </div>
          </div>
          <h1 class="text-2xl font-bold font-serif mb-2 bg-gradient-to-r from-amber-600 to-orange-600 dark:from-amber-400 dark:to-orange-400 bg-clip-text text-transparent">
            {{ lockedGalleryName || '受保护的画集' }}
          </h1>
          <p class="text-stone-500 dark:text-stone-400 mb-8 text-sm">此画集需要授权 Token 才能访问</p>
          <UButton
            block size="lg"
            class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-lg shadow-amber-500/25"
            @click="showLoginModal = true"
          >验证身份</UButton>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="flex items-center justify-center min-h-[60vh] px-4">
        <div class="w-full max-w-sm text-center">
          <div class="relative w-24 h-24 mx-auto mb-6">
            <div class="absolute inset-0 bg-gradient-to-br from-red-400 to-orange-400 rounded-full blur-xl opacity-20"></div>
            <div class="relative w-full h-full bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center border border-red-200/50 dark:border-red-700/30">
              <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-500" />
            </div>
          </div>
          <h1 class="text-2xl font-bold font-serif text-stone-900 dark:text-white mb-2">无法访问</h1>
          <p class="text-stone-500 dark:text-stone-400 mb-8 text-sm">{{ error }}</p>
          <UButton
            :to="`/galleries/${shareAllToken}`"
            class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-lg shadow-amber-500/25"
          >返回画集列表</UButton>
        </div>
      </div>

      <!-- 画集内容 -->
      <div v-else-if="galleryData">

        <!-- NSFW 全屏警告遮罩 -->
        <Transition name="fade">
          <div
            v-if="nsfwWarning && !nsfwConfirmed"
            class="fixed inset-0 flex items-center justify-center bg-black/85 backdrop-blur-lg"
            style="z-index: 200;"
          >
            <div class="max-w-md w-full mx-4 bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl p-8 text-center border border-stone-200/60 dark:border-neutral-700/60">
              <div class="relative w-20 h-20 mx-auto mb-5">
                <div class="absolute inset-0 bg-gradient-to-br from-red-500 to-orange-500 rounded-full blur-xl opacity-30"></div>
                <div class="relative w-full h-full bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center border border-red-200/50 dark:border-red-700/30">
                  <UIcon name="heroicons:eye-slash" class="w-10 h-10 text-red-500" />
                </div>
              </div>
              <h2 class="text-xl font-bold font-serif text-stone-900 dark:text-white mb-2">内容警告</h2>
              <p class="text-stone-500 dark:text-stone-400 mb-6 text-sm leading-relaxed">
                此画集可能包含敏感内容，不适合所有人查看。<br>请确认您已年满 18 岁且愿意继续。
              </p>
              <div class="flex gap-3">
                <UButton
                  block variant="outline"
                  class="border-stone-300 dark:border-neutral-600 text-stone-600 dark:text-stone-300"
                  @click="leaveNsfw"
                >离开</UButton>
                <UButton
                  block
                  class="bg-gradient-to-r from-red-500 to-orange-500 hover:from-red-600 hover:to-orange-600 text-white"
                  @click="confirmNsfw"
                >我已了解，继续</UButton>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Hero Banner -->
        <div
          class="relative w-full overflow-hidden"
          :class="hasCover ? 'h-52 sm:h-72' : 'h-36 sm:h-48'"
        >
          <img
            v-if="hasCover"
            :src="galleryData.gallery.cover_url || galleryData.gallery.cover_image"
            alt=""
            aria-hidden="true"
            class="absolute inset-0 w-full h-full object-cover scale-110 blur-sm"
          />
          <div
            v-else
            class="absolute inset-0"
            :style="themeColor
              ? `background: linear-gradient(135deg, ${themeColor}40, ${themeColor}20)`
              : 'background: linear-gradient(135deg, rgb(245 158 11 / 0.25), rgb(249 115 22 / 0.15))'"
          ></div>
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-black/10"></div>
          <div class="absolute inset-0 flex flex-col justify-end px-4 sm:px-8 pb-6 sm:pb-8 max-w-7xl mx-auto w-full left-0 right-0">
            <h2 class="text-2xl sm:text-4xl font-bold font-serif text-white drop-shadow-lg mb-1 sm:mb-2 line-clamp-2">
              {{ galleryTitle }}
            </h2>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-white/80 text-sm">
              <span class="inline-flex items-center gap-1">
                <UIcon name="heroicons:photo" class="w-4 h-4" />
                {{ galleryData.gallery.image_count }} 张图片
              </span>
              <span v-if="galleryData.gallery.description" class="hidden sm:inline opacity-60">·</span>
              <span v-if="galleryData.gallery.description" class="hidden sm:inline line-clamp-1">{{ galleryData.gallery.description }}</span>
            </div>
            <p v-if="customHeaderText" class="mt-2 text-white/70 text-xs sm:text-sm leading-relaxed line-clamp-2">
              {{ customHeaderText }}
            </p>
          </div>
        </div>

        <!-- 图片区域 -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">

          <!-- 空状态 -->
          <div v-if="galleryData.images.length === 0" class="text-center py-20">
            <div class="relative w-20 h-20 mx-auto mb-4">
              <div class="absolute inset-0 rounded-full blur-xl opacity-15" :style="`background: var(--gallery-accent)`"></div>
              <div class="relative w-full h-full bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center border border-stone-200/50 dark:border-neutral-700/50">
                <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-400" />
              </div>
            </div>
            <p class="text-lg font-medium font-serif text-stone-900 dark:text-white">画集暂无图片</p>
          </div>

          <!-- 图片网格 -->
          <div v-else>

            <!-- 瀑布流（masonry，默认） -->
            <div
              v-if="layoutMode === 'masonry'"
              class="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 [column-gap:1rem]"
            >
              <button
                v-for="(image, index) in galleryData.images"
                :key="image.encrypted_id"
                type="button"
                style="content-visibility: auto; contain-intrinsic-size: 360px 240px;"
                class="group mb-4 w-full break-inside-avoid rounded-2xl overflow-hidden border border-stone-200/60 dark:border-neutral-700/60 bg-white dark:bg-neutral-900 shadow-sm hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30 hover:-translate-y-1 transition-all duration-300 text-left block"
                @click="openLightbox(index)"
              >
                <div class="relative">
                  <div class="absolute inset-0 bg-stone-200 dark:bg-neutral-800 animate-pulse"></div>
                  <img
                    :src="image.image_url"
                    :alt="image.original_filename"
                    loading="lazy"
                    decoding="async"
                    class="relative block w-full h-auto"
                    @load="(e) => (e.target as HTMLElement).previousElementSibling?.remove()"
                  />
                  <div class="absolute inset-0 bg-black/0 group-hover:bg-black/15 transition-colors duration-300" />
                  <div class="absolute inset-0 flex items-center justify-center">
                    <UIcon name="heroicons:magnifying-glass-plus" class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 drop-shadow-lg" />
                  </div>
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  >
                    <p class="text-white/90 text-xs truncate">{{ image.original_filename }}</p>
                  </div>
                </div>
              </button>
            </div>

            <!-- 网格（grid） -->
            <div
              v-else-if="layoutMode === 'grid'"
              class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3"
            >
              <button
                v-for="(image, index) in galleryData.images"
                :key="image.encrypted_id"
                type="button"
                class="group aspect-square rounded-2xl overflow-hidden border border-stone-200/60 dark:border-neutral-700/60 bg-stone-200 dark:bg-neutral-800 shadow-sm hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30 hover:-translate-y-1 transition-all duration-300 text-left block"
                @click="openLightbox(index)"
              >
                <div class="relative w-full h-full">
                  <img
                    :src="image.image_url"
                    :alt="image.original_filename"
                    loading="lazy"
                    decoding="async"
                    class="w-full h-full object-cover"
                  />
                  <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300" />
                  <div class="absolute inset-0 flex items-center justify-center">
                    <UIcon name="heroicons:magnifying-glass-plus" class="w-7 h-7 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 drop-shadow-lg" />
                  </div>
                  <div
                    v-if="showImageInfo"
                    class="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  >
                    <p class="text-white/90 text-xs truncate">{{ image.original_filename }}</p>
                  </div>
                </div>
              </button>
            </div>

            <!-- 等高行（justified） -->
            <div
              v-else-if="layoutMode === 'justified'"
              class="flex flex-wrap gap-2"
            >
              <button
                v-for="(image, index) in galleryData.images"
                :key="image.encrypted_id"
                type="button"
                class="group relative rounded-2xl overflow-hidden border border-stone-200/60 dark:border-neutral-700/60 bg-stone-200 dark:bg-neutral-800 shadow-sm hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30 hover:-translate-y-1 transition-all duration-300 text-left block"
                style="height: 200px; flex-grow: 1; min-width: 150px; max-width: 380px;"
                @click="openLightbox(index)"
              >
                <img
                  :src="image.image_url"
                  :alt="image.original_filename"
                  loading="lazy"
                  decoding="async"
                  class="w-full h-full object-cover"
                />
                <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300" />
                <div class="absolute inset-0 flex items-center justify-center">
                  <UIcon name="heroicons:magnifying-glass-plus" class="w-7 h-7 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 drop-shadow-lg" />
                </div>
                <div
                  v-if="showImageInfo"
                  class="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                >
                  <p class="text-white/90 text-xs truncate">{{ image.original_filename }}</p>
                </div>
              </button>
            </div>

          </div>

          <!-- 加载更多骨架屏 -->
          <div v-if="loadingMore" class="mt-4">
            <div
              v-if="layoutMode === 'masonry'"
              class="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 [column-gap:1rem]"
            >
              <div
                v-for="i in 4"
                :key="i"
                class="mb-4 break-inside-avoid rounded-2xl bg-stone-200 dark:bg-neutral-800 animate-pulse"
                :style="`height: ${[180, 220, 160, 200][i-1]}px`"
              ></div>
            </div>
            <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              <div
                v-for="i in 4"
                :key="i"
                class="aspect-square rounded-2xl bg-stone-200 dark:bg-neutral-800 animate-pulse"
              ></div>
            </div>
          </div>

          <!-- 手动加载更多 -->
          <div v-if="galleryData.has_more && !loadingMore" class="text-center pt-6">
            <UButton
              variant="outline"
              class="border-stone-300 dark:border-neutral-600 text-stone-600 dark:text-stone-300 hover:border-amber-400 hover:text-amber-600 dark:hover:border-amber-500 dark:hover:text-amber-400"
              @click="loadMore"
            >加载更多</UButton>
          </div>

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

    <!-- 页脚 -->
    <footer class="relative border-t border-stone-200/60 dark:border-stone-700/60" style="z-index: 10;">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex items-center justify-center gap-2 text-xs text-stone-400 dark:text-stone-500">
          <NuxtLink
            to="/"
            class="inline-flex items-center gap-1.5 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
          >
            <UIcon name="heroicons:cloud-arrow-up" class="w-3.5 h-3.5" />
            <span>Powered by {{ displayName }}</span>
          </NuxtLink>
        </div>
      </div>
    </footer>

    <!-- 回到顶部浮动按钮 -->
    <Transition name="slide-up">
      <button
        v-if="showBackToTop"
        type="button"
        class="fixed bottom-6 right-6 w-10 h-10 rounded-full shadow-lg flex items-center justify-center text-white transition-all duration-200 hover:scale-110 active:scale-95"
        :style="`background: var(--gallery-accent); box-shadow: 0 4px 14px color-mix(in srgb, var(--gallery-accent) 40%, transparent); z-index: 50;`"
        aria-label="回到顶部"
        @click="scrollToTop"
      >
        <UIcon name="heroicons:arrow-up" class="w-5 h-5" />
      </button>
    </Transition>

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
import { useInfiniteScroll, useWindowScroll } from '@vueuse/core'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()
const { displayName } = useSeoSettings()

const shareAllToken = computed(() => route.params.token as string)
const galleryId = computed(() => parseInt(route.params.id as string, 10))

// 数据状态
const loading = ref(true)
const error = ref('')
const galleryData = ref<{
  gallery: {
    id: number
    name: string
    description?: string
    image_count: number
    access_mode: string
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

// 新字段：可选链 + 默认值
const layoutMode = computed(() => galleryData.value?.gallery?.layout_mode || 'masonry')
const themeColor = computed(() => galleryData.value?.gallery?.theme_color || '')
const showImageInfo = computed(() => galleryData.value?.gallery?.show_image_info !== false)
const allowDownload = computed(() => galleryData.value?.gallery?.allow_download !== false)
const nsfwWarning = computed(() => galleryData.value?.gallery?.nsfw_warning === true)
const customHeaderText = computed(() => galleryData.value?.gallery?.custom_header_text || '')
const hasCover = computed(() => !!(galleryData.value?.gallery?.cover_url || galleryData.value?.gallery?.cover_image))

// NSFW 确认（sessionStorage 记忆）
const nsfwConfirmed = ref(false)
const nsfwSessionKey = computed(() => `nsfw_confirmed_${shareAllToken.value}_${galleryId.value}`)

const confirmNsfw = () => {
  nsfwConfirmed.value = true
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(nsfwSessionKey.value, '1')
  }
}

const leaveNsfw = () => {
  if (typeof window !== 'undefined') window.history.back()
}

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
  // 检查 sessionStorage 中的 NSFW 确认状态
  if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(nsfwSessionKey.value)) {
    nsfwConfirmed.value = true
  } else {
    nsfwConfirmed.value = false
  }

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

const openLightbox = (index: number) => {
  const count = galleryData.value?.images?.length || 0
  if (!count) return
  lightboxIndex.value = Math.min(Math.max(index, 0), count - 1)
  lightboxOpen.value = true
}

// 回到顶部
const { y: scrollY } = useWindowScroll()
const showBackToTop = computed(() => scrollY.value > 500)
const scrollToTop = () => {
  if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch(requiresToken, (needsToken) => {
  if (needsToken) showLoginModal.value = true
})

watch([shareAllToken, galleryId], () => {
  lightboxOpen.value = false
  loadGallery()
})

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
