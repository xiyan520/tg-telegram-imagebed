<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
    <h1 class="text-3xl font-bold font-serif text-stone-900 dark:text-white mb-8">全部画集</h1>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <div v-for="i in 8" :key="i" class="rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-white dark:bg-neutral-900">
        <USkeleton class="w-full aspect-[3/2]" />
        <div class="p-4 space-y-2">
          <USkeleton class="h-5 w-3/4" />
          <USkeleton class="h-4 w-1/3" />
        </div>
      </div>
    </div>

    <!-- 画集网格 -->
    <div v-else-if="galleries.length" class="space-y-8">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <NuxtLink
          v-for="gallery in galleries"
          :key="gallery.id"
          :to="`/gallery-site/galleries/${gallery.id}`"
          class="group rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-white dark:bg-neutral-900 hover:shadow-lg hover:border-amber-300 dark:hover:border-amber-600 transition-all duration-300"
        >
          <div class="aspect-[3/2] overflow-hidden bg-stone-100 dark:bg-neutral-800">
            <img
              v-if="gallery.cover_url"
              :src="gallery.cover_url"
              :alt="gallery.name"
              class="w-full h-full object-cover transform group-hover:scale-[1.03] transition-transform duration-500"
              loading="lazy"
            />
            <div v-else class="w-full h-full bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30 flex items-center justify-center">
              <UIcon name="heroicons:photo" class="w-10 h-10 text-amber-300 dark:text-amber-700" />
            </div>
          </div>
          <div class="p-4">
            <h3 class="font-semibold font-serif text-stone-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors truncate">
              {{ gallery.name }}
            </h3>
            <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">
              {{ gallery.image_count }} 张图片
            </p>
          </div>
        </NuxtLink>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex justify-center">
        <UPagination
          v-model="currentPage"
          :page-count="perPage"
          :total="total"
        />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="text-center py-20">
      <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-300 dark:text-stone-600 mx-auto" />
      <p class="mt-4 text-stone-500 dark:text-stone-400">暂无公开画集</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem } from '~/composables/useGallerySite'

definePageMeta({ layout: 'gallery-site' })

const { getGalleries } = useGallerySiteApi()

const loading = ref(true)
const galleries = ref<GallerySiteItem[]>([])
const currentPage = ref(1)
const total = ref(0)
const perPage = 20
const totalPages = computed(() => Math.ceil(total.value / perPage))

/** 加载画集列表 */
const loadGalleries = async () => {
  loading.value = true
  try {
    const data = await getGalleries(currentPage.value, perPage)
    galleries.value = data.items
    total.value = data.total
  } catch (e) {
    console.error('加载画集列表失败:', e)
  } finally {
    loading.value = false
  }
}

// 翻页时重新加载
watch(currentPage, () => {
  loadGalleries()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

onMounted(() => loadGalleries())
</script>