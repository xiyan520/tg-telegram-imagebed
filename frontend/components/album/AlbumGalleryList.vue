<template>
  <div class="space-y-4">
    <!-- "我的上传"快捷入口 -->
    <div
      class="relative rounded-xl overflow-hidden border border-amber-200 dark:border-amber-800 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 p-4 cursor-pointer hover:shadow-md transition-shadow"
      @click="$emit('navigate', 'uploads')"
    >
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center flex-shrink-0">
          <UIcon name="heroicons:cloud-arrow-up" class="w-6 h-6 text-white" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-gray-900 dark:text-white">我的上传</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            共 <span class="font-semibold text-amber-600 dark:text-amber-400">{{ uploadCount }}</span> 张图片
          </p>
        </div>
        <UIcon name="heroicons:chevron-right" class="w-5 h-5 text-gray-400" />
      </div>
    </div>

    <!-- 标题栏 -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white">
        我的画集 ({{ total }})
      </h2>
      <div class="flex items-center gap-2">
        <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="sm" :loading="loading" @click="loadGalleries" />
        <UButton icon="heroicons:plus" color="primary" size="sm" @click="showCreate = true">
          创建画集
        </UButton>
      </div>
    </div>

    <!-- 搜索 -->
    <div v-if="galleries.length > 0" class="max-w-xs">
      <UInput v-model="searchQuery" placeholder="搜索画集..." size="sm">
        <template #leading><UIcon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
      </UInput>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && galleries.length === 0" class="flex justify-center py-12">
      <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && galleries.length === 0" class="text-center py-12">
      <UIcon name="heroicons:rectangle-stack" class="w-16 h-16 text-stone-400 mx-auto mb-4" />
      <p class="text-stone-600 dark:text-stone-400 mb-4">还没有画集</p>
      <UButton color="primary" @click="showCreate = true">
        <template #leading><UIcon name="heroicons:plus" /></template>
        创建第一个画集
      </UButton>
    </div>

    <!-- 画集网格 -->
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <AlbumGalleryCard
        v-for="gallery in filteredGalleries"
        :key="gallery.id"
        :gallery="gallery"
        @click="$emit('navigate', 'detail', gallery.id)"
      />
    </div>

    <!-- 搜索无结果 -->
    <div v-if="!loading && galleries.length > 0 && filteredGalleries.length === 0" class="text-center py-8">
      <p class="text-stone-500">没有匹配的画集</p>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center">
      <UPagination v-model="currentPage" :total="total" :page-count="pageSize" @update:model-value="loadGalleries" />
    </div>

    <!-- 创建画集弹窗 -->
    <AlbumCreateGalleryModal v-model="showCreate" @created="loadGalleries" />
  </div>
</template>

<script setup lang="ts">
import type { Gallery } from '~/composables/useGalleryApi'

defineProps<{ uploadCount: number }>()
defineEmits<{
  (e: 'navigate', view: string, galleryId?: number): void
}>()

const toast = useLightToast()
const galleryApi = useGalleryApi()

const loading = ref(false)
const galleries = ref<Gallery[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const showCreate = ref(false)
const searchQuery = ref('')

// 前端过滤画集名称
const filteredGalleries = computed(() => {
  if (!searchQuery.value.trim()) return galleries.value
  const q = searchQuery.value.toLowerCase()
  return galleries.value.filter(g => g.name.toLowerCase().includes(q))
})

const loadGalleries = async () => {
  // 确保有有效 Token 再请求
  const tokenStore = useTokenStore()
  if (!tokenStore.hasToken) return

  loading.value = true
  try {
    const data = await galleryApi.getGalleries(currentPage.value, pageSize)
    galleries.value = data.items
    total.value = data.total
  } catch (e: any) {
    // 401 错误静默处理（Token 可能已失效）
    if (e?.response?.status === 401 || e?.statusCode === 401) return
    toast.error('加载画集失败', e.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadGalleries)

defineExpose({ refresh: loadGalleries })
</script>
