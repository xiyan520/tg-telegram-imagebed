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
        class="p-4 rounded-xl border transition-all cursor-pointer"
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
              <span v-if="item.tokenInfo?.expires_at">· 到期 {{ formatDate(item.tokenInfo.expires_at) }}</span>
              <template v-if="item.tokenInfo?.tg_user_id && tgAuth.isLoggedIn && tgAuth.user">
                <span class="inline-flex items-center gap-0.5 text-blue-500">
                  <UIcon name="heroicons:chat-bubble-left-right" class="w-3 h-3" />
                  {{ tgAuth.user.first_name || tgAuth.user.username }}
                </span>
              </template>
            </div>
          </div>
          <!-- 操作按钮 -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <UBadge v-if="item.id === tokenStore.activeVaultId" size="xs" color="amber" variant="soft">当前</UBadge>
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
    </template>

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

const removeToken = async (id: string) => {
  if (!window.confirm('删除后该 Token 关联的上传记录将解除绑定，且无法恢复。确定删除？')) return
  try {
    await tokenStore.deleteTokenFromServer(id)
    toast.success('Token 已删除')
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
  } catch (e: any) { toast.error(e.message || '删除失败') }
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
