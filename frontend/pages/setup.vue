<template>
  <div class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-emerald-400/20 to-teal-500/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-cyan-400/20 to-blue-500/20 rounded-full blur-3xl"></div>
    </div>

    <!-- 设置卡片 -->
    <div class="w-full max-w-md relative">
      <UCard class="shadow-2xl backdrop-blur-sm bg-white/95 dark:bg-gray-900/95 border border-gray-200 dark:border-gray-800">
        <!-- 头部 -->
        <div class="text-center space-y-6 mb-8">
          <div class="flex justify-center">
            <div class="relative">
              <div class="w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center shadow-lg transform hover:scale-105 transition-transform">
                <UIcon name="heroicons:cog-6-tooth" class="w-10 h-10 text-white" />
              </div>
              <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-blue-500 rounded-full border-4 border-white dark:border-gray-900 flex items-center justify-center">
                <UIcon name="heroicons:sparkles" class="w-3 h-3 text-white" />
              </div>
            </div>
          </div>

          <div>
            <h1 class="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent mb-2">
              初始化设置
            </h1>
            <p class="text-gray-600 dark:text-gray-400 text-sm">
              首次使用，请设置管理员账号
            </p>
          </div>
        </div>

        <!-- 设置表单 -->
        <UForm :state="setupForm" @submit="handleSetup" class="space-y-5">
          <!-- 用户名 -->
          <UFormGroup label="管理员用户名" name="username" required>
            <UInput
              v-model="setupForm.username"
              placeholder="至少3个字符"
              size="xl"
            >
              <template #leading>
                <UIcon name="heroicons:user-circle" class="w-5 h-5 text-gray-400" />
              </template>
            </UInput>
          </UFormGroup>

          <!-- 密码 -->
          <UFormGroup label="密码" name="password" required>
            <UInput
              v-model="setupForm.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="至少6个字符"
              size="xl"
            >
              <template #leading>
                <UIcon name="heroicons:key" class="w-5 h-5 text-gray-400" />
              </template>
              <template #trailing>
                <UButton
                  :icon="showPassword ? 'heroicons:eye-slash' : 'heroicons:eye'"
                  color="gray"
                  variant="ghost"
                  size="xs"
                  @click="showPassword = !showPassword"
                />
              </template>
            </UInput>
          </UFormGroup>

          <!-- 确认密码 -->
          <UFormGroup label="确认密码" name="confirmPassword" required>
            <UInput
              v-model="setupForm.confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              placeholder="再次输入密码"
              size="xl"
            >
              <template #leading>
                <UIcon name="heroicons:key" class="w-5 h-5 text-gray-400" />
              </template>
            </UInput>
          </UFormGroup>

          <!-- 错误提示 -->
          <div v-if="errorMsg" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <p class="text-sm text-red-700 dark:text-red-300">{{ errorMsg }}</p>
          </div>

          <!-- 提交按钮 -->
          <UButton
            type="submit"
            color="primary"
            size="xl"
            block
            :loading="loading"
            class="shadow-lg hover:shadow-xl transition-shadow"
          >
            <template #leading>
              <UIcon name="heroicons:check-circle" />
            </template>
            {{ loading ? '设置中...' : '完成设置' }}
          </UButton>
        </UForm>

        <!-- 提示 -->
        <div class="mt-6 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <div class="flex items-start gap-3">
            <UIcon name="heroicons:information-circle" class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div class="flex-1">
              <p class="text-sm text-amber-900 dark:text-amber-100 font-medium mb-1">首次设置</p>
              <p class="text-xs text-amber-700 dark:text-amber-300">
                此页面仅在首次启动时显示，设置完成后将自动跳转到登录页面
              </p>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin-login'
})

const router = useRouter()

const loading = ref(false)
const showPassword = ref(false)
const errorMsg = ref('')
const setupForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

// 检查是否需要设置，如果不需要则跳转
onMounted(async () => {
  try {
    const res = await $fetch<{ need_setup: boolean }>('/api/setup/status')
    if (!res.need_setup) {
      router.replace('/admin')
    }
  } catch {
    // 接口异常时留在当前页
  }
})

const handleSetup = async () => {
  errorMsg.value = ''

  if (setupForm.value.username.length < 3) {
    errorMsg.value = '用户名至少需要3个字符'
    return
  }
  if (setupForm.value.password.length < 8) {
    errorMsg.value = '密码长度至少需要8个字符'
    return
  }
  if (!/[a-zA-Z]/.test(setupForm.value.password)) {
    errorMsg.value = '密码必须包含字母'
    return
  }
  if (!/[0-9]/.test(setupForm.value.password)) {
    errorMsg.value = '密码必须包含数字'
    return
  }
  if (setupForm.value.password !== setupForm.value.confirmPassword) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await $fetch('/api/setup', {
      method: 'POST',
      body: {
        username: setupForm.value.username,
        password: setupForm.value.password
      }
    })
    router.replace('/admin')
  } catch (e: any) {
    const msg = e?.data?.error || e?.message || '设置失败，请重试'
    errorMsg.value = msg
  } finally {
    loading.value = false
  }
}
</script>
