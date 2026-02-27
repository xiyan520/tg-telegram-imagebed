<template>
  <USlideover :model-value="open" side="right" :ui="{ width: 'max-w-2xl' }" @update:model-value="emit('update:open', $event)">
    <UCard :ui="{ body: { base: 'p-0' }, header: { base: 'px-4 py-3' }, footer: { base: 'px-4 py-3' } }" class="flex h-full flex-col">
      <template #header>
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="text-xs uppercase tracking-[0.14em] text-stone-500 dark:text-stone-400">Token Quick View</p>
            <h3 class="truncate text-sm font-semibold text-stone-900 dark:text-white">
              {{ overview?.token_masked || (tokenId ? `#${tokenId}` : '未选择 Token') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <UButton color="gray" variant="ghost" icon="heroicons:arrow-path" :loading="loadingOverview" @click="refreshAll" />
            <UButton color="gray" variant="ghost" icon="heroicons:x-mark" @click="emit('update:open', false)" />
          </div>
        </div>
      </template>

      <div class="min-h-0 flex-1 overflow-y-auto p-4">
        <div v-if="loadingOverview && !overview" class="flex h-48 items-center justify-center">
          <div class="h-10 w-10 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
        </div>

        <div v-else-if="overview" class="space-y-4">
          <div class="flex items-center gap-2">
            <code class="flex-1 break-all rounded-lg bg-stone-100 px-2.5 py-2 font-mono text-xs dark:bg-neutral-800">{{ overview.token }}</code>
            <UButton color="primary" variant="soft" icon="heroicons:clipboard-document" @click="copyToken">复制</UButton>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
              <p class="text-xs text-stone-500 dark:text-stone-400">状态</p>
              <div class="mt-1 flex items-center gap-2">
                <UBadge v-if="overview.is_expired" color="amber" variant="subtle" size="xs">已过期</UBadge>
                <UBadge v-else :color="overview.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                  {{ overview.is_active ? '启用' : '禁用' }}
                </UBadge>
                <UToggle
                  :model-value="overview.is_active"
                  :disabled="overview.is_expired || updatingStatus"
                  size="sm"
                  @update:model-value="toggleStatus"
                />
              </div>
            </div>
            <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
              <p class="text-xs text-stone-500 dark:text-stone-400">上传用量</p>
              <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">
                {{ overview.upload_count }} / {{ overview.upload_limit ?? '∞' }}
              </p>
            </div>
            <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
              <p class="text-xs text-stone-500 dark:text-stone-400">上传图片</p>
              <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ overview.summary?.upload_total ?? 0 }}</p>
            </div>
            <div class="rounded-lg bg-stone-100/80 px-3 py-2 dark:bg-neutral-800/80">
              <p class="text-xs text-stone-500 dark:text-stone-400">关联画集</p>
              <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ overview.summary?.gallery_total ?? 0 }}</p>
            </div>
          </div>

          <div class="rounded-lg border border-stone-200/80 p-3 dark:border-neutral-700/80">
            <p class="text-xs text-stone-500 dark:text-stone-400">描述</p>
            <p class="mt-1 text-sm text-stone-800 dark:text-stone-200">{{ overview.description?.trim() || '--' }}</p>
          </div>

          <div>
            <div class="flex items-center gap-2 border-b border-stone-200 pb-1 dark:border-neutral-700">
              <button
                class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
                :class="activeTab === 'uploads' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'"
                @click="activeTab = 'uploads'"
              >
                上传图片
              </button>
              <button
                class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
                :class="activeTab === 'galleries' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'"
                @click="activeTab = 'galleries'"
              >
                关联画集
              </button>
            </div>

            <div v-if="activeTab === 'uploads'" class="mt-3 space-y-2">
              <div v-if="loadingUploads" class="py-8 text-center text-sm text-stone-500 dark:text-stone-400">加载中...</div>
              <div v-else-if="uploads.length === 0" class="py-8 text-center text-sm text-stone-500 dark:text-stone-400">暂无上传图片</div>
              <a
                v-for="item in uploads"
                :key="item.encrypted_id"
                :href="item.cdn_url || item.image_url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex items-center justify-between rounded-lg border border-stone-200/80 px-2.5 py-2 text-sm transition hover:border-amber-300 dark:border-neutral-700/80 dark:hover:border-amber-700/60"
              >
                <span class="truncate text-stone-800 dark:text-stone-200">{{ item.original_filename }}</span>
                <span class="ml-2 text-xs text-stone-500 dark:text-stone-400">{{ formatDate(item.created_at) }}</span>
              </a>
            </div>

            <div v-if="activeTab === 'galleries'" class="mt-3 space-y-2">
              <div v-if="loadingGalleries" class="py-8 text-center text-sm text-stone-500 dark:text-stone-400">加载中...</div>
              <div v-else-if="galleries.length === 0" class="py-8 text-center text-sm text-stone-500 dark:text-stone-400">暂无关联画集</div>
              <NuxtLink
                v-for="gallery in galleries"
                :key="gallery.id"
                :to="`/admin/galleries/${gallery.id}`"
                class="flex items-center justify-between rounded-lg border border-stone-200/80 px-2.5 py-2 text-sm transition hover:border-amber-300 dark:border-neutral-700/80 dark:hover:border-amber-700/60"
              >
                <span class="truncate text-stone-800 dark:text-stone-200">{{ gallery.name }}</span>
                <span class="ml-2 text-xs text-stone-500 dark:text-stone-400">{{ gallery.image_count || 0 }} 张</span>
              </NuxtLink>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-between gap-2">
          <UButton color="red" variant="soft" icon="heroicons:trash" :loading="deleting" @click="deleteToken">
            删除 Token
          </UButton>
          <UButton color="primary" icon="heroicons:arrow-top-right-on-square" @click="emit('openFull')">
            打开完整详情
          </UButton>
        </div>
      </template>
    </UCard>
  </USlideover>
</template>

<script setup lang="ts">
import type { AdminTokenOverview } from '~/types/admin'

const props = defineProps<{
  open: boolean
  tokenId: number | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'updated': []
  'deleted': []
  'openFull': []
}>()

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()
const activeTab = ref<'uploads' | 'galleries'>('uploads')

const loadingOverview = ref(false)
const loadingUploads = ref(false)
const loadingGalleries = ref(false)
const updatingStatus = ref(false)
const deleting = ref(false)

const overview = ref<AdminTokenOverview | null>(null)
const uploads = ref<any[]>([])
const galleries = ref<any[]>([])

const formatDate = (date?: string | null) => {
  if (!date) return '--'
  return new Date(date).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadOverview = async () => {
  if (!props.tokenId) return
  loadingOverview.value = true
  let overviewErr: any = null
  try {
    let resp: any = null
    try {
      resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}/overview`, {
        credentials: 'include',
      })
    } catch (err: any) {
      overviewErr = err
    }
    if (!resp?.success) {
      resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
        credentials: 'include',
      })
    }
    if (!resp?.success) throw new Error(resp?.error || '加载失败')
    overview.value = resp.data
  } catch (error: any) {
    const fallbackErr = error?.data?.error || error?.message
    const rootErr = overviewErr?.data?.error || overviewErr?.message
    notification.error('加载失败', fallbackErr || rootErr || '无法加载 Token 概览')
  } finally {
    loadingOverview.value = false
  }
}

const loadUploads = async () => {
  if (!props.tokenId) return
  loadingUploads.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}/uploads`, {
      credentials: 'include',
      params: { page: 1, page_size: 8 },
    })
    uploads.value = resp?.success ? (resp.data?.items || []) : []
  } catch {
    uploads.value = []
  } finally {
    loadingUploads.value = false
  }
}

const loadGalleries = async () => {
  if (!props.tokenId) return
  loadingGalleries.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}/galleries`, {
      credentials: 'include',
      params: { page: 1, page_size: 8 },
    })
    galleries.value = resp?.success ? (resp.data?.items || []) : []
  } catch {
    galleries.value = []
  } finally {
    loadingGalleries.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([loadOverview(), loadUploads(), loadGalleries()])
}

const copyToken = async () => {
  const token = overview.value?.token
  if (!token) return
  try {
    await navigator.clipboard.writeText(token)
    notification.success('已复制', 'Token 已复制到剪贴板')
  } catch {
    notification.error('复制失败', '请检查浏览器剪贴板权限')
  }
}

const toggleStatus = async (next: boolean) => {
  if (!overview.value || !props.tokenId) return
  if (!next && !window.confirm('确定要禁用该 Token 吗？')) return
  const prev = overview.value.is_active
  overview.value.is_active = next
  updatingStatus.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
      method: 'PATCH',
      credentials: 'include',
      body: { is_active: next },
    })
    if (!resp?.success) throw new Error(resp?.error || '更新失败')
    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')
    emit('updated')
  } catch (error: any) {
    overview.value.is_active = prev
    notification.error('更新失败', error?.data?.error || error?.message || '无法更新状态')
  } finally {
    updatingStatus.value = false
  }
}

const deleteToken = async () => {
  if (!props.tokenId) return
  const ok = window.confirm('确定要删除该 Token 吗？此操作不可恢复。')
  if (!ok) return
  deleting.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${props.tokenId}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    if (resp && resp.success === false) throw new Error(resp?.error || '删除失败')
    notification.success('删除成功', 'Token 已删除')
    emit('update:open', false)
    emit('deleted')
  } catch (error: any) {
    notification.error('删除失败', error?.data?.error || error?.message || '无法删除 Token')
  } finally {
    deleting.value = false
  }
}

watch(
  () => [props.open, props.tokenId] as const,
  async ([open, tokenId]) => {
    if (!open || !tokenId) return
    activeTab.value = 'uploads'
    await refreshAll()
  },
  { immediate: true },
)
</script>
