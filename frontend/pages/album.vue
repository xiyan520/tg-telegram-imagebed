<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="text-center space-y-3">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        相册
      </h1>
      <p class="text-stone-600 dark:text-stone-400">
        Token Vault：本地保存多个 Token 并随时切换查看
      </p>
    </div>

    <!-- Token 切换器 -->
    <TokenVaultSwitcher />

    <!-- 无Token提示 -->
    <UCard v-if="!store.hasToken" class="shadow-lg">
      <div class="text-center py-8 space-y-4">
        <div class="w-16 h-16 mx-auto bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl flex items-center justify-center">
          <UIcon name="heroicons:photo" class="w-8 h-8 text-white" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            选择或添加一个 Token
          </h2>
          <p class="text-gray-600 dark:text-gray-400">
            点击上方"管理 Token"按钮添加或生成 Token 后查看相册内容
          </p>
        </div>
      </div>
    </UCard>

    <!-- 相册信息卡片 -->
    <UCard v-if="store.hasToken" class="shadow-lg">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-gradient-to-br from-emerald-600 to-teal-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <UIcon name="heroicons:photo" class="w-6 h-6 text-white" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <input
                v-model="albumName"
                type="text"
                class="text-xl font-bold bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400 w-full max-w-xs"
                placeholder="点击命名相册…"
                @blur="saveAlbumName"
                @keyup.enter="($event.target as HTMLInputElement)?.blur()"
              />
              <UButton
                v-if="savingName"
                size="xs"
                color="gray"
                variant="ghost"
                loading
              />
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              已上传 <span class="font-semibold text-emerald-600 dark:text-emerald-400">{{ store.uploadCount }}</span> 张图片
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <NuxtLink to="/">
            <UButton color="primary" variant="soft" size="sm">
              <template #leading>
                <UIcon name="heroicons:cloud-arrow-up" />
              </template>
              上传图片
            </UButton>
          </NuxtLink>
          <UButton
            icon="heroicons:arrow-path"
            color="gray"
            variant="outline"
            size="sm"
            :loading="loading"
            @click="loadImages"
          >
            刷新
          </UButton>
        </div>
      </div>
    </UCard>

    <!-- 搜索和筛选 -->
    <UCard v-if="store.hasToken && images.length > 0" class="shadow-lg">
      <div class="flex flex-wrap items-center gap-4">
        <div class="flex-1 min-w-[200px]">
          <UInput
            v-model="searchQuery"
            placeholder="搜索图片..."
            size="lg"
            @input="handleSearch"
          >
            <template #leading>
              <UIcon name="heroicons:magnifying-glass" class="w-5 h-5" />
            </template>
          </UInput>
        </div>
        <USelect
          v-model="sortBy"
          :options="sortOptions"
          size="lg"
        />
      </div>
    </UCard>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center items-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="store.hasToken && images.length === 0" class="text-center py-12">
      <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-400 mx-auto mb-4" />
      <p class="text-stone-600 dark:text-stone-400">暂无图片</p>
      <NuxtLink to="/" class="mt-4 inline-block">
        <UButton color="primary">
          <template #leading>
            <UIcon name="heroicons:cloud-arrow-up" />
          </template>
          上传第一张图片
        </UButton>
      </NuxtLink>
    </div>

    <!-- 图片网格 -->
    <div v-else-if="store.hasToken" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="image in filteredImages"
        :key="image.id"
        class="relative group aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-xl transition-all cursor-pointer"
        @click="viewImage(image)"
      >
        <img
          :src="image.url"
          :alt="image.filename"
          class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
          loading="lazy"
        />

        <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
          <div class="absolute bottom-0 left-0 right-0 p-4">
            <p class="text-white text-sm font-semibold truncate">
              {{ image.filename }}
            </p>
            <p class="text-white/80 text-xs">
              {{ image.uploadTime }}
            </p>
          </div>
        </div>

        <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <UButton
            icon="heroicons:clipboard-document"
            color="white"
            size="sm"
            @click.stop="copyImageUrl(image.url)"
          />
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center">
      <UPagination
        v-model="currentPage"
        :total="totalPages"
        @update:model-value="loadImages"
      />
    </div>

    <!-- 图片查看器模态框 -->
    <UModal v-model="viewerOpen" :ui="{ width: 'max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold truncate">{{ currentImage?.filename }}</h3>
            <div class="flex items-center gap-2">
              <UButton
                icon="heroicons:clipboard-document"
                color="gray"
                variant="ghost"
                @click="copyImageUrl(currentImage?.url)"
              />
              <UButton
                icon="heroicons:arrow-down-tray"
                color="gray"
                variant="ghost"
                @click="downloadImage(currentImage)"
              />
              <UButton
                icon="heroicons:x-mark"
                color="gray"
                variant="ghost"
                @click="viewerOpen = false"
              />
            </div>
          </div>
        </template>

        <div v-if="currentImage" class="space-y-4">
          <img
            :src="currentImage.url"
            :alt="currentImage.filename"
            class="w-full rounded-lg"
          />
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-gray-600 dark:text-gray-400">文件名:</span>
              <p class="font-semibold mt-1">{{ currentImage.filename }}</p>
            </div>
            <div>
              <span class="text-gray-600 dark:text-gray-400">大小:</span>
              <p class="font-semibold mt-1">{{ currentImage.size }}</p>
            </div>
            <div>
              <span class="text-gray-600 dark:text-gray-400">上传时间:</span>
              <p class="font-semibold mt-1">{{ currentImage.uploadTime }}</p>
            </div>
          </div>
          <div>
            <span class="text-gray-600 dark:text-gray-400">URL:</span>
            <code class="block mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs break-all">
              {{ currentImage.url }}
            </code>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between">
            <UButton
              icon="heroicons:chevron-left"
              color="gray"
              :disabled="currentIndex === 0"
              @click="previousImage"
            >
              上一张
            </UButton>
            <UButton
              icon="heroicons:chevron-right"
              color="gray"
              trailing
              :disabled="currentIndex === filteredImages.length - 1"
              @click="nextImage"
            >
              下一张
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const toast = useLightToast()
const store = useGuestTokenStore()

// 状态
const loading = ref(false)
const images = ref<any[]>([])
const searchQuery = ref('')
const sortBy = ref('newest')
const currentPage = ref(1)
const totalPages = ref(1)
const viewerOpen = ref(false)
const currentImage = ref<any>(null)
const currentIndex = ref(0)
const albumName = ref('')
const savingName = ref(false)

const sortOptions = [
  { label: '最新上传', value: 'newest' },
  { label: '最早上传', value: 'oldest' },
  { label: '文件名', value: 'name' }
]

// 过滤和排序后的图片
const filteredImages = computed(() => {
  let result = [...images.value]

  // 搜索过滤
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(img =>
      img.filename?.toLowerCase().includes(query)
    )
  }

  // 排序
  if (sortBy.value === 'oldest') {
    result.reverse()
  } else if (sortBy.value === 'name') {
    result.sort((a, b) => (a.filename || '').localeCompare(b.filename || ''))
  }

  return result
})

// 加载图片
const loadImages = async () => {
  if (!store.hasToken) return

  loading.value = true
  try {
    const data = await store.getUploads(currentPage.value, 50)

    images.value = (data.uploads || []).map((item: any) => ({
      id: item.encrypted_id || item.file_id,
      url: item.image_url,
      filename: item.original_filename,
      uploadTime: formatDate(item.created_at),
      size: formatFileSize(item.file_size || 0)
    }))

    totalPages.value = Math.max(1, Math.ceil((data.total_uploads || 0) / 50))
  } catch (error: any) {
    toast.error('加载失败', error.message)
  } finally {
    loading.value = false
  }
}

// 保存相册名称
const saveAlbumName = async () => {
  if (!store.hasToken || !store.activeVaultId) return
  const name = albumName.value.trim()

  // 更新本地vault
  store.updateAlbumName(store.activeVaultId, name)

  // 尝试同步到服务器（如果API支持）
  savingName.value = true
  try {
    await store.updateDescription(name)
  } catch {
    // 服务器同步失败不影响本地保存
  } finally {
    savingName.value = false
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return '--'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

// 搜索处理
const handleSearch = useDebounceFn(() => {
  // 搜索是前端过滤，不需要重新加载
}, 300)

// 查看图片
const viewImage = (image: any) => {
  currentImage.value = image
  currentIndex.value = filteredImages.value.findIndex(img => img.id === image.id)
  viewerOpen.value = true
}

// 上一张
const previousImage = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    currentImage.value = filteredImages.value[currentIndex.value]
  }
}

// 下一张
const nextImage = () => {
  if (currentIndex.value < filteredImages.value.length - 1) {
    currentIndex.value++
    currentImage.value = filteredImages.value[currentIndex.value]
  }
}

// 复制图片 URL
const copyImageUrl = async (url: string) => {
  try {
    await navigator.clipboard.writeText(url)
    toast.success('链接已复制')
  } catch {
    toast.error('复制失败')
  }
}

// 下载图片
const downloadImage = (image: any) => {
  const link = document.createElement('a')
  link.href = image.url
  link.download = image.filename
  link.click()
}

// 监听token变化，重新加载图片
watch(() => store.token, async (newToken) => {
  if (newToken) {
    currentPage.value = 1
    albumName.value = store.activeVaultItem?.albumName || ''
    await loadImages()
  } else {
    images.value = []
  }
})

// 页面加载
onMounted(async () => {
  await store.restoreToken()
  if (store.hasToken) {
    albumName.value = store.activeVaultItem?.albumName || ''
    await loadImages()
  }
})
</script>
