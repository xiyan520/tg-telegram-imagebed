<template>
  <UModal
    v-model="open"
    :ui="{
      width: 'sm:max-w-lg',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-hidden flex flex-col max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:clock" class="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white">上传历史</h3>
              <p v-if="totalUploads > 0" class="text-xs text-gray-500">共 {{ totalUploads }} 条记录</p>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <UButton
              icon="heroicons:arrow-path"
              color="gray"
              variant="ghost"
              size="xs"
              :loading="loading"
              title="刷新"
              @click="refresh"
            />
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              size="xs"
              @click="open = false"
            />
          </div>
        </div>
      </template>

      <!-- 列表区域 - 可滚动 -->
      <div class="overflow-y-auto flex-1 -mx-1 px-1" style="max-height: calc(80vh - 10rem);">
        <!-- 加载中（首次） -->
        <div v-if="loading && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          <p class="text-sm text-gray-500">加载中...</p>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="error && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
            <UIcon name="heroicons:exclamation-triangle" class="w-6 h-6 text-red-500" />
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">{{ error }}</p>
          <UButton size="sm" color="primary" variant="soft" @click="refresh">重试</UButton>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!loading && history.length === 0" class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-14 h-14 bg-stone-100 dark:bg-stone-800 rounded-2xl flex items-center justify-center">
            <UIcon name="heroicons:photo" class="w-7 h-7 text-stone-400" />
          </div>
          <p class="text-sm text-gray-500 dark:text-gray-400">暂无上传记录</p>
        </div>

        <!-- 历史列表 -->
        <div v-else class="space-y-2">
          <div
            v-for="item in history"
            :key="item.encrypted_id || item.image_url"
            class="group flex items-center gap-3 p-2.5 rounded-xl hover:bg-stone-50 dark:hover:bg-stone-800/50 transition-colors"
          >
            <!-- 缩略图（可点击预览） -->
            <div
              class="relative w-14 h-14 rounded-lg overflow-hidden border border-stone-200 dark:border-stone-700 flex-shrink-0 cursor-pointer"
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
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                {{ item.original_filename }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {{ formatTime(item.created_at) }}
              </p>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
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
          <div v-if="hasMore" class="pt-2 pb-1">
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
const open = defineModel<boolean>('open', { default: false })

const tokenStore = useTokenStore()
const { copy: clipboardCopy } = useClipboardCopy()

const history = ref<any[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const page = ref(1)
const hasMore = ref(false)
const totalUploads = ref(0)
const previewOpen = ref(false)
const previewImage = ref<{ url: string; filename: string } | null>(null)

const PAGE_SIZE = 20

const formatLink = (item: any, format: string) => {
  const url = item.image_url
  const name = item.original_filename || 'image'
  switch (format) {
    case 'markdown': return `![${name}](${url})`
    case 'html': return `<img src="${url}" alt="${name}" />`
    case 'bbcode': return `[img]${url}[/img]`
    default: return url
  }
}

const getCopyMenuItems = (item: any) => [[
  { label: 'URL', icon: 'i-heroicons-link', click: () => clipboardCopy(formatLink(item, 'url'), '已复制 URL') },
  { label: 'Markdown', icon: 'i-heroicons-hashtag', click: () => clipboardCopy(formatLink(item, 'markdown'), '已复制 Markdown') },
  { label: 'HTML', icon: 'i-heroicons-code-bracket', click: () => clipboardCopy(formatLink(item, 'html'), '已复制 HTML') },
  { label: 'BBCode', icon: 'i-heroicons-chat-bubble-left', click: () => clipboardCopy(formatLink(item, 'bbcode'), '已复制 BBCode') },
]]

const openInNewTab = (url: string) => {
  window.open(url, '_blank')
}

const previewItem = (item: any) => {
  previewImage.value = {
    url: item.image_url,
    filename: item.original_filename,
  }
  previewOpen.value = true
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
  loadHistory()
}

// 打开时自动加载
watch(open, (val) => {
  if (val) {
    page.value = 1
    loadHistory()
  }
})
</script>
