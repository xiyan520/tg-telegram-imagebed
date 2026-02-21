<template>
  <UCard class="shadow-lg">
    <!-- 有 Token：显示当前信息 -->
    <div v-if="store.hasToken" class="space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <UIcon name="heroicons:key" class="w-5 h-5 text-white" />
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-white truncate font-mono">{{ maskToken(store.token) }}</p>
            <p class="text-xs text-gray-500">
              已上传 {{ store.uploadCount }} 张<template v-if="store.uploadLimit"> / {{ store.uploadLimit }}</template>
            </p>
          </div>
        </div>
        <div class="flex gap-1 flex-shrink-0">
          <UButton size="xs" color="gray" variant="ghost" icon="heroicons:clipboard-document" title="复制 Token" @click="copyCurrentToken" />
          <UButton size="xs" :color="showInfo ? 'primary' : 'gray'" variant="ghost" icon="heroicons:information-circle" title="Token 详情" @click="showInfo = !showInfo" />
          <UButton size="xs" color="gray" variant="ghost" icon="heroicons:arrow-path" title="更换 Token" @click="openReplace" />
          <UButton size="xs" color="red" variant="ghost" icon="heroicons:x-mark" title="移除 Token" @click="removeCurrent" />
        </div>
      </div>

      <!-- Token 完整信息面板 -->
      <div v-if="showInfo && store.tokenInfo" class="grid grid-cols-2 md:grid-cols-3 gap-3 p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg text-sm">
        <div>
          <p class="text-xs text-gray-500 mb-0.5">上传额度</p>
          <p class="font-medium">{{ store.uploadCount }} / {{ store.uploadLimit || '∞' }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-0.5">剩余额度</p>
          <p class="font-medium">{{ store.uploadLimit ? store.remainingUploads : '无限制' }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-0.5">创建时间</p>
          <p class="font-medium">{{ formatDate(store.tokenInfo.created_at) }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-0.5">过期时间</p>
          <p class="font-medium" :class="store.isExpired ? 'text-red-500' : ''">
            {{ store.expiresAt ? formatDate(store.expiresAt) : '永不过期' }}
            <span v-if="store.isExpired" class="text-xs">(已过期)</span>
          </p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-0.5">最后使用</p>
          <p class="font-medium">{{ store.tokenInfo.last_used ? formatDate(store.tokenInfo.last_used) : '从未' }}</p>
        </div>
        <div v-if="store.tokenInfo.description">
          <p class="text-xs text-gray-500 mb-0.5">描述</p>
          <p class="font-medium truncate">{{ store.tokenInfo.description }}</p>
        </div>
      </div>
    </div>

    <!-- 无 Token：紧凑操作入口 -->
    <div v-else class="flex flex-col sm:flex-row items-center gap-3 py-2">
      <div class="flex items-center gap-2 text-gray-500 flex-1">
        <UIcon name="heroicons:key" class="w-5 h-5" />
        <span class="text-sm">未设置 Token</span>
      </div>
      <div class="flex gap-2">
        <UButton color="primary" size="sm" @click="openReplace">
          <template #leading><UIcon name="heroicons:plus" /></template>
          添加 Token
        </UButton>
        <UButton color="primary" variant="outline" size="sm" :loading="generating" @click="generateNew">
          <template #leading><UIcon name="heroicons:sparkles" /></template>
          生成新 Token
        </UButton>
      </div>
    </div>
  </UCard>

  <!-- 添加/更换 Token 弹窗 -->
  <UModal v-model="showReplace">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">{{ store.hasToken ? '更换' : '添加' }} Token</h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="showReplace = false" />
        </div>
      </template>
      <div class="space-y-4">
        <UInput v-model="tokenInput" placeholder="粘贴 Token：guest_... / admin_..." size="lg" :ui="{ base: 'font-mono text-sm' }" />
        <div class="flex gap-2">
          <UButton color="primary" :loading="adding" :disabled="!tokenInput.trim()" @click="verifyAndAdd">
            <template #leading><UIcon name="heroicons:check" /></template>
            验证并使用
          </UButton>
          <UButton color="primary" variant="outline" :loading="generating" @click="generateNew">
            <template #leading><UIcon name="heroicons:sparkles" /></template>
            生成新 Token
          </UButton>
        </div>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import { maskToken } from '~/stores/token'

const toast = useLightToast()
const store = useTokenStore()
const { copy: clipboardCopy } = useClipboardCopy()

const showInfo = ref(false)
const showReplace = ref(false)
const adding = ref(false)
const generating = ref(false)
const tokenInput = ref('')

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

const copyCurrentToken = () => {
  clipboardCopy(store.token, 'Token 已复制')
}

const openReplace = () => {
  tokenInput.value = ''
  showReplace.value = true
}

// 清理 vault 中非活跃的旧 token
const cleanupOldTokens = () => {
  const activeId = store.activeVaultId
  const toRemove = store.vaultItems.filter(i => i.id !== activeId).map(i => i.id)
  toRemove.forEach(id => store.removeTokenFromVault(id))
}

const verifyAndAdd = async () => {
  if (!tokenInput.value.trim()) return
  adding.value = true
  try {
    await store.addTokenToVault(tokenInput.value, { makeActive: true, verify: true })
    cleanupOldTokens()
    toast.success('Token 验证成功')
    showReplace.value = false
    tokenInput.value = ''
  } catch (e: any) {
    const existing = store.vaultItems.find(i => i.token === tokenInput.value.trim())
    if (existing && e?.tokenInvalid) store.removeTokenFromVault(existing.id)
    toast.error('Token 无效', e.message || '验证失败，请检查 Token 是否正确')
  } finally {
    adding.value = false
  }
}

const generateNew = async () => {
  generating.value = true
  try {
    await store.generateToken()
    cleanupOldTokens()
    toast.success('新 Token 已生成')
    showReplace.value = false
    tokenInput.value = ''
  } catch (e: any) {
    toast.error('生成失败', e.message)
  } finally {
    generating.value = false
  }
}

const removeCurrent = () => {
  if (!store.activeVaultId) return
  if (!confirm('确定要移除当前 Token 吗？')) return
  store.removeTokenFromVault(store.activeVaultId)
  showInfo.value = false
  toast.success('已移除')
}
</script>
