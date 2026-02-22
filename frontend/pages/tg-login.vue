<template>
  <div class="min-h-[60vh] flex items-center justify-center">
    <UCard class="w-full max-w-md">
      <div class="text-center space-y-4 py-4">
        <!-- 加载中 -->
        <template v-if="status === 'loading'">
          <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p class="text-gray-600 dark:text-gray-400">正在验证登录链接...</p>
        </template>

        <!-- 成功 -->
        <template v-else-if="status === 'success'">
          <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
            <UIcon name="heroicons:check-circle" class="w-10 h-10 text-green-500" />
          </div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white">登录成功</h2>
          <p class="text-gray-500">正在跳转...</p>
        </template>

        <!-- 失败 -->
        <template v-else>
          <div class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto">
            <UIcon name="heroicons:x-circle" class="w-10 h-10 text-red-500" />
          </div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white">登录失败</h2>
          <p class="text-gray-500">{{ errorMsg }}</p>
          <UButton color="primary" to="/album">返回相册</UButton>
        </template>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const tgAuth = useTgAuthStore()

const status = ref<'loading' | 'success' | 'error'>('loading')
const errorMsg = ref('')

onMounted(async () => {
  const code = (route.query.code as string || '').trim()
  if (!code) {
    status.value = 'error'
    errorMsg.value = '缺少登录码参数'
    return
  }

  try {
    await tgAuth.consumeLoginLink(code)
    status.value = 'success'
    setTimeout(() => router.replace('/album'), 1000)
  } catch (e: any) {
    status.value = 'error'
    errorMsg.value = e.message || '登录链接无效或已过期'
  }
})
</script>
