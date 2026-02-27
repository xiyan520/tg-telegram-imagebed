<template>
  <div class="space-y-6 sm:space-y-8">
    <section class="rounded-3xl border border-stone-200/70 bg-white/85 p-5 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/75 sm:p-7">
      <div class="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber-600 dark:text-amber-400">Collections</p>
          <h1 class="text-2xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-4xl">画集管理</h1>
          <p class="text-sm leading-relaxed text-stone-600 dark:text-stone-300 sm:text-base">管理画集分享状态、访问权限和内容封面。</p>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-xs text-stone-500 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <UButton
            icon="heroicons:arrow-path"
            color="gray"
            variant="ghost"
            :loading="loading"
            @click="loadData(currentPage)"
          />
        </div>
      </div>
    </section>

    <section class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/80">
      <div class="flex items-center justify-between gap-3">
        <p class="text-sm text-stone-500 dark:text-stone-400">本页共 {{ galleries.length }} 个画集，点击任意卡片进入详情管理。</p>
        <p class="text-xs text-stone-400 dark:text-stone-500">每页 {{ perPage }} 项</p>
      </div>
    </section>

    <div v-if="loading && galleries.length === 0" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div v-for="i in 8" :key="i" class="overflow-hidden rounded-2xl border border-stone-200 dark:border-stone-700">
        <USkeleton class="aspect-[4/3] w-full" />
        <div class="space-y-2 p-4">
          <USkeleton class="h-5 w-2/3" />
          <USkeleton class="h-4 w-1/3" />
        </div>
      </div>
    </div>

    <div v-else-if="loadError" class="rounded-2xl border border-red-200 bg-red-50 p-8 text-center dark:border-red-900/40 dark:bg-red-950/20">
      <UIcon name="heroicons:exclamation-triangle" class="mx-auto h-9 w-9 text-red-500" />
      <p class="mt-3 text-sm text-red-700 dark:text-red-300">画集列表加载失败，请重试。</p>
    </div>

    <div v-else-if="galleries.length === 0" class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-10 text-center dark:border-stone-700 dark:bg-neutral-900/70">
      <UIcon name="heroicons:rectangle-stack" class="mx-auto h-12 w-12 text-stone-300 dark:text-stone-600" />
      <p class="mt-3 text-lg font-medium text-stone-900 dark:text-white">暂无画集</p>
      <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">请在主站管理后台创建画集</p>
    </div>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <NuxtLink
        v-for="gallery in galleries"
        :key="gallery.id"
        :to="`/gallery-site/admin/galleries/${gallery.id}`"
        class="group overflow-hidden rounded-2xl border border-stone-200 bg-white transition-all duration-300 hover:-translate-y-1 hover:border-amber-300 hover:shadow-xl dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
      >
        <div class="relative aspect-[4/3] overflow-hidden">
          <img
            v-if="gallery.cover_url"
            :src="gallery.cover_url"
            :alt="gallery.name"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.06]"
          />
          <div
            v-else
            class="flex h-full w-full items-center justify-center bg-gradient-to-br from-stone-100 to-stone-200 dark:from-neutral-800 dark:to-neutral-700"
          >
            <UIcon name="heroicons:photo" class="h-10 w-10 text-stone-400" />
          </div>

          <div class="absolute left-2 top-2 flex items-center gap-1.5">
            <UBadge v-if="gallery.access_mode !== 'public'" :color="gallery.access_mode === 'admin_only' ? 'red' : 'amber'" variant="solid" size="xs" class="shadow">
              {{ gallery.access_mode === 'password' ? '密码' : gallery.access_mode === 'token' ? 'Token' : '私有' }}
            </UBadge>
            <UBadge v-if="gallery.share_enabled" color="green" variant="solid" size="xs" class="shadow">
              已分享
            </UBadge>
          </div>
          <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3">
            <p class="truncate text-sm font-semibold text-white">{{ gallery.name }}</p>
          </div>
        </div>

        <div class="flex items-center justify-between p-4 text-xs text-stone-500 dark:text-stone-400">
          <span>{{ gallery.image_count }} 张图片</span>
          <span>更新 {{ formatDate(gallery.updated_at) }}</span>
        </div>
      </NuxtLink>
    </div>

    <div v-if="totalPages > 1" class="flex justify-center">
      <div class="flex items-center gap-2">
        <UButton icon="heroicons:chevron-left" color="gray" variant="ghost" size="sm" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)" />
        <span class="text-sm text-stone-500 dark:text-stone-400">{{ currentPage }} / {{ totalPages }}</span>
        <UButton icon="heroicons:chevron-right" color="gray" variant="ghost" size="sm" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)" />
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import type { AdminGallerySiteItem } from '~/composables/useGallerySiteAdmin'

definePageMeta({
  layout: 'gallery-site-admin',
  middleware: 'gallery-site-admin-auth'
})

const { getGalleries } = useGallerySiteAdmin()
const notification = useNotification()

const loading = ref(true)
const loadError = ref<string | null>(null)
const galleries = ref<AdminGallerySiteItem[]>([])
const currentPage = ref(1)
const totalPages = ref(1)
const perPage = 20

const formatDate = (value?: string) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}

const loadData = async (page = 1) => {
  loading.value = true
  loadError.value = null
  try {
    const res = await getGalleries(page, perPage)
    galleries.value = res.items
    currentPage.value = res.page
    totalPages.value = Math.ceil(res.total / res.per_page) || 1
  } catch (e: any) {
    notification.error('加载失败', e.message || '无法加载画集列表')
    loadError.value = 'failed'
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) loadData(page)
}

onMounted(() => loadData())
</script>
