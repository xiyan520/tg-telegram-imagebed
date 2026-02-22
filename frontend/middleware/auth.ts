export default defineNuxtRouteMiddleware(async (to, from) => {
  const authStore = useAuthStore()

  // 检查是否需要首次设置
  if (import.meta.client) {
    try {
      const res = await $fetch<{ need_setup: boolean }>('/api/setup/status')
      if (res.need_setup) {
        return navigateTo('/setup')
      }
    } catch {
      // 接口异常时继续正常认证流程
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
