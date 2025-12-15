import { defineStore } from 'pinia'

interface TokenInfo {
  token: string
  upload_count: number
  upload_limit: number
  remaining_uploads: number
  expires_at: string
  created_at: string
  last_used: string | null
}

export const useGuestTokenStore = defineStore('guestToken', {
  state: () => ({
    token: '',
    tokenInfo: null as TokenInfo | null,
    isGuest: false
  }),

  getters: {
    hasToken: (state) => !!state.token,
    remainingUploads: (state) => state.tokenInfo?.remaining_uploads || 0,
    uploadLimit: (state) => state.tokenInfo?.upload_limit || 0,
    uploadCount: (state) => state.tokenInfo?.upload_count || 0,
    expiresAt: (state) => state.tokenInfo?.expires_at || '',
    isExpired: (state) => {
      if (!state.tokenInfo?.expires_at) return false
      return new Date(state.tokenInfo.expires_at) < new Date()
    }
  },

  actions: {
    // 生成新的游客token
    async generateToken(options?: { upload_limit?: number; expires_days?: number }) {
      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/auth/token/generate`, {
          method: 'POST',
          body: {
            upload_limit: options?.upload_limit || 999999,  // 默认无限制
            expires_days: options?.expires_days || 36500,   // 默认100年
            description: '游客Token'
          }
        })

        if (response.success) {
          this.token = response.data.token
          this.isGuest = true

          // 保存到 localStorage
          if (process.client) {
            localStorage.setItem('guest_token', this.token)
            localStorage.setItem('is_guest', 'true')
          }

          // 获取token详细信息
          await this.verifyToken()

          return response.data
        } else {
          throw new Error(response.error || '生成Token失败')
        }
      } catch (error: any) {
        throw new Error(error.data?.error || error.message || '生成Token失败')
      }
    },

    // 验证token
    async verifyToken() {
      if (!this.token) {
        throw new Error('未提供Token')
      }

      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/auth/token/verify`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })

        if (response.success && response.valid) {
          this.tokenInfo = response.data
          return response.data
        } else {
          throw new Error(response.reason || 'Token无效')
        }
      } catch (error: any) {
        // Token无效,清除本地存储
        this.clearToken()
        throw new Error(error.data?.reason || error.message || 'Token验证失败')
      }
    },

    // 刷新token(重新生成)
    async refreshToken(options?: { upload_limit?: number; expires_days?: number }) {
      // 清除旧token
      this.clearToken()

      // 生成新token
      return await this.generateToken(options)
    },

    // 清除token
    clearToken() {
      this.token = ''
      this.tokenInfo = null
      this.isGuest = false

      if (process.client) {
        localStorage.removeItem('guest_token')
        localStorage.removeItem('is_guest')
      }
    },

    // 从 localStorage 恢复token
    async restoreToken() {
      if (process.client) {
        const token = localStorage.getItem('guest_token')
        const isGuest = localStorage.getItem('is_guest')

        if (token && isGuest === 'true') {
          this.token = token
          this.isGuest = true

          try {
            // 验证token是否仍然有效
            await this.verifyToken()
          } catch (error) {
            // Token无效,清除
            this.clearToken()
          }
        }
      }
    },

    // 获取上传历史
    async getUploads(page: number = 1, limit: number = 50) {
      if (!this.token) {
        throw new Error('未提供Token')
      }

      const config = useRuntimeConfig()

      try {
        const response = await $fetch<any>(`${config.public.apiBase}/api/auth/uploads`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.token}`
          },
          params: { page, limit }
        })

        if (response.success) {
          // 更新token信息
          if (response.data.total_uploads !== undefined) {
            if (this.tokenInfo) {
              this.tokenInfo.upload_count = response.data.total_uploads
              this.tokenInfo.remaining_uploads = response.data.remaining_uploads
            }
          }
          return response.data
        } else {
          throw new Error(response.error || '获取上传历史失败')
        }
      } catch (error: any) {
        throw new Error(error.data?.error || error.message || '获取上传历史失败')
      }
    }
  }
})
