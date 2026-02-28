import { defineStore } from 'pinia'
import type { ApiResponse } from '~/types/api'
import type { TgSessionItem, TgSessionListData } from '~/types/tg-session'
import { getClientDeviceFingerprint } from '~/utils/deviceFingerprint'

interface TgUser {
  tg_user_id: number
  username: string | null
  first_name: string
  token_count: number
  max_tokens: number
  current_session_id?: string
  online_sessions_count?: number
}

function extractError(e: any, fallback: string): string {
  return e?.data?.error || e?.message || fallback
}

function getTgDeviceFingerprint() {
  return getClientDeviceFingerprint({
    deviceIdKey: 'tg_device_id',
    deviceIdPrefix: 'dev'
  })
}

function buildClientHeaders() {
  return getTgDeviceFingerprint().headers
}

function buildCurrentBrowserFallbackSession(currentSessionId?: string): TgSessionItem {
  const fp = getTgDeviceFingerprint()
  const now = new Date().toISOString()
  const deviceId = fp.deviceId || ''
  const platform = fp.platform || 'web'
  const deviceName = fp.deviceLabel
  const fallbackSessionId = currentSessionId || (deviceId ? `local-${deviceId.slice(0, 12)}` : `local-${Date.now().toString(36)}`)

  return {
    session_id: fallbackSessionId,
    device_id: deviceId,
    device_name: deviceName || platform || 'Current Browser',
    device_label: fp.deviceLabel,
    os_name: fp.osName,
    browser_name: fp.browserName,
    browser_version: fp.browserVersion,
    platform: platform || 'web',
    ip_address: '',
    user_agent: import.meta.client ? (navigator.userAgent || '') : '',
    created_at: now,
    last_seen_at: now,
    expires_at: '',
    is_current: true
  }
}

export const useTgAuthStore = defineStore('tgAuth', {
  state: () => ({
    user: null as TgUser | null,
    isLoggedIn: false,
    loading: false,
    sessions: [] as TgSessionItem[],
    currentSessionId: '' as string,
    onlineSessionCount: 0,
  }),

  actions: {
    async checkSession() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<TgUser>>(`${config.public.apiBase}/api/auth/tg/session`, {
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (res.success && res.data) {
          this.user = res.data
          this.isLoggedIn = true
          this.currentSessionId = res.data.current_session_id || ''
          this.onlineSessionCount = res.data.online_sessions_count || 0
        } else {
          this.user = null
          this.isLoggedIn = false
          this.currentSessionId = ''
          this.onlineSessionCount = 0
          this.sessions = []
        }
      } catch {
        this.user = null
        this.isLoggedIn = false
        this.currentSessionId = ''
        this.onlineSessionCount = 0
        this.sessions = []
      }
    },

    async requestCode(username: string) {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ message: string }>>(`${config.public.apiBase}/api/auth/tg/request-code`, {
          method: 'POST',
          body: { tg_username: username },
          credentials: 'include',
          headers: buildClientHeaders(),
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
          headers: buildClientHeaders(),
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
          headers: buildClientHeaders(),
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
          headers: buildClientHeaders(),
        })
      } catch { /* 忽略 */ }
      this.user = null
      this.isLoggedIn = false
      this.currentSessionId = ''
      this.onlineSessionCount = 0
      this.sessions = []
    },

    async getMyTokens() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ tokens: any[] }>>(`${config.public.apiBase}/api/auth/tg/tokens`, {
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (!res.success) throw new Error(res.error || '获取 Token 列表失败')
        return res.data?.tokens || []
      } catch (e: any) {
        throw new Error(extractError(e, '获取 Token 列表失败'))
      }
    },

    async syncTokensToVault() {
      const config = useRuntimeConfig()
      const tokenStore = useTokenStore()
      try {
        const res = await $fetch<ApiResponse<{ tokens: any[] }>>(`${config.public.apiBase}/api/auth/tg/sync-tokens`, {
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (!res.success || !res.data?.tokens?.length) return

        for (const t of res.data.tokens) {
          if (!t.token) continue
          const vaultId = await tokenStore.addTokenToVault(t.token, {
            albumName: t.description || '',
            makeActive: false,
            verify: false,
          })
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
        if (!tokenStore.hasToken && tokenStore.vaultItems.length > 0) {
          await tokenStore.setActiveTokenById(tokenStore.vaultItems[0].id, { verify: true })
        } else {
          tokenStore.syncActiveFromVault()
        }
      } catch {
        // 同步失败不阻断主流程
      }
    },

    async generateWebCode(): Promise<{ code: string; bot_username: string }> {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ code: string; bot_username: string }>>(`${config.public.apiBase}/api/auth/tg/web-code`, {
          method: 'POST',
          credentials: 'include',
          headers: buildClientHeaders(),
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
          headers: buildClientHeaders(),
        })
        if (!res.success || !res.data) throw new Error(res.error || '查询状态失败')
        if (res.data.status === 'ok') {
          await this.checkSession()
        }
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '查询状态失败'))
      }
    },

    async fetchSessions() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<TgSessionListData>>(`${config.public.apiBase}/api/auth/tg/sessions`, {
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (!res.success || !res.data) throw new Error(res.error || '获取在线会话失败')
        const currentSessionId = res.data.current_session_id || this.currentSessionId
        let sessions = Array.isArray(res.data.sessions) ? [...res.data.sessions] : []
        if (!sessions.some(s => s.is_current)) {
          sessions.unshift(buildCurrentBrowserFallbackSession(currentSessionId))
        } else if (currentSessionId) {
          sessions = sessions.map(s => ({
            ...s,
            is_current: Boolean(s.is_current || s.session_id === currentSessionId)
          }))
        }

        this.sessions = sessions
        this.currentSessionId = currentSessionId || sessions.find(s => s.is_current)?.session_id || ''
        this.onlineSessionCount = Math.max(Number(res.data.count || 0), sessions.length)
        if (this.user) {
          this.user.online_sessions_count = this.onlineSessionCount
          this.user.current_session_id = this.currentSessionId
        }
        return this.sessions
      } catch (e: any) {
        throw new Error(extractError(e, '获取在线会话失败'))
      }
    },

    async revokeSession(sessionId: string) {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ revoked_session_id: string }>>(`${config.public.apiBase}/api/auth/tg/sessions/revoke`, {
          method: 'POST',
          body: { session_id: sessionId },
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (!res.success) throw new Error(res.error || '下线失败')
        this.sessions = this.sessions.filter(s => s.session_id !== sessionId)
        this.onlineSessionCount = Math.max(0, this.onlineSessionCount - 1)
        if (this.user) this.user.online_sessions_count = this.onlineSessionCount
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '下线失败'))
      }
    },

    async heartbeat() {
      const config = useRuntimeConfig()
      try {
        const res = await $fetch<ApiResponse<{ server_time: number }>>(`${config.public.apiBase}/api/auth/tg/sessions/heartbeat`, {
          method: 'POST',
          credentials: 'include',
          headers: buildClientHeaders(),
        })
        if (!res.success) throw new Error(res.error || '会话心跳失败')
        return res.data
      } catch (e: any) {
        throw new Error(extractError(e, '会话心跳失败'))
      }
    },
  }
})
