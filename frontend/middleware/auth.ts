export default defineNuxtRouteMiddleware(async (to, from) => {
  const authStore = useAuthStore()

  // 恢复并验证认证状态
  if (process.client && !authStore.isAuthenticated) {
    await authStore.restoreAuth()
  }

  // 如果未认证，重定向到登录页
  if (!authStore.isAuthenticated) {
    return navigateTo('/admin')
  }
})
