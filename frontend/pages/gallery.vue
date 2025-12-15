<template>
  <div class="space-y-6">
    <div class="text-center space-y-4">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        图片画廊
      </h1>
      <p class="text-stone-600 dark:text-stone-400">
        浏览所有已上传的图片
      </p>
    </div>

    <!-- Token登录提示卡片 -->
    <div v-if="!guestStore.hasToken" class="flex justify-center">
      <UCard class="shadow-2xl w-full max-w-2xl">
        <div class="text-center space-y-6 py-8">
          <div class="flex justify-center">
            <div class="w-20 h-20 bg-gradient-to-br from-amber-500 to-orange-500 rounded-3xl flex items-center justify-center">
              <UIcon name="heroicons:key" class="w-10 h-10 text-white" />
            </div>
          </div>
          <div>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              需要Token才能查看图片
            </h2>
            <p class="text-gray-600 dark:text-gray-400">
              请前往Token模式页面生成或输入您的Token
            </p>
          </div>

          <!-- 跳转到Token模式 -->
          <div class="max-w-md mx-auto">
            <NuxtLink to="/guest">
              <UButton
                size="xl"
                color="primary"
                block
              >
                <template #leading>
                  <UIcon name="heroicons:arrow-right" />
                </template>
                前往Token模式
              </UButton>
            </NuxtLink>
          </div>
        </div>
      </UCard>
    </div>

    <!-- 搜索和筛选 -->
    <UCard v-if="guestStore.hasToken" class="shadow-lg">
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
          @change="loadImages"
        />
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          size="lg"
          @click="loadImages"
        >
          刷新
        </UButton>
      </div>
    </UCard>

    <!-- 图片网格 -->
    <div v-if="loading" class="flex justify-center items-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <div v-else-if="images.length === 0" class="text-center py-12">
      <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-400 mx-auto mb-4" />
      <p class="text-stone-600 dark:text-stone-400">暂无图片</p>
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="image in images"
        :key="image.id"
        class="relative group aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-xl transition-all cursor-pointer"
        @click="viewImage(image)"
        @mouseenter="handleImageHover(image.id, true)"
        @mouseleave="handleImageHover(image.id, false)"
      >
        <img
          :src="image.url"
          :alt="image.filename"
          class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
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

        <div
          class="absolute top-2 right-2 transition-opacity"
          :class="hoveredImageId === image.id || recentlyCopiedId === image.id ? 'opacity-100' : 'opacity-0'"
        >
          <UButton
            :icon="recentlyCopiedId === image.id ? 'heroicons:check' : 'heroicons:clipboard-document'"
            :color="recentlyCopiedId === image.id ? 'green' : 'white'"
            size="sm"
            @click.stop="copyImageUrl(image.url, image.id)"
          >
            {{ recentlyCopiedId === image.id ? '已复制' : '' }}
          </UButton>
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
            <h3 class="text-lg font-semibold">{{ currentImage?.filename }}</h3>
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
            <div>
              <span class="text-gray-600 dark:text-gray-400">分辨率:</span>
              <p class="font-semibold mt-1">{{ currentImage.resolution || '--' }}</p>
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
              :disabled="currentIndex === images.length - 1"
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
const toast = useLightToast()  // 使用新的轻量级Toast框架
const guestStore = useGuestTokenStore()

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
const hoveredImageId = ref<string | null>(null)
const recentlyCopiedId = ref<string | null>(null)

const sortOptions = [
  { label: '最新上传', value: 'newest' },
  { label: '最早上传', value: 'oldest' },
  { label: '文件名', value: 'name' },
  { label: '文件大小', value: 'size' }
]

// 退出登录
const handleLogout = () => {
  if (confirm('确定要退出吗？')) {
    guestStore.clearToken()
    images.value = []
    toast.success('已退出')
  }
}

// 加载图片
const loadImages = async () => {
  if (!guestStore.hasToken) {
    return
  }

  loading.value = true
  try {
    // 使用Token API获取图片列表
    const data = await guestStore.getUploads(currentPage.value, 50)

    // 转换数据格式以匹配画廊显示
    images.value = data.uploads.map((item: any) => ({
      id: item.file_id,
      url: item.image_url,
      filename: item.original_filename,
      uploadTime: formatDate(item.created_at),
      size: formatFileSize(item.file_size || 0)
    }))

    // 计算总页数
    totalPages.value = Math.ceil(data.total_uploads / 50)
  } catch (error: any) {
    toast.error('加载失败', error.message)
  } finally {
    loading.value = false
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
  currentPage.value = 1
  loadImages()
}, 500)

// 查看图片
const viewImage = (image: any) => {
  currentImage.value = image
  currentIndex.value = images.value.findIndex(img => img.id === image.id)
  viewerOpen.value = true
}

// 上一张
const previousImage = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    currentImage.value = images.value[currentIndex.value]
  }
}

// 下一张
const nextImage = () => {
  if (currentIndex.value < images.value.length - 1) {
    currentIndex.value++
    currentImage.value = images.value[currentIndex.value]
  }
}

// 处理图片hover状态
const handleImageHover = (imageId: string, isHovering: boolean) => {
  if (isHovering) {
    hoveredImageId.value = imageId
  } else {
    // 如果不是最近复制的图片，才清除hover状态
    if (recentlyCopiedId.value !== imageId) {
      hoveredImageId.value = null
    }
  }
}

// 通用复制函数（带错误处理）
const copyToClipboard = async (text: string, successMessage: string = '已复制') => {
  try {
    // 优先使用现代剪贴板API
    await navigator.clipboard.writeText(text)
    toast.success(successMessage)
    return true
  } catch (err) {
    // 回退方案：使用传统方法
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)

      if (successful) {
        toast.success(successMessage)
        return true
      } else {
        throw new Error('复制失败')
      }
    } catch (fallbackErr) {
      toast.error('复制失败', '请手动复制内容')
      console.error('复制失败:', fallbackErr)
      return false
    }
  }
}

// 复制图片 URL
const copyImageUrl = async (url: string, imageId?: string) => {
  const success = await copyToClipboard(url, '已复制')

  // 只有复制成功时才标记为最近复制
  if (success && imageId) {
    recentlyCopiedId.value = imageId
    setTimeout(() => {
      if (recentlyCopiedId.value === imageId) {
        recentlyCopiedId.value = null
      }
    }, 3000)
  }
}

// 下载图片
const downloadImage = (image: any) => {
  const link = document.createElement('a')
  link.href = image.url
  link.download = image.filename
  link.click()
}

// 页面加载
onMounted(async () => {
  // 尝试恢复Token
  await guestStore.restoreToken()

  // 如果有Token则加载图片
  if (guestStore.hasToken) {
    await loadImages()
  }
})
</script>
