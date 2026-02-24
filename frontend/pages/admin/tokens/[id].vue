<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3">
        <UButton
          icon="heroicons:arrow-left"
          color="gray"
          variant="ghost"
          to="/admin/tokens"
        />
        <div>
          <h1 class="text-2xl font-bold text-stone-900 dark:text-white">Token 详情</h1>
          <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
            ID: {{ tokenDetail?.id || route.params.id }}
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          icon="heroicons:pencil"
          color="gray"
          variant="outline"
          @click="openEditModal"
        >
          编辑
        </UButton>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadDetail"
        >
          刷新
        </UButton>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading && !tokenDetail" class="flex flex-col justify-center items-center py-16">
      <div class="w-14 h-14 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-stone-600 dark:text-stone-400">加载中...</p>
    </div>

    <template v-else-if="tokenDetail">
      <!-- Token 信息卡片 -->
      <UCard>
        <!-- Token 值 -->
        <div class="flex items-center gap-2 mb-5">
          <code class="flex-1 font-mono text-xs p-2.5 rounded-lg bg-stone-100 dark:bg-neutral-800 break-all select-all truncate">
            {{ tokenDetail.token }}
          </code>
          <UButton
            icon="heroicons:clipboard-document"
            color="primary"
            variant="soft"
            size="sm"
            @click="copyToken"
          >
            复制
          </UButton>
        </div>

        <!-- 核心指标卡片 -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <div class="p-3 rounded-lg bg-stone-50 dark:bg-neutral-800/60 border border-stone-100 dark:border-neutral-700/50">
            <div class="text-[11px] text-stone-400 dark:text-stone-500 mb-1">状态</div>
            <div class="flex items-center gap-2">
              <UBadge
                v-if="tokenDetail.is_expired"
                color="amber" variant="subtle" size="xs"
              >已过期</UBadge>
              <UBadge
                v-else
                :color="tokenDetail.is_active ? 'green' : 'gray'" variant="subtle" size="xs"
              >{{ tokenDetail.is_active ? '启用' : '禁用' }}</UBadge>
              <UToggle
                :model-value="tokenDetail.is_active"
                size="sm"
                :disabled="tokenDetail.is_expired || updatingStatus"
                @update:model-value="toggleStatus"
              />
            </div>
          </div>
          <div class="p-3 rounded-lg bg-stone-50 dark:bg-neutral-800/60 border border-stone-100 dark:border-neutral-700/50">
            <div class="text-[11px] text-stone-400 dark:text-stone-500 mb-1">上传用量</div>
            <div class="text-sm font-semibold text-stone-800 dark:text-stone-200">
              {{ tokenDetail.upload_count }} / {{ tokenDetail.upload_limit ?? '∞' }}
            </div>
            <div v-if="tokenDetail.upload_limit" class="mt-1.5">
              <div class="w-full bg-stone-200 dark:bg-neutral-700 rounded-full h-1.5">
                <div
                  class="h-1.5 rounded-full transition-all"
                  :class="uploadPercent >= 90 ? 'bg-red-500' : uploadPercent >= 70 ? 'bg-amber-500' : 'bg-green-500'"
                  :style="{ width: `${Math.min(100, uploadPercent)}%` }"
                />
              </div>
            </div>
          </div>
          <div class="p-3 rounded-lg bg-stone-50 dark:bg-neutral-800/60 border border-stone-100 dark:border-neutral-700/50">
            <div class="text-[11px] text-stone-400 dark:text-stone-500 mb-1">创建时间</div>
            <div class="text-sm font-medium text-stone-800 dark:text-stone-200">{{ formatDate(tokenDetail.created_at) }}</div>
          </div>
          <div class="p-3 rounded-lg bg-stone-50 dark:bg-neutral-800/60 border border-stone-100 dark:border-neutral-700/50">
            <div class="text-[11px] text-stone-400 dark:text-stone-500 mb-1">过期时间</div>
            <div class="text-sm font-medium text-stone-800 dark:text-stone-200">{{ tokenDetail.expires_at ? formatDate(tokenDetail.expires_at) : '永不过期' }}</div>
          </div>
        </div>

        <!-- 详细信息 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-3 text-sm">
          <div>
            <span class="text-[11px] text-stone-400 dark:text-stone-500">描述</span>
            <p class="text-stone-800 dark:text-stone-200">{{ tokenDetail.description?.trim() || '--' }}</p>
          </div>
          <div>
            <span class="text-[11px] text-stone-400 dark:text-stone-500">最后使用</span>
            <p class="text-stone-800 dark:text-stone-200">{{ tokenDetail.last_used ? formatDate(tokenDetail.last_used) : '从未使用' }}</p>
          </div>
          <div>
            <span class="text-[11px] text-stone-400 dark:text-stone-500">IP 地址</span>
            <p class="text-stone-800 dark:text-stone-200 font-mono text-xs">{{ tokenDetail.ip_address || '--' }}</p>
          </div>
          <div>
            <span class="text-[11px] text-stone-400 dark:text-stone-500">User-Agent</span>
            <p class="text-stone-800 dark:text-stone-200 text-xs break-all line-clamp-2" :title="tokenDetail.user_agent">{{ tokenDetail.user_agent || '--' }}</p>
          </div>
        </div>
      </UCard>

      <!-- TG 用户关联卡片 -->
      <UCard v-if="tokenDetail.tg_user_id">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
            <UIcon name="heroicons:chat-bubble-left-right" class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-semibold text-stone-900 dark:text-white">Telegram 用户</span>
              <UBadge color="blue" variant="subtle" size="xs">已绑定</UBadge>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
              <div>
                <span class="text-[11px] text-stone-400 dark:text-stone-500">用户名</span>
                <p class="text-stone-800 dark:text-stone-200">{{ tokenDetail.tg_username ? `@${tokenDetail.tg_username}` : '--' }}</p>
              </div>
              <div>
                <span class="text-[11px] text-stone-400 dark:text-stone-500">名称</span>
                <p class="text-stone-800 dark:text-stone-200">{{ [tokenDetail.tg_first_name, tokenDetail.tg_last_name].filter(Boolean).join(' ') || '--' }}</p>
              </div>
              <div>
                <span class="text-[11px] text-stone-400 dark:text-stone-500">TG User ID</span>
                <p class="text-stone-800 dark:text-stone-200 font-mono text-xs">{{ tokenDetail.tg_user_id }}</p>
              </div>
            </div>
          </div>
          <UButton
            size="xs"
            color="blue"
            variant="soft"
            icon="heroicons:funnel"
            @click="navigateTo(`/admin/tokens?tg_user_id=${tokenDetail.tg_user_id}`)"
          >
            该用户所有Token
          </UButton>
        </div>
      </UCard>

      <!-- Tab 切换 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-1 border-b border-stone-200 dark:border-neutral-700 -mb-px">
            <button
              class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'uploads'
                ? 'border-amber-500 text-amber-600 dark:text-amber-400'
                : 'border-transparent text-stone-500 hover:text-stone-700 dark:hover:text-stone-300'"
              @click="switchTab('uploads')"
            >
              上传图片 ({{ uploadsTotal }})
            </button>
            <button
              class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'galleries'
                ? 'border-amber-500 text-amber-600 dark:text-amber-400'
                : 'border-transparent text-stone-500 hover:text-stone-700 dark:hover:text-stone-300'"
              @click="switchTab('galleries')"
            >
              画集 ({{ galleriesTotal }})
            </button>
          </div>
        </template>

        <!-- 上传图片 Tab -->
        <div v-if="activeTab === 'uploads'">
          <div v-if="loadingUploads" class="flex justify-center py-12">
            <div class="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <div v-else-if="uploads.length === 0" class="text-center py-12">
            <div class="w-16 h-16 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-3">
              <UIcon name="heroicons:photo" class="w-8 h-8 text-stone-400" />
            </div>
            <p class="text-stone-600 dark:text-stone-400">暂无上传图片</p>
          </div>

          <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <div
              v-for="(img, idx) in uploads"
              :key="img.encrypted_id"
              class="group relative aspect-square rounded-xl overflow-hidden border border-stone-200 dark:border-neutral-700 hover:shadow-lg transition-all cursor-pointer"
              @click="openLightbox(idx)"
            >
              <img
                :src="getImageSrc(img)"
                :alt="img.original_filename"
                loading="lazy"
                class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
              />
              <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                <p class="text-white text-xs truncate">{{ img.original_filename }}</p>
                <p class="text-white/70 text-xs">{{ formatFileSize(img.file_size) }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 画集 Tab -->
        <div v-if="activeTab === 'galleries'">
          <div v-if="loadingGalleries" class="flex justify-center py-12">
            <div class="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <div v-else-if="galleries.length === 0" class="text-center py-12">
            <div class="w-16 h-16 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-3">
              <UIcon name="heroicons:rectangle-stack" class="w-8 h-8 text-stone-400" />
            </div>
            <p class="text-stone-600 dark:text-stone-400">暂无关联画集</p>
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <NuxtLink
              v-for="g in galleries"
              :key="g.id"
              :to="`/admin/galleries/${g.id}`"
              class="block p-4 rounded-xl border border-stone-200 dark:border-neutral-700 hover:border-amber-400 hover:shadow-md transition-all"
            >
              <div class="flex items-start gap-3">
                <div class="w-14 h-14 rounded-lg overflow-hidden bg-stone-100 dark:bg-neutral-800 flex-shrink-0">
                  <img
                    v-if="g.cover_url"
                    :src="g.cover_url"
                    class="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div v-else class="w-full h-full flex items-center justify-center">
                    <UIcon name="heroicons:photo" class="w-6 h-6 text-stone-400" />
                  </div>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="font-medium text-stone-900 dark:text-white truncate">{{ g.name }}</p>
                  <p class="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                    {{ g.image_count || 0 }} 张图片
                  </p>
                  <div class="flex items-center gap-2 mt-1">
                    <UBadge
                      v-if="g.share_enabled"
                      color="green"
                      variant="subtle"
                      size="xs"
                    >
                      已分享
                    </UBadge>
                    <span class="text-xs text-stone-400">{{ formatDate(g.created_at) }}</span>
                  </div>
                </div>
              </div>
            </NuxtLink>
          </div>
        </div>

        <!-- 分页 -->
        <template #footer>
          <div v-if="currentTotalPages > 1" class="flex justify-center pt-2">
            <UPagination v-model="currentPage" :total="currentTotal" :page-count="currentPageSize" />
          </div>
        </template>
      </UCard>
    </template>

    <!-- 图片灯箱 -->
    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="lightboxImages"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
      @copy-link="handleCopyLink"
    />

    <!-- 编辑 Token 模态框 -->
    <UModal v-model="editModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">编辑 Token</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="editModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="描述" hint="可选，用于备注Token用途">
            <UInput
              v-model="editForm.description"
              placeholder="例如：前端站点 / 服务器脚本"
              :maxlength="200"
            />
          </UFormGroup>

          <UFormGroup label="过期时间" hint="留空表示永不过期">
            <UInput
              v-model="editForm.expires_at"
              type="datetime-local"
            />
          </UFormGroup>

          <UFormGroup label="上传限制" hint="留空表示不限制">
            <UInput
              v-model.number="editForm.upload_limit"
              type="number"
              min="0"
              max="1000000"
              placeholder="不限制"
            />
          </UFormGroup>

          <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <div>
              <p class="text-sm font-medium text-stone-900 dark:text-white">启用状态</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">禁用后该 Token 将无法使用</p>
            </div>
            <UToggle v-model="editForm.is_active" size="lg" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="editModalOpen = false">取消</UButton>
            <UButton color="primary" :loading="saving" @click="saveEdit">保存</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'auth' })

const route = useRoute()
const config = useRuntimeConfig()
const notification = useNotification()
const { copy: clipboardCopy } = useClipboardCopy()

const tokenId = computed(() => Number(route.params.id))

// 详情
const loading = ref(false)
const tokenDetail = ref<any>(null)
const updatingStatus = ref(false)

// 编辑
const editModalOpen = ref(false)
const saving = ref(false)
const editForm = ref({
  description: '',
  expires_at: '',
  upload_limit: null as number | null,
  is_active: true,
})

// Tab
const activeTab = ref<'uploads' | 'galleries'>('uploads')

// 上传图片
const uploads = ref<any[]>([])
const uploadsTotal = ref(0)
const uploadsPage = ref(1)
const uploadsPageSize = ref(50)
const loadingUploads = ref(false)

// 画集
const galleries = ref<any[]>([])
const galleriesTotal = ref(0)
const galleriesPage = ref(1)
const galleriesPageSize = ref(50)
const loadingGalleries = ref(false)

// 灯箱
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

const lightboxImages = computed(() =>
  uploads.value.map(img => ({
    ...img,
    image_url: getImageSrc(img),
  }))
)

const openLightbox = (idx: number) => {
  lightboxIndex.value = idx
  lightboxOpen.value = true
}

const handleCopyLink = (image: any) => {
  const url = image.image_url || image.cdn_url
  if (url && import.meta.client) {
    navigator.clipboard.writeText(url).catch(() => {})
  }
}

const uploadPercent = computed(() => {
  if (!tokenDetail.value?.upload_limit) return 0
  return (tokenDetail.value.upload_count / tokenDetail.value.upload_limit) * 100
})

// 当前 Tab 的分页状态
const currentPage = computed({
  get: () => activeTab.value === 'uploads' ? uploadsPage.value : galleriesPage.value,
  set: (v) => {
    if (activeTab.value === 'uploads') uploadsPage.value = v
    else galleriesPage.value = v
  }
})
const currentTotal = computed(() => activeTab.value === 'uploads' ? uploadsTotal.value : galleriesTotal.value)
const currentPageSize = computed(() => activeTab.value === 'uploads' ? uploadsPageSize.value : galleriesPageSize.value)
const currentTotalPages = computed(() => Math.max(1, Math.ceil(currentTotal.value / currentPageSize.value)))

const formatDate = (dateStr?: string | null) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const joinUrl = (base: string, path: string) => `${String(base || '').replace(/\/$/, '')}${path}`

const normalizeImageSrc = (raw: string) => {
  if (!raw || !import.meta.client) return raw
  try {
    const u = new URL(raw, window.location.origin)
    const loc = window.location
    if (loc.protocol === 'https:' && u.protocol === 'http:' && u.host === loc.host) u.protocol = loc.protocol
    return u.toString()
  } catch { return raw }
}

const getImageSrc = (img: any) =>
  normalizeImageSrc(img.cdn_url || joinUrl(config.public.apiBase, `/image/${img.encrypted_id}`) || img.image_url)

const copyToken = () => {
  if (tokenDetail.value?.token) {
    clipboardCopy(tokenDetail.value.token, 'Token 已复制')
  }
}

const toLocalDatetimeValue = (dateStr?: string | null) => {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
    // 转为 datetime-local 格式: YYYY-MM-DDTHH:mm
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch { return '' }
}

const openEditModal = () => {
  if (!tokenDetail.value) return
  editForm.value = {
    description: tokenDetail.value.description || '',
    expires_at: toLocalDatetimeValue(tokenDetail.value.expires_at),
    upload_limit: tokenDetail.value.upload_limit ?? null,
    is_active: tokenDetail.value.is_active,
  }
  editModalOpen.value = true
}

const saveEdit = async () => {
  // 保存前二次确认
  if (!window.confirm('确定要保存对该 Token 的修改吗？')) {
    return
  }

  saving.value = true
  try {
    const body: Record<string, any> = {
      description: editForm.value.description.trim() || null,
      expires_at: editForm.value.expires_at || null,
      upload_limit: editForm.value.upload_limit,
      is_active: editForm.value.is_active,
    }

    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      method: 'PATCH',
      credentials: 'include',
      body,
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')

    // 用返回数据更新本地（保留完整 token 字段）
    const fullToken = tokenDetail.value?.token
    tokenDetail.value = { ...resp.data, token: fullToken }

    notification.success('保存成功', 'Token 信息已更新')
    editModalOpen.value = false
  } catch (error: any) {
    notification.error('保存失败', error.data?.error || error.message)
  } finally {
    saving.value = false
  }
}

const loadDetail = async () => {
  loading.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    tokenDetail.value = resp.data
  } catch (error: any) {
    notification.error('加载失败', error.data?.error || error.message)
  } finally {
    loading.value = false
  }
}

const toggleStatus = async (next: boolean) => {
  if (!tokenDetail.value || tokenDetail.value.is_expired) return

  // 禁用时二次确认
  if (!next) {
    if (!window.confirm('确定要禁用该 Token 吗？禁用后该 Token 将无法使用。')) {
      return
    }
  }

  const prev = tokenDetail.value.is_active
  tokenDetail.value.is_active = next
  updatingStatus.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      method: 'PATCH',
      credentials: 'include',
      body: { is_active: next }
    })
    if (!resp?.success) throw new Error(resp?.error || '更新失败')
    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')
  } catch (error: any) {
    tokenDetail.value.is_active = prev
    notification.error('更新失败', error.data?.error || error.message)
  } finally {
    updatingStatus.value = false
  }
}

const loadUploads = async () => {
  loadingUploads.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}/uploads`, {
      params: { page: uploadsPage.value, page_size: uploadsPageSize.value },
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    uploads.value = resp.data.items || []
    uploadsTotal.value = resp.data.total || 0
  } catch (error: any) {
    notification.error('加载上传记录失败', error.data?.error || error.message)
  } finally {
    loadingUploads.value = false
  }
}

const loadGalleries = async () => {
  loadingGalleries.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}/galleries`, {
      params: { page: galleriesPage.value, page_size: galleriesPageSize.value },
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    galleries.value = resp.data.items || []
    galleriesTotal.value = resp.data.total || 0
  } catch (error: any) {
    notification.error('加载画集失败', error.data?.error || error.message)
  } finally {
    loadingGalleries.value = false
  }
}

const switchTab = (tab: 'uploads' | 'galleries') => {
  if (activeTab.value === tab) return
  activeTab.value = tab
  if (tab === 'uploads' && uploads.value.length === 0) loadUploads()
  if (tab === 'galleries' && galleries.value.length === 0) loadGalleries()
}

watch(uploadsPage, () => { if (activeTab.value === 'uploads') loadUploads() })
watch(galleriesPage, () => { if (activeTab.value === 'galleries') loadGalleries() })

onMounted(async () => {
  await loadDetail()
  // 并行加载两个 tab 的数据，确保计数立即可用
  await Promise.all([loadUploads(), loadGalleries()])
})
</script>
