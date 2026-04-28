import { defineStore } from 'pinia'
import type { ApiResponse, AdminLoginData, AdminCheckResponse, AdminUpdateCredentialsData, AdminLoginTotpRequired, TotpStatusData, TotpSetupData } from '~/types/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    username: '',
    isAuthenticated: false,
    isChecking: false,
    // TOTP 相关状态
    totpEnabled: false,
    totpSetupData: null as TotpSetupData | null,
  }),

  actions: {
    // 登录
    async login(username: string, password: string, rememberMe: boolean = false) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<ApiResponse<AdminLoginData> | AdminLoginTotpRequired>(`${config.public.apiBase}/api/admin/login`, {
          method: 'POST',
          body: { username, password, remember_me: rememberMe },
          credentials: 'include'
        })

        // 检查是否需要 TOTP 二次验证
        if (response.success && 'totp_required' in response && response.totp_required) {
          return response
        }

        if (response.success && 'data' in response && response.data) {
          this.username = response.data.username
          this.isAuthenticated = true

          if (import.meta.client) {
            localStorage.setItem('has_session', 'true')
            localStorage.setItem('auth_username', this.username)
          }

          return response.data
        } else {
          throw new Error(response.message || '登录失败')
        }
      } catch (error: any) {
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

    // TOTP 验证码登录（第二步）
    async verifyTotpLogin(verificationToken: string, code: string) {
      const config = useRuntimeConfig()

      const response = await $fetch<ApiResponse<AdminLoginData>>(`${config.public.apiBase}/api/admin/login/verify-totp`, {
        method: 'POST',
        body: { verification_token: verificationToken, code },
        credentials: 'include'
      })

      if (response.success && response.data) {
        this.username = response.data.username
        this.isAuthenticated = true

        if (import.meta.client) {
          localStorage.setItem('has_session', 'true')
          localStorage.setItem('auth_username', this.username)
        }

        return response.data
      } else {
        throw new Error(response.message || '验证失败')
      }
    },

    // 获取 TOTP 状态
    async fetchTotpStatus() {
      const config = useRuntimeConfig()
      const response = await $fetch<ApiResponse<TotpStatusData>>(`${config.public.apiBase}/api/admin/totp/status`, {
        credentials: 'include'
      })
      if (response.success && response.data) {
        this.totpEnabled = response.data.enabled
      }
      return response
    },

    // 开始 TOTP 设置
    async startTotpSetup() {
      const config = useRuntimeConfig()
      const response = await $fetch<ApiResponse<TotpSetupData>>(`${config.public.apiBase}/api/admin/totp/setup`, {
        method: 'POST',
        credentials: 'include'
      })
      if (response.success && response.data) {
        this.totpSetupData = response.data
      }
      return response
    },

    // 验证并启用 TOTP
    async verifyAndEnableTotp(code: string) {
      const config = useRuntimeConfig()
      const response = await $fetch<ApiResponse<{}>>(`${config.public.apiBase}/api/admin/totp/verify`, {
        method: 'POST',
        body: { code },
        credentials: 'include'
      })
      if (response.success) {
        this.totpEnabled = true
        this.totpSetupData = null
      }
      return response
    },

    // 禁用 TOTP
    async disableTotp(password: string, code: string) {
      const config = useRuntimeConfig()
      const response = await $fetch<ApiResponse<{}>>(`${config.public.apiBase}/api/admin/totp/disable`, {
        method: 'POST',
        body: { password, code },
        credentials: 'include'
      })
      if (response.success) {
        this.totpEnabled = false
      }
      return response
    },

    // 登出
    async logout() {
      const config = useRuntimeConfig()

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
      this.totpEnabled = false
      this.totpSetupData = null

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

      if (username) {
        this.username = username
      }

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
      this.totpEnabled = false
      this.totpSetupData = null

      if (import.meta.client) {
        localStorage.removeItem('has_session')
        localStorage.removeItem('auth_username')
      }
    },

    // 处理 401 错误
    handleUnauthorized() {
      this.clearAuth()
      if (import.meta.client) {
        navigateTo('/admin')
      }
    }
  }
})
