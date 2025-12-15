import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    username: '',
    isAuthenticated: false
  }),

  actions: {
    // 登录
    async login(username: string, password: string) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/admin/login`, {
          method: 'POST',
          body: { username, password }
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
        throw new Error(error.message || '登录失败')
      }
    },

    // 登出
    async logout() {
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

    // 从 localStorage 恢复状态
    restoreAuth() {
      if (process.client) {
        const token = localStorage.getItem('auth_token')
        const username = localStorage.getItem('auth_username')

        if (token && username) {
          this.token = token
          this.username = username
          this.isAuthenticated = true
        }
      }
    }
  }
})
