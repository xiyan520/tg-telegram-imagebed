<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">系统设置</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">配置游客模式、上传限制和 Token 管理</p>
      </div>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="outline"
        :loading="loading"
        @click="loadSettings"
      >
        刷新
      </UButton>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !settings" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <!-- 游客上传策略 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:user-group" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">游客上传策略</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">控制非管理员用户的上传权限</p>
            </div>
          </div>
        </template>

        <div class="space-y-6">
          <!-- 上传策略选择 -->
          <div>
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">上传策略</label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                v-for="option in policyOptions.guest_upload_policy"
                :key="option.value"
                class="relative p-4 rounded-xl border-2 cursor-pointer transition-all"
                :class="[
                  settings.guest_upload_policy === option.value
                    ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20'
                    : 'border-stone-200 dark:border-neutral-700 hover:border-stone-300 dark:hover:border-neutral-600'
                ]"
                @click="settings.guest_upload_policy = option.value"
              >
                <div class="flex items-start gap-3">
                  <div
                    class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5"
                    :class="[
                      settings.guest_upload_policy === option.value
                        ? 'border-amber-500 bg-amber-500'
                        : 'border-stone-300 dark:border-neutral-600'
                    ]"
                  >
                    <UIcon
                      v-if="settings.guest_upload_policy === option.value"
                      name="heroicons:check"
                      class="w-3 h-3 text-white"
                    />
                  </div>
                  <div>
                    <p class="font-medium text-stone-900 dark:text-white">{{ option.label }}</p>
                    <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">{{ option.description }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Token 生成开关 -->
          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">允许游客生成 Token</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                关闭后，游客无法自行生成新的上传 Token
              </p>
            </div>
            <UToggle
              v-model="settings.guest_token_generation_enabled"
              size="lg"
              :disabled="settings.guest_upload_policy === 'admin_only'"
            />
          </div>

          <!-- 已有 Token 处理策略 -->
          <div v-if="settings.guest_upload_policy !== 'open'">
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">
              已有 Token 处理策略
            </label>
            <USelect
              v-model="settings.guest_existing_tokens_policy"
              :options="policyOptions.guest_existing_tokens_policy"
              option-attribute="label"
              value-attribute="value"
            />
            <p class="text-xs text-stone-500 dark:text-stone-400 mt-2">
              当切换到限制模式时，如何处理已经生成的 Token
            </p>
          </div>
        </div>
      </UCard>

      <!-- Token 限制设置 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:key" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Token 限制</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置游客 Token 的上传数量和有效期限制</p>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <UFormGroup label="单个 Token 最大上传数">
            <UInput
              v-model.number="settings.guest_token_max_upload_limit"
              type="number"
              min="1"
              max="1000000"
              placeholder="1000"
            />
            <template #hint>
              <span class="text-xs text-stone-500">游客生成的 Token 最多可上传的图片数量</span>
            </template>
          </UFormGroup>

          <UFormGroup label="Token 最大有效期（天）">
            <UInput
              v-model.number="settings.guest_token_max_expires_days"
              type="number"
              min="1"
              max="36500"
              placeholder="365"
            />
            <template #hint>
              <span class="text-xs text-stone-500">游客生成的 Token 最长有效天数</span>
            </template>
          </UFormGroup>
        </div>
      </UCard>

      <!-- 上传限制 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">上传限制</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置文件大小和每日上传数量限制</p>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <UFormGroup label="最大文件大小（MB）">
            <UInput
              v-model.number="settings.max_file_size_mb"
              type="number"
              min="1"
              max="100"
              placeholder="20"
            />
            <template #hint>
              <span class="text-xs text-stone-500">单个文件的最大上传大小，范围 1-100 MB</span>
            </template>
          </UFormGroup>

          <UFormGroup label="每日上传限制">
            <UInput
              v-model.number="settings.daily_upload_limit"
              type="number"
              min="0"
              max="1000000"
              placeholder="0"
            />
            <template #hint>
              <span class="text-xs text-stone-500">每日最大上传数量，0 表示不限制</span>
            </template>
          </UFormGroup>
        </div>
      </UCard>

      <!-- Token 管理 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:shield-exclamation" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Token 管理</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">批量禁用已生成的 Token</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div class="flex items-start gap-3">
              <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p class="font-medium text-red-800 dark:text-red-200">危险操作</p>
                <p class="text-sm text-red-600 dark:text-red-300 mt-1">
                  禁用 Token 后，使用这些 Token 的用户将无法继续上传图片。此操作不可撤销。
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
            <UButton
              color="red"
              variant="soft"
              :loading="revokingTokens"
              @click="revokeTokens('guest')"
            >
              <template #leading>
                <UIcon name="heroicons:user-minus" />
              </template>
              禁用所有游客 Token
            </UButton>
            <UButton
              color="red"
              variant="outline"
              :loading="revokingTokens"
              @click="revokeTokens('all')"
            >
              <template #leading>
                <UIcon name="heroicons:no-symbol" />
              </template>
              禁用所有 Token
            </UButton>
          </div>
        </div>
      </UCard>

      <!-- 保存按钮 -->
      <div class="flex justify-end gap-3 pt-4">
        <UButton color="gray" variant="outline" @click="resetSettings">
          重置
        </UButton>
        <UButton color="primary" :loading="saving" @click="saveSettings">
          <template #leading>
            <UIcon name="heroicons:check" />
          </template>
          保存设置
        </UButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

// 状态
const loading = ref(false)
const saving = ref(false)
const revokingTokens = ref(false)

// 设置数据
const settings = ref({
  guest_upload_policy: 'open',
  guest_token_generation_enabled: true,
  guest_existing_tokens_policy: 'keep',
  guest_token_max_upload_limit: 1000,
  guest_token_max_expires_days: 365,
  max_file_size_mb: 20,
  daily_upload_limit: 0,
})

// 原始设置（用于重置）
const originalSettings = ref<typeof settings.value | null>(null)

// 策略选项
const policyOptions = ref({
  guest_upload_policy: [
    { value: 'open', label: '完全开放', description: '允许匿名上传和 Token 上传' },
    { value: 'token_only', label: '仅 Token', description: '禁止匿名上传，允许 Token 上传' },
    { value: 'admin_only', label: '仅管理员', description: '禁止所有游客上传' },
  ],
  guest_existing_tokens_policy: [
    { value: 'keep', label: '保留有效', description: '关闭游客模式后，已有 Token 仍可使用' },
    { value: 'disable_guest', label: '禁用游客 Token', description: '关闭时禁用所有游客生成的 Token' },
    { value: 'disable_all', label: '禁用所有 Token', description: '关闭时禁用所有 Token' },
  ],
})

// 加载设置
const loadSettings = async () => {
  loading.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      credentials: 'include'
    })

    if (response.success) {
      settings.value = { ...response.data }
      originalSettings.value = { ...response.data }

      if (response.policy_options) {
        policyOptions.value = response.policy_options
      }
    }
  } catch (error: any) {
    console.error('加载设置失败:', error)
    notification.error('加载失败', error.data?.error || '无法加载系统设置')
  } finally {
    loading.value = false
  }
}

// 保存设置
const saveSettings = async () => {
  saving.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      method: 'PUT',
      credentials: 'include',
      body: {
        ...settings.value,
        apply_token_policy: settings.value.guest_upload_policy !== 'open'
      }
    })

    if (response.success) {
      notification.success('保存成功', response.message || '系统设置已更新')
      originalSettings.value = { ...settings.value }

      if (response.tokens_disabled > 0) {
        notification.info('Token 已处理', `已禁用 ${response.tokens_disabled} 个 Token`)
      }
    }
  } catch (error: any) {
    console.error('保存设置失败:', error)
    notification.error('保存失败', error.data?.error || '无法保存系统设置')
  } finally {
    saving.value = false
  }
}

// 重置设置
const resetSettings = () => {
  if (originalSettings.value) {
    settings.value = { ...originalSettings.value }
    notification.info('已重置', '设置已恢复到上次保存的状态')
  }
}

// 批量禁用 Token
const revokeTokens = async (type: 'guest' | 'all') => {
  const confirmMessage = type === 'all'
    ? '确定要禁用所有 Token 吗？此操作不可撤销。'
    : '确定要禁用所有游客 Token 吗？此操作不可撤销。'

  if (!confirm(confirmMessage)) {
    return
  }

  revokingTokens.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/revoke`, {
      method: 'POST',
      credentials: 'include',
      body: { type }
    })

    if (response.success) {
      notification.success('操作成功', response.message)
    }
  } catch (error: any) {
    console.error('禁用 Token 失败:', error)
    notification.error('操作失败', error.data?.error || '无法禁用 Token')
  } finally {
    revokingTokens.value = false
  }
}

// 页面加载
onMounted(() => {
  loadSettings()
})
</script>
