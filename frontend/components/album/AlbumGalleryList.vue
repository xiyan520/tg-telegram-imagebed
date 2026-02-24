<template>
  <div class="space-y-4">
    <!-- "我的上传"快捷入口 -->
    <div
      class="relative group rounded-2xl overflow-hidden border border-amber-200/60 dark:border-amber-800/40 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 p-4 cursor-pointer hover:shadow-md hover:shadow-amber-500/10 transition-all duration-300"
      @click="$emit('navigate', 'uploads')"
    >
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm shadow-amber-500/25 group-hover:scale-105 transition-transform duration-300">
          <UIcon name="heroicons:cloud-arrow-up" class="w-6 h-6 text-white" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-stone-800 dark:text-white">我的上传</h3>
          <p class="text-sm text-stone-500 dark:text-stone-400">
            共 <span class="font-semibold text-amber-600 dark:text-amber-400">{{ uploadCount }}</span> 张图片
          </p>
        </div>
        <UIcon name="heroicons:chevron-right" class="w-5 h-5 text-stone-300 dark:text-stone-600 group-hover:text-amber-500 group-hover:translate-x-0.5 transition-all" />
      </div>
    </div>

    <!-- 标题栏 -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-bold text-stone-900 dark:text-white">
        我的画集
        <span v-if="total > 0" class="text-sm font-normal text-stone-400 ml-1">({{ total }})</span>
      </h2>
      <div class="flex items-center gap-1.5">
        <button
          class="w-8 h-8 rounded-lg flex items-center justify-center text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-700/50 transition-all"
          :class="{ 'animate-spin': loading }"
          @click="loadGalleries"
        >
          <UIcon name="heroicons:arrow-path" class="w-4 h-4" />
        </button>
        <UButton icon="heroicons:plus" color="primary" size="sm" :ui="{ rounded: 'rounded-xl' }" @click="showCreate = true">
          创建画集
        </UButton>
      </div>
    </div>

    <!-- 搜索 -->
    <div v-if="galleries.length > 0" class="max-w-xs">
      <UInput v-model="searchQuery" placeholder="搜索画集..." size="sm" :ui="{ rounded: 'rounded-xl' }">
        <template #leading><UIcon name="heroicons:magnifying-glass" class="w-4 h-4 text-stone-400" /></template>
      </UInput>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && galleries.length === 0" class="flex justify-center py-16">
      <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && galleries.length === 0" class="text-center py-16">
      <div class="w-16 h-16 mx-auto bg-stone-100 dark:bg-neutral-800 rounded-2xl flex items-center justify-center mb-4">
        <UIcon name="heroicons:rectangle-stack" class="w-8 h-8 text-stone-300 dark:text-neutral-600" />
      </div>
      <p class="text-stone-500 dark:text-stone-400 mb-4">还没有画集</p>
      <UButton color="primary" :ui="{ rounded: 'rounded-xl' }" @click="showCreate = true">
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
    <div v-if="!loading && galleries.length > 0 && filteredGalleries.length === 0" class="text-center py-10">
      <p class="text-stone-400 text-sm">没有匹配的画集</p>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center pt-2">
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
