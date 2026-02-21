import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    username: '',
    isAuthenticated: false,
    isChecking: false
  }),

  actions: {
    // 登录
    async login(username: string, password: string) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/admin/login`, {
          method: 'POST',
          body: { username, password },
          credentials: 'include'
        })

        if (response.success) {
          this.token = response.data.token
          this.username = response.data.username
          this.isAuthenticated = true

          // 保存到 localStorage
          if (process.client) {
            localStorage.setItem('auth_token', this.token)
            localStorage.setItem('auth_username', this.username)
          }

          return response.data
        } else {
          throw new Error(response.message || '登录失败')
        }
      } catch (error: any) {
        // 解析后端返回的结构化错误
        const data = error?.data || error?.response?._data
        if (data?.locked) {
          const err: any = new Error(data.message || '登录尝试过多')
          err.locked = true
          err.retryAfter = data.retry_after
          throw err
        }
        if (data?.remaining_attempts !== undefined) {
          const err: any = new Error(data.message || '登录失败')
          err.remainingAttempts = data.remaining_attempts
          throw err
        }
        throw new Error(error.message || error?.data?.message || '登录失败')
      }
    },

    // 登出
    async logout() {
      const config = useRuntimeConfig()

      // 调用后端登出接口
      try {
        await $fetch(`${config.public.apiBase}/api/admin/logout`, {
          method: 'POST',
          credentials: 'include'
        })
      } catch (e) {
        // 忽略错误，继续清理本地状态
      }

      this.token = ''
      this.username = ''
      this.isAuthenticated = false

      if (process.client) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_username')
      }
    },

    // 更新设置
    async updateSettings(settings: { username?: string; password?: string; confirmPassword?: string }) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/admin/update_credentials`, {
          method: 'POST',
          body: settings,
          credentials: 'include'
        })

        if (response.success && settings.username) {
          this.username = settings.username
          if (process.client) {
            localStorage.setItem('auth_username', settings.username)
          }
        }

        return response
      } catch (error: any) {
        throw new Error(error.message || '更新设置失败')
      }
    },

    // 从 localStorage 恢复状态并验证后端 session
    async restoreAuth() {
      if (!process.client) return

      const token = localStorage.getItem('auth_token')
      const username = localStorage.getItem('auth_username')

      if (!token || !username) {
        this.clearAuth()
        return
      }

      // 先临时设置状态（避免闪烁）
      this.token = token
      this.username = username

      // 验证后端 session 是否有效
      const isValid = await this.checkAuth()
      if (!isValid) {
        this.clearAuth()
      }
    },

    // 检查后端 session 是否有效
    async checkAuth(): Promise<boolean> {
      if (this.isChecking) return this.isAuthenticated

      const config = useRuntimeConfig()
      this.isChecking = true

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/admin/check`, {
          credentials: 'include'
        })

        if (response.authenticated) {
          this.isAuthenticated = true
          this.username = response.username || this.username
          return true
        } else {
          return false
        }
      } catch (error) {
        console.warn('Session 验证失败:', error)
        return false
      } finally {
        this.isChecking = false
      }
    },

    // 清除认证状态
    clearAuth() {
      this.token = ''
      this.username = ''
      this.isAuthenticated = false

      if (process.client) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_username')
      }
    },

    // 处理 401 错误（供全局错误处理调用）
    handleUnauthorized() {
      this.clearAuth()
      if (process.client) {
        navigateTo('/admin')
      }
    }
  }
})
