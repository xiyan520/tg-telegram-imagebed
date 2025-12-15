<template>
  <div class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-cyan-400/20 to-blue-500/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-purple-400/20 to-pink-500/20 rounded-full blur-3xl"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="w-full max-w-md relative">
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
            class="shadow-lg hover:shadow-xl transition-shadow"
          >
            <template #leading>
              <UIcon name="heroicons:arrow-right-on-rectangle" />
            </template>
            {{ loading ? '登录中...' : '立即登录' }}
          </UButton>
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
          © 2024 图床管理系统. All rights reserved.
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
const showPassword = ref(false)
const rememberMe = ref(false)
const loginForm = ref({
  username: '',
  password: ''
})

// 如果已登录，重定向到仪表盘
onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/admin/dashboard')
  }

  // 从localStorage恢复记住的用户名
  if (process.client) {
    const savedUsername = localStorage.getItem('admin_username')
    if (savedUsername) {
      loginForm.value.username = savedUsername
      rememberMe.value = true
    }
  }
})

// 登录处理
const handleLogin = async () => {
  loading.value = true
  try {
    await authStore.login(loginForm.value.username, loginForm.value.password)

    // 如果选择记住我，保存用户名
    if (process.client) {
      if (rememberMe.value) {
        localStorage.setItem('admin_username', loginForm.value.username)
      } else {
        localStorage.removeItem('admin_username')
      }
    }

    notification.success('登录成功', '欢迎回来！')

    router.push('/admin/dashboard')
  } catch (error: any) {
    notification.error('登录失败', error.message || '用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>
