<template>
  <div class="max-w-4xl mx-auto space-y-8">
    <!-- 页面标题 -->
    <div class="text-center space-y-3">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        Token模式
      </h1>
      <p class="text-stone-600 dark:text-stone-400 text-lg">
        无需注册，生成专属Token即可上传图片，无数量和时间限制
      </p>
    </div>

    <!-- Token状态卡片 -->
    <div v-if="!guestStore.hasToken" class="flex justify-center">
      <UCard class="shadow-2xl w-full max-w-3xl overflow-hidden">
        <div class="grid md:grid-cols-2 gap-8 p-8">
          <!-- 左侧：生成Token -->
          <div class="space-y-6">
            <div class="text-center md:text-left">
              <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl mb-4">
                <UIcon name="heroicons:sparkles" class="w-8 h-8 text-white" />
              </div>
              <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                生成新Token
              </h2>
              <p class="text-gray-600 dark:text-gray-400 text-sm">
                一键生成专属Token，立即开始上传
              </p>
            </div>

            <!-- Token特性 -->
            <div class="space-y-3">
              <div class="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span class="text-sm text-green-900 dark:text-green-100">无上传数量限制</span>
              </div>
              <div class="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <UIcon name="heroicons:clock" class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                <span class="text-sm text-blue-900 dark:text-blue-100">永久有效，无时间限制</span>
              </div>
              <div class="flex items-center gap-3 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <UIcon name="heroicons:photo" class="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                <span class="text-sm text-purple-900 dark:text-purple-100">随时查看上传历史</span>
              </div>
            </div>

            <UButton
              size="xl"
              color="primary"
              block
              :loading="generating"
              @click="handleGenerateToken"
            >
              <template #leading>
                <UIcon name="heroicons:sparkles" />
              </template>
              立即生成Token
            </UButton>
          </div>

          <!-- 右侧：使用已有Token -->
          <div class="space-y-6 md:border-l md:border-gray-200 md:dark:border-gray-700 md:pl-8">
            <div class="text-center md:text-left">
              <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl mb-4">
                <UIcon name="heroicons:key" class="w-8 h-8 text-white" />
              </div>
              <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                使用已有Token
              </h2>
              <p class="text-gray-600 dark:text-gray-400 text-sm">
                已经有Token？直接输入验证登录
              </p>
            </div>

            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  输入您的Token
                </label>
                <UInput
                  v-model="tokenInput"
                  placeholder="粘贴您的Token..."
                  size="xl"
                  :ui="{ base: 'font-mono' }"
                />
              </div>

              <UButton
                size="xl"
                color="primary"
                variant="outline"
                block
                :loading="verifying"
                @click="handleVerifyToken"
              >
                <template #leading>
                  <UIcon name="heroicons:arrow-right-circle" />
                </template>
                验证并登录
              </UButton>

              <p class="text-xs text-gray-500 dark:text-gray-400 text-center">
                Token是您的唯一凭证，请妥善保管
              </p>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Token管理面板 -->
    <div v-if="guestStore.hasToken" class="space-y-6">
      <!-- Token信息卡片 -->
      <UCard class="shadow-2xl">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-gradient-to-br from-emerald-600 to-teal-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900 dark:text-white">Token管理</h3>
                <p class="text-sm text-gray-600 dark:text-gray-400">管理您的Token和服务设置</p>
              </div>
            </div>
          </div>
        </template>

        <div class="space-y-6">
          <!-- Token信息 -->
          <div class="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-xl border border-emerald-200 dark:border-emerald-700">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h4 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">Token状态</h4>
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  已上传 <span class="font-semibold text-emerald-600 dark:text-emerald-400">{{ guestStore.uploadCount }}</span> 张图片
                </p>
              </div>
              <div class="flex items-center gap-2 px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/40 rounded-full">
                <div class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                <span class="text-sm font-medium text-emerald-700 dark:text-emerald-300">已激活</span>
              </div>
            </div>

            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  您的Token
                </label>
                <div class="flex gap-2">
                  <UInput
                    :model-value="guestStore.token"
                    readonly
                    class="flex-1 font-mono text-sm"
                    size="lg"
                  />
                  <UButton
                    :icon="tokenCopied ? 'heroicons:check' : 'heroicons:clipboard-document'"
                    :color="tokenCopied ? 'green' : 'gray'"
                    size="lg"
                    @click="copyToken"
                  >
                    {{ tokenCopied ? '已复制' : '复制' }}
                  </UButton>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  请妥善保管您的Token，丢失后将无法找回
                </p>
              </div>
            </div>
          </div>

          <!-- 服务特性 -->
          <div>
            <h4 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">服务特性</h4>
            <div class="grid md:grid-cols-3 gap-4">
              <div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <div class="flex items-center gap-3 mb-2">
                  <UIcon name="heroicons:check-circle" class="w-6 h-6 text-green-600 dark:text-green-400" />
                  <h5 class="font-semibold text-gray-900 dark:text-white">无限上传</h5>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-400">无上传数量限制，随时上传</p>
              </div>
              <div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div class="flex items-center gap-3 mb-2">
                  <UIcon name="heroicons:clock" class="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  <h5 class="font-semibold text-gray-900 dark:text-white">永久有效</h5>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-400">Token永久有效，无时间限制</p>
              </div>
              <div class="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <div class="flex items-center gap-3 mb-2">
                  <UIcon name="heroicons:photo" class="w-6 h-6 text-purple-600 dark:text-purple-400" />
                  <h5 class="font-semibold text-gray-900 dark:text-white">历史记录</h5>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-400">随时查看上传历史</p>
              </div>
            </div>
          </div>

          <!-- 快速操作 -->
          <div>
            <h4 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">快速操作</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <NuxtLink to="/">
                <UButton
                  color="primary"
                  variant="soft"
                  size="lg"
                  block
                >
                  <template #leading>
                    <UIcon name="heroicons:cloud-arrow-up" />
                  </template>
                  前往上传图片
                </UButton>
              </NuxtLink>
              <NuxtLink to="/gallery">
                <UButton
                  color="cyan"
                  variant="soft"
                  size="lg"
                  block
                >
                  <template #leading>
                    <UIcon name="heroicons:photo" />
                  </template>
                  查看图片画廊
                </UButton>
              </NuxtLink>
            </div>
          </div>

          <!-- Token操作 -->
          <div class="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h4 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Token操作</h4>
            <div class="flex flex-wrap gap-3">
              <UButton
                color="gray"
                variant="outline"
                :loading="refreshing"
                @click="handleRefreshToken"
              >
                <template #leading>
                  <UIcon name="heroicons:arrow-path" />
                </template>
                刷新Token
              </UButton>
              <UButton
                color="red"
                variant="outline"
                @click="handleClearToken"
              >
                <template #leading>
                  <UIcon name="heroicons:arrow-right-on-rectangle" />
                </template>
                退出登录
              </UButton>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-3">
              刷新Token将生成新的Token并清除旧Token，退出登录将清除本地保存的Token
            </p>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
const toast = useLightToast()  // 使用新的轻量级Toast框架
const guestStore = useGuestTokenStore()

// 状态
const generating = ref(false)
const refreshing = ref(false)
const verifying = ref(false)
const tokenInput = ref('')
const tokenCopied = ref(false)

// Token配置
const tokenConfig = ref({
  upload_limit: 100,
  expires_days: 30
})

// 生成Token
const handleGenerateToken = async () => {
  generating.value = true
  try {
    await guestStore.generateToken(tokenConfig.value)
    toast.success('Token已生成')
  } catch (error: any) {
    toast.error('生成失败', error.message)
  } finally {
    generating.value = false
  }
}

// 验证Token
const handleVerifyToken = async () => {
  if (!tokenInput.value.trim()) {
    toast.error('请输入Token')
    return
  }

  verifying.value = true
  try {
    // 设置token到store
    guestStore.token = tokenInput.value.trim()
    guestStore.isGuest = true

    // 验证token
    await guestStore.verifyToken()

    // 保存到localStorage
    if (process.client) {
      localStorage.setItem('guest_token', guestStore.token)
      localStorage.setItem('is_guest', 'true')
    }

    toast.success('验证成功')

    // 清空输入
    tokenInput.value = ''
  } catch (error: any) {
    // 验证失败，清除store中的token
    guestStore.clearToken()
    toast.error('验证失败', error.message || 'Token无效或已过期')
  } finally {
    verifying.value = false
  }
}

// 刷新Token
const handleRefreshToken = async () => {
  refreshing.value = true
  try {
    await guestStore.refreshToken(tokenConfig.value)
    toast.success('Token已刷新')
  } catch (error: any) {
    toast.error('刷新失败', error.message)
  } finally {
    refreshing.value = false
  }
}

// 清除Token
const handleClearToken = () => {
  if (confirm('确定要清除Token吗？清除后将无法恢复。')) {
    guestStore.clearToken()
    toast.success('已清除')
  }
}

// 通用复制函数（带错误处理）
const copyToClipboard = async (text: string, successMessage: string = '已复制') => {
  try {
    // 优先使用现代剪贴板API
    await navigator.clipboard.writeText(text)
    toast.success(successMessage)
    return true
  } catch (err) {
    // 回退方案：使用传统方法
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)

      if (successful) {
        toast.success(successMessage)
        return true
      } else {
        throw new Error('复制失败')
      }
    } catch (fallbackErr) {
      toast.error('复制失败', '请手动复制内容')
      console.error('复制失败:', fallbackErr)
      return false
    }
  }
}

// 复制Token
const copyToken = async () => {
  const success = await copyToClipboard(guestStore.token, 'Token已复制到剪贴板')

  // 只有复制成功时才显示按钮状态变化
  if (success) {
    tokenCopied.value = true
    setTimeout(() => {
      tokenCopied.value = false
    }, 2000)
  }
}

// 页面加载时恢复token
onMounted(async () => {
  await guestStore.restoreToken()
})
</script>
