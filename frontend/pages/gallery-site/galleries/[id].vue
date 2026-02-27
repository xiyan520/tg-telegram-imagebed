<template>
  <div class="pb-14 sm:pb-20">
    <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <div v-if="loading" class="space-y-6">
        <USkeleton class="h-7 w-36" />
        <USkeleton class="h-64 w-full rounded-3xl sm:h-80" />
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <USkeleton v-for="i in 12" :key="i" class="aspect-square rounded-xl" />
        </div>
      </div>

      <div v-else-if="gallery" class="space-y-8 sm:space-y-10">
        <section class="relative overflow-hidden rounded-3xl border border-stone-200/70 dark:border-stone-700/70">
          <div class="absolute inset-0">
            <img
              v-if="heroCover"
              :src="heroCover"
              :alt="gallery.name"
              class="h-full w-full object-cover"
              loading="eager"
            />
            <div v-else class="h-full w-full bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30" />
            <div class="absolute inset-0 bg-gradient-to-r from-black/70 via-black/50 to-black/30" />
          </div>

          <div class="relative flex min-h-[17.5rem] flex-col justify-between p-5 text-white sm:min-h-[22rem] sm:p-8 lg:min-h-[25rem]">
            <div class="flex flex-col gap-2 min-[430px]:flex-row min-[430px]:items-center min-[430px]:justify-between">
              <NuxtLink
                to="/gallery-site/galleries"
                class="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-white/30 bg-black/20 px-3 py-1.5 text-sm text-white/90 backdrop-blur transition-colors hover:bg-black/35 min-[430px]:w-auto"
              >
                <UIcon name="heroicons:arrow-left" class="h-4 w-4" />
                返回画集列表
              </NuxtLink>

              <button
                v-if="gallery.share_url"
                class="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-white/30 bg-black/20 px-3 py-1.5 text-sm text-white/90 backdrop-blur transition-colors hover:bg-black/35 min-[430px]:w-auto"
                @click="copyShareUrl"
              >
                <UIcon :name="copied ? 'heroicons:check' : 'heroicons:share'" class="h-4 w-4" />
                {{ copied ? '链接已复制' : '分享画集' }}
              </button>
            </div>

            <div class="space-y-3">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-white/75">Gallery Detail</p>
              <h1 class="max-w-3xl text-3xl font-bold font-serif tracking-tight text-white sm:text-4xl lg:text-5xl">
                {{ gallery.name }}
              </h1>
              <p class="max-w-2xl text-sm leading-relaxed text-white/85 sm:text-base">
                {{ gallery.description || '这一组内容暂未填写描述，直接进入浏览区查看完整图片序列。' }}
              </p>
              <div class="flex flex-wrap items-center gap-2 pt-1 text-xs text-white/85 sm:text-sm">
                <span class="rounded-full border border-white/25 bg-white/10 px-3 py-1">{{ gallery.image_count }} 张图片</span>
                <span class="rounded-full border border-white/25 bg-white/10 px-3 py-1">更新时间 {{ formatDate(gallery.updated_at) }}</span>
                <span class="rounded-full border border-white/25 bg-white/10 px-3 py-1">当前第 {{ currentPage }} 页</span>
              </div>
            </div>
          </div>
        </section>

        <section class="space-y-5">
          <div class="flex flex-col gap-2 rounded-2xl border border-stone-200/80 bg-white/90 p-4 backdrop-blur dark:border-stone-700/70 dark:bg-neutral-900/80 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-sm text-stone-500 dark:text-stone-400">
              共 <span class="font-semibold text-stone-900 dark:text-white">{{ totalImages }}</span> 张图片，点击任意图片可进入灯箱浏览。
            </p>
            <p class="text-xs leading-relaxed text-stone-400 dark:text-stone-500 sm:text-right">
              每页 {{ imagesPerPage }} 项 · 第 {{ currentPage }} / {{ Math.max(totalPages, 1) }} 页
            </p>
          </div>

          <div v-if="images.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4">
            <button
              v-for="(img, idx) in images"
              :key="img.encrypted_id"
              class="group relative aspect-square overflow-hidden rounded-xl bg-stone-100 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 dark:bg-neutral-800 dark:focus:ring-offset-neutral-900"
              :class="{ 'sm:col-span-2 sm:row-span-2 sm:aspect-[4/3] lg:aspect-square': idx === 0 }"
              @click="openLightbox(idx)"
            >
              <img
                :src="img.url"
                :alt="img.original_filename"
                class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                loading="lazy"
              />
              <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/40 via-black/10 to-transparent opacity-70 transition-opacity group-hover:opacity-95" />
              <div class="absolute bottom-0 left-0 right-0 flex items-center justify-between p-2.5 text-xs text-white/90">
                <span class="truncate">{{ img.original_filename }}</span>
                <span>#{{ idx + 1 }}</span>
              </div>
            </button>
          </div>

          <div v-else class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-10 text-center dark:border-stone-700 dark:bg-neutral-900/70">
            <UIcon name="heroicons:photo" class="mx-auto h-12 w-12 text-stone-300 dark:text-stone-600" />
            <p class="mt-3 text-stone-500 dark:text-stone-400">该画集暂无图片</p>
          </div>

          <div v-if="totalPages > 1" class="flex justify-center pt-2">
            <UPagination
              v-model="currentPage"
              :page-count="imagesPerPage"
              :total="totalImages"
            />
          </div>
        </section>
      </div>

      <div v-else class="rounded-2xl border border-red-200 bg-red-50 p-10 text-center dark:border-red-900/40 dark:bg-red-950/20">
        <UIcon name="heroicons:exclamation-triangle" class="mx-auto h-12 w-12 text-red-500" />
        <p class="mt-4 text-lg text-red-700 dark:text-red-300">画集不存在或不可访问</p>
        <NuxtLink
          to="/gallery-site/galleries"
          class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-amber-600 transition-colors hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
        >
          <UIcon name="heroicons:arrow-left" class="h-4 w-4" />
          返回画集列表
        </NuxtLink>
      </div>
    </div>

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
          ref="lightboxRef"
          class="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="图片查看器"
          tabindex="0"
          @click.self="closeLightbox"
          @keydown.esc="closeLightbox"
          @keydown.left="lightboxPrev"
          @keydown.right="lightboxNext"
        >
          <button
            class="absolute right-3 top-3 z-10 rounded-lg p-2 text-white/70 transition-colors hover:bg-white/10 hover:text-white sm:right-5 sm:top-5"
            @click="closeLightbox"
            aria-label="关闭"
          >
            <UIcon name="heroicons:x-mark" class="h-6 w-6" />
          </button>

          <div class="absolute left-3 right-14 top-3 z-10 rounded-lg bg-black/30 px-3 py-2 text-xs text-white/75 backdrop-blur sm:left-5 sm:right-auto sm:top-5 sm:text-sm">
            <p class="max-w-[calc(100vw-6.5rem)] truncate font-medium text-white/90 sm:max-w-[55vw]">{{ currentLightboxImage?.original_filename }}</p>
            <p>{{ formatFileSize(currentLightboxImage?.file_size) }} · {{ lightboxIndex + 1 }} / {{ images.length }}</p>
          </div>

          <button
            v-if="lightboxIndex > 0"
            class="absolute left-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full p-3 text-white/60 transition-colors hover:bg-white/10 hover:text-white sm:block"
            @click.stop="lightboxPrev"
            aria-label="上一张"
          >
            <UIcon name="heroicons:chevron-left" class="h-8 w-8" />
          </button>

          <div class="absolute inset-0 flex items-center justify-center p-8 sm:p-16">
            <img
              v-if="currentLightboxImage"
              :src="currentLightboxImage.url"
              :alt="currentLightboxImage.original_filename"
              class="max-h-full max-w-full select-none object-contain"
              draggable="false"
            />
          </div>

          <button
            v-if="lightboxIndex < images.length - 1"
            class="absolute right-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full p-3 text-white/60 transition-colors hover:bg-white/10 hover:text-white sm:block"
            @click.stop="lightboxNext"
            aria-label="下一张"
          >
            <UIcon name="heroicons:chevron-right" class="h-8 w-8" />
          </button>

          <div class="absolute bottom-4 left-0 right-0 flex items-center justify-center gap-3 sm:hidden">
            <button
              class="inline-flex items-center justify-center rounded-full border border-white/20 bg-black/40 p-2 text-white/80"
              :disabled="lightboxIndex === 0"
              @click.stop="lightboxPrev"
              aria-label="上一张"
            >
              <UIcon name="heroicons:chevron-left" class="h-5 w-5" />
            </button>
            <button
              class="inline-flex items-center justify-center rounded-full border border-white/20 bg-black/40 p-2 text-white/80"
              :disabled="lightboxIndex >= images.length - 1"
              @click.stop="lightboxNext"
              aria-label="下一张"
            >
              <UIcon name="heroicons:chevron-right" class="h-5 w-5" />
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem, GallerySiteImage } from '~/composables/useGallerySite'

definePageMeta({ layout: 'gallery-site' })

const route = useRoute()
const { getGallery } = useGallerySiteApi()

const loading = ref(true)
const gallery = ref<GallerySiteItem | null>(null)
const images = ref<GallerySiteImage[]>([])
const currentPage = ref(1)
const totalImages = ref(0)
const imagesPerPage = 20
const totalPages = computed(() => Math.ceil(totalImages.value / imagesPerPage))

const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxRef = ref<HTMLElement | null>(null)
const currentLightboxImage = computed(() => images.value[lightboxIndex.value] || null)
const heroCover = computed(() => gallery.value?.cover_url || images.value[0]?.url || '')

const formatDate = (value?: string) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}

const copyShareUrl = async () => {
  const url = gallery.value?.share_url
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 2000)
  } catch {
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 2000)
  }
}

const loadGallery = async () => {
  loading.value = true
  try {
    const id = Number(route.params.id)
    if (isNaN(id)) throw new Error('无效的画集 ID')
    const data = await getGallery(id, currentPage.value)
    gallery.value = data.gallery
    images.value = data.images.items
    totalImages.value = data.images.total
  } catch (e) {
    console.error('加载画集详情失败:', e)
    gallery.value = null
  } finally {
    loading.value = false
  }
}

const openLightbox = (idx: number) => {
  lightboxIndex.value = idx
  lightboxOpen.value = true
  document.body.style.overflow = 'hidden'
  nextTick(() => lightboxRef.value?.focus())
}

const closeLightbox = () => {
  lightboxOpen.value = false
  document.body.style.overflow = ''
}

const lightboxPrev = () => {
  if (lightboxIndex.value > 0) lightboxIndex.value--
}

const lightboxNext = () => {
  if (lightboxIndex.value < images.value.length - 1) lightboxIndex.value++
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

watch(currentPage, () => {
  loadGallery()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

onMounted(() => loadGallery())

onUnmounted(() => {
  document.body.style.overflow = ''
  if (copyTimer) clearTimeout(copyTimer)
})
</script>

