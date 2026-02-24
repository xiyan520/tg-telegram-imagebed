<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">画集管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">管理画集的分享状态和访问权限</p>
      </div>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="ghost"
        :loading="loading"
        @click="loadData(currentPage)"
      />
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading && galleries.length === 0" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      <div v-for="i in 10" :key="i" class="aspect-square rounded-xl overflow-hidden">
        <USkeleton class="w-full h-full" />
      </div>
    </div>

    <!-- 空状态 -->
    <UCard v-else-if="!loading && galleries.length === 0">
      <div class="text-center py-16">
        <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <UIcon name="heroicons:rectangle-stack" class="w-10 h-10 text-stone-400" />
        </div>
        <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无画集</p>
        <p class="text-sm text-stone-600 dark:text-stone-400">请在主站管理后台创建画集</p>
      </div>
    </UCard>

    <!-- 画集卡片网格 -->
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      <NuxtLink
        v-for="gallery in galleries"
        :key="gallery.id"
        :to="`/gallery-site/admin/galleries/${gallery.id}`"
        class="group relative aspect-square rounded-xl overflow-hidden border-2 border-stone-200 dark:border-neutral-700 hover:border-amber-400 dark:hover:border-amber-500 transition-all hover:shadow-lg"
      >
        <!-- 封面图 -->
        <img
          v-if="gallery.cover_url"
          :src="gallery.cover_url"
          :alt="gallery.name"
          class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
        />
        <div
          v-else
          class="w-full h-full bg-gradient-to-br from-stone-100 to-stone-200 dark:from-neutral-800 dark:to-neutral-700 flex items-center justify-center"
        >
          <UIcon name="heroicons:photo" class="w-12 h-12 text-stone-400" />
        </div>

        <!-- 分享标记 -->
        <div v-if="gallery.share_enabled" class="absolute top-2 right-2 z-10">
          <UBadge color="green" variant="solid" size="xs" class="shadow-lg">
            <template #leading><UIcon name="heroicons:share" class="w-3 h-3" /></template>
            已分享
          </UBadge>
        </div>

        <!-- 访问模式标记 -->
        <div v-if="gallery.access_mode !== 'public'" class="absolute top-2 left-2 z-10">
          <UBadge :color="gallery.access_mode === 'admin_only' ? 'red' : 'amber'" variant="solid" size="xs" class="shadow-lg">
            {{ gallery.access_mode === 'password' ? '密码' : gallery.access_mode === 'token' ? 'Token' : '私有' }}
          </UBadge>
        </div>

        <!-- 信息遮罩 -->
        <div class="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/80 via-black/50 to-transparent">
          <p class="text-white font-medium truncate">{{ gallery.name }}</p>
          <p class="text-stone-300 text-xs">{{ gallery.image_count }} 张图片</p>
        </div>
      </NuxtLink>
    </div>

    <!-- 分页 -->
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
const galleries = ref<AdminGallerySiteItem[]>([])
const currentPage = ref(1)
const totalPages = ref(1)
const perPage = 20

const loadData = async (page = 1) => {
  loading.value = true
  try {
    const res = await getGalleries(page, perPage)
    galleries.value = res.items
    currentPage.value = res.page
    totalPages.value = Math.ceil(res.total / res.per_page) || 1
  } catch (e: any) {
    notification.error('加载失败', e.message || '无法加载画集列表')
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) loadData(page)
}

onMounted(() => loadData())
</script>
