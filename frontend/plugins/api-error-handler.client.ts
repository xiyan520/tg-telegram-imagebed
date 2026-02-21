/**
 * 全局 API 错误处理插件
 * 拦截所有 fetch 响应中的 401，自动登出并跳转到登录页
 */
export default defineNuxtPlugin((nuxtApp) => {
  const authStore = useAuthStore()

  // 拦截原生 fetch，捕获所有 401 响应（包括 $fetch 内部调用）
  const _originalFetch = globalThis.fetch
  globalThis.fetch = async (...args: Parameters<typeof fetch>) => {
    const response = await _originalFetch(...args)
    if (response.status === 401) {
      // 仅拦截管理后台 API 的 401
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request).url
      if (url.includes('/api/admin/')) {
        authStore.handleUnauthorized()
      }
    }
    return response
  }

  // 拦截 Vue 组件内未捕获的错误
  nuxtApp.hook('vue:error', (error: any) => {
    if (error?.statusCode === 401 || error?.status === 401) {
      authStore.handleUnauthorized()
    }
  })

  // 提供一个全局的 API 请求包装器（向后兼容）
  return {
    provide: {
      apiRequest: async <T>(url: string, options: any = {}): Promise<T> => {
        const config = useRuntimeConfig()
        const fullUrl = url.startsWith('http') ? url : `${config.public.apiBase}${url}`
        return await $fetch<T>(fullUrl, {
          ...options,
          credentials: 'include',
        })
      }
    }
  }
})
