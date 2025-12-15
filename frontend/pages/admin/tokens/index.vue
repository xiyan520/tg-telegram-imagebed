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
        <div class="flex items-center gap-2">
          <span class="text-sm text-stone-600 dark:text-stone-400">状态筛选</span>
          <USelect
            v-model="status"
            :options="statusOptions"
            size="sm"
          />
        </div>

        <div class="md:ml-auto text-xs text-stone-500 dark:text-stone-400">
          固定按创建时间倒序排序
        </div>
      </div>
    </UCard>

    <!-- 列表表格 -->
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
              <th class="py-3 pr-4 font-medium">ID</th>
              <th class="py-3 pr-4 font-medium">Token</th>
              <th class="py-3 pr-4 font-medium">描述</th>
              <th class="py-3 pr-4 font-medium whitespace-nowrap">创建时间</th>
              <th class="py-3 pr-4 font-medium whitespace-nowrap">过期时间</th>
              <th class="py-3 pr-4 font-medium whitespace-nowrap">上传次数/限制</th>
              <th class="py-3 pr-4 font-medium">状态</th>
              <th class="py-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-200/50 dark:divide-neutral-700/50">
            <tr
              v-for="t in tokens"
              :key="t.id"
              class="text-stone-800 dark:text-stone-100"
            >
              <td class="py-3 pr-4">
                <span class="font-mono text-xs text-stone-700 dark:text-stone-300">{{ t.id }}</span>
              </td>
              <td class="py-3 pr-4">
                <code class="font-mono text-xs px-2 py-1 rounded bg-stone-100 dark:bg-neutral-800">
                  {{ t.token_masked }}
                </code>
              </td>
              <td class="py-3 pr-4 max-w-[18rem]">
                <span class="text-stone-700 dark:text-stone-300 truncate block">
                  {{ t.description?.trim() ? t.description : '--' }}
                </span>
              </td>
              <td class="py-3 pr-4 whitespace-nowrap text-stone-700 dark:text-stone-300">
                {{ formatDate(t.created_at) }}
              </td>
              <td class="py-3 pr-4 whitespace-nowrap text-stone-700 dark:text-stone-300">
                {{ t.expires_at ? formatDate(t.expires_at) : '--' }}
              </td>
              <td class="py-3 pr-4 whitespace-nowrap">
                <span class="text-stone-700 dark:text-stone-300">
                  {{ t.upload_count }} / {{ t.upload_limit ?? '--' }}
                </span>
              </td>
              <td class="py-3 pr-4">
                <div class="flex items-center gap-3">
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

                  <div class="flex items-center gap-2">
                    <UToggle
                      :model-value="t.is_active"
                      size="md"
                      :disabled="isExpired(t) || updatingId === t.id"
                      @update:model-value="(v) => updateStatus(t, v)"
                    />
                    <span v-if="updatingId === t.id" class="text-xs text-stone-500 dark:text-stone-400">
                      更新中...
                    </span>
                  </div>
                </div>
              </td>
              <td class="py-3 text-right">
                <UButton
                  icon="heroicons:trash"
                  color="red"
                  variant="ghost"
                  size="sm"
                  @click="askDelete(t)"
                />
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

        <div class="space-y-2">
          <p class="text-stone-700 dark:text-stone-300">
            确定要删除该Token吗？此操作不可恢复。
          </p>
          <div v-if="deletingToken" class="text-xs text-stone-600 dark:text-stone-400">
            <div>ID：<span class="font-mono">{{ deletingToken.id }}</span></div>
            <div>Token：<span class="font-mono">{{ deletingToken.token_masked }}</span></div>
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
}

interface TokenListData {
  page: number
  page_size: number
  total: number
  items: AdminTokenItem[]
}

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'disabled' },
  { label: '已过期', value: 'expired' },
]

// 列表状态
const status = ref<TokenStatus>('all')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const tokens = ref<AdminTokenItem[]>([])
const loading = ref(false)
const updatingId = ref<number | null>(null)

const totalPages = computed(() => {
  const pages = Math.ceil(total.value / pageSize.value)
  return Math.max(1, Number.isFinite(pages) ? pages : 1)
})

// 创建Token
const createModalOpen = ref(false)
const creating = ref(false)
const createdToken = ref<string | null>(null)
const createForm = ref({
  description: '',
  expires_at: '',
  upload_limit: 100,
  is_active: true,
})

// 删除Token
const deleteModalOpen = ref(false)
const deleting = ref(false)
const deletingToken = ref<AdminTokenItem | null>(null)

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

watch(page, async () => {
  await loadTokens()
})

const openCreateModal = () => {
  createdToken.value = null
  createForm.value = {
    description: '',
    expires_at: '',
    upload_limit: 100,
    is_active: true,
  }
  createModalOpen.value = true
}

const closeCreateModal = () => {
  createModalOpen.value = false
  createdToken.value = null
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
    notification.success('已复制', 'Token 已复制到剪贴板')
  } catch (error) {
    notification.error('复制失败', '无法复制到剪贴板')
  }
}

const updateStatus = async (t: AdminTokenItem, next: boolean) => {
  if (isExpired(t)) {
    notification.warning('无法操作', '已过期的Token无法修改状态')
    return
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

const askDelete = (t: AdminTokenItem) => {
  deletingToken.value = t
  deleteModalOpen.value = true
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
    await loadTokens()
  } catch (error: any) {
    console.error('删除Token失败:', error)
    notification.error('删除失败', error.data?.error || error.message || '无法删除Token')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadTokens()
})
</script>

<style scoped>
</style>
