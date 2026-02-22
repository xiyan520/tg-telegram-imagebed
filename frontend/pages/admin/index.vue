<template>
  <div class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-cyan-400/20 to-blue-500/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-purple-400/20 to-pink-500/20 rounded-full blur-3xl"></div>
    </div>

    <!-- 认证检查中的加载状态 -->
    <div v-if="authChecking" class="flex flex-col items-center justify-center gap-4">
      <div class="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-sm text-gray-500 dark:text-gray-400">正在验证登录状态...</p>
    </div>

    <!-- 登录卡片 -->
    <div v-else class="w-full max-w-md relative">
      <UCard class="shadow-2xl backdrop-blur-sm bg-white/95 dark:bg-gray-900/95 border border-gray-200 dark:border-gray-800">
        <!-- 头部 -->
        <div class="text-center space-y-6 mb-8">
          <!-- Logo图标 -->
          <div class="flex justify-center">
            <div class="relative">
              <div class="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg transform hover:scale-105 transition-transform">
                <UIcon name="heroicons:shield-check" class="w-10 h-10 text-white" />
              </div>
              <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 rounded-full border-4 border-white dark:border-gray-900 flex items-center justify-center">
                <UIcon name="heroicons:lock-closed" class="w-3 h-3 text-white" />
              </div>
            </div>
          </div>

          <!-- 标题 -->
          <div>
            <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text text-transparent mb-2">
              管理后台
            </h1>
            <p class="text-gray-600 dark:text-gray-400 text-sm">
              欢迎回来，请登录您的管理员账户
            </p>
          </div>
        </div>

        <!-- 登录表单 -->
        <UForm :state="loginForm" @submit="handleLogin" class="space-y-5">
          <!-- 用户名输入 -->
          <UFormGroup label="用户名" name="username" required>
            <UInput
              v-model="loginForm.username"
              placeholder="请输入管理员用户名"
              size="xl"
              :ui="{
                icon: { trailing: { pointer: '' } },
                base: 'transition-all duration-200'
              }"
            >
              <template #leading>
                <UIcon name="heroicons:user-circle" class="w-5 h-5 text-gray-400" />
              </template>
            </UInput>
          </UFormGroup>

          <!-- 密码输入 -->
          <UFormGroup label="密码" name="password" required>
            <UInput
              v-model="loginForm.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入管理员密码"
              size="xl"
              :ui="{
                icon: { trailing: { pointer: '' } },
                base: 'transition-all duration-200'
              }"
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

          <!-- 记住我 -->
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="rememberMe"
                type="checkbox"
                class="w-4 h-4 text-cyan-600 bg-gray-100 border-gray-300 rounded focus:ring-cyan-500 dark:focus:ring-cyan-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span class="text-sm text-gray-600 dark:text-gray-400">记住我</span>
            </label>
          </div>

          <!-- 登录按钮 -->
          <UButton
            type="submit"
            color="primary"
            size="xl"
            block
            :loading="loading"
            :disabled="lockoutTimer > 0"
            class="shadow-lg hover:shadow-xl transition-shadow"
          >
            <template #leading>
              <UIcon :name="lockoutTimer > 0 ? 'heroicons:clock' : 'heroicons:arrow-right-on-rectangle'" />
            </template>
            {{ lockoutTimer > 0 ? `请等待 ${lockoutTimer} 秒` : loading ? '登录中...' : '立即登录' }}
          </UButton>

          <!-- 剩余尝试次数警告 -->
          <div v-if="remainingAttempts >= 0 && remainingAttempts <= 2 && lockoutTimer <= 0"
               class="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <div class="flex items-center gap-2">
              <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <p class="text-sm text-amber-800 dark:text-amber-200">
                还剩 <span class="font-bold">{{ remainingAttempts }}</span> 次尝试机会，之后账户将被临时锁定
              </p>
            </div>
          </div>
        </UForm>

        <!-- 底部链接 -->
        <div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800">
          <div class="flex items-center justify-center gap-4 text-sm">
            <NuxtLink
              to="/"
              class="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
            >
              <UIcon name="heroicons:arrow-left" class="w-4 h-4" />
              返回首页
            </NuxtLink>
            <span class="text-gray-300 dark:text-gray-700">|</span>
            <NuxtLink
              to="/guest"
              class="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
            >
              <UIcon name="heroicons:key" class="w-4 h-4" />
              Token模式
            </NuxtLink>
          </div>
        </div>

        <!-- 安全提示 -->
        <div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div class="flex items-start gap-3">
            <UIcon name="heroicons:information-circle" class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div class="flex-1">
              <p class="text-sm text-blue-900 dark:text-blue-100 font-medium mb-1">安全提示</p>
              <p class="text-xs text-blue-700 dark:text-blue-300">
                请确保您在安全的网络环境下登录，不要在公共设备上保存密码
              </p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- 版权信息 -->
      <div class="mt-6 text-center">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          &copy; {{ new Date().getFullYear() }} 图床管理系统. All rights reserved.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin-login'
})

const authStore = useAuthStore()
const notification = useNotification()
const router = useRouter()

// 状态
const loading = ref(false)
const authChecking = ref(true)  // 认证检查中，避免登录表单闪烁
const showPassword = ref(false)
const rememberMe = ref(false)
const lockoutTimer = ref(0)        // 锁定倒计时秒数
const remainingAttempts = ref(-1)  // 剩余尝试次数，-1 表示未知
let countdownInterval: ReturnType<typeof setInterval> | null = null
const loginForm = ref({
  username: '',
  password: ''
})

// 页面初始化：先恢复认证状态，再决定显示登录表单还是跳转
onMounted(async () => {
  // 检查是否需要首次设置
  try {
    const setupRes = await $fetch<{ need_setup: boolean }>('/api/setup/status')
    if (setupRes.need_setup) {
      router.replace('/setup')
      return
    }
  } catch {
    // 接口异常时继续正常流程
  }

  // 恢复并验证后端 session
  if (import.meta.client && !authStore.isAuthenticated) {
    await authStore.restoreAuth()
  }

  // 已登录则直接跳转，不显示登录表单
  if (authStore.isAuthenticated) {
    router.replace('/admin/dashboard')
    return
  }

  // 未登录，显示登录表单
  authChecking.value = false

  // 从localStorage恢复记住的用户名
  if (import.meta.client) {
    const savedUsername = localStorage.getItem('admin_username')
    if (savedUsername) {
      loginForm.value.username = savedUsername
      rememberMe.value = true
    }
  }
})

// 启动锁定倒计时
const startLockoutCountdown = (seconds: number) => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  lockoutTimer.value = seconds
  countdownInterval = setInterval(() => {
    lockoutTimer.value--
    if (lockoutTimer.value <= 0) {
      lockoutTimer.value = 0
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
    }
  }, 1000)
}

// 登录处理
const handleLogin = async () => {
  loading.value = true
  try {
    await authStore.login(loginForm.value.username, loginForm.value.password, rememberMe.value)

    // 重置安全状态
    remainingAttempts.value = -1
    lockoutTimer.value = 0

    // 如果选择记住我，保存用户名
    if (import.meta.client) {
      if (rememberMe.value) {
        localStorage.setItem('admin_username', loginForm.value.username)
      } else {
        localStorage.removeItem('admin_username')
      }
    }

    notification.success('登录成功', '欢迎回来！')

    router.push('/admin/dashboard')
  } catch (error: any) {
    if (error.locked && error.retryAfter) {
      startLockoutCountdown(error.retryAfter)
      notification.error('账户已锁定', error.message || '登录尝试过多，请稍后再试')
    } else if (error.remainingAttempts !== undefined) {
      remainingAttempts.value = error.remainingAttempts
      notification.error('登录失败', error.message || '用户名或密码错误')
    } else {
      notification.error('登录失败', error.message || '用户名或密码错误')
    }
  } finally {
    loading.value = false
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
})
</script>
