<template>
  <UCard class="shadow-lg">
    <div class="flex flex-col md:flex-row md:items-end gap-4">
      <div class="flex-1">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          当前相册
        </label>
        <USelect
          v-model="selectedId"
          :options="options"
          placeholder="选择或添加一个Token…"
          size="lg"
          :disabled="options.length === 0"
        />
      </div>

      <div class="flex gap-2">
        <UButton color="primary" size="lg" @click="openManage = true">
          <template #leading>
            <UIcon name="heroicons:key" />
          </template>
          管理 Token
        </UButton>
      </div>
    </div>
  </UCard>

  <!-- Token Vault 管理弹窗 -->
  <UModal v-model="openManage" :ui="{ width: 'sm:max-w-2xl' }">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Token Vault</h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="openManage = false" />
        </div>
      </template>

      <div class="space-y-6">
        <!-- 添加新Token -->
        <div class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg space-y-4">
          <h4 class="text-sm font-semibold text-stone-700 dark:text-stone-300">添加 Token</h4>
          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-2">粘贴 Token</label>
              <UInput v-model="tokenInput" placeholder="guest_... / admin_..." size="lg" :ui="{ base: 'font-mono text-sm' }" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-2">相册名称（可空）</label>
              <UInput v-model="albumNameInput" placeholder="例如：工作素材" size="lg" />
            </div>
          </div>

          <div class="flex gap-2">
            <UButton color="primary" :loading="adding" @click="verifyAndAdd">
              <template #leading>
                <UIcon name="heroicons:plus" />
              </template>
              验证并加入
            </UButton>
            <UButton color="primary" variant="outline" :loading="generating" @click="generateNew">
              <template #leading>
                <UIcon name="heroicons:sparkles" />
              </template>
              生成新 Token
            </UButton>
          </div>
        </div>

        <!-- 已保存的Token列表 -->
        <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 class="text-sm font-semibold mb-3">已保存的 Token ({{ vaultItems.length }})</h4>
          <div v-if="vaultItems.length === 0" class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
            还没有保存任何 Token，请添加或生成一个。
          </div>
          <div v-else class="space-y-2 max-h-64 overflow-y-auto">
            <div
              v-for="item in vaultItems"
              :key="item.id"
              class="flex items-center justify-between p-3 rounded-lg border transition-colors"
              :class="item.id === store.activeVaultId
                ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-600'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <p class="font-medium truncate">
                    {{ (item.albumName || '').trim() || '未命名相册' }}
                  </p>
                  <span v-if="item.id === store.activeVaultId" class="px-2 py-0.5 text-xs bg-amber-500 text-white rounded-full">
                    当前
                  </span>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
                  {{ mask(item.token) }}
                </p>
                <p v-if="item.tokenInfo" class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  已上传 {{ item.tokenInfo.upload_count }} 张
                </p>
              </div>
              <div class="flex gap-2 ml-4">
                <UButton
                  v-if="item.id !== store.activeVaultId"
                  size="sm"
                  color="primary"
                  variant="soft"
                  @click="activate(item.id)"
                >
                  切换
                </UButton>
                <UButton
                  size="sm"
                  color="gray"
                  variant="outline"
                  icon="heroicons:clipboard-document"
                  @click="copyToken(item.token)"
                />
                <UButton
                  size="sm"
                  color="red"
                  variant="outline"
                  icon="heroicons:trash"
                  @click="remove(item.id)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const toast = useLightToast()
const store = useGuestTokenStore()

const openManage = ref(false)
const adding = ref(false)
const generating = ref(false)
const tokenInput = ref('')
const albumNameInput = ref('')

const vaultItems = computed(() => store.vaultItems)
const options = computed(() => store.vaultItems.map(i => ({
  label: `${(i.albumName || '').trim() || '未命名相册'} (${mask(i.token)})`,
  value: i.id
})))

const selectedId = computed<string | null>({
  get: () => store.activeVaultId,
  set: async (id) => {
    if (!id) return
    try {
      await store.setActiveTokenById(id, { verify: true })
      toast.success('已切换相册')
    } catch (e: any) {
      toast.error('切换失败', e.message)
    }
  }
})

const mask = (t: string) => {
  const s = (t || '').trim()
  if (s.length <= 12) return s
  return `${s.slice(0, 8)}…${s.slice(-4)}`
}

const clearInputs = () => {
  tokenInput.value = ''
  albumNameInput.value = ''
}

const verifyAndAdd = async () => {
  if (!tokenInput.value.trim()) {
    toast.error('请输入 Token')
    return
  }
  adding.value = true
  try {
    await store.addTokenToVault(tokenInput.value, {
      albumName: albumNameInput.value,
      makeActive: true,
      verify: true
    })
    toast.success('Token 已加入并验证成功')
    clearInputs()
  } catch (e: any) {
    toast.error('加入失败', e.message)
  } finally {
    adding.value = false
  }
}

const generateNew = async () => {
  generating.value = true
  try {
    await store.generateToken({ albumName: albumNameInput.value || '' })
    toast.success('新 Token 已生成')
    clearInputs()
  } catch (e: any) {
    toast.error('生成失败', e.message)
  } finally {
    generating.value = false
  }
}

const activate = async (id: string) => {
  try {
    await store.setActiveTokenById(id, { verify: true })
    toast.success('已切换相册')
  } catch (e: any) {
    toast.error('切换失败', e.message)
  }
}

const copyToken = async (token: string) => {
  try {
    await navigator.clipboard.writeText(token)
    toast.success('Token 已复制')
  } catch {
    toast.error('复制失败')
  }
}

const remove = async (id: string) => {
  if (!confirm('确定要移除这个 Token 吗？移除后可重新添加。')) return
  store.removeTokenFromVault(id)
  toast.success('已移除')
}
</script>
