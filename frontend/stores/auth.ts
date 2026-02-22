import { defineStore } from 'pinia'
import type { ApiResponse, AdminLoginData, AdminCheckResponse, AdminUpdateCredentialsData } from '~/types/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    username: '',
    isAuthenticated: false,
    isChecking: false
  }),

  actions: {
    // 登录
    async login(username: string, password: string, rememberMe: boolean = false) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<ApiResponse<AdminLoginData>>(`${config.public.apiBase}/api/admin/login`, {
          method: 'POST',
          body: { username, password, remember_me: rememberMe },
          credentials: 'include'
        })

        if (response.success && response.data) {
          this.username = response.data.username
          this.isAuthenticated = true

          // 仅存储会话标记，不持久化实际 token（防止 XSS 窃取）
          if (import.meta.client) {
            localStorage.setItem('has_session', 'true')
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

      this.username = ''
      this.isAuthenticated = false

      if (import.meta.client) {
        localStorage.removeItem('has_session')
        localStorage.removeItem('auth_username')
      }
    },

    // 更新设置
    async updateSettings(settings: { username?: string; password?: string; confirmPassword?: string }) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<ApiResponse<AdminUpdateCredentialsData>>(`${config.public.apiBase}/api/admin/update_credentials`, {
          method: 'POST',
          body: settings,
          credentials: 'include'
        })

        if (response.success && settings.username) {
          this.username = settings.username
          if (import.meta.client) {
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
      if (!import.meta.client) return

      const hasSession = localStorage.getItem('has_session')
      const username = localStorage.getItem('auth_username')

      if (!hasSession) {
        this.clearAuth()
        return
      }

      // 先临时设置用户名（避免闪烁）
      if (username) {
        this.username = username
      }

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
        const response = await $fetch<AdminCheckResponse>(`${config.public.apiBase}/api/admin/check`, {
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
      this.username = ''
      this.isAuthenticated = false

      if (import.meta.client) {
        localStorage.removeItem('has_session')
        localStorage.removeItem('auth_username')
      }
    },

    // 处理 401 错误（供全局错误处理调用）
    handleUnauthorized() {
      this.clearAuth()
      if (import.meta.client) {
        navigateTo('/admin')
      }
    }
  }
})
