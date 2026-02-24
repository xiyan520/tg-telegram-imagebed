import { defineStore } from 'pinia'
import type { ApiResponse } from '~/types/api'

interface TgUser {
  tg_user_id: number
  username: string | null
  first_name: string
  token_count: number
  max_tokens: number
}

// 从 $fetch 错误中提取后端返回的 error 字段
function extractError(e: any, fallback: string): string {
  return e?.data?.error || e?.message || fallback
}

export const useTgAuthStore = defineStore('tgAuth', {
  state: () => ({
    user: null as TgUser | null,
    isLoggedIn: false,
    loading: false,
  }),

  actions: {
    async checkSession() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<TgUser>>(`${config.public.apiBase}/api/auth/tg/session`, {
          credentials: 'include',
        })
        if (res.success && res.data) {
          this.user = res.data
          this.isLoggedIn = true
        } else {
          this.user = null
          this.isLoggedIn = false
        }
      } catch {
        this.user = null
        this.isLoggedIn = false
      }
    },

    async requestCode(username: string) {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ message: string }>>(`${config.public.apiBase}/api/auth/tg/request-code`, {
          method: 'POST',
          body: { tg_username: username },
          credentials: 'include',
        })
        if (!res.success) throw new Error(res.error || '发送验证码失败')
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '发送验证码失败'))
      }
    },

    async verifyCode(username: string, code: string) {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ message: string }>>(`${config.public.apiBase}/api/auth/tg/verify-code`, {
          method: 'POST',
          body: { tg_username: username, code },
          credentials: 'include',
        })
        if (!res.success) throw new Error(res.error || '验证码无效')
        await this.checkSession()
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '验证码无效'))
      }
    },

    async consumeLoginLink(code: string) {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ message: string }>>(`${config.public.apiBase}/api/auth/tg/login-link`, {
          method: 'POST',
          body: { code },
          credentials: 'include',
        })
        if (!res.success) throw new Error(res.error || '登录链接无效')
        await this.checkSession()
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '登录链接无效'))
      }
    },

    async logout() {
      const config = useRuntimeConfig()
      try {
        await $fetch<ApiResponse>(`${config.public.apiBase}/api/auth/tg/logout`, {
          method: 'POST',
          credentials: 'include',
        })
      } catch { /* 忽略 */ }
      this.user = null
      this.isLoggedIn = false
    },

    async getMyTokens() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ tokens: any[] }>>(`${config.public.apiBase}/api/auth/tg/tokens`, {
          credentials: 'include',
        })
        if (!res.success) throw new Error(res.error || '获取 Token 列表失败')
        return res.data?.tokens || []
      } catch (e: any) {
        throw new Error(extractError(e, '获取 Token 列表失败'))
      }
    },

    /**
     * TG 登录/绑定后，自动同步该用户下所有 Token 到本地 vault。
     * 调用 /api/auth/tg/sync-tokens 获取完整 token 字符串 + tokenInfo，
     * 逐个添加到 tokenStore vault（已存在则跳过），并填充 tokenInfo。
     */
    async syncTokensToVault() {
      const config = useRuntimeConfig()
      const tokenStore = useTokenStore()
      try {
        const res = await $fetch<ApiResponse<{ tokens: any[] }>>(`${config.public.apiBase}/api/auth/tg/sync-tokens`, {
          credentials: 'include',
        })
        if (!res.success || !res.data?.tokens?.length) return

        for (const t of res.data.tokens) {
          if (!t.token) continue
          const vaultId = await tokenStore.addTokenToVault(t.token, {
            albumName: t.description || '',
            makeActive: false,
            verify: false,
          })
          // 用后端返回的数据填充 tokenInfo，避免需要逐个 verify
          if (vaultId) {
            const item = tokenStore.vaultItems.find(i => i.id === vaultId)
            if (item) {
              item.tokenInfo = {
                upload_count: t.upload_count ?? 0,
                upload_limit: t.upload_limit ?? 0,
                remaining_uploads: t.remaining_uploads ?? 0,
                expires_at: t.expires_at ?? '',
                created_at: t.created_at ?? '',
                last_used: t.last_used ?? null,
                can_upload: t.can_upload ?? true,
                description: t.description ?? null,
                tg_user_id: t.tg_user_id ?? null,
              }
              item.lastVerifiedAt = new Date().toISOString()
            }
          }
        }
        tokenStore.persistVault()
        // 如果当前没有激活的 Token，自动选择第一个
        if (!tokenStore.hasToken && tokenStore.vaultItems.length > 0) {
          await tokenStore.setActiveTokenById(tokenStore.vaultItems[0].id, { verify: true })
        } else {
          // 激活的 Token 可能 tokenInfo 也被更新了，同步到顶层状态
          tokenStore.syncActiveFromVault()
        }
      } catch {
        // 同步失败静默忽略，不影响主流程
      }
    },

    async generateWebCode(): Promise<{ code: string; bot_username: string }> {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ code: string; bot_username: string }>>(`${config.public.apiBase}/api/auth/tg/web-code`, {
          method: 'POST',
          credentials: 'include',
        })
        if (!res.success || !res.data) throw new Error(res.error || '生成验证码失败')
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '生成验证码失败'))
      }
    },

    async pollCodeStatus(code: string): Promise<{ status: 'pending' | 'ok' | 'expired' }> {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ status: 'pending' | 'ok' | 'expired' }>>(`${config.public.apiBase}/api/auth/tg/code-status`, {
          params: { code },
          credentials: 'include',
        })
        if (!res.success || !res.data) throw new Error(res.error || '查询状态失败')
        // 登录成功时 Cookie 已由后端设置，刷新会话状态
        if (res.data.status === 'ok') {
          await this.checkSession()
        }
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '查询状态失败'))
      }
    },
  }
})
