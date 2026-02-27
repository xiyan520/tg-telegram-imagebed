<template>
  <UModal
    v-model="open"
    :ui="{
      width: 'sm:max-w-2xl',
      height: 'max-h-[88vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-stone-900/35 backdrop-blur-[1px]' }
    }"
  >
    <UCard class="overflow-hidden flex flex-col max-h-[84vh]">
      <template #header>
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-2.5 min-w-0">
            <div class="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center shadow-sm shadow-amber-500/30 flex-shrink-0">
              <UIcon name="heroicons:clock" class="w-4 h-4 text-white" />
            </div>
            <div class="min-w-0">
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">上传历史</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                共 {{ totalUploads }} 条
                <template v-if="history.length > 0"> · 显示 {{ filteredHistory.length }} 条</template>
              </p>
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <UButton
              icon="heroicons:arrow-path"
              color="gray"
              variant="soft"
              size="xs"
              :loading="loading || loadingMore"
              title="刷新"
              @click="refresh"
            />
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="soft"
              size="xs"
              @click="open = false"
            />
          </div>
        </div>
      </template>

      <div class="overflow-y-auto flex-1 -mx-1 px-1">
        <div class="sticky top-0 z-10 pb-2 bg-white/90 dark:bg-stone-900/90 supports-[backdrop-filter]:bg-white/70 supports-[backdrop-filter]:dark:bg-stone-900/70 backdrop-blur">
          <div class="rounded-xl border border-stone-200/80 dark:border-stone-700/70 bg-stone-50/80 dark:bg-stone-800/40 p-2.5">
            <div class="flex flex-col sm:flex-row gap-2">
              <UInput
                v-model="searchQuery"
                size="sm"
                class="flex-1"
                placeholder="搜索文件名或格式..."
                :ui="{ rounded: 'rounded-xl' }"
              >
                <template #leading>
                  <UIcon name="heroicons:magnifying-glass" class="w-4 h-4 text-stone-400" />
                </template>
              </UInput>
              <USelect
                v-model="sortBy"
                size="sm"
                class="sm:w-36"
                :options="sortOptions"
                :ui="{ rounded: 'rounded-xl' }"
              />
            </div>
            <p class="text-[11px] text-stone-500 dark:text-stone-400 mt-1.5">
              <span v-if="tokenStore.tokenInfo">剩余可上传 {{ tokenStore.remainingUploads }} 次</span>
              <span v-else>支持按名称、格式、大小快速筛选</span>
            </p>
          </div>
        </div>

        <!-- 加载中（首次） -->
        <div v-if="loading && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          <p class="text-sm text-stone-500">加载中...</p>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="error && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
            <UIcon name="heroicons:exclamation-triangle" class="w-6 h-6 text-red-500" />
          </div>
          <p class="text-sm text-stone-600 dark:text-stone-400">{{ error }}</p>
          <UButton size="sm" color="primary" variant="soft" @click="refresh">重试</UButton>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!loading && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-14 h-14 bg-stone-100 dark:bg-stone-800 rounded-2xl flex items-center justify-center">
            <UIcon name="heroicons:photo" class="w-7 h-7 text-stone-400" />
          </div>
          <p class="text-sm text-gray-500 dark:text-gray-400">暂无上传记录</p>
        </div>

        <div v-else-if="!loading && filteredHistory.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-14 h-14 bg-stone-100 dark:bg-stone-800 rounded-2xl flex items-center justify-center">
            <UIcon name="heroicons:magnifying-glass" class="w-7 h-7 text-stone-400" />
          </div>
          <p class="text-sm text-stone-500 dark:text-stone-400">没有匹配的上传记录</p>
          <UButton size="sm" color="gray" variant="soft" @click="clearFilters">清空筛选</UButton>
        </div>

        <!-- 历史列表 -->
        <div v-else class="space-y-2.5 pb-1">
          <div
            v-for="item in filteredHistory"
            :key="item.encrypted_id || item.image_url"
            class="group flex items-center gap-3 p-2.5 rounded-xl border border-transparent hover:border-stone-200/80 dark:hover:border-stone-700/70 hover:bg-stone-50 dark:hover:bg-stone-800/40 transition-all"
          >
            <!-- 缩略图（可点击预览） -->
            <div
              class="relative w-14 h-14 sm:w-16 sm:h-16 rounded-lg overflow-hidden border border-stone-200 dark:border-stone-700 flex-shrink-0 cursor-pointer"
              @click="previewItem(item)"
            >
              <img
                :src="item.image_url"
                :alt="item.original_filename"
                class="w-full h-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
              />
              <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                <UIcon name="heroicons:magnifying-glass-plus" class="w-4 h-4 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>

            <!-- 信息 -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-stone-900 dark:text-white truncate">
                {{ item.original_filename }}
              </p>
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                {{ formatTime(item.created_at) }}
              </p>
              <div class="flex items-center gap-1.5 mt-1">
                <UBadge color="gray" variant="subtle" size="xs">{{ formatFileSize(item.file_size) }}</UBadge>
                <UBadge v-if="item.cdn_cached" color="green" variant="subtle" size="xs">CDN</UBadge>
                <span v-if="item.mime_type" class="text-[11px] text-stone-400 dark:text-stone-500 uppercase tracking-wide">
                  {{ formatMime(item.mime_type) }}
                </span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-0.5 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity flex-shrink-0">
              <UButton
                icon="heroicons:clipboard-document"
                color="gray"
                variant="ghost"
                size="xs"
                title="复制 URL"
                @click="clipboardCopy(item.image_url, '已复制 URL')"
              />
              <UDropdown
                :items="getCopyMenuItems(item)"
                :popper="{ placement: 'bottom-end' }"
                :ui="{ width: 'w-40' }"
              >
                <UButton
                  icon="heroicons:link"
                  color="gray"
                  variant="ghost"
                  size="xs"
                  title="复制链接"
                />
              </UDropdown>
              <UButton
                icon="heroicons:arrow-top-right-on-square"
                color="gray"
                variant="ghost"
                size="xs"
                title="新窗口打开"
                @click="openInNewTab(item.image_url)"
              />
            </div>
          </div>

          <!-- 加载更多 -->
          <div v-if="hasMore" class="pt-1 pb-1">
            <UButton
              block
              color="gray"
              variant="soft"
              size="sm"
              :loading="loadingMore"
              @click="loadMore"
            >
              加载更多
            </UButton>
          </div>
        </div>
      </div>
    </UCard>
  </UModal>

  <!-- 图片预览弹窗 -->
  <HomeImagePreview v-model:open="previewOpen" :image="previewImage" />
</template>

<script setup lang="ts">
import type { TokenUploadItem } from '~/types/api'

const open = defineModel<boolean>('open', { default: false })

const tokenStore = useTokenStore()
const { copy: clipboardCopy } = useClipboardCopy()

const history = ref<TokenUploadItem[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const page = ref(1)
const hasMore = ref(false)
const totalUploads = ref(0)
const previewOpen = ref(false)
const previewImage = ref<{ url: string; filename: string } | null>(null)
const searchQuery = ref('')
const sortBy = ref<'newest' | 'oldest' | 'name' | 'size'>('newest')

const sortOptions = [
  { label: '最新上传', value: 'newest' },
  { label: '最早上传', value: 'oldest' },
  { label: '文件名', value: 'name' },
  { label: '文件大小', value: 'size' },
]

const PAGE_SIZE = 20

const filteredHistory = computed(() => {
  let list = [...history.value]
  const query = searchQuery.value.trim().toLowerCase()

  if (query) {
    list = list.filter(item => {
      const filename = (item.original_filename || '').toLowerCase()
      const mime = (item.mime_type || '').toLowerCase()
      return filename.includes(query) || mime.includes(query)
    })
  }

  if (sortBy.value === 'newest') {
    list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } else if (sortBy.value === 'oldest') {
    list.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  } else if (sortBy.value === 'name') {
    list.sort((a, b) => (a.original_filename || '').localeCompare(b.original_filename || '', 'zh-CN'))
  } else {
    list.sort((a, b) => (b.file_size || 0) - (a.file_size || 0))
  }

  return list
})

const clearFilters = () => {
  searchQuery.value = ''
  sortBy.value = 'newest'
}

const formatLink = (item: TokenUploadItem, format: string) => {
  const url = item.image_url
  const name = item.original_filename || 'image'
  switch (format) {
    case 'markdown': return `![${name}](${url})`
    case 'html': return `<img src="${url}" alt="${name}" />`
    case 'bbcode': return `[img]${url}[/img]`
    default: return url
  }
}

const getCopyMenuItems = (item: TokenUploadItem) => [[
  { label: 'URL', icon: 'i-heroicons-link', click: () => clipboardCopy(formatLink(item, 'url'), '已复制 URL') },
  { label: 'Markdown', icon: 'i-heroicons-hashtag', click: () => clipboardCopy(formatLink(item, 'markdown'), '已复制 Markdown') },
  { label: 'HTML', icon: 'i-heroicons-code-bracket', click: () => clipboardCopy(formatLink(item, 'html'), '已复制 HTML') },
  { label: 'BBCode', icon: 'i-heroicons-chat-bubble-left', click: () => clipboardCopy(formatLink(item, 'bbcode'), '已复制 BBCode') },
]]

const openInNewTab = (url: string) => {
  window.open(url, '_blank')
}

const previewItem = (item: TokenUploadItem) => {
  previewImage.value = {
    url: item.image_url,
    filename: item.original_filename,
  }
  previewOpen.value = true
}

const formatFileSize = (size: number) => {
  if (!Number.isFinite(size) || size <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex++
  }
  const fixed = value >= 100 || unitIndex === 0 ? 0 : 1
  return `${value.toFixed(fixed)} ${units[unitIndex]}`
}

const formatMime = (mime: string) => {
  if (!mime) return ''
  const [, subtype] = mime.split('/')
  return subtype || mime
}

const formatTime = (dateStr: string) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMs / 3600000)
    const diffDay = Math.floor(diffMs / 86400000)

    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin} 分钟前`
    if (diffHour < 24) return `${diffHour} 小时前`
    if (diffDay < 7) return `${diffDay} 天前`

    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

const loadHistory = async (isLoadMore = false) => {
  if (!tokenStore.hasToken) return

  if (isLoadMore) {
    loadingMore.value = true
  } else {
    loading.value = true
    error.value = ''
  }

  try {
    const data = await tokenStore.getUploads(page.value, PAGE_SIZE)
    if (isLoadMore) {
      history.value.push(...(data.uploads || []))
    } else {
      history.value = data.uploads || []
    }
    totalUploads.value = data.total_uploads || 0
    hasMore.value = data.has_more || false
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  page.value++
  loadHistory(true)
}

const refresh = () => {
  page.value = 1
  history.value = []
  error.value = ''
  loadHistory()
}

// 打开时自动加载
watch(open, (val) => {
  if (val) {
    clearFilters()
    page.value = 1
    loadHistory()
  }
})
</script>
