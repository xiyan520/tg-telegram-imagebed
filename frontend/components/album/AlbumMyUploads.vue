<template>
  <div class="space-y-4">
    <!-- 顶部导航 -->
    <div class="flex items-center gap-3">
      <UButton icon="heroicons:arrow-left" color="gray" variant="ghost" @click="$emit('navigate', 'list')" />
      <div class="flex-1">
        <h2 class="text-lg font-bold text-gray-900 dark:text-white">我的上传</h2>
        <p class="text-sm text-gray-500">共 {{ total }} 张图片</p>
      </div>
    </div>

    <!-- 搜索和排序 -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="flex-1 min-w-[200px]">
        <UInput v-model="searchQuery" placeholder="搜索图片..." size="sm">
          <template #leading><UIcon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
        </UInput>
      </div>
      <USelect v-model="sortBy" :options="sortOptions" size="sm" />
    </div>

    <!-- 操作栏 -->
    <AlbumActionBar
      :selected-count="selectedIds.length"
      :total-count="filteredImages.length"
      :select-all="selectAll"
      :show-add-to-gallery="true"
      :loading="loading"
      @toggle-select-all="toggleSelectAll"
      @copy-links="copySelectedLinks"
      @add-to-gallery="showAddToGallery = true"
      @refresh="loadUploads"
    />

    <!-- 图片网格 -->
    <AlbumImageGrid
      :images="filteredImages"
      :selected-ids="selectedIds"
      :loading="loading"
      :show-selection="true"
      @toggle-select="toggleSelect"
      @view-image="handleViewImage"
    />

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center">
      <UPagination v-model="currentPage" :total="total" :page-count="pageSize" @update:model-value="loadUploads" />
    </div>

    <!-- 添加到画集弹窗 -->
    <UModal v-model="showAddToGallery">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">添加到画集</h3>
        </template>
        <div v-if="galleriesLoading" class="flex justify-center py-4">
          <div class="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <div v-else-if="galleryOptions.length === 0" class="text-center py-4 text-gray-500">
          暂无画集，请先创建
        </div>
        <div v-else class="space-y-2 max-h-60 overflow-y-auto">
          <div
            v-for="g in galleryOptions"
            :key="g.id"
            class="flex items-center gap-3 p-2 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
            :class="{ 'bg-amber-50 dark:bg-amber-900/20': targetGalleryId === g.id }"
            @click="targetGalleryId = g.id"
          >
            <div class="w-4 h-4 rounded-full border-2 flex items-center justify-center"
              :class="targetGalleryId === g.id ? 'border-amber-500 bg-amber-500' : 'border-gray-300'">
              <UIcon v-if="targetGalleryId === g.id" name="heroicons:check" class="w-3 h-3 text-white" />
            </div>
            <span class="flex-1 truncate">{{ g.name }}</span>
            <span class="text-xs text-gray-400">{{ g.image_count }} 张</span>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="showAddToGallery = false">取消</UButton>
            <UButton color="primary" :loading="adding" :disabled="!targetGalleryId" @click="addToGallery">
              添加 ({{ selectedIds.length }})
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { Gallery, GalleryImage } from '~/composables/useGalleryApi'

const emit = defineEmits<{
  (e: 'navigate', view: string): void
  (e: 'view-image', images: GalleryImage[], index: number): void
}>()

const toast = useLightToast()
const { copy: clipboardCopy } = useClipboardCopy()
const store = useTokenStore()
const galleryApi = useGalleryApi()
const config = useRuntimeConfig()
const baseURL = config.public.apiBase

const loading = ref(false)
const images = ref<GalleryImage[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const searchQuery = ref('')
const sortBy = ref('newest')
const sortOptions = [
  { label: '最新上传', value: 'newest' },
  { label: '最早上传', value: 'oldest' },
  { label: '文件名', value: 'name' }
]

const selectedIds = ref<string[]>([])
const selectAll = computed(() => filteredImages.value.length > 0 && selectedIds.value.length === filteredImages.value.length)

// 前端过滤和排序
const filteredImages = computed(() => {
  let result = [...images.value]
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(img => img.original_filename?.toLowerCase().includes(q))
  }
  if (sortBy.value === 'newest') {
    result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } else if (sortBy.value === 'oldest') {
    result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  } else if (sortBy.value === 'name') {
    result.sort((a, b) => (a.original_filename || '').localeCompare(b.original_filename || ''))
  }
  return result
})

const toggleSelect = (id: string) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

const toggleSelectAll = () => {
  if (selectAll.value) selectedIds.value = []
  else selectedIds.value = filteredImages.value.map(img => img.encrypted_id)
}

const copySelectedLinks = () => {
  const links = filteredImages.value
    .filter(img => selectedIds.value.includes(img.encrypted_id))
    .map(img => img.image_url)
    .join('\n')
  clipboardCopy(links, `已复制 ${selectedIds.value.length} 个链接`)
}

const handleViewImage = (imgs: GalleryImage[], idx: number) => {
  emit('view-image', imgs, idx)
}

// 加载上传列表
const loadUploads = async () => {
  loading.value = true
  selectedIds.value = []
  try {
    const data = await store.getUploads(currentPage.value, pageSize)
    images.value = (data.uploads || []).map((item: any) => ({
      encrypted_id: item.encrypted_id || item.file_id,
      original_filename: item.original_filename,
      file_size: item.file_size || 0,
      created_at: item.created_at,
      cdn_cached: item.cdn_cached || false,
      mime_type: item.mime_type || '',
      image_url: item.image_url || `${baseURL}/image/${item.encrypted_id || item.file_id}`,
      added_at: item.created_at
    } as GalleryImage))
    total.value = data.total_uploads || 0
  } catch (e: any) {
    toast.error('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

// 添加到画集
const showAddToGallery = ref(false)
const galleryOptions = ref<Gallery[]>([])
const galleriesLoading = ref(false)
const targetGalleryId = ref<number | null>(null)
const adding = ref(false)

watch(showAddToGallery, async (v) => {
  if (!v) return
  galleriesLoading.value = true
  targetGalleryId.value = null
  try {
    const data = await galleryApi.getGalleries(1, 100)
    galleryOptions.value = data.items
  } catch { /* ignore */ } finally {
    galleriesLoading.value = false
  }
})

const addToGallery = async () => {
  if (!targetGalleryId.value || selectedIds.value.length === 0) return
  adding.value = true
  try {
    const result = await galleryApi.addImagesToGallery(targetGalleryId.value, selectedIds.value)
    if (result.added > 0) {
      toast.success(`已添加 ${result.added} 张图片${result.skipped ? `，${result.skipped} 张已存在` : ''}`)
    } else if (result.skipped > 0) {
      toast.info(`所选图片均已在画集中`)
    } else {
      toast.warning('未能添加任何图片')
    }
    showAddToGallery.value = false
    selectedIds.value = []
  } catch (e: any) {
    toast.error('添加失败', e.message)
  } finally {
    adding.value = false
  }
}

onMounted(loadUploads)
defineExpose({ refresh: loadUploads })
</script>
