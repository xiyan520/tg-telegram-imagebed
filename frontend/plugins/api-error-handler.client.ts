/**
 * 全局 API 错误处理插件
 * 处理 401 未授权错误，自动登出并跳转到登录页
 */
export default defineNuxtPlugin((nuxtApp) => {
  const authStore = useAuthStore()

  // 拦截全局错误
  nuxtApp.hook('vue:error', (error: any) => {
    // 检查是否是 401 错误
    if (error?.statusCode === 401 || error?.status === 401) {
      console.warn('检测到 401 未授权错误，正在登出...')
      authStore.handleUnauthorized()
    }
  })

  // 提供一个全局的 API 请求包装器
  return {
    provide: {
      apiRequest: async <T>(url: string, options: any = {}): Promise<T> => {
        const config = useRuntimeConfig()
        const fullUrl = url.startsWith('http') ? url : `${config.public.apiBase}${url}`

        try {
          return await $fetch<T>(fullUrl, {
            ...options,
            credentials: 'include',
            onResponseError({ response }) {
              if (response.status === 401) {
                console.warn('API 请求返回 401，正在登出...')
                authStore.handleUnauthorized()
              }
            }
          })
        } catch (error: any) {
          if (error?.statusCode === 401 || error?.status === 401) {
            authStore.handleUnauthorized()
          }
          throw error
        }
      }
    }
  }
})
