<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">图片管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
          共 {{ totalCount }} 张图片
        </p>
      </div>
    </div>

    <!-- 操作栏 -->
    <UCard>
      <div class="flex flex-col md:flex-row md:items-center gap-4">
        <!-- 左侧：批量操作 -->
        <div class="flex items-center gap-3">
          <UCheckbox v-model="selectAll" @change="handleSelectAll">
            <template #label>
              <span class="text-sm font-medium">全选</span>
            </template>
          </UCheckbox>
          <UButton
            color="red"
            variant="soft"
            size="sm"
            :disabled="selectedImages.length === 0"
            @click="handleDeleteSelected"
          >
            <template #leading>
              <UIcon name="heroicons:trash" />
            </template>
            删除选中 ({{ selectedImages.length }})
          </UButton>
          <UButton
            color="yellow"
            variant="soft"
            size="sm"
            @click="handleClearCache"
          >
            <template #leading>
              <UIcon name="heroicons:arrow-path" />
            </template>
            清理缓存
          </UButton>
        </div>

        <!-- 右侧：筛选和搜索 -->
        <div class="flex items-center gap-2 md:ml-auto">
          <!-- 视图切换 -->
          <div class="flex items-center border border-stone-200 dark:border-neutral-700 rounded-lg overflow-hidden">
            <button
              class="p-1.5 transition-colors"
              :class="viewMode === 'grid' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' : 'text-stone-400 hover:text-stone-600'"
              title="网格视图"
              @click="viewMode = 'grid'"
            >
              <UIcon name="heroicons:squares-2x2" class="w-4 h-4" />
            </button>
            <button
              class="p-1.5 transition-colors"
              :class="viewMode === 'list' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' : 'text-stone-400 hover:text-stone-600'"
              title="列表视图"
              @click="viewMode = 'list'"
            >
              <UIcon name="heroicons:list-bullet" class="w-4 h-4" />
            </button>
            <button
              class="p-1.5 transition-colors"
              :class="viewMode === 'masonry' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' : 'text-stone-400 hover:text-stone-600'"
              title="瀑布流视图"
              @click="viewMode = 'masonry'"
            >
              <UIcon name="heroicons:view-columns" class="w-4 h-4" />
            </button>
          </div>
          <USelect
            v-model="filterType"
            :options="filterOptions"
            size="sm"
            @change="handleFilterChange"
          />
          <USelect
            v-model="pageSize"
            :options="pageSizeOptions"
            size="sm"
            @change="handlePageSizeChange"
          />
          <UInput
            v-model="searchQuery"
            placeholder="搜索文件名..."
            size="sm"
            @input="handleSearch"
          >
            <template #leading>
              <UIcon name="heroicons:magnifying-glass" class="w-4 h-4" />
            </template>
          </UInput>
          <UButton
            icon="heroicons:arrow-path"
            color="gray"
            variant="ghost"
            size="sm"
            :loading="loading"
            @click="loadImages"
          />
        </div>
      </div>
    </UCard>

    <!-- 图片网格 -->
    <UCard>
      <div v-if="loading" class="flex flex-col justify-center items-center py-16">
        <div class="w-16 h-16 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-stone-600 dark:text-stone-400">加载中...</p>
      </div>

      <div v-else-if="images.length === 0" class="text-center py-16">
        <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-400" />
        </div>
        <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无图片</p>
        <p class="text-sm text-stone-600 dark:text-stone-400">还没有上传任何图片</p>
      </div>

      <!-- 列表视图 -->
      <AdminImageListView
        v-else-if="viewMode === 'list'"
        :images="images"
        :selected-images="selectedImages"
        @toggle-select="toggleImageSelection"
        @view-detail="viewImageDetail"
        @copy-url="copyImageUrl"
        @delete="deleteImage"
      />

      <!-- 瀑布流视图 -->
      <MasonryGrid
        v-else-if="viewMode === 'masonry'"
        :items="images"
        :column-width="240"
        :gap="12"
      >
        <template #default="{ item: image }">
          <div
            class="relative group rounded-xl overflow-hidden border-2 transition-all hover:shadow-lg"
            :class="[
              selectedImages.includes(image.id)
                ? 'border-amber-500 ring-2 ring-amber-500 ring-offset-2'
                : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
            ]"
          >
            <img
              :src="image.url"
              :alt="image.filename"
              loading="lazy"
              decoding="async"
              class="w-full h-auto object-cover"
              @error="handleImageError($event, image)"
            />
            <!-- 选择框 -->
            <div class="absolute top-2 left-2 z-10">
              <div class="bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
                <UCheckbox :model-value="selectedImages.includes(image.id)" @change="toggleImageSelection(image.id)" />
              </div>
            </div>
            <!-- 操作悬浮层 -->
            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <UButton icon="heroicons:eye" color="white" size="sm" @click="viewImageDetail(image)" />
              <UButton icon="heroicons:clipboard-document" color="white" size="sm" @click="copyImageUrl(image.url)" />
              <UButton icon="heroicons:trash" color="red" size="sm" @click="deleteImage(image.id)" />
            </div>
            <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
              <p class="text-white text-xs truncate">{{ image.filename }}</p>
            </div>
          </div>
        </template>
      </MasonryGrid>

      <!-- 网格视图 -->
      <div v-else class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div
          v-for="image in images"
          :key="image.id"
          class="relative group aspect-square rounded-xl overflow-hidden border-2 transition-all hover:shadow-lg"
          :class="[
            selectedImages.includes(image.id)
              ? 'border-amber-500 ring-2 ring-amber-500 ring-offset-2'
              : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
          ]"
        >
          <img
            :src="image.url"
            :alt="image.filename"
            loading="lazy"
            decoding="async"
            class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
            @error="handleImageError($event, image)"
          />

          <!-- 选择框 -->
          <div class="absolute top-2 left-2 z-10">
            <div class="bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
              <UCheckbox
                :model-value="selectedImages.includes(image.id)"
                @change="toggleImageSelection(image.id)"
              />
            </div>
          </div>

          <!-- 缓存状态 -->
          <div v-if="image.cached" class="absolute top-2 right-2 z-10">
            <UBadge color="green" variant="solid" size="xs" class="shadow-lg">
              <template #leading>
                <UIcon name="heroicons:check-circle" class="w-3 h-3" />
              </template>
              已缓存
            </UBadge>
          </div>

          <!-- 访问次数 -->
          <div class="absolute bottom-2 right-2 z-10">
            <div class="bg-black/50 backdrop-blur-sm rounded-md px-1.5 py-0.5 flex items-center gap-1">
              <UIcon name="heroicons:eye" class="w-3 h-3 text-stone-200" />
              <span class="text-xs font-medium text-white">{{ image.access_count || 0 }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <UButton
              icon="heroicons:eye"
              color="white"
              size="sm"
              @click="viewImageDetail(image)"
            />
            <UButton
              icon="heroicons:clipboard-document"
              color="white"
              size="sm"
              @click="copyImageUrl(image.url)"
            />
            <UButton
              icon="heroicons:trash"
              color="red"
              size="sm"
              @click="deleteImage(image.id)"
            />
          </div>

          <!-- 文件名提示 -->
          <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <p class="text-white text-xs truncate">{{ image.filename }}</p>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <template #footer>
        <div class="flex justify-center pt-4">
          <UPagination
            v-model="currentPage"
            :total="totalCount"
            :page-count="Number(pageSize)"
            @update:model-value="loadImages"
          />
        </div>
      </template>
    </UCard>

    <!-- 图片详情模态框 -->
    <UModal v-model="detailModalOpen" :ui="{ width: 'sm:max-w-4xl', height: 'max-h-[90vh]' }">
      <UCard :ui="{ body: { base: 'overflow-y-auto', padding: 'p-4 sm:p-5' }, ring: '', divide: 'divide-y divide-gray-100 dark:divide-gray-800' }" class="flex flex-col max-h-[85vh]">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">图片详情</h3>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              @click="detailModalOpen = false"
            />
          </div>
        </template>

        <div v-if="selectedImage" class="flex flex-col md:flex-row gap-5">
          <!-- 左侧：图片预览 -->
          <div class="md:w-1/2 flex-shrink-0">
            <img
              :src="selectedImage.url"
              :alt="selectedImage.filename"
              loading="lazy"
              decoding="async"
              class="w-full rounded-lg object-contain max-h-[60vh]"
              @error="handleImageError($event, selectedImage)"
            />
          </div>
          <!-- 右侧：信息面板 -->
          <div class="md:w-1/2 space-y-3 text-sm">
            <div>
              <span class="text-stone-500 dark:text-stone-400 text-xs">文件名</span>
              <p class="font-medium break-all">{{ selectedImage.filename }}</p>
            </div>
            <div>
              <span class="text-stone-500 dark:text-stone-400 text-xs">大小</span>
              <p class="font-medium">{{ formatSizeMB(selectedImage.size) }}</p>
            </div>
            <div>
              <span class="text-stone-500 dark:text-stone-400 text-xs">上传时间</span>
              <p class="font-medium">{{ selectedImage.uploadTime }}</p>
            </div>
            <div>
              <span class="text-stone-500 dark:text-stone-400 text-xs">缓存状态</span>
              <div class="mt-0.5">
                <UBadge :color="selectedImage.cached ? 'green' : 'gray'" size="xs">
                  {{ selectedImage.cached ? '已缓存' : '未缓存' }}
                </UBadge>
              </div>
            </div>

            <!-- 访问统计 -->
            <div class="pt-3 mt-3 border-t border-stone-100 dark:border-stone-800">
              <h4 class="text-xs font-medium text-stone-500 dark:text-stone-400 mb-2">访问统计</h4>
              <div class="grid grid-cols-3 gap-2">
                <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-2 text-center border border-amber-100 dark:border-amber-800/30">
                  <div class="text-[10px] text-stone-500 dark:text-stone-400">总访问</div>
                  <div class="text-base font-bold text-amber-600 dark:text-amber-500">
                    {{ selectedImage.access_count || 0 }}
                  </div>
                </div>
                <div class="bg-stone-50 dark:bg-stone-800 rounded-lg p-2 text-center border border-stone-100 dark:border-stone-700">
                  <div class="text-[10px] text-stone-500 dark:text-stone-400">CDN 回源</div>
                  <div class="text-base font-bold text-stone-700 dark:text-stone-300">
                    {{ selectedImage.cdn_hit_count || 0 }}
                  </div>
                </div>
                <div class="bg-stone-50 dark:bg-stone-800 rounded-lg p-2 text-center border border-stone-100 dark:border-stone-700">
                  <div class="text-[10px] text-stone-500 dark:text-stone-400">直连访问</div>
                  <div class="text-base font-bold text-stone-700 dark:text-stone-300">
                    {{ selectedImage.direct_hit_count || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <div>
              <span class="text-stone-500 dark:text-stone-400 text-xs">URL</span>
              <code class="block mt-1 p-2 bg-stone-100 dark:bg-neutral-800 rounded text-xs break-all">
                {{ selectedImage.url }}
              </code>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="detailModalOpen = false">
              关闭
            </UButton>
            <UButton color="primary" @click="copyImageUrl(selectedImage?.url)">
              复制链接
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 删除确认模态框 -->
    <UModal v-model="deleteModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
        </template>

        <p class="text-stone-700 dark:text-stone-300">
          {{ deleteMessage }}
        </p>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">
              取消
            </UButton>
            <UButton color="red" :loading="deleting" @click="confirmDelete">
              确认删除
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const notification = useNotification()
const { getImages, deleteImages, clearCache } = useImageApi()

// 视图模式（持久化到 localStorage）
const viewMode = ref<'grid' | 'list' | 'masonry'>('grid')
if (import.meta.client) {
  const saved = localStorage.getItem('admin_images_view_mode')
  if (saved === 'list' || saved === 'grid' || saved === 'masonry') viewMode.value = saved
}
watch(viewMode, (v) => {
  if (import.meta.client) localStorage.setItem('admin_images_view_mode', v)
})

// 状态
const loading = ref(false)
const deleting = ref(false)
const images = ref<any[]>([])
const selectedImages = ref<string[]>([])
const selectAll = ref(false)
const filterType = ref('all')
const searchQuery = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const totalCount = ref(0)
const pageSize = ref(50)
const detailModalOpen = ref(false)
const deleteModalOpen = ref(false)
const selectedImage = ref<any>(null)
const deleteMessage = ref('')

const filterOptions = [
  { label: '全部图片', value: 'all' },
  { label: '已缓存', value: 'cached' },
  { label: '未缓存', value: 'uncached' },
  { label: '群组上传', value: 'group' }
]

const pageSizeOptions = [
  { label: '20 / 页', value: 20 },
  { label: '50 / 页', value: 50 },
  { label: '100 / 页', value: 100 },
  { label: '200 / 页', value: 200 }
]

// 加载图片列表
const loadImages = async () => {
  loading.value = true
  try {
    const data = await getImages({
      page: currentPage.value,
      limit: Number(pageSize.value),
      filter: filterType.value,
      search: searchQuery.value
    })
    images.value = data.images
    totalPages.value = data.totalPages
    totalCount.value = data.total ?? data.images.length
    // 重置选择状态，避免保留旧页的勾选
    selectedImages.value = []
    selectAll.value = false
  } catch (error) {
    notification.error('错误', '加载图片列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = useDebounceFn(() => {
  currentPage.value = 1
  loadImages()
}, 500)

// 筛选变化处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadImages()
}

// 每页数量变化处理
const handlePageSizeChange = () => {
  currentPage.value = 1
  loadImages()
}

// 全选处理
const handleSelectAll = () => {
  if (selectAll.value) {
    selectedImages.value = images.value.map(img => img.id)
  } else {
    selectedImages.value = []
  }
}

// 切换图片选择
const toggleImageSelection = (id: string) => {
  const index = selectedImages.value.indexOf(id)
  if (index > -1) {
    selectedImages.value.splice(index, 1)
  } else {
    selectedImages.value.push(id)
  }
}

// 查看图片详情
const viewImageDetail = (image: any) => {
  selectedImage.value = image
  detailModalOpen.value = true
}

// 复制图片 URL
const copyImageUrl = async (url: string) => {
  if (!url) return
  await navigator.clipboard.writeText(url)
  notification.success('已复制', 'URL 已复制到剪贴板')
}

// 删除单个图片
const deleteImage = (id: string) => {
  selectedImages.value = [id]
  deleteMessage.value = '确定要删除这张图片吗？此操作不可恢复。'
  deleteModalOpen.value = true
}

// 删除选中图片
const handleDeleteSelected = () => {
  deleteMessage.value = `确定要删除选中的 ${selectedImages.value.length} 张图片吗？此操作不可恢复。`
  deleteModalOpen.value = true
}

// 确认删除
const confirmDelete = async () => {
  deleting.value = true
  try {
    await deleteImages(selectedImages.value)
    notification.success('删除成功', `已删除 ${selectedImages.value.length} 张图片`)
    selectedImages.value = []
    selectAll.value = false
    deleteModalOpen.value = false
    await loadImages()
  } catch (error) {
    notification.error('删除失败', '删除图片时出错')
  } finally {
    deleting.value = false
  }
}

// 清理缓存
const handleClearCache = async () => {
  try {
    await clearCache()
    notification.success('成功', '缓存已清理')
  } catch (error) {
    notification.error('错误', '清理缓存失败')
  }
}

// 文件大小格式化为 MB
const formatSizeMB = (size: any): string => {
  if (!size) return '--'
  // 如果是字符串（如 "1.2 MB"），尝试提取数值
  if (typeof size === 'string') {
    const num = parseFloat(size)
    if (isNaN(num)) return size
    // 已经包含单位的直接返回
    if (/[a-zA-Z]/.test(size)) return size
    // 纯数字字符串当作字节处理
    return (num / (1024 * 1024)).toFixed(2) + ' MB'
  }
  if (typeof size === 'number') {
    return (size / (1024 * 1024)).toFixed(2) + ' MB'
  }
  return String(size)
}

// 处理图片加载错误
const handleImageError = (event: Event, image: any) => {
  const imgElement = event.target as HTMLImageElement
  console.error('图片加载失败:', image.url)

  // 尝试使用 CDN URL（如果存在）
  if (image.cdn_url && imgElement.src !== image.cdn_url) {
    console.log('尝试使用 CDN URL:', image.cdn_url)
    imgElement.src = image.cdn_url
  } else {
    // 设置占位图
    imgElement.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23ddd" width="400" height="400"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="24"%3E加载失败%3C/text%3E%3C/svg%3E'
  }
}

// 页面加载
onMounted(() => {
  loadImages()
})
</script>
