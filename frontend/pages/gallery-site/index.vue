<template>
  <div>
    <!-- Hero 区域 -->
    <section class="relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-amber-50 via-orange-50/50 to-stone-50 dark:from-amber-950/30 dark:via-neutral-950 dark:to-neutral-950"></div>
      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
        <div class="text-center">
          <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold font-serif text-stone-900 dark:text-white tracking-tight">
            {{ siteName }}
          </h1>
          <p class="mt-4 text-lg sm:text-xl text-stone-500 dark:text-stone-400 max-w-2xl mx-auto">
            {{ siteDescription }}
          </p>
          <!-- 统计数据 -->
          <div v-if="stats" class="mt-8 flex items-center justify-center gap-8 sm:gap-12">
            <div class="text-center">
              <p class="text-3xl sm:text-4xl font-bold text-amber-600 dark:text-amber-400">{{ stats.gallery_count }}</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">画集</p>
            </div>
            <div class="w-px h-10 bg-stone-300 dark:bg-stone-600"></div>
            <div class="text-center">
              <p class="text-3xl sm:text-4xl font-bold text-amber-600 dark:text-amber-400">{{ stats.image_count }}</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">图片</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 精选画集 -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <div class="flex items-center justify-between mb-8">
        <h2 class="text-2xl sm:text-3xl font-bold font-serif text-stone-900 dark:text-white">精选画集</h2>
        <NuxtLink
          to="/gallery-site/galleries"
          class="text-sm font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 transition-colors"
        >
          查看全部 &rarr;
        </NuxtLink>
      </div>

      <!-- 加载骨架屏 -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-white dark:bg-neutral-900">
          <USkeleton class="w-full aspect-[3/2]" />
          <div class="p-5 space-y-3">
            <USkeleton class="h-5 w-3/4" />
            <USkeleton class="h-4 w-1/3" />
          </div>
        </div>
      </div>

      <!-- 精选画集网格 -->
      <div v-else-if="featured.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <NuxtLink
          v-for="gallery in featured"
          :key="gallery.id"
          :to="`/gallery-site/galleries/${gallery.id}`"
          class="group rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-white dark:bg-neutral-900 hover:shadow-lg hover:border-amber-300 dark:hover:border-amber-600 transition-all duration-300"
        >
          <!-- 封面图 -->
          <div class="aspect-[3/2] overflow-hidden bg-stone-100 dark:bg-neutral-800">
            <img
              v-if="gallery.cover_url"
              :src="gallery.cover_url"
              :alt="gallery.name"
              class="w-full h-full object-cover transform group-hover:scale-[1.03] transition-transform duration-500"
              loading="lazy"
            />
            <div v-else class="w-full h-full bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30 flex items-center justify-center">
              <UIcon name="heroicons:photo" class="w-12 h-12 text-amber-300 dark:text-amber-700" />
            </div>
          </div>
          <!-- 信息 -->
          <div class="p-5">
            <h3 class="text-lg font-semibold font-serif text-stone-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors truncate">
              {{ gallery.name }}
            </h3>
            <p class="mt-1.5 text-sm text-stone-500 dark:text-stone-400">
              {{ gallery.image_count }} 张图片
            </p>
          </div>
        </NuxtLink>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-20">
        <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-300 dark:text-stone-600 mx-auto" />
        <p class="mt-4 text-stone-500 dark:text-stone-400">暂无画集</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem, GallerySiteStats } from '~/composables/useGallerySite'

definePageMeta({ layout: 'gallery-site' })

const { getFeatured, getStats } = useGallerySiteApi()

// 从缓存的站点模式中获取信息
const siteMode = useState<{ mode: string; site_name?: string; site_description?: string } | null>('gallery-site-mode', () => null)
const siteName = computed(() => siteMode.value?.site_name || '画集')
const siteDescription = computed(() => siteMode.value?.site_description || '精选图片画集')

const loading = ref(true)
const featured = ref<GallerySiteItem[]>([])
const stats = ref<GallerySiteStats | null>(null)

onMounted(async () => {
  try {
    const [featuredData, statsData] = await Promise.all([
      getFeatured(6),
      getStats()
    ])
    featured.value = featuredData
    stats.value = statsData
  } catch (e) {
    console.error('加载画集首页数据失败:', e)
  } finally {
    loading.value = false
  }
})
</script>
