<template>
  <div class="space-y-4 pb-10">
    <AdminPageHeader
      title="Token 详情"
      eyebrow="Resources"
      icon="heroicons:key"
      :description="`ID: ${tokenDetail?.id || route.params.id}`"
    >
      <template #actions>
        <UButton icon="heroicons:arrow-left" color="gray" variant="ghost" to="/admin/tokens">
          返回列表
        </UButton>
        <UButton icon="heroicons:pencil-square" color="gray" variant="outline" @click="openEditModal">
          编辑
        </UButton>
        <UButton icon="heroicons:arrow-path" color="gray" variant="outline" :loading="loading" @click="refreshAll">
          刷新
        </UButton>
      </template>
    </AdminPageHeader>

    <div v-if="loading && !tokenDetail" class="flex flex-col items-center justify-center py-20">
      <div class="h-14 w-14 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
      <p class="mt-3 text-sm text-stone-500 dark:text-stone-400">加载 Token 详情中...</p>
    </div>

    <template v-else-if="tokenDetail">
      <div class="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <section class="space-y-4">
          <UCard>
            <div class="space-y-3">
              <div class="flex items-center gap-2">
                <code class="flex-1 break-all rounded-lg bg-stone-100 px-3 py-2 font-mono text-xs dark:bg-neutral-800">
                  {{ tokenDetail.token }}
                </code>
                <UButton color="primary" variant="soft" icon="heroicons:clipboard-document" @click="copyToken">
                  复制
                </UButton>
              </div>

              <div class="grid grid-cols-2 gap-2 md:grid-cols-4">
                <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">状态</p>
                  <div class="mt-1 flex items-center gap-2">
                    <UBadge v-if="tokenDetail.is_expired" color="amber" variant="subtle" size="xs">已过期</UBadge>
                    <UBadge v-else :color="tokenDetail.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ tokenDetail.is_active ? '启用' : '禁用' }}
                    </UBadge>
                    <UToggle
                      :model-value="tokenDetail.is_active"
                      :disabled="tokenDetail.is_expired || updatingStatus"
                      size="sm"
                      @update:model-value="toggleStatus"
                    />
                  </div>
                </div>
                <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">上传用量</p>
                  <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">
                    {{ tokenDetail.upload_count }} / {{ tokenDetail.upload_limit ?? '∞' }}
                  </p>
                </div>
                <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">上传图片</p>
                  <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ summary.upload_total }}</p>
                </div>
                <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">关联画集</p>
                  <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ summary.gallery_total }}</p>
                </div>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="space-y-3">
              <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">描述</p>
                  <p class="mt-1 text-sm text-stone-800 dark:text-stone-200">{{ tokenDetail.description?.trim() || '--' }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">最后使用</p>
                  <p class="mt-1 text-sm text-stone-800 dark:text-stone-200">{{ tokenDetail.last_used ? formatDate(tokenDetail.last_used) : '从未使用' }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">创建时间</p>
                  <p class="mt-1 text-sm text-stone-800 dark:text-stone-200">{{ formatDate(tokenDetail.created_at) }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">过期时间</p>
                  <p class="mt-1 text-sm text-stone-800 dark:text-stone-200">{{ tokenDetail.expires_at ? formatDate(tokenDetail.expires_at) : '永不过期' }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">IP 地址</p>
                  <p class="mt-1 break-all font-mono text-xs text-stone-800 dark:text-stone-200">{{ tokenDetail.ip_address || '--' }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">User-Agent</p>
                  <p class="mt-1 line-clamp-2 break-all text-xs text-stone-800 dark:text-stone-200" :title="tokenDetail.user_agent || ''">
                    {{ tokenDetail.user_agent || '--' }}
                  </p>
                </div>
              </div>

              <div v-if="tokenDetail.tg_user_id" class="rounded-lg border border-blue-200/80 bg-blue-50/70 p-3 dark:border-blue-900/50 dark:bg-blue-900/20">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p class="text-xs text-blue-700/80 dark:text-blue-300/80">Telegram 绑定</p>
                    <p class="mt-1 text-sm font-medium text-blue-700 dark:text-blue-300">
                      {{ [tokenDetail.tg_first_name, tokenDetail.tg_last_name].filter(Boolean).join(' ') || '--' }}
                      <span v-if="tokenDetail.tg_username">{{ ` @${tokenDetail.tg_username}` }}</span>
                    </p>
                    <p class="mt-0.5 text-xs text-blue-600/90 dark:text-blue-300/90">TG ID: {{ tokenDetail.tg_user_id }}</p>
                  </div>
                  <UButton
                    size="xs"
                    color="blue"
                    variant="soft"
                    icon="heroicons:funnel"
                    @click="navigateTo(`/admin/tokens?tg_user_id=${tokenDetail.tg_user_id}`)"
                  >
                    查看该用户 Token
                  </UButton>
                </div>
              </div>
            </div>
          </UCard>
        </section>

        <section class="space-y-4">
          <UCard>
            <div class="space-y-3">
              <h3 class="text-sm font-semibold text-stone-900 dark:text-white">容量与关联概览</h3>
              <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-stone-500 dark:text-stone-400">上传占用</span>
                  <span class="text-sm font-semibold text-stone-900 dark:text-white">{{ Math.round(uploadPercent) }}%</span>
                </div>
                <div class="mt-2 h-2 rounded-full bg-stone-200 dark:bg-neutral-700">
                  <div
                    class="h-2 rounded-full transition-all"
                    :class="uploadPercent >= 90 ? 'bg-red-500' : uploadPercent >= 70 ? 'bg-amber-500' : 'bg-green-500'"
                    :style="{ width: `${Math.min(100, uploadPercent)}%` }"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">画集授权</p>
                  <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ summary.access_total }}</p>
                </div>
                <div class="rounded-lg border border-stone-200/80 px-3 py-2 dark:border-neutral-700/80">
                  <p class="text-xs text-stone-500 dark:text-stone-400">最近上传</p>
                  <p class="mt-1 text-sm text-stone-900 dark:text-white">{{ summary.last_upload_at ? formatDate(summary.last_upload_at) : '--' }}</p>
                </div>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="space-y-2">
              <h3 class="text-sm font-semibold text-stone-900 dark:text-white">风险操作</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">删除后不可恢复，可选择是否连同关联图片一起删除。</p>
              <UButton color="red" variant="soft" icon="heroicons:trash" block :loading="deleting" @click="deleteToken">
                删除 Token
              </UButton>
            </div>
          </UCard>
        </section>
      </div>

      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <button
              class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
              :class="activeTab === 'uploads' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'"
              @click="switchTab('uploads')"
            >
              上传图片 ({{ uploadsTotal }})
            </button>
            <button
              class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
              :class="activeTab === 'galleries' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'"
              @click="switchTab('galleries')"
            >
              画集 ({{ galleriesTotal }})
            </button>
          </div>
        </template>

        <div v-if="activeTab === 'uploads'">
          <div v-if="loadingUploads" class="py-12 text-center text-sm text-stone-500 dark:text-stone-400">加载中...</div>
          <div v-else-if="uploads.length === 0" class="py-12 text-center text-sm text-stone-500 dark:text-stone-400">暂无上传图片</div>
          <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            <div
              v-for="(item, index) in uploads"
              :key="item.encrypted_id"
              class="group relative aspect-square cursor-pointer overflow-hidden rounded-xl border border-stone-200 dark:border-neutral-700"
              @click="openLightbox(index)"
            >
              <img :src="item.cdn_url || item.image_url" :alt="item.original_filename" class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110" loading="lazy">
              <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                <p class="truncate text-xs text-white">{{ item.original_filename }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'galleries'">
          <div v-if="loadingGalleries" class="py-12 text-center text-sm text-stone-500 dark:text-stone-400">加载中...</div>
          <div v-else-if="galleries.length === 0" class="py-12 text-center text-sm text-stone-500 dark:text-stone-400">暂无关联画集</div>
          <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            <NuxtLink
              v-for="item in galleries"
              :key="item.id"
              :to="`/admin/galleries/${item.id}`"
              class="flex items-center gap-3 rounded-xl border border-stone-200/80 p-3 transition hover:border-amber-300 dark:border-neutral-700/80 dark:hover:border-amber-700/60"
            >
              <div class="h-12 w-12 flex-shrink-0 overflow-hidden rounded-lg bg-stone-100 dark:bg-neutral-800">
                <img v-if="item.cover_url" :src="item.cover_url" class="h-full w-full object-cover" loading="lazy">
                <div v-else class="flex h-full w-full items-center justify-center">
                  <UIcon name="heroicons:photo" class="h-6 w-6 text-stone-400" />
                </div>
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-stone-900 dark:text-white">{{ item.name }}</p>
                <p class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">{{ item.image_count || 0 }} 张图片</p>
              </div>
            </NuxtLink>
          </div>
        </div>

        <template #footer>
          <div v-if="currentTotalPages > 1" class="flex justify-center">
            <UPagination v-model="currentPage" :total="currentTotal" :page-count="currentPageSize" />
          </div>
        </template>
      </UCard>
    </template>

    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="lightboxImages"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
      @copy-link="handleCopyLink"
    />

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
            <UInput v-model="editForm.description" placeholder="例如：前端站点 / 服务器脚本" :maxlength="200" />
          </UFormGroup>

          <UFormGroup label="过期时间" hint="留空表示永不过期">
            <UInput v-model="editForm.expires_at" type="datetime-local" />
          </UFormGroup>

          <UFormGroup label="上传限制" hint="留空表示不限制">
            <UInput v-model.number="editForm.upload_limit" type="number" min="0" max="1000000" placeholder="不限制" />
          </UFormGroup>

          <div class="flex items-center justify-between rounded-lg bg-stone-50 p-3 dark:bg-neutral-800">
            <div>
              <p class="text-sm font-medium text-stone-900 dark:text-white">启用状态</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">禁用后该 Token 将无法上传</p>
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

    <UModal v-model="confirmModalOpen" :ui="{ width: 'sm:max-w-md' }">
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="heroicons:exclamation-triangle" class="h-5 w-5 text-amber-500" />
            <span class="font-semibold">{{ confirmModalTitle }}</span>
          </div>
        </template>
        <p class="text-sm text-stone-600 dark:text-stone-400">{{ confirmModalDesc }}</p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="onConfirmCancel">取消</UButton>
            <UButton color="primary" @click="onConfirmOk">确认</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { AdminTokenOverview, AdminTokenOverviewSummary } from '~/types/admin'

definePageMeta({ layout: 'admin', middleware: 'auth' })

const route = useRoute()
const config = useRuntimeConfig()
const notification = useNotification()
const { copy: clipboardCopy } = useClipboardCopy()

const tokenId = computed(() => Number(route.params.id))

const loading = ref(false)
const deleting = ref(false)
const tokenDetail = ref<AdminTokenOverview | null>(null)
const updatingStatus = ref(false)

const activeTab = ref<'uploads' | 'galleries'>('uploads')
const uploads = ref<any[]>([])
const uploadsTotal = ref(0)
const uploadsPage = ref(1)
const uploadsPageSize = ref(50)
const loadingUploads = ref(false)

const galleries = ref<any[]>([])
const galleriesTotal = ref(0)
const galleriesPage = ref(1)
const galleriesPageSize = ref(30)
const loadingGalleries = ref(false)

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

const editModalOpen = ref(false)
const saving = ref(false)
const editForm = ref({
  description: '',
  expires_at: '',
  upload_limit: null as number | null,
  is_active: true,
})

const confirmModalOpen = ref(false)
const confirmModalTitle = ref('')
const confirmModalDesc = ref('')
const confirmModalResolve = ref<((v: boolean) => void) | null>(null)

const showConfirm = (title: string, desc: string): Promise<boolean> => {
  return new Promise((resolve) => {
    confirmModalTitle.value = title
    confirmModalDesc.value = desc
    confirmModalResolve.value = resolve
    confirmModalOpen.value = true
  })
}

const onConfirmOk = () => {
  confirmModalOpen.value = false
  confirmModalResolve.value?.(true)
  confirmModalResolve.value = null
}

const onConfirmCancel = () => {
  confirmModalOpen.value = false
  confirmModalResolve.value?.(false)
  confirmModalResolve.value = null
}

const summary = computed<AdminTokenOverviewSummary>(() => tokenDetail.value?.summary || {
  upload_total: uploadsTotal.value,
  gallery_total: galleriesTotal.value,
  access_total: 0,
  last_upload_at: null,
  last_gallery_at: null,
})

const uploadPercent = computed(() => {
  if (!tokenDetail.value?.upload_limit) return 0
  return (tokenDetail.value.upload_count / tokenDetail.value.upload_limit) * 100
})

const currentPage = computed({
  get: () => (activeTab.value === 'uploads' ? uploadsPage.value : galleriesPage.value),
  set: (value) => {
    if (activeTab.value === 'uploads') uploadsPage.value = value
    else galleriesPage.value = value
  },
})

const currentTotal = computed(() => (activeTab.value === 'uploads' ? uploadsTotal.value : galleriesTotal.value))
const currentPageSize = computed(() => (activeTab.value === 'uploads' ? uploadsPageSize.value : galleriesPageSize.value))
const currentTotalPages = computed(() => Math.max(1, Math.ceil(currentTotal.value / currentPageSize.value)))

const lightboxImages = computed(() => uploads.value.map((item) => ({
  ...item,
  image_url: item.cdn_url || item.image_url,
})))

const formatDate = (dateStr?: string | null) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadDetail = async () => {
  if (!tokenId.value) return
  loading.value = true
  let overviewErr: any = null
  try {
    let resp: any = null
    try {
      resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}/overview`, {
        credentials: 'include',
      })
    } catch (err: any) {
      overviewErr = err
    }
    if (!resp?.success) {
      resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
        credentials: 'include',
      })
    }
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    tokenDetail.value = resp.data
  } catch (error: any) {
    const fallbackErr = error?.data?.error || error?.message
    const rootErr = overviewErr?.data?.error || overviewErr?.message
    notification.error('加载失败', fallbackErr || rootErr || '无法获取 Token 详情')
  } finally {
    loading.value = false
  }
}

const loadUploads = async () => {
  if (!tokenId.value) return
  loadingUploads.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}/uploads`, {
      credentials: 'include',
      params: { page: uploadsPage.value, page_size: uploadsPageSize.value },
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    uploads.value = resp.data.items || []
    uploadsTotal.value = resp.data.total || 0
  } catch (error: any) {
    notification.error('加载上传记录失败', error?.data?.error || error?.message || '获取上传记录失败')
  } finally {
    loadingUploads.value = false
  }
}

const loadGalleries = async () => {
  if (!tokenId.value) return
  loadingGalleries.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}/galleries`, {
      credentials: 'include',
      params: { page: galleriesPage.value, page_size: galleriesPageSize.value },
    })
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    galleries.value = resp.data.items || []
    galleriesTotal.value = resp.data.total || 0
  } catch (error: any) {
    notification.error('加载画集失败', error?.data?.error || error?.message || '获取画集失败')
  } finally {
    loadingGalleries.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([
    loadDetail(),
    loadUploads(),
    loadGalleries(),
  ])
}

const switchTab = (tab: 'uploads' | 'galleries') => {
  if (activeTab.value === tab) return
  activeTab.value = tab
}

const openLightbox = (index: number) => {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const handleCopyLink = (image: any) => {
  const url = image.image_url || image.cdn_url
  if (!url) return
  navigator.clipboard.writeText(url).catch(() => {})
}

const copyToken = () => {
  const token = tokenDetail.value?.token
  if (!token) return
  clipboardCopy(token, 'Token 已复制')
}

const toLocalDatetimeValue = (dateStr?: string | null) => {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (Number.isNaN(d.getTime())) return ''
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return ''
  }
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
  const ok = await showConfirm('保存 Token 修改', '确定要保存对该 Token 的修改吗？')
  if (!ok || !tokenId.value) return
  saving.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      method: 'PATCH',
      credentials: 'include',
      body: {
        description: editForm.value.description.trim() || null,
        expires_at: editForm.value.expires_at || null,
        upload_limit: editForm.value.upload_limit,
        is_active: editForm.value.is_active,
      },
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')
    notification.success('保存成功', 'Token 信息已更新')
    editModalOpen.value = false
    await refreshAll()
  } catch (error: any) {
    notification.error('保存失败', error?.data?.error || error?.message || '无法保存 Token')
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (next: boolean) => {
  if (!tokenDetail.value || !tokenId.value || tokenDetail.value.is_expired) return
  if (!next) {
    const ok = await showConfirm('禁用 Token', '确定要禁用该 Token 吗？禁用后将无法继续上传。')
    if (!ok) return
  }

  const prev = tokenDetail.value.is_active
  tokenDetail.value.is_active = next
  updatingStatus.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      method: 'PATCH',
      credentials: 'include',
      body: { is_active: next },
    })
    if (!resp?.success) throw new Error(resp?.error || '更新失败')
    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')
  } catch (error: any) {
    tokenDetail.value.is_active = prev
    notification.error('更新失败', error?.data?.error || error?.message || '无法更新 Token 状态')
  } finally {
    updatingStatus.value = false
  }
}

const deleteToken = async () => {
  if (!tokenId.value) return
  const ok = await showConfirm('删除 Token', '确定要删除该 Token 吗？此操作不可恢复。')
  if (!ok) return

  deleting.value = true
  try {
    const resp = await $fetch<any>(`${config.public.apiBase}/api/admin/tokens/${tokenId.value}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    if (resp && resp.success === false) throw new Error(resp?.error || '删除失败')
    notification.success('删除成功', 'Token 已删除')
    navigateTo('/admin/tokens')
  } catch (error: any) {
    notification.error('删除失败', error?.data?.error || error?.message || '无法删除 Token')
  } finally {
    deleting.value = false
  }
}

watch(uploadsPage, () => {
  if (activeTab.value === 'uploads') loadUploads()
})

watch(galleriesPage, () => {
  if (activeTab.value === 'galleries') loadGalleries()
})

watch(
  () => route.params.id,
  async () => {
    activeTab.value = 'uploads'
    uploadsPage.value = 1
    galleriesPage.value = 1
    await refreshAll()
  },
)

onMounted(async () => {
  await refreshAll()
})
</script>
