<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-950">
    <!-- 页头 -->
    <header class="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl border-b border-stone-200/50 dark:border-neutral-700/50 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-base sm:text-lg font-semibold text-stone-900 dark:text-white">全部画集</h1>
            <p class="text-xs sm:text-sm text-stone-500 dark:text-stone-400">
              共 {{ total }} 个画集
            </p>
          </div>
          <UButton
            color="gray"
            variant="ghost"
            size="sm"
            :icon="copied ? 'heroicons:check' : 'heroicons:link'"
            @click="copyLink"
          >
            <span class="hidden sm:inline">{{ copied ? '已复制' : '复制链接' }}</span>
          </UButton>
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
      </div>

      <!-- 空状态 -->
      <div v-else-if="galleries.length === 0" class="text-center py-32">
        <div class="w-24 h-24 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-6">
          <UIcon name="heroicons:rectangle-stack" class="w-12 h-12 text-stone-400" />
        </div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">暂无画集</h1>
        <p class="text-stone-600 dark:text-stone-400">还没有可展示的画集</p>
      </div>

      <!-- 画集网格 -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <NuxtLink
          v-for="gallery in galleries"
          :key="gallery.id"
          :to="`/galleries/${shareToken}/${gallery.id}`"
          :prefetch="false"
          style="content-visibility: auto; contain-intrinsic-size: 320px 240px;"
          class="group relative aspect-[4/3] rounded-2xl overflow-hidden border border-stone-200 dark:border-neutral-700 hover:border-amber-400 dark:hover:border-amber-500 transition-all hover:shadow-xl bg-white dark:bg-neutral-900"
        >
          <!-- 封面图 -->
          <img
            v-if="gallery.cover_url"
            :src="gallery.cover_url"
            :alt="gallery.name"
            loading="lazy"
            decoding="async"
            class="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500"
          />
          <div
            v-else
            class="w-full h-full bg-gradient-to-br from-stone-100 to-stone-200 dark:from-neutral-800 dark:to-neutral-700 flex items-center justify-center"
          >
            <UIcon :name="gallery.is_locked ? 'heroicons:lock-closed' : 'heroicons:photo'" class="w-16 h-16 text-stone-300 dark:text-neutral-600" />
          </div>

          <!-- 锁定标记 -->
          <div v-if="gallery.is_locked" class="absolute top-3 right-3 z-10">
            <div class="bg-black/60 backdrop-blur-sm rounded-full p-2">
              <UIcon name="heroicons:lock-closed" class="w-4 h-4 text-white" />
            </div>
          </div>

          <!-- 信息遮罩 -->
          <div class="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
            <h3 class="text-white font-semibold text-lg truncate">{{ gallery.name }}</h3>
            <p class="text-stone-300 text-sm mt-1">{{ gallery.image_count }} 张图片</p>
          </div>
        </NuxtLink>
      </div>

      <!-- 加载更多 -->
      <div v-if="hasMore" class="text-center pt-8">
        <UButton color="gray" variant="outline" :loading="loadingMore" @click="loadMore">
          加载更多
        </UButton>
      </div>
    </main>

    <!-- 底部 -->
    <footer class="py-6 text-center">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-1.5 text-xs text-stone-400 dark:text-stone-500 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
      >
        <UIcon name="heroicons:cloud-arrow-up" class="w-3.5 h-3.5" />
        <span>Powered by {{ displayName }}</span>
      </NuxtLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useInfiniteScroll } from '@vueuse/core'

definePageMeta({ layout: false })

const route = useRoute()
const config = useRuntimeConfig()
const { displayName } = useSeoSettings()

const shareToken = computed(() => route.params.token as string)

const loading = ref(true)
const error = ref('')
const galleries = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loadingMore = ref(false)

const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

const loadGalleries = async (append = false) => {
  if (!append) loading.value = true
  error.value = ''

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/shared/all/${shareToken.value}`, {
      params: { page: page.value, limit: 20 }
    })

    if (response.success) {
      if (append) {
        galleries.value.push(...response.data.items)
      } else {
        galleries.value = response.data.items
      }
      total.value = response.data.total
      hasMore.value = response.data.has_more
    } else {
      throw new Error(response.error)
    }
  } catch (e: any) {
    error.value = e.data?.error || e.message || '分享链接无效或已过期'
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = async () => {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  page.value++
  await loadGalleries(true)
}

const copyLink = async () => {
  if (typeof window === 'undefined') return
  try {
    await navigator.clipboard.writeText(window.location.href)
  } catch {
    const el = document.createElement('textarea')
    el.value = window.location.href
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

// 监听路由参数变化
watch(shareToken, () => {
  page.value = 1
  galleries.value = []
  loadGalleries()
})

// 无限滚动
if (import.meta.client) {
  useInfiniteScroll(window, loadMore, {
    distance: 800,
    canLoadMore: () => hasMore.value && !loadingMore.value && !loading.value && !error.value
  })
}

onMounted(loadGalleries)

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})
</script>
