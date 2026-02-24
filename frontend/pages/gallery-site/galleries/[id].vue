<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
    <!-- 加载骨架屏 -->
    <div v-if="loading">
      <div class="flex items-center gap-3 mb-6">
        <USkeleton class="h-8 w-8 rounded-lg" />
        <USkeleton class="h-8 w-48" />
      </div>
      <USkeleton class="h-5 w-64 mb-8" />
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <USkeleton v-for="i in 12" :key="i" class="aspect-square rounded-lg" />
      </div>
    </div>

    <!-- 画集内容 -->
    <div v-else-if="gallery">
      <!-- 顶部信息 -->
      <div class="mb-8">
        <NuxtLink
          to="/gallery-site/galleries"
          class="inline-flex items-center gap-1.5 text-sm text-stone-500 dark:text-stone-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors mb-4"
        >
          <UIcon name="heroicons:arrow-left" class="w-4 h-4" />
          返回画集列表
        </NuxtLink>
        <h1 class="text-3xl sm:text-4xl font-bold font-serif text-stone-900 dark:text-white">
          {{ gallery.name }}
        </h1>
        <p v-if="gallery.description" class="mt-2 text-stone-500 dark:text-stone-400">
          {{ gallery.description }}
        </p>
        <p class="mt-2 text-sm text-stone-400 dark:text-stone-500">
          共 {{ gallery.image_count }} 张图片
        </p>
      </div>

      <!-- 图片网格 -->
      <div v-if="images.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <button
          v-for="(img, idx) in images"
          :key="img.encrypted_id"
          class="group relative aspect-square rounded-lg overflow-hidden bg-stone-100 dark:bg-neutral-800 cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900"
          @click="openLightbox(idx)"
        >
          <img
            :src="`/image/${img.encrypted_id}`"
            :alt="img.original_filename"
            class="w-full h-full object-cover transform group-hover:scale-[1.03] transition-transform duration-300"
            loading="lazy"
          />
          <!-- hover 遮罩 -->
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-300"></div>
        </button>
      </div>

      <!-- 图片为空 -->
      <div v-else class="text-center py-20">
        <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-300 dark:text-stone-600 mx-auto" />
        <p class="mt-4 text-stone-500 dark:text-stone-400">该画集暂无图片</p>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex justify-center mt-8">
        <UPagination
          v-model="currentPage"
          :page-count="imagesPerPage"
          :total="totalImages"
        />
      </div>
    </div>

    <!-- 画集不存在 -->
    <div v-else class="text-center py-20">
      <UIcon name="heroicons:exclamation-triangle" class="w-16 h-16 text-stone-300 dark:text-stone-600 mx-auto" />
      <p class="mt-4 text-lg text-stone-500 dark:text-stone-400">画集不存在或不可访问</p>
      <NuxtLink
        to="/gallery-site/galleries"
        class="inline-flex items-center gap-1.5 mt-4 text-sm text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
      >
        <UIcon name="heroicons:arrow-left" class="w-4 h-4" />
        返回画集列表
      </NuxtLink>
    </div>

    <!-- 灯箱 -->
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
          class="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="图片查看器"
          @click.self="closeLightbox"
          @keydown.esc="closeLightbox"
          @keydown.left="lightboxPrev"
          @keydown.right="lightboxNext"
          tabindex="0"
          ref="lightboxRef"
        >
          <!-- 关闭按钮 -->
          <button
            class="absolute top-4 right-4 z-10 p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            @click="closeLightbox"
            aria-label="关闭"
          >
            <UIcon name="heroicons:x-mark" class="w-6 h-6" />
          </button>

          <!-- 图片信息 -->
          <div class="absolute top-4 left-4 z-10 text-white/70 text-sm">
            <p class="font-medium text-white/90">{{ currentLightboxImage?.original_filename }}</p>
            <p>{{ formatFileSize(currentLightboxImage?.file_size) }} &middot; {{ lightboxIndex + 1 }} / {{ images.length }}</p>
          </div>

          <!-- 左箭头 -->
          <button
            v-if="lightboxIndex > 0"
            class="absolute left-4 top-1/2 -translate-y-1/2 z-10 p-3 text-white/60 hover:text-white hover:bg-white/10 rounded-full transition-colors hidden sm:block"
            @click.stop="lightboxPrev"
            aria-label="上一张"
          >
            <UIcon name="heroicons:chevron-left" class="w-8 h-8" />
          </button>

          <!-- 图片 -->
          <div class="absolute inset-0 flex items-center justify-center p-12 sm:p-16">
            <img
              v-if="currentLightboxImage"
              :src="`/image/${currentLightboxImage.encrypted_id}`"
              :alt="currentLightboxImage.original_filename"
              class="max-w-full max-h-full object-contain select-none"
              draggable="false"
            />
          </div>

          <!-- 右箭头 -->
          <button
            v-if="lightboxIndex < images.length - 1"
            class="absolute right-4 top-1/2 -translate-y-1/2 z-10 p-3 text-white/60 hover:text-white hover:bg-white/10 rounded-full transition-colors hidden sm:block"
            @click.stop="lightboxNext"
            aria-label="下一张"
          >
            <UIcon name="heroicons:chevron-right" class="w-8 h-8" />
          </button>
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

// 灯箱状态
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxRef = ref<HTMLElement | null>(null)
const currentLightboxImage = computed(() => images.value[lightboxIndex.value] || null)

/** 加载画集数据 */
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

/** 打开灯箱 */
const openLightbox = (idx: number) => {
  lightboxIndex.value = idx
  lightboxOpen.value = true
  document.body.style.overflow = 'hidden'
  nextTick(() => lightboxRef.value?.focus())
}

/** 关闭灯箱 */
const closeLightbox = () => {
  lightboxOpen.value = false
  document.body.style.overflow = ''
}

/** 灯箱导航 */
const lightboxPrev = () => { if (lightboxIndex.value > 0) lightboxIndex.value-- }
const lightboxNext = () => { if (lightboxIndex.value < images.value.length - 1) lightboxIndex.value++ }

/** 格式化文件大小 */
const formatFileSize = (bytes?: number) => {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// 翻页时重新加载
watch(currentPage, () => {
  loadGallery()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

onMounted(() => loadGallery())

// 组件卸载时确保恢复 body 滚动
onUnmounted(() => { document.body.style.overflow = '' })
</script>

