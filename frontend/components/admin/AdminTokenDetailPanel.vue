<template>
  <div class="h-full flex flex-col">
    <!-- 面板头部 -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-stone-200 dark:border-neutral-700">
      <h3 class="text-lg font-semibold text-stone-900 dark:text-white truncate">Token 详情</h3>
      <div class="flex items-center gap-1">
        <UButton icon="heroicons:pencil" color="gray" variant="ghost" size="sm" @click="openEditModal" />
        <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="sm" :loading="loading" @click="loadDetail" />
        <UButton icon="heroicons:x-mark" color="gray" variant="ghost" size="sm" @click="emit('close')" />
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading && !tokenDetail" class="flex-1 flex items-center justify-center">
      <div class="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- 内容区域 -->
    <div v-else-if="tokenDetail" class="flex-1 overflow-y-auto">
      <!-- Token 信息卡片 -->
      <div class="p-5 space-y-4">
        <!-- 完整 Token -->
        <div>
          <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">完整 Token</label>
          <div class="mt-1 flex items-center gap-2">
            <code class="flex-1 font-mono text-xs p-2 rounded-lg bg-stone-100 dark:bg-neutral-800 break-all select-all">
              {{ tokenDetail.token }}
            </code>
            <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" size="xs" @click="copyToken" />
          </div>
        </div>

        <!-- 状态 + 描述 -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">状态</label>
            <div class="mt-1 flex items-center gap-2">
              <UBadge v-if="tokenDetail.is_expired" color="amber" variant="subtle" size="xs">已过期</UBadge>
              <UBadge v-else :color="tokenDetail.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                {{ tokenDetail.is_active ? '启用' : '禁用' }}
              </UBadge>
              <UToggle :model-value="tokenDetail.is_active" size="sm" :disabled="tokenDetail.is_expired || updatingStatus" @update:model-value="toggleStatus" />
            </div>
          </div>
          <div>
            <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">描述</label>
            <p class="mt-1 text-sm text-stone-800 dark:text-stone-200 truncate">{{ tokenDetail.description?.trim() || '--' }}</p>
          </div>
        </div>
        <!-- 时间信息 -->
        <div class="grid grid-cols-3 gap-3 text-sm">
          <div>
            <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">创建时间</label>
            <p class="mt-1 text-stone-800 dark:text-stone-200">{{ formatDate(tokenDetail.created_at) }}</p>
          </div>
          <div>
            <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">过期时间</label>
            <p class="mt-1 text-stone-800 dark:text-stone-200">{{ tokenDetail.expires_at ? formatDate(tokenDetail.expires_at) : '永不' }}</p>
          </div>
          <div>
            <label class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide">上传</label>
            <p class="mt-1 text-stone-800 dark:text-stone-200">{{ tokenDetail.upload_count }} / {{ tokenDetail.upload_limit ?? '∞' }}</p>
          </div>
        </div>

        <!-- 上传进度条 -->
        <div v-if="tokenDetail.upload_limit" class="mt-1">
          <div class="w-full bg-stone-200 dark:bg-neutral-700 rounded-full h-1.5">
            <div
              class="h-1.5 rounded-full transition-all"
              :class="uploadPercent >= 90 ? 'bg-red-500' : uploadPercent >= 70 ? 'bg-amber-500' : 'bg-green-500'"
              :style="{ width: `${Math.min(100, uploadPercent)}%` }"
            />
          </div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="border-t border-stone-200 dark:border-neutral-700">
        <div class="flex border-b border-stone-200 dark:border-neutral-700">
          <button
            class="flex-1 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
            :class="activeTab === 'uploads' ? 'border-amber-500 text-amber-600 dark:text-amber-400' : 'border-transparent text-stone-500 hover:text-stone-700'"
            @click="switchTab('uploads')"
          >
            上传图片 ({{ uploadsTotal }})
          </button>
          <button
            class="flex-1 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
            :class="activeTab === 'galleries' ? 'border-amber-500 text-amber-600 dark:text-amber-400' : 'border-transparent text-stone-500 hover:text-stone-700'"
            @click="switchTab('galleries')"
          >
            画集 ({{ galleriesTotal }})
          </button>
        </div>

        <!-- 上传图片 Tab -->
        <div v-if="activeTab === 'uploads'" class="p-4">
          <div v-if="loadingUploads" class="flex justify-center py-8">
            <div class="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div v-else-if="uploads.length === 0" class="text-center py-8 text-stone-500 text-sm">暂无上传图片</div>
          <div v-else class="grid grid-cols-3 sm:grid-cols-4 gap-2">
            <div v-for="img in uploads" :key="img.encrypted_id" class="group relative aspect-square rounded-lg overflow-hidden border border-stone-200 dark:border-neutral-700">
              <img :src="getImageSrc(img)" :alt="img.original_filename" loading="lazy" class="w-full h-full object-cover" />
              <div class="absolute bottom-0 left-0 right-0 p-1 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                <p class="text-white text-xs truncate">{{ img.original_filename }}</p>
              </div>
            </div>
          </div>
          <div v-if="uploadsTotalPages > 1" class="flex justify-center pt-3">
            <UPagination v-model="uploadsPage" :total="uploadsTotal" :page-count="uploadsPageSize" size="xs" />
          </div>
        </div>
        <!-- 画集 Tab -->
        <div v-if="activeTab === 'galleries'" class="p-4">
          <div v-if="loadingGalleries" class="flex justify-center py-8">
            <div class="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div v-else-if="galleries.length === 0" class="text-center py-8 text-stone-500 text-sm">暂无关联画集</div>
          <div v-else class="space-y-2">
            <NuxtLink
              v-for="g in galleries"
              :key="g.id"
              :to="`/admin/galleries/${g.id}`"
              class="flex items-center gap-3 p-2 rounded-lg border border-stone-200 dark:border-neutral-700 hover:border-amber-400 transition-all"
            >
              <div class="w-10 h-10 rounded-lg overflow-hidden bg-stone-100 dark:bg-neutral-800 flex-shrink-0">
                <img v-if="g.cover_url" :src="g.cover_url" class="w-full h-full object-cover" loading="lazy" />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <UIcon name="heroicons:photo" class="w-5 h-5 text-stone-400" />
                </div>
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-stone-900 dark:text-white truncate">{{ g.name }}</p>
                <p class="text-xs text-stone-500">{{ g.image_count || 0 }} 张图片</p>
              </div>
            </NuxtLink>
          </div>
          <div v-if="galleriesTotalPages > 1" class="flex justify-center pt-3">
            <UPagination v-model="galleriesPage" :total="galleriesTotal" :page-count="galleriesPageSize" size="xs" />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div v-if="tokenDetail" class="px-5 py-3 border-t border-stone-200 dark:border-neutral-700 flex items-center justify-between">
      <UButton color="red" variant="soft" size="sm" @click="askDelete">删除 Token</UButton>
      <UButton color="gray" variant="ghost" size="sm" :to="`/admin/tokens/${tokenId}`">查看完整页面</UButton>
    </div>

    <!-- 编辑模态框 -->
    <UModal v-model="editModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">编辑 Token</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="editModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="描述" hint="可选">
            <UInput v-model="editForm.description" placeholder="Token 用途" :maxlength="200" />
          </UFormGroup>
          <UFormGroup label="过期时间" hint="留空表示永不过期">
            <UInput v-model="editForm.expires_at" type="datetime-local" />
          </UFormGroup>
          <UFormGroup label="上传限制">
            <UInput v-model.number="editForm.upload_limit" type="number" min="0" max="1000000" placeholder="不限制" />
          </UFormGroup>
          <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <div>
              <p class="text-sm font-medium text-stone-900 dark:text-white">启用状态</p>
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
const props = defineProps<{ tokenId: number }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
  (e: 'deleted'): void
}>()

const config = useRuntimeConfig()
const notification = useNotification()
const { copy: clipboardCopy } = useClipboardCopy()

const loading = ref(false)
const tokenDetail = ref<any>(null)
const updatingStatus = ref(false)

// Tab
const activeTab = ref<'uploads' | 'galleries'>('uploads')
const uploads = ref<any[]>([])
const uploadsTotal = ref(0)
const uploadsPage = ref(1)
const uploadsPageSize = ref(24)
const loadingUploads = ref(false)
const uploadsTotalPages = computed(() => Math.max(1, Math.ceil(uploadsTotal.value / uploadsPageSize.value)))

const galleries = ref<any[]>([])
const galleriesTotal = ref(0)
const galleriesPage = ref(1)
const galleriesPageSize = ref(20)
const loadingGalleries = ref(false)
const galleriesTotalPages = computed(() => Math.max(1, Math.ceil(galleriesTotal.value / galleriesPageSize.value)))

const uploadPercent = computed(() => {
  if (!tokenDetail.value?.upload_limit) return 0
  return (tokenDetail.value.upload_count / tokenDetail.value.upload_limit) * 100
})

// 编辑
const editModalOpen = ref(false)
const saving = ref(false)
const editForm = ref({ description: '', expires_at: '', upload_limit: null as number | null, is_active: true })

const formatDate = (dateStr?: string | null) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const joinUrl = (base: string, path: string) => `${String(base || '').replace(/\/$/, '')}${path}`
const getImageSrc = (img: any) => img.cdn_url || joinUrl(config.public.apiBase, `/image/${img.encrypted_id}`) || img.image_url

const copyToken = () => {
  if (tokenDetail.value?.token) clipboardCopy(tokenDetail.value.token, 'Token 已复制')
}

const loadDetail = async () => {
  loading.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}`, { credentials: 'include' })
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
  if (!next && !window.confirm('确定要禁用该 Token 吗？')) return
  const prev = tokenDetail.value.is_active
  tokenDetail.value.is_active = next
  updatingStatus.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
      method: 'PATCH', credentials: 'include', body: { is_active: next }
    })
    if (!resp?.success) throw new Error(resp?.error || '更新失败')
    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')
    emit('updated')
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
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}/uploads`, {
      params: { page: uploadsPage.value, page_size: uploadsPageSize.value }, credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    uploads.value = resp.data.items || []
    uploadsTotal.value = resp.data.total || 0
  } catch { /* 静默 */ }
  finally { loadingUploads.value = false }
}

const loadGalleries = async () => {
  loadingGalleries.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}/galleries`, {
      params: { page: galleriesPage.value, page_size: galleriesPageSize.value }, credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    const base_url = config.public.apiBase
    const items = resp.data.items || []
    items.forEach((item: any) => {
      if (item.cover_image) item.cover_url = `${base_url}/image/${item.cover_image}`
    })
    galleries.value = items
    galleriesTotal.value = resp.data.total || 0
  } catch { /* 静默 */ }
  finally { loadingGalleries.value = false }
}

const switchTab = (tab: 'uploads' | 'galleries') => {
  if (activeTab.value === tab) return
  activeTab.value = tab
  if (tab === 'uploads' && uploads.value.length === 0) loadUploads()
  if (tab === 'galleries' && galleries.value.length === 0) loadGalleries()
}

const toLocalDatetimeValue = (dateStr?: string | null) => {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
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
  saving.value = true
  try {
    const body: Record<string, any> = {
      description: editForm.value.description.trim() || null,
      expires_at: editForm.value.expires_at || null,
      upload_limit: editForm.value.upload_limit,
      is_active: editForm.value.is_active,
    }
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
      method: 'PATCH', credentials: 'include', body
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')
    const fullToken = tokenDetail.value?.token
    tokenDetail.value = { ...resp.data, token: fullToken }
    notification.success('保存成功', 'Token 信息已更新')
    editModalOpen.value = false
    emit('updated')
  } catch (error: any) {
    notification.error('保存失败', error.data?.error || error.message)
  } finally {
    saving.value = false
  }
}

const askDelete = async () => {
  if (!window.confirm('确定要删除该 Token 吗？此操作不可恢复。')) return
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
      method: 'DELETE', credentials: 'include'
    })
    if (resp && resp.success === false) throw new Error(resp?.error || '删除失败')
    notification.success('删除成功', 'Token 已删除')
    emit('deleted')
  } catch (error: any) {
    notification.error('删除失败', error.data?.error || error.message)
  }
}

watch(uploadsPage, () => { if (activeTab.value === 'uploads') loadUploads() })
watch(galleriesPage, () => { if (activeTab.value === 'galleries') loadGalleries() })

// 监听 tokenId 变化重新加载
watch(() => props.tokenId, async (newId) => {
  if (!newId) return
  activeTab.value = 'uploads'
  uploads.value = []
  galleries.value = []
  uploadsPage.value = 1
  galleriesPage.value = 1
  await loadDetail()
  await loadUploads()
}, { immediate: true })
</script>
