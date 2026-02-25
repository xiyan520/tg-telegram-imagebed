export default defineNuxtRouteMiddleware(async (to, from) => {
  const authStore = useAuthStore()

  // 检查是否需要首次设置（使用 useState 缓存，避免每次路由跳转重复请求）
  if (import.meta.client) {
    const setupChecked = useState<boolean>('setup_status_checked', () => false)
    const needSetup = useState<boolean>('setup_status', () => false)

    if (!setupChecked.value) {
      try {
        const res = await $fetch<{ need_setup: boolean }>('/api/setup/status')
        needSetup.value = !!res.need_setup
        setupChecked.value = true
      } catch {
        // 接口异常时继续正常认证流程
        setupChecked.value = true
      }
    }

    if (needSetup.value) {
      return navigateTo('/setup')
    }
  }

  // 恢复并验证认证状态
  if (import.meta.client && !authStore.isAuthenticated) {
    await authStore.restoreAuth()
  }

  // 如果未认证，重定向到登录页
  if (!authStore.isAuthenticated) {
    return navigateTo('/admin')
  }
})
