<template>
  <div class="pb-14 sm:pb-20">
    <section class="relative overflow-hidden border-b border-stone-200/70 dark:border-stone-800/70">
      <div class="pointer-events-none absolute inset-0">
        <div class="absolute inset-0 bg-gradient-to-br from-stone-100/80 via-amber-50/50 to-orange-100/60 dark:from-neutral-950 dark:via-amber-950/20 dark:to-neutral-900" />
        <div class="absolute -left-24 top-0 h-56 w-56 rounded-full bg-amber-300/20 blur-3xl dark:bg-amber-600/10" />
        <div class="absolute right-0 top-1/2 h-60 w-60 -translate-y-1/2 rounded-full bg-orange-300/25 blur-3xl dark:bg-orange-600/10" />
      </div>

      <div class="relative mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div class="grid gap-5 md:grid-cols-[minmax(0,1fr)_300px] md:items-end">
          <div class="space-y-4">
            <span class="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-white/80 px-3 py-1 text-xs font-semibold tracking-[0.2em] text-amber-700 shadow-sm dark:border-amber-700/60 dark:bg-neutral-900/70 dark:text-amber-300">
              <UIcon name="heroicons:squares-2x2" class="h-3.5 w-3.5" />
              ALL COLLECTIONS
            </span>
            <h1 class="text-3xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-5xl">
              全部画集
            </h1>
            <p class="max-w-2xl text-sm leading-relaxed text-stone-600 dark:text-stone-300 sm:text-base">
              这里收录站点全部公开画集。按内容量与更新时间持续迭代，适合从宏观视角一次性浏览完整内容脉络。
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="rounded-xl border border-stone-200/80 bg-white/80 p-3 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/70">
              <p class="text-xs text-stone-500 dark:text-stone-400">画集总数</p>
              <USkeleton v-if="loading && !total" class="mt-2 h-7 w-16" />
              <p v-else class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">{{ total }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/80 bg-white/80 p-3 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/70">
              <p class="text-xs text-stone-500 dark:text-stone-400">当前页码</p>
              <p class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">{{ currentPage }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="mx-auto mt-8 max-w-7xl space-y-7 px-4 sm:mt-10 sm:px-6 lg:px-8">
      <div class="flex flex-col gap-3 rounded-2xl border border-stone-200/80 bg-white/90 p-4 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/80 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-stone-500 dark:text-stone-400">
          共 <span class="font-semibold text-stone-900 dark:text-white">{{ total }}</span> 个公开画集
        </p>
        <p class="text-xs leading-relaxed text-stone-400 dark:text-stone-500 sm:text-right">
          每页 {{ perPage }} 项 · 第 {{ currentPage }} / {{ Math.max(totalPages, 1) }} 页
        </p>
      </div>

      <div v-if="loading" class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        <div v-for="i in 9" :key="i" class="overflow-hidden rounded-2xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-neutral-900">
          <USkeleton class="aspect-[4/3] w-full" />
          <div class="space-y-3 p-5">
            <USkeleton class="h-5 w-4/5" />
            <USkeleton class="h-4 w-1/2" />
            <USkeleton class="h-4 w-1/3" />
          </div>
        </div>
      </div>

      <div v-else-if="loadError" class="rounded-2xl border border-red-200 bg-red-50 p-8 text-center dark:border-red-900/40 dark:bg-red-950/20">
        <UIcon name="heroicons:exclamation-triangle" class="mx-auto h-10 w-10 text-red-500" />
        <p class="mt-3 text-sm text-red-700 dark:text-red-300">画集列表加载失败，请刷新后重试。</p>
      </div>

      <div v-else-if="galleries.length" class="space-y-8">
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <NuxtLink
            v-for="gallery in galleries"
            :key="gallery.id"
            :to="`/gallery-site/galleries/${gallery.id}`"
            class="group overflow-hidden rounded-2xl border border-stone-200 bg-white transition-all duration-300 hover:-translate-y-1 hover:border-amber-300 hover:shadow-xl hover:shadow-amber-500/10 dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
          >
            <div class="relative aspect-[4/3] overflow-hidden bg-stone-100 dark:bg-neutral-800">
              <img
                v-if="gallery.cover_url"
                :src="gallery.cover_url"
                :alt="gallery.name"
                class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
                loading="lazy"
              />
              <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30">
                <UIcon name="heroicons:photo" class="h-12 w-12 text-amber-300 dark:text-amber-700" />
              </div>
              <div class="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-4">
                <p class="text-xs uppercase tracking-[0.2em] text-white/75">Collection</p>
                <h2 class="mt-1 truncate text-lg font-semibold text-white">{{ gallery.name }}</h2>
              </div>
            </div>

            <div class="space-y-2 p-4">
              <p class="line-clamp-2 min-h-[2.75rem] text-sm leading-relaxed text-stone-500 dark:text-stone-400">
                {{ gallery.description || '暂无描述，点击进入查看该画集全部图片内容。' }}
              </p>
              <div class="flex min-h-[1.625rem] flex-wrap items-center justify-between gap-x-2 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
                <span>{{ gallery.image_count }} 张图片</span>
                <span class="truncate text-right sm:text-left">更新于 {{ formatDate(gallery.updated_at) }}</span>
              </div>
            </div>
          </NuxtLink>
        </div>

        <div v-if="totalPages > 1" class="flex justify-center">
          <UPagination
            v-model="currentPage"
            :page-count="perPage"
            :total="total"
          />
        </div>
      </div>

      <div v-else class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-10 text-center dark:border-stone-700 dark:bg-neutral-900/70">
        <UIcon name="heroicons:photo" class="mx-auto h-12 w-12 text-stone-300 dark:text-stone-600" />
        <p class="mt-3 text-stone-500 dark:text-stone-400">暂无公开画集</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem } from '~/composables/useGallerySite'

definePageMeta({ layout: 'gallery-site' })

const { getGalleries } = useGallerySiteApi()

const loading = ref(true)
const loadError = ref<string | null>(null)
const galleries = ref<GallerySiteItem[]>([])
const currentPage = ref(1)
const total = ref(0)
const perPage = 20
const totalPages = computed(() => Math.ceil(total.value / perPage))

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}

const loadGalleries = async () => {
  loading.value = true
  loadError.value = null
  try {
    const data = await getGalleries(currentPage.value, perPage)
    galleries.value = data.items
    total.value = data.total
  } catch (e) {
    console.error('加载画集列表失败:', e)
    loadError.value = 'failed'
  } finally {
    loading.value = false
  }
}

watch(currentPage, () => {
  loadGalleries()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

onMounted(() => loadGalleries())
</script>
