<template>
  <UCard>
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="font-semibold text-stone-900 dark:text-white">Token 管理</h3>
        <UButton
          v-if="canCreateToken"
          size="xs" color="primary" variant="soft" icon="heroicons:plus"
          :loading="generating" @click="handleGenerate"
        >
          生成新 Token
        </UButton>
      </div>
    </template>

    <!-- Token 列表 -->
    <div v-if="tokenStore.vaultItems.length === 0" class="text-center py-8 text-sm text-stone-400">
      暂无 Token，点击上方按钮生成
    </div>
    <template v-else>
      <!-- P2-b: 未绑定 Token 提示 -->
      <div v-if="hasUnboundTokens" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg mb-3">
        <div class="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300">
          <UIcon name="heroicons:information-circle" class="w-4 h-4 flex-shrink-0" />
          <span>检测到未绑定的 Token，绑定后可享受多 Token 额度管理</span>
        </div>
      </div>
      <div class="space-y-3">
      <div
        v-for="item in tokenStore.vaultItems"
        :key="item.id"
        class="group p-4 rounded-xl border transition-all cursor-pointer"
        :class="item.id === tokenStore.activeVaultId
          ? 'border-amber-300 dark:border-amber-600 bg-amber-50/50 dark:bg-amber-900/10'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
        @click="selectToken(item.id)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0 space-y-2">
            <!-- Token 值 -->
            <div class="flex items-center gap-2">
              <code class="text-sm font-mono text-stone-700 dark:text-stone-300 truncate">
                {{ revealedTokenId === item.id ? item.token : maskToken(item.token) }}
              </code>
              <UButton
                :icon="revealedTokenId === item.id ? 'heroicons:eye-slash' : 'heroicons:eye'"
                size="2xs" color="gray" variant="ghost"
                @click.stop="revealedTokenId = revealedTokenId === item.id ? null : item.id"
              />
              <UButton
                v-if="revealedTokenId === item.id"
                icon="heroicons:clipboard-document" size="2xs" color="gray" variant="ghost" title="复制"
                @click.stop="copyToken(item.token)"
              />
            </div>
            <!-- 信息行 -->
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-400">
              <span>{{ item.tokenInfo?.upload_count ?? '?' }} / {{ item.tokenInfo?.upload_limit ?? '?' }} 次上传</span>
              <span v-if="item.albumName">· {{ item.albumName }}</span>
              <span v-if="item.tokenInfo?.expires_at" class="inline-flex items-center gap-0.5">
                · <UIcon name="heroicons:clock" class="w-3 h-3" />
                {{ formatDate(item.tokenInfo.expires_at) }}
              </span>
              <template v-if="item.tokenInfo?.tg_user_id && tgAuth.isLoggedIn && tgAuth.user">
                <span class="inline-flex items-center gap-0.5 text-blue-500">
                  <UIcon name="heroicons:chat-bubble-left-right" class="w-3 h-3" />
                  {{ tgAuth.user.first_name || tgAuth.user.username }}
                </span>
              </template>
            </div>
            <!-- 配额进度条 -->
            <div v-if="item.tokenInfo" class="mt-2">
              <div class="h-1.5 bg-stone-100 dark:bg-neutral-700 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="getQuotaColor(item)"
                  :style="{ width: `${getQuotaPercent(item)}%` }"
                />
              </div>
            </div>
          </div>
          <!-- 状态标签 + 操作按钮 -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <UBadge v-if="item.id === tokenStore.activeVaultId" size="xs" color="amber" variant="soft">当前</UBadge>
            <UBadge v-if="item.tokenInfo?.tg_user_id" size="xs" color="blue" variant="soft"><UIcon name="heroicons:link" class="w-3 h-3 mr-0.5" />TG</UBadge>
            <UBadge v-else-if="tgAuth.isLoggedIn && publicSettings.tgBindEnabled" size="xs" color="orange" variant="outline">未绑定</UBadge>
            <div class="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <UButton
                v-if="tgAuth.isLoggedIn && publicSettings.tgBindEnabled && !item.tokenInfo?.tg_user_id"
                icon="heroicons:link" size="2xs" color="blue" variant="ghost" title="绑定 TG"
                :loading="bindingTokenId === item.id"
                @click.stop="bindTokenToTg(item)"
              />
              <UButton
                icon="heroicons:trash" size="2xs" color="red" variant="ghost"
                @click.stop="removeToken(item.id)"
              />
            </div>
          </div>
        </div>
      </div>
      </div>
    </template>

    <!-- 删除设置：用户自主选择是否同时删除存储文件 -->
    <div v-if="publicSettings.tgSyncDeleteEnabled" class="mt-4 p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 min-w-0">
          <UIcon name="heroicons:trash" class="w-4 h-4 text-stone-500 flex-shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-stone-700 dark:text-stone-300">删除时清除存储文件</p>
            <p class="text-xs text-stone-400 dark:text-stone-500">关闭后仅删除数据库记录，保留存储库中的文件</p>
          </div>
        </div>
        <UToggle v-model="deleteStorageEnabled" @update:model-value="saveDeleteStoragePref" />
      </div>
    </div>

    <!-- 添加已有 Token（可创建时显示） -->
    <template v-if="canCreateToken" #footer>
      <div class="space-y-2">
        <button
          class="text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
          @click="showAddInput = !showAddInput"
        >
          {{ showAddInput ? '收起' : '添加已有 Token' }}
        </button>
        <div v-if="showAddInput" class="flex gap-2">
          <UInput v-model="addTokenInput" placeholder="粘贴 Token" size="sm" class="flex-1" @keyup.enter="verifyAndAdd" />
          <UButton size="sm" color="primary" :loading="verifying" @click="verifyAndAdd">添加</UButton>
        </div>
      </div>
    </template>
  </UCard>

  <!-- 删除确认弹窗 -->
  <UModal v-model="deleteModalOpen">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold text-red-600">确认删除 Token</h3>
      </template>

      <div class="space-y-3">
        <p class="text-sm text-stone-700 dark:text-stone-300">
          删除后该 Token 将无法恢复。
        </p>
        <div v-if="deletingItem" class="text-xs text-stone-500 dark:text-stone-400">
          Token：<code class="font-mono">{{ maskToken(deletingItem.token) }}</code>
          <span v-if="deletingItem.albumName"> · {{ deletingItem.albumName }}</span>
        </div>
        <div v-if="deletingItem?.tokenInfo" class="text-xs text-stone-500 dark:text-stone-400">
          已上传 {{ deletingItem.tokenInfo.upload_count ?? 0 }} 张图片
        </div>

        <!-- 同时删除图片选项 -->
        <div v-if="deletingItem?.tokenInfo?.upload_count" class="p-3 border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/30 rounded-lg">
          <label class="flex items-start gap-2 cursor-pointer select-none">
            <input
              v-model="deleteWithImages"
              type="checkbox"
              class="mt-0.5 rounded border-red-400 dark:border-red-600 text-red-600 focus:ring-red-500"
            />
            <div>
              <span class="text-sm font-medium text-red-700 dark:text-red-300">
                {{ publicSettings.tgSyncDeleteEnabled ? '同时永久删除关联的所有图片' : '同时删除关联的所有图片记录' }}
              </span>
              <p class="text-xs text-red-500 dark:text-red-400 mt-0.5">
                {{ publicSettings.tgSyncDeleteEnabled
                  ? `将从数据库和存储中永久删除 ${deletingItem.tokenInfo.upload_count} 张图片，此操作不可恢复`
                  : `仅删除数据库中的 ${deletingItem.tokenInfo.upload_count} 张图片记录，存储文件将保留`
                }}
              </p>
            </div>
          </label>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">取消</UButton>
          <UButton color="red" :loading="deletingLoading" @click="confirmRemoveToken">
            {{ deleteWithImages ? (publicSettings.tgSyncDeleteEnabled ? '删除Token及图片' : '删除Token及记录') : '删除Token' }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<!-- PLACEHOLDER_SCRIPT -->
<script setup lang="ts">
import { maskToken } from '~/stores/token'

const toast = useLightToast()
const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const { publicSettings } = useGuestAuth()

const generating = ref(false)
const showAddInput = ref(false)
const addTokenInput = ref('')
const verifying = ref(false)
const bindingTokenId = ref<string | null>(null)
const revealedTokenId = ref<string | null>(null)

// 删除弹窗状态
const deleteModalOpen = ref(false)
const deletingItem = ref<any>(null)
const deleteWithImages = ref(false)
const deletingLoading = ref(false)

// 删除时是否同时清除存储文件（用户偏好，localStorage 持久化）
const deleteStorageEnabled = ref(true)
if (import.meta.client) {
  deleteStorageEnabled.value = localStorage.getItem('user_delete_storage') !== 'false'
}
const saveDeleteStoragePref = (val: boolean) => {
  if (import.meta.client) {
    localStorage.setItem('user_delete_storage', String(val))
  }
}

// P2-b: 检测未绑定的 Token
const hasUnboundTokens = computed(() =>
  tgAuth.isLoggedIn && publicSettings.value.tgBindEnabled &&
  tokenStore.vaultItems.some(i => !i.tokenInfo?.tg_user_id)
)

// TG 登录时可创建多个 Token（不超过上限），非 TG 登录时只允许一个
const canCreateToken = computed(() => {
  if (tgAuth.isLoggedIn && tgAuth.user) {
    return tgAuth.user.token_count < tgAuth.user.max_tokens
  }
  return tokenStore.vaultItems.length === 0
})

const formatDate = (d: string) => {
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return d }
}

const getQuotaPercent = (item: any) => {
  const count = item.tokenInfo?.upload_count ?? 0
  const limit = item.tokenInfo?.upload_limit ?? 1
  return Math.min(100, Math.round((count / limit) * 100))
}

const getQuotaColor = (item: any) => {
  const pct = getQuotaPercent(item)
  if (pct > 90) return 'bg-red-500'
  if (pct > 70) return 'bg-orange-500'
  return 'bg-gradient-to-r from-amber-400 to-orange-400'
}

const copyToken = async (token: string) => {
  try {
    await navigator.clipboard.writeText(token)
    toast.success('已复制')
  } catch { toast.error('复制失败') }
}

const selectToken = async (id: string) => {
  try { await tokenStore.setActiveTokenById(id, { verify: true }) }
  catch (e: any) { toast.error(e.message || '切换失败') }
}

const handleGenerate = async () => {
  generating.value = true
  try {
    await tokenStore.generateToken()
    toast.success('新 Token 已生成')
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
  } catch (e: any) { toast.error(e.message || '生成失败') }
  finally { generating.value = false }
}

const removeToken = (id: string) => {
  const item = tokenStore.vaultItems.find(i => i.id === id)
  if (!item) return
  deletingItem.value = item
  deleteWithImages.value = false
  deleteModalOpen.value = true
}

const confirmRemoveToken = async () => {
  if (!deletingItem.value) return
  deletingLoading.value = true
  try {
    await tokenStore.deleteTokenFromServer(deletingItem.value.id, { deleteImages: deleteWithImages.value })
    const msg = deleteWithImages.value ? 'Token 及图片已删除' : 'Token 已删除'
    toast.success(msg)
    deleteModalOpen.value = false
    deletingItem.value = null
    deleteWithImages.value = false
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
  } catch (e: any) { toast.error(e.message || '删除失败') }
  finally { deletingLoading.value = false }
}

const verifyAndAdd = async () => {
  const t = addTokenInput.value.trim()
  if (!t) return
  verifying.value = true
  try {
    await tokenStore.addTokenToVault(t, { makeActive: true, verify: true })
    toast.success('Token 已添加')
    addTokenInput.value = ''
    showAddInput.value = false
  } catch (e: any) { toast.error(e.message || 'Token 无效') }
  finally { verifying.value = false }
}

const bindTokenToTg = async (item: any) => {
  bindingTokenId.value = item.id
  try {
    const config = useRuntimeConfig()
    await $fetch(`${config.public.apiBase}/api/auth/token/bind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${item.token}` },
      credentials: 'include',
    })
    if (item.tokenInfo) item.tokenInfo.tg_user_id = true
    toast.success('绑定成功')
    tgAuth.checkSession()
  } catch (e: any) { toast.error(e.data?.error || e.message || '绑定失败') }
  finally { bindingTokenId.value = null }
}
</script>
