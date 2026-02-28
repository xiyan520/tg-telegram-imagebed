<template>
  <UModal v-model="isOpen" :ui="{ width: 'max-w-md' }" prevent-close>
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ title || '需要验证' }}
          </h3>
          <UButton
            v-if="allowClose"
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="handleClose"
          />
        </div>
        <p v-if="subtitle" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ subtitle }}
        </p>
      </template>

      <!-- Tab 切换 -->
      <UTabs v-model="activeTab" :items="tabs" class="w-full">
        <template #item="{ item }">
          <div class="p-4 space-y-4">
            <!-- 管理员登录 -->
            <template v-if="item.key === 'admin'">
              <UFormGroup label="用户名">
                <UInput
                  v-model="adminForm.username"
                  placeholder="请输入用户名"
                  icon="heroicons:user"
                  :disabled="loading"
                  @keyup.enter="handleAdminLogin"
                />
              </UFormGroup>
              <UFormGroup label="密码">
                <UInput
                  v-model="adminForm.password"
                  type="password"
                  placeholder="请输入密码"
                  icon="heroicons:lock-closed"
                  :disabled="loading"
                  @keyup.enter="handleAdminLogin"
                />
              </UFormGroup>
              <UButton
                block
                color="primary"
                :loading="loading"
                :disabled="!adminForm.username || !adminForm.password"
                @click="handleAdminLogin"
              >
                登录
              </UButton>
            </template>

            <!-- Token 验证 -->
            <template v-else-if="item.key === 'token'">
              <UFormGroup label="Token">
                <UInput
                  v-model="tokenForm.token"
                  placeholder="请输入或粘贴 Token"
                  icon="heroicons:key"
                  :disabled="loading"
                  @keyup.enter="handleTokenVerify"
                />
              </UFormGroup>

              <!-- Token Vault 选择 -->
              <div v-if="vaultItems.length > 0" class="space-y-2">
                <p class="text-sm text-gray-500 dark:text-gray-400">或从已保存的 Token 中选择：</p>
                <div class="max-h-32 overflow-y-auto space-y-1">
                  <button
                    v-for="item in vaultItems"
                    :key="item.id"
                    class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors"
                    :class="tokenForm.token === item.token
                      ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800'"
                    @click="selectVaultToken(item)"
                  >
                    <span class="font-medium">{{ item.albumName || '未命名相册' }}</span>
                    <span class="ml-2 text-gray-400 text-xs">{{ maskToken(item.token) }}</span>
                  </button>
                </div>
              </div>

              <UButton
                block
                color="primary"
                :loading="loading"
                :disabled="!tokenForm.token"
                @click="handleTokenVerify"
              >
                验证 Token
              </UButton>
            </template>
          </div>
        </template>
      </UTabs>

      <!-- 错误提示 -->
      <UAlert
        v-if="error"
        color="red"
        icon="heroicons:exclamation-circle"
        :description="error"
        class="mt-4"
      />
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import type { TokenVaultItem } from '~/types/tokenVault'
import { maskToken } from '~/stores/token'

interface Props {
  modelValue?: boolean
  title?: string
  subtitle?: string
  allowClose?: boolean
  mode?: 'admin' | 'token' | 'both'
  galleryShareToken?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  allowClose: true,
  mode: 'both'
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'success': [type: 'admin' | 'token']
  'close': []
}>()

const config = useRuntimeConfig()
const authStore = useAuthStore()
const tokenStore = useTokenStore()

const isOpen = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const loading = ref(false)
const error = ref('')
const activeTab = ref(0)

const adminForm = reactive({ username: '', password: '' })
const tokenForm = reactive({ token: '' })

const tabs = computed(() => {
  const items = []
  if (props.mode === 'admin' || props.mode === 'both') {
    items.push({ key: 'admin', label: '管理员登录' })
  }
  if (props.mode === 'token' || props.mode === 'both') {
    items.push({ key: 'token', label: 'Token 验证' })
  }
  return items
})

const vaultItems = computed(() => tokenStore.vaultItems)

const selectVaultToken = (item: TokenVaultItem) => {
  tokenForm.token = item.token
}

const handleAdminLogin = async () => {
  if (!adminForm.username || !adminForm.password) return

  loading.value = true
  error.value = ''

  try {
    await authStore.login(adminForm.username, adminForm.password)
    isOpen.value = false
    emit('success', 'admin')
  } catch (e: any) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

const handleTokenVerify = async () => {
  if (!tokenForm.token) return

  loading.value = true
  error.value = ''

  try {
    // 如果有画集分享 token，先尝试解锁画集
    if (props.galleryShareToken) {
      const response = await $fetch<any>(`${config.public.apiBase}/api/shared/galleries/${props.galleryShareToken}/unlock-token`, {
        method: 'POST',
        body: { token: tokenForm.token },
        credentials: 'include'
      })
      if (!response.success) {
        throw new Error(response.error || '验证失败')
      }
    } else {
      // 普通 Token 验证
      const response = await $fetch<any>(`${config.public.apiBase}/api/auth/token/verify`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokenForm.token}` },
        credentials: 'include'
      })
      if (!response.success || !response.valid) {
        throw new Error(response.reason || 'Token 无效')
      }
    }

    // 添加到 vault
    await tokenStore.addTokenToVault(tokenForm.token, { makeActive: true, verify: true })

    isOpen.value = false
    emit('success', 'token')
  } catch (e: any) {
    error.value = e.data?.error || e.message || '验证失败'
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  isOpen.value = false
  emit('close')
}

// 重置表单
watch(isOpen, (open) => {
  if (open) {
    adminForm.username = ''
    adminForm.password = ''
    tokenForm.token = ''
    error.value = ''
    // 根据 mode 设置默认 tab
    activeTab.value = props.mode === 'admin' ? 0 : (props.mode === 'token' ? 0 : 0)
  }
})

defineExpose({
  open: () => { isOpen.value = true },
  close: () => { isOpen.value = false }
})
</script>
