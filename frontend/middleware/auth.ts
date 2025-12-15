export default defineNuxtRouteMiddleware((to, from) => {
  const authStore = useAuthStore()

  // 恢复认证状态
  if (process.client && !authStore.isAuthenticated) {
    authStore.restoreAuth()
  }

  // 如果未认证，重定向到登录页
  if (!authStore.isAuthenticated) {
    return navigateTo('/admin')
  }
})
