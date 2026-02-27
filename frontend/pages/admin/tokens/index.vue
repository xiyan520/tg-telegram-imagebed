<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">Token管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">共 {{ total }} 个 Token</p>
      </div>
      <div class="flex items-center gap-2">
        <UButton icon="heroicons:arrow-path" color="gray" variant="outline" :loading="loading" @click="loadTokens">
          刷新
        </UButton>
        <UButton icon="heroicons:plus" color="primary" @click="openCreateModal">
          创建Token
        </UButton>
      </div>
    </div>

    <!-- 筛选栏 -->
    <AdminTokensTokenFilters
      v-model:search-query="searchQuery"
      v-model:status="status"
      v-model:tg-bind="tgBind"
      :selected-count="selectedIds.length"
      @batch="batchAction"
      @clear-selection="clearSelection"
    />

    <!-- Token 表格 -->
    <AdminTokensTokenTable
      :tokens="tokens"
      :loading="loading"
      :selected-ids="selectedIds"
      :is-all-selected="isAllSelected"
      :is-partial-selected="isPartialSelected"
      :updating-id="updatingId"
      :page="page"
      :total="total"
      :page-size="pageSize"
      :total-pages="totalPages"
      @toggle-select-all="toggleSelectAll"
      @toggle-select="toggleSelect"
      @select-token="selectToken"
      @update-status="updateStatus"
      @ask-delete="askDelete"
      @update:page="page = $event"
    />

    <!-- 创建 Token 弹窗 -->
    <AdminTokensTokenCreateModal
      v-model:open="createModalOpen"
      :creating="creating"
      :created-token="createdToken"
      :initial-form="createForm"
      @close="closeCreateModal"
      @create="createToken"
      @copy-token="copyCreatedToken"
    />

    <!-- 删除 / 批量操作弹窗 -->
    <AdminTokensTokenBatchActions
      v-model:delete-open="deleteModalOpen"
      :deleting-token="deletingToken"
      :delete-impact="deleteImpact"
      :loading-impact="loadingImpact"
      :deleting="deleting"
      v-model:batch-open="batchModalOpen"
      :batch-action="batchModalAction"
      :batch-impact="batchImpact"
      :loading-batch-impact="loadingBatchImpact"
      :batch-processing="batchProcessing"
      :selected-count="selectedIds.length"
      :tg-sync-delete-enabled="tgSyncDeleteEnabled"
      @confirm-delete="confirmDelete"
      @confirm-batch="confirmBatch"
    />

    <!-- 通用确认弹窗（替代 window.confirm） -->
    <UModal v-model="confirmModalOpen" :ui="{ width: 'sm:max-w-md' }">
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-500" />
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
import type { AdminTokenItem, TokenListData } from '~/types/admin'
import type { ImpactData } from '~/components/admin/tokens/TokenBatchActions.vue'
import type { CreateTokenForm } from '~/components/admin/tokens/TokenCreateModal.vue'

definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

type TokenStatus = 'all' | 'active' | 'disabled' | 'expired'

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

// 列表状态
const status = ref<TokenStatus>('all')
const tgBind = ref('all')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const tokens = ref<AdminTokenItem[]>([])
const loading = ref(false)
const updatingId = ref<number | null>(null)
const searchQuery = ref('')

const selectToken = (id: number) => {
  navigateTo(`/admin/tokens/${id}`)
}

const totalPages = computed(() => {
  const pages = Math.ceil(total.value / pageSize.value)
  return Math.max(1, Number.isFinite(pages) ? pages : 1)
})

// 批量选择
const selectedIds = ref<number[]>([])
const isAllSelected = computed(() => tokens.value.length > 0 && selectedIds.value.length === tokens.value.length)
const isPartialSelected = computed(() => selectedIds.value.length > 0 && selectedIds.value.length < tokens.value.length)
const toggleSelect = (id: number) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}
const toggleSelectAll = () => {
  if (isAllSelected.value) selectedIds.value = []
  else selectedIds.value = tokens.value.map(t => t.id)
}
const clearSelection = () => { selectedIds.value = [] }

// 通用确认弹窗状态（替代 window.confirm）
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

// 创建Token
const createModalOpen = ref(false)
const creating = ref(false)
const createdToken = ref<string | null>(null)
const tokenCopied = ref(false)
const createForm = ref<CreateTokenForm>({
  description: '',
  expires_at: '',
  upload_limit: 100,
  is_active: true,
})

// 系统设置默认值
const tokenDefaults = ref({ upload_limit: 100, expires_days: 365 })
const tokenDefaultsLoaded = ref(false)
const tgSyncDeleteEnabled = ref(false)

const loadTokenDefaults = async () => {
  if (tokenDefaultsLoaded.value) return
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      credentials: 'include'
    })
    if (resp?.success) {
      const d = resp.data
      tokenDefaults.value = {
        upload_limit: Number(d.guest_token_max_upload_limit) || 1000,
        expires_days: Number(d.guest_token_max_expires_days) || 365,
      }
      tgSyncDeleteEnabled.value = d.tg_sync_delete_enabled === true || String(d.tg_sync_delete_enabled) === '1'
      tokenDefaultsLoaded.value = true
    }
  } catch { /* 静默失败，使用硬编码默认值 */ }
}

// 删除Token
const deleteModalOpen = ref(false)
const deleting = ref(false)
const deletingToken = ref<AdminTokenItem | null>(null)
const deleteImpact = ref<ImpactData | null>(null)
const loadingImpact = ref(false)

// 批量操作
const batchModalOpen = ref(false)
const batchModalAction = ref<'enable' | 'disable' | 'delete'>('enable')
const batchProcessing = ref(false)
const batchImpact = ref<ImpactData | null>(null)
const loadingBatchImpact = ref(false)

const loadTokens = async () => {
  loading.value = true
  try {
    const qs = new URLSearchParams({
      status: status.value,
      page: String(page.value),
      page_size: String(pageSize.value),
    })
    if (searchQuery.value.trim()) qs.set('search', searchQuery.value.trim())
    if (tgBind.value && tgBind.value !== 'all') qs.set('tg_bind', tgBind.value)
    const routeTgUserId = useRoute().query.tg_user_id
    if (routeTgUserId) qs.set('tg_user_id', String(routeTgUserId))

    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens?${qs.toString()}`, {
      credentials: 'include'
    })

    if (!resp?.success) throw new Error(resp?.error || '加载失败')

    const data = resp.data as TokenListData
    total.value = data.total ?? 0

    const computedPages = Math.max(1, Math.ceil((data.total ?? 0) / (data.page_size ?? pageSize.value)))
    if (page.value > computedPages) {
      page.value = computedPages
      return
    }

    tokens.value = data.items ?? []
    const currentIds = new Set(tokens.value.map(t => t.id))
    selectedIds.value = selectedIds.value.filter(id => currentIds.has(id))
  } catch (error: any) {
    console.error('加载Token列表失败:', error)
    notification.error('加载失败', error.data?.error || error.message || '无法加载Token列表')
  } finally {
    loading.value = false
  }
}

watch(status, async () => { page.value = 1; await loadTokens() })
watch(tgBind, async () => { page.value = 1; await loadTokens() })
watch(page, async () => { await loadTokens() })

const handleSearch = useDebounceFn(() => {
  page.value = 1
  loadTokens()
}, 400)

watch(searchQuery, handleSearch)

const openCreateModal = async () => {
  createdToken.value = null
  tokenCopied.value = false
  await loadTokenDefaults()

  const days = tokenDefaults.value.expires_days
  const expires = new Date(Date.now() + days * 86400000)
  const pad = (n: number) => String(n).padStart(2, '0')
  const defaultExpires = `${expires.getFullYear()}-${pad(expires.getMonth() + 1)}-${pad(expires.getDate())}T${pad(expires.getHours())}:${pad(expires.getMinutes())}`

  createForm.value = {
    description: '',
    expires_at: defaultExpires,
    upload_limit: tokenDefaults.value.upload_limit,
    is_active: true,
  }
  createModalOpen.value = true
}

const closeCreateModal = () => {
  if (createdToken.value && !tokenCopied.value) {
    showConfirm('Token 尚未复制', 'Token 尚未复制，关闭后将无法再次查看。确定要关闭吗？').then(ok => {
      if (ok) {
        createModalOpen.value = false
        createdToken.value = null
        tokenCopied.value = false
      }
    })
    return
  }
  createModalOpen.value = false
  createdToken.value = null
  tokenCopied.value = false
}

const createToken = async (form: CreateTokenForm) => {
  creating.value = true
  try {
    const payload = {
      description: form.description?.trim() || null,
      expires_at: form.expires_at?.trim() || null,
      upload_limit: Number(form.upload_limit),
      is_active: Boolean(form.is_active),
    }
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens`, {
      method: 'POST',
      credentials: 'include',
      body: payload
    })
    if (!resp?.success) throw new Error(resp?.error || '创建失败')
    createdToken.value = resp.data?.token || null
    tokenCopied.value = false
    notification.success('创建成功', 'Token 已生成，请及时复制保存')
    await loadTokens()
  } catch (error: any) {
    console.error('创建Token失败:', error)
    notification.error('创建失败', error.data?.error || error.message || '无法创建Token')
  } finally {
    creating.value = false
  }
}

const copyCreatedToken = async () => {
  if (!createdToken.value) return
  try {
    await navigator.clipboard.writeText(createdToken.value)
    tokenCopied.value = true
    notification.success('已复制', 'Token 已复制到剪贴板')
  } catch {
    notification.error('复制失败', '无法复制到剪贴板')
  }
}

const updateStatus = async (t: AdminTokenItem, next: boolean) => {
  if (t.is_expired || (t.expires_at && new Date(t.expires_at).getTime() < Date.now())) {
    notification.warning('无法操作', '已过期的Token无法修改状态')
    return
  }
  if (!next) {
    const ok = await showConfirm('禁用 Token', '确定要禁用该 Token 吗？禁用后该 Token 将无法使用。')
    if (!ok) return
  }
  const prev = t.is_active
  t.is_active = next
  updatingId.value = t.id
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${t.id}`, {
      method: 'PATCH',
      credentials: 'include',
      body: { is_active: next }
    })
    if (!resp?.success) throw new Error(resp?.error || '更新失败')
    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')
    if (status.value !== 'all') await loadTokens()
  } catch (error: any) {
    t.is_active = prev
    console.error('更新Token状态失败:', error)
    notification.error('更新失败', error.data?.error || error.message || '无法更新Token状态')
  } finally {
    updatingId.value = null
  }
}

const askDelete = async (t: AdminTokenItem) => {
  deletingToken.value = t
  deleteImpact.value = null
  deleteModalOpen.value = true
  loadingImpact.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${t.id}/impact`, {
      credentials: 'include'
    })
    if (resp?.success) deleteImpact.value = resp.data
  } catch { /* 静默失败 */ }
  finally { loadingImpact.value = false }
}

const confirmDelete = async (withImages: boolean) => {
  if (!deletingToken.value) return
  deleting.value = true
  try {
    const qs = withImages ? '?delete_images=true' : ''
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${deletingToken.value.id}${qs}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    if (resp && resp.success === false) throw new Error(resp?.error || '删除失败')
    notification.success('删除成功', withImages ? 'Token 及关联图片已删除' : 'Token 已删除')
    deleteModalOpen.value = false
    deletingToken.value = null
    deleteImpact.value = null
    await loadTokens()
  } catch (error: any) {
    console.error('删除Token失败:', error)
    notification.error('删除失败', error.data?.error || error.message || '无法删除Token')
  } finally {
    deleting.value = false
  }
}

const batchAction = async (action: 'enable' | 'disable' | 'delete') => {
  if (selectedIds.value.length === 0) return
  batchModalAction.value = action
  batchImpact.value = null
  batchModalOpen.value = true

  if (action === 'delete') {
    loadingBatchImpact.value = true
    try {
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/batch`, {
        method: 'POST',
        credentials: 'include',
        body: { action: 'impact', ids: selectedIds.value }
      })
      if (resp?.success) batchImpact.value = resp.data
    } catch { /* 静默失败 */ }
    finally { loadingBatchImpact.value = false }
  }
}

const confirmBatch = async (withImages: boolean) => {
  batchProcessing.value = true
  try {
    const body: Record<string, any> = { action: batchModalAction.value, ids: selectedIds.value }
    if (batchModalAction.value === 'delete' && withImages) body.delete_images = true
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/batch`, {
      method: 'POST',
      credentials: 'include',
      body,
    })
    if (!resp?.success) throw new Error(resp?.error || '操作失败')
    const d = resp.data
    const actionText = { enable: '批量启用', disable: '批量禁用', delete: '批量删除' }[batchModalAction.value]
    let detail = `成功 ${d.success_count} 个，失败 ${d.fail_count} 个`
    if (d.images_deleted != null) detail += `，删除图片 ${d.images_deleted} 张`
    notification.success(`${actionText}完成`, detail)
    batchModalOpen.value = false
    selectedIds.value = []
    await loadTokens()
  } catch (error: any) {
    console.error('批量操作失败:', error)
    notification.error('操作失败', error.data?.error || error.message || '批量操作失败')
  } finally {
    batchProcessing.value = false
  }
}

onMounted(() => {
  loadTokens()
  loadTokenDefaults()
})
</script>

<style scoped>
</style>