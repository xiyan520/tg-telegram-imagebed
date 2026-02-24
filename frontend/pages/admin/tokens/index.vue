<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">Token管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
          共 {{ total }} 个 Token
        </p>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadTokens"
        >
          刷新
        </UButton>
        <UButton
          icon="heroicons:plus"
          color="primary"
          @click="openCreateModal"
        >
          创建Token
        </UButton>
      </div>
    </div>

    <!-- 操作栏 -->
    <UCard>
      <div class="flex flex-col gap-4 md:flex-row md:items-center">
        <div class="flex items-center gap-2 flex-wrap">
          <UInput
            v-model="searchQuery"
            placeholder="搜索 Token / 描述 / TG用户名..."
            size="sm"
            class="w-48"
            @input="handleSearch"
          >
            <template #leading>
              <UIcon name="heroicons:magnifying-glass" class="w-4 h-4" />
            </template>
          </UInput>
          <span class="text-sm text-stone-600 dark:text-stone-400">状态</span>
          <USelect
            v-model="status"
            :options="statusOptions"
            size="sm"
          />
          <span class="text-sm text-stone-600 dark:text-stone-400">TG绑定</span>
          <USelect
            v-model="tgBind"
            :options="tgBindOptions"
            size="sm"
          />
        </div>

        <!-- 批量操作按钮 -->
        <div v-if="selectedIds.length > 0" class="flex items-center gap-2">
          <span class="text-sm text-amber-600 dark:text-amber-400 font-medium">
            已选 {{ selectedIds.length }} 项
          </span>
          <UButton size="sm" color="green" variant="soft" @click="batchAction('enable')">批量启用</UButton>
          <UButton size="sm" color="gray" variant="soft" @click="batchAction('disable')">批量禁用</UButton>
          <UButton size="sm" color="red" variant="soft" @click="batchAction('delete')">批量删除</UButton>
          <UButton size="sm" color="gray" variant="ghost" @click="clearSelection">取消选择</UButton>
        </div>
      </div>
    </UCard>

    <!-- Token 列表 -->
    <UCard>
          <div v-if="loading" class="flex flex-col justify-center items-center py-16">
            <div class="w-14 h-14 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p class="text-stone-600 dark:text-stone-400">加载中...</p>
          </div>

          <div v-else-if="tokens.length === 0" class="text-center py-16">
            <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <UIcon name="heroicons:key" class="w-10 h-10 text-stone-400" />
            </div>
            <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无Token</p>
            <p class="text-sm text-stone-600 dark:text-stone-400">点击右上角"创建Token"开始使用</p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="min-w-full text-sm">
              <thead>
                <tr class="text-left text-stone-600 dark:text-stone-300 border-b border-stone-200/60 dark:border-neutral-700/60">
                  <th class="py-3 pr-2 font-medium w-10">
                    <input
                      type="checkbox"
                      :checked="isAllSelected"
                      :indeterminate="isPartialSelected"
                      class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
                      @change="toggleSelectAll"
                    />
                  </th>
                  <th class="py-3 pr-4 font-medium">Token</th>
                  <th class="py-3 pr-4 font-medium">描述</th>
                  <th class="py-3 pr-4 font-medium">状态</th>
                  <th class="py-3 pr-4 font-medium hidden md:table-cell">上传</th>
                  <th class="py-3 pr-4 font-medium hidden lg:table-cell">TG 绑定</th>
                  <th class="py-3 pr-4 font-medium hidden lg:table-cell">创建时间</th>
                  <th class="py-3 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-200/50 dark:divide-neutral-700/50">
                <tr
                  v-for="t in tokens"
                  :key="t.id"
                  class="text-stone-800 dark:text-stone-100 cursor-pointer transition-colors"
                  :class="[
                    selectedIds.includes(t.id) ? 'bg-amber-50/50 dark:bg-amber-900/10' : 'hover:bg-stone-50 dark:hover:bg-neutral-800/50'
                  ]"
                  @click="selectToken(t.id)"
                >
                  <td class="py-3 pr-2" @click.stop>
                    <input
                      type="checkbox"
                      :checked="selectedIds.includes(t.id)"
                      class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
                      @change="toggleSelect(t.id)"
                    />
                  </td>
                  <td class="py-3 pr-4">
                    <code class="font-mono text-xs px-2 py-1 rounded bg-stone-100 dark:bg-neutral-800">
                      {{ t.token_masked }}
                    </code>
                  </td>
                  <td class="py-3 pr-4 max-w-[16rem]">
                    <span class="text-stone-700 dark:text-stone-300 truncate block text-xs">
                      {{ t.description?.trim() ? t.description : '--' }}
                    </span>
                  </td>
                  <td class="py-3 pr-4">
                    <UBadge
                      v-if="isExpired(t)"
                      color="amber"
                      variant="subtle"
                      size="xs"
                    >
                      已过期
                    </UBadge>
                    <UBadge
                      v-else
                      :color="t.is_active ? 'green' : 'gray'"
                      variant="subtle"
                      size="xs"
                    >
                      {{ t.is_active ? '启用' : '禁用' }}
                    </UBadge>
                  </td>
                  <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden md:table-cell">
                    {{ t.upload_count }} / {{ t.upload_limit ?? '∞' }}
                  </td>
                  <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden lg:table-cell">
                    <template v-if="t.tg_username || t.tg_first_name">
                      <UIcon name="heroicons:chat-bubble-left-right" class="w-3.5 h-3.5 inline" />
                      {{ t.tg_first_name || '' }}{{ t.tg_username ? ` @${t.tg_username}` : '' }}
                    </template>
                    <span v-else>--</span>
                  </td>
                  <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden lg:table-cell">
                    {{ formatDate(t.created_at) }}
                  </td>
                  <td class="py-3 text-right" @click.stop>
                    <div class="flex items-center justify-end gap-1">
                      <UButton
                        icon="heroicons:eye"
                        color="gray"
                        variant="ghost"
                        size="sm"
                        title="查看详情"
                        @click="navigateTo(`/admin/tokens/${t.id}`)"
                      />
                      <UToggle
                        :model-value="t.is_active"
                        size="sm"
                        :disabled="isExpired(t) || updatingId === t.id"
                        @update:model-value="(v) => updateStatus(t, v)"
                      />
                      <UButton
                        icon="heroicons:trash"
                        color="red"
                        variant="ghost"
                        size="sm"
                        @click="askDelete(t)"
                      />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 分页 -->
          <template #footer>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="text-xs text-stone-500 dark:text-stone-400">
                第 {{ page }} / {{ totalPages }} 页
              </div>
              <UPagination
                v-model="page"
                :total="totalPages"
              />
            </div>
          </template>
        </UCard>

    <!-- 创建Token模态框 -->
    <UModal v-model="createModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">创建Token</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">
                创建成功后仅显示一次完整Token，请及时复制保存
              </p>
            </div>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              @click="closeCreateModal"
            />
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="描述" hint="可选，用于备注Token用途">
            <UInput
              v-model="createForm.description"
              placeholder="例如：前端站点 / 服务器脚本"
            />
          </UFormGroup>

          <UFormGroup label="过期时间" hint="可选，不填写表示不过期">
            <UInput
              v-model="createForm.expires_at"
              type="datetime-local"
            />
          </UFormGroup>

          <UFormGroup label="上传限制" hint="达到限制后该Token将无法继续上传">
            <UInput
              v-model.number="createForm.upload_limit"
              type="number"
              min="0"
              max="1000000"
              placeholder="100"
            />
          </UFormGroup>

          <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <div>
              <p class="text-sm font-medium text-stone-900 dark:text-white">创建后启用</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">关闭则创建为禁用状态</p>
            </div>
            <UToggle v-model="createForm.is_active" size="lg" />
          </div>
          <div v-if="createdToken" class="p-4 border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 rounded-xl space-y-3">
            <div class="flex items-start gap-3">
              <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div class="flex-1">
                <p class="font-medium text-amber-900 dark:text-amber-200">完整Token（仅显示一次）</p>
                <p class="text-xs text-amber-700 dark:text-amber-300 mt-1">
                  请立即复制保存。关闭弹窗后将无法再次查看完整Token。
                </p>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <code class="flex-1 font-mono text-xs p-3 rounded bg-white/70 dark:bg-neutral-900/40 break-all">
                {{ createdToken }}
              </code>
              <UButton
                icon="heroicons:clipboard-document"
                color="primary"
                variant="soft"
                @click="copyCreatedToken"
              >
                复制
              </UButton>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton
              color="gray"
              variant="ghost"
              @click="closeCreateModal"
            >
              关闭
            </UButton>
            <UButton
              color="primary"
              :loading="creating"
              :disabled="creating"
              @click="createToken"
            >
              创建
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

        <div class="space-y-3">
          <p class="text-stone-700 dark:text-stone-300">
            确定要删除该Token吗？此操作不可恢复。
          </p>
          <div v-if="deletingToken" class="text-xs text-stone-600 dark:text-stone-400">
            <div>ID：<span class="font-mono">{{ deletingToken.id }}</span></div>
            <div>Token：<span class="font-mono">{{ deletingToken.token_masked }}</span></div>
          </div>
          <!-- 影响范围 -->
          <div v-if="deleteImpact" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm space-y-1">
            <p class="font-medium text-red-700 dark:text-red-300">删除影响范围：</p>
            <p class="text-red-600 dark:text-red-400">关联图片：{{ deleteImpact.upload_count }} 张（将解除关联）</p>
            <p class="text-red-600 dark:text-red-400">拥有画集：{{ deleteImpact.gallery_count }} 个（将解除关联）</p>
            <p v-if="deleteImpact.access_count > 0" class="text-red-600 dark:text-red-400">画集授权：{{ deleteImpact.access_count }} 条（将被清除）</p>
          </div>
          <div v-else-if="loadingImpact" class="flex items-center gap-2 text-sm text-stone-500">
            <div class="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            正在查询影响范围...
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">
              取消
            </UButton>
            <UButton color="red" :loading="deleting" :disabled="deleting" @click="confirmDelete">
              删除
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 批量操作确认模态框 -->
    <UModal v-model="batchModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold" :class="batchModalAction === 'delete' ? 'text-red-600' : 'text-stone-900 dark:text-white'">
            {{ batchModalTitle }}
          </h3>
        </template>

        <div class="space-y-3">
          <p class="text-stone-700 dark:text-stone-300">
            {{ batchModalDesc }}
          </p>
          <!-- 批量删除影响范围 -->
          <div v-if="batchModalAction === 'delete' && batchImpact" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm space-y-1">
            <p class="font-medium text-red-700 dark:text-red-300">删除影响范围汇总：</p>
            <p class="text-red-600 dark:text-red-400">关联图片：{{ batchImpact.upload_count }} 张</p>
            <p class="text-red-600 dark:text-red-400">拥有画集：{{ batchImpact.gallery_count }} 个</p>
            <p v-if="batchImpact.access_count > 0" class="text-red-600 dark:text-red-400">画集授权：{{ batchImpact.access_count }} 条</p>
          </div>
          <div v-else-if="batchModalAction === 'delete' && loadingBatchImpact" class="flex items-center gap-2 text-sm text-stone-500">
            <div class="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            正在查询影响范围...
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="batchModalOpen = false">取消</UButton>
            <UButton
              :color="batchModalAction === 'delete' ? 'red' : 'primary'"
              :loading="batchProcessing"
              :disabled="batchProcessing"
              @click="confirmBatch"
            >
              确认
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

type TokenStatus = 'all' | 'active' | 'disabled' | 'expired'

interface AdminTokenItem {
  id: number
  token_masked: string
  description?: string | null
  created_at: string
  expires_at?: string | null
  upload_count: number
  upload_limit?: number | null
  is_active: boolean
  is_expired?: boolean
  tg_user_id?: number | null
  tg_username?: string | null
  tg_first_name?: string | null
}

interface TokenListData {
  page: number
  page_size: number
  total: number
  items: AdminTokenItem[]
}

interface ImpactData {
  upload_count: number
  gallery_count: number
  access_count: number
  token_count?: number
}

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'disabled' },
  { label: '已过期', value: 'expired' },
]

const tgBindOptions = [
  { label: '全部', value: 'all' },
  { label: '已绑定', value: 'bound' },
  { label: '未绑定', value: 'unbound' },
]

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

// 创建Token
const createModalOpen = ref(false)
const creating = ref(false)
const createdToken = ref<string | null>(null)
const tokenCopied = ref(false)
const createForm = ref({
  description: '',
  expires_at: '',
  upload_limit: 100,
  is_active: true,
})

// 系统设置默认值
const tokenDefaults = ref({ upload_limit: 100, expires_days: 365 })
const tokenDefaultsLoaded = ref(false)

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

const batchModalTitle = computed(() => {
  const map = { enable: '批量启用', disable: '批量禁用', delete: '批量删除' }
  return map[batchModalAction.value] || '批量操作'
})

const batchModalDesc = computed(() => {
  const n = selectedIds.value.length
  const map = {
    enable: `确定要启用选中的 ${n} 个 Token 吗？`,
    disable: `确定要禁用选中的 ${n} 个 Token 吗？禁用后这些 Token 将无法使用。`,
    delete: `确定要删除选中的 ${n} 个 Token 吗？此操作不可恢复。`,
  }
  return map[batchModalAction.value] || ''
})
const isExpired = (t: AdminTokenItem) => {
  if (typeof t.is_expired === 'boolean') return t.is_expired
  if (!t.expires_at) return false
  return new Date(t.expires_at).getTime() < Date.now()
}

const formatDate = (dateString: string | null | undefined) => {
  if (!dateString) return '--'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

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
    // 支持从 URL query 传入 tg_user_id（从详情页跳转）
    const routeTgUserId = useRoute().query.tg_user_id
    if (routeTgUserId) qs.set('tg_user_id', String(routeTgUserId))

    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens?${qs.toString()}`, {
      credentials: 'include'
    })

    if (!resp?.success) {
      throw new Error(resp?.error || '加载失败')
    }

    const data = resp.data as TokenListData
    total.value = data.total ?? 0

    // 若当前页超出范围，回退并重新加载一次
    const computedPages = Math.max(1, Math.ceil((data.total ?? 0) / (data.page_size ?? pageSize.value)))
    if (page.value > computedPages) {
      page.value = computedPages
      return
    }

    tokens.value = data.items ?? []
    // 清除不在当前页的选中项
    const currentIds = new Set(tokens.value.map(t => t.id))
    selectedIds.value = selectedIds.value.filter(id => currentIds.has(id))
  } catch (error: any) {
    console.error('加载Token列表失败:', error)
    notification.error('加载失败', error.data?.error || error.message || '无法加载Token列表')
  } finally {
    loading.value = false
  }
}

watch(status, async () => {
  page.value = 1
  await loadTokens()
})

watch(tgBind, async () => {
  page.value = 1
  await loadTokens()
})

const handleSearch = useDebounceFn(() => {
  page.value = 1
  loadTokens()
}, 400)

watch(page, async () => {
  await loadTokens()
})
const openCreateModal = async () => {
  createdToken.value = null
  tokenCopied.value = false
  await loadTokenDefaults()

  // 根据系统设置计算默认过期时间
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
  // 创建保护：如果已创建 Token 但未复制，二次确认
  if (createdToken.value && !tokenCopied.value) {
    if (!window.confirm('Token 尚未复制，关闭后将无法再次查看。确定要关闭吗？')) {
      return
    }
  }
  createModalOpen.value = false
  createdToken.value = null
  tokenCopied.value = false
}

const createToken = async () => {
  creating.value = true
  try {
    const payload = {
      description: createForm.value.description?.trim() || null,
      expires_at: createForm.value.expires_at?.trim() || null,
      upload_limit: Number(createForm.value.upload_limit),
      is_active: Boolean(createForm.value.is_active),
    }

    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens`, {
      method: 'POST',
      credentials: 'include',
      body: payload
    })

    if (!resp?.success) {
      throw new Error(resp?.error || '创建失败')
    }

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
  } catch (error) {
    notification.error('复制失败', '无法复制到剪贴板')
  }
}
// 禁用保护
const updateStatus = async (t: AdminTokenItem, next: boolean) => {
  if (isExpired(t)) {
    notification.warning('无法操作', '已过期的Token无法修改状态')
    return
  }

  // 禁用时二次确认
  if (!next) {
    if (!window.confirm('确定要禁用该 Token 吗？禁用后该 Token 将无法使用。')) {
      return
    }
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

    if (!resp?.success) {
      throw new Error(resp?.error || '更新失败')
    }

    notification.success('更新成功', next ? 'Token 已启用' : 'Token 已禁用')

    // 如果当前有筛选条件，刷新列表以保持一致性
    if (status.value !== 'all') {
      await loadTokens()
    }
  } catch (error: any) {
    t.is_active = prev
    console.error('更新Token状态失败:', error)
    notification.error('更新失败', error.data?.error || error.message || '无法更新Token状态')
  } finally {
    updatingId.value = null
  }
}

// 删除增强：请求影响范围
const askDelete = async (t: AdminTokenItem) => {
  deletingToken.value = t
  deleteImpact.value = null
  deleteModalOpen.value = true

  // 异步加载影响范围
  loadingImpact.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${t.id}/impact`, {
      credentials: 'include'
    })
    if (resp?.success) {
      deleteImpact.value = resp.data
    }
  } catch { /* 静默失败 */ }
  finally { loadingImpact.value = false }
}

const confirmDelete = async () => {
  if (!deletingToken.value) return
  deleting.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/${deletingToken.value.id}`, {
      method: 'DELETE',
      credentials: 'include',
    })

    if (resp && resp.success === false) {
      throw new Error(resp?.error || '删除失败')
    }

    notification.success('删除成功', 'Token 已删除')
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
// 批量操作
const batchAction = async (action: 'enable' | 'disable' | 'delete') => {
  if (selectedIds.value.length === 0) return
  batchModalAction.value = action
  batchImpact.value = null
  batchModalOpen.value = true

  // 批量删除时异步加载影响范围
  if (action === 'delete') {
    loadingBatchImpact.value = true
    try {
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/batch`, {
        method: 'POST',
        credentials: 'include',
        body: { action: 'impact', ids: selectedIds.value }
      })
      if (resp?.success) {
        batchImpact.value = resp.data
      }
    } catch { /* 静默失败 */ }
    finally { loadingBatchImpact.value = false }
  }
}

const confirmBatch = async () => {
  batchProcessing.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/batch`, {
      method: 'POST',
      credentials: 'include',
      body: { action: batchModalAction.value, ids: selectedIds.value }
    })

    if (!resp?.success) {
      throw new Error(resp?.error || '操作失败')
    }

    const d = resp.data
    const actionText = batchModalTitle.value
    notification.success(`${actionText}完成`, `成功 ${d.success_count} 个，失败 ${d.fail_count} 个`)
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
})
</script>

<style scoped>
</style>
