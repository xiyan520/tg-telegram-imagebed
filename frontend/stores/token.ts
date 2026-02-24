import { defineStore } from 'pinia'
import type { TokenInfo, TokenVaultItem, TokenVaultPersistedV1 } from '~/types/tokenVault'
import type { ApiResponse, TokenGenerateResult, TokenVerifyData, TokenUploadsData } from '~/types/api'

const VAULT_STORAGE_KEY = 'token_vault_v1'
const LEGACY_TOKEN_KEY = 'guest_token'
const LEGACY_IS_GUEST_KEY = 'is_guest'

const nowIso = () => new Date().toISOString()

export const maskToken = (token: string) => {
  const t = (token || '').trim()
  if (t.length <= 12) return t
  return `${t.slice(0, 8)}…${t.slice(-4)}`
}

const safeParse = <T,>(raw: string | null, fallback: T): T => {
  try {
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

const newId = () => {
  const c = globalThis.crypto as any
  if (c?.randomUUID) return c.randomUUID()
  return `id_${Math.random().toString(16).slice(2)}_${Date.now()}`
}

export const useTokenStore = defineStore('token', {
  state: () => ({
    vault: {
      version: 1 as const,
      activeId: null as string | null,
      items: [] as TokenVaultItem[]
    } satisfies TokenVaultPersistedV1,

    // 向后兼容：保留这些字段作为"当前激活Token"视图
    token: '',
    tokenInfo: null as TokenInfo | null,
    isGuest: true
  }),

  getters: {
    vaultItems: (state) => state.vault.items,
    activeVaultId: (state) => state.vault.activeId,
    activeVaultItem: (state) => state.vault.items.find(i => i.id === state.vault.activeId) || null,

    hasToken: (state) => !!state.token,
    activeAlbumLabel: (state) => {
      const item = state.vault.items.find(i => i.id === state.vault.activeId)
      if (!item) return ''
      const name = (item.albumName || '').trim()
      return name || '未命名相册'
    },
    activeAlbumLabelWithToken: (state) => {
      const item = state.vault.items.find(i => i.id === state.vault.activeId)
      if (!item) return ''
      const name = (item.albumName || '').trim()
      return `${name || '未命名相册'} (${maskToken(item.token)})`
    },

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
    persistVault() {
      if (!import.meta.client) return
      localStorage.setItem(VAULT_STORAGE_KEY, JSON.stringify(this.vault))
    },

    loadVault() {
      if (!import.meta.client) return
      const raw = localStorage.getItem(VAULT_STORAGE_KEY)
      const parsed = safeParse<TokenVaultPersistedV1 | null>(raw, null)
      if (parsed?.version === 1 && Array.isArray(parsed.items)) {
        const validItems = parsed.items
          .filter(i => i && typeof i.id === 'string' && typeof i.token === 'string')
          .map(i => ({
            id: i.id,
            token: (i.token || '').trim(),
            albumName: typeof i.albumName === 'string' ? i.albumName : '',
            addedAt: i.addedAt || nowIso(),
            lastSelectedAt: i.lastSelectedAt,
            lastVerifiedAt: i.lastVerifiedAt,
            tokenInfo: i.tokenInfo
          }))

        // 验证 activeId 是否有效，无效则自动选择第一个
        let activeId = parsed.activeId || null
        if (activeId && !validItems.some(i => i.id === activeId)) {
          activeId = validItems[0]?.id || null
        }

        this.vault = {
          version: 1,
          activeId,
          items: validItems
        }
      }
    },

    importLegacySingleTokenIfNeeded() {
      if (!import.meta.client) return
      const legacyToken = (localStorage.getItem(LEGACY_TOKEN_KEY) || '').trim()
      const legacyIsGuest = localStorage.getItem(LEGACY_IS_GUEST_KEY) === 'true'
      if (!legacyToken || !legacyIsGuest) return

      const exists = this.vault.items.some(i => i.token === legacyToken)
      if (!exists) {
        const item: TokenVaultItem = {
          id: newId(),
          token: legacyToken,
          albumName: '',
          addedAt: nowIso()
        }
        this.vault.items.unshift(item)
        this.vault.activeId = item.id
        this.persistVault()
      }

      localStorage.removeItem(LEGACY_TOKEN_KEY)
      localStorage.removeItem(LEGACY_IS_GUEST_KEY)
    },

    syncActiveFromVault() {
      const active = this.vault.items.find(i => i.id === this.vault.activeId) || null
      this.token = active?.token || ''
      this.tokenInfo = active?.tokenInfo || null
      this.isGuest = true
    },

    async setActiveTokenById(id: string, opts?: { verify?: boolean }) {
      const item = this.vault.items.find(i => i.id === id)
      if (!item) throw new Error('Token不存在')
      this.vault.activeId = item.id
      item.lastSelectedAt = nowIso()
      this.persistVault()
      this.syncActiveFromVault()
      if (opts?.verify) return this.verifyToken()
    },

    updateAlbumName(id: string, albumName: string) {
      const item = this.vault.items.find(i => i.id === id)
      if (!item) throw new Error('Token不存在')
      item.albumName = (albumName || '').slice(0, 50)
      this.persistVault()
    },

    removeTokenFromVault(id: string) {
      const idx = this.vault.items.findIndex(i => i.id === id)
      if (idx < 0) return
      const removingActive = this.vault.activeId === id
      this.vault.items.splice(idx, 1)

      if (removingActive) {
        this.vault.activeId = this.vault.items[0]?.id || null
      }
      this.persistVault()
      this.syncActiveFromVault()
    },

    async addTokenToVault(token: string, opts?: { albumName?: string; makeActive?: boolean; verify?: boolean }) {
      const t = (token || '').trim()
      if (!t) throw new Error('Token不能为空')

      // 先验证 Token 有效性，无效则不添加
      if (opts?.verify) {
        const config = useRuntimeConfig()
        const response = await $fetch<any>(`${config.public.apiBase}/api/auth/token/verify`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${t}` }
        })
        if (!response?.success || !response?.valid) {
          const err: any = new Error(response?.reason || 'Token无效或不存在')
          err.tokenInvalid = true
          throw err
        }
      }

      const existing = this.vault.items.find(i => i.token === t)
      if (existing) {
        if (typeof opts?.albumName === 'string') existing.albumName = opts.albumName.slice(0, 50)
        if (opts?.makeActive) {
          this.vault.activeId = existing.id
          existing.lastSelectedAt = nowIso()
        }
        this.persistVault()
        this.syncActiveFromVault()
        if (opts?.verify) await this.verifyToken()
        return existing.id
      }

      const item: TokenVaultItem = {
        id: newId(),
        token: t,
        albumName: typeof opts?.albumName === 'string' ? opts.albumName.slice(0, 50) : '',
        addedAt: nowIso()
      }
      this.vault.items.unshift(item)
      if (opts?.makeActive !== false) {
        this.vault.activeId = item.id
        item.lastSelectedAt = nowIso()
      }
      this.persistVault()
      this.syncActiveFromVault()
      // 已在上面验证过，这里同步 tokenInfo
      if (opts?.verify) await this.verifyToken()
      return item.id
    },

    // 生成新的游客token
    async generateToken(options?: { upload_limit?: number; expires_days?: number; albumName?: string }) {
      const config = useRuntimeConfig()

      try {
        // 只传递用户明确指定的参数，否则让后端使用默认值
        const body: Record<string, any> = {}
        if (options?.upload_limit != null) body.upload_limit = options.upload_limit
        if (options?.expires_days != null) body.expires_days = options.expires_days
        if (options?.albumName) body.description = options.albumName

        const response = await $fetch<ApiResponse<TokenGenerateResult>>(`${config.public.apiBase}/api/auth/token/generate`, {
          method: 'POST',
          body,
          credentials: 'include',
        })

        if (response.success && response.data) {
          await this.addTokenToVault(response.data.token, {
            albumName: options?.albumName || '',
            makeActive: true,
            verify: true
          })
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

      // 5 分钟缓存：如果最近验证过且有 tokenInfo，跳过 API 调用
      const active = this.vault.items.find(i => i.id === this.vault.activeId)
      if (active?.lastVerifiedAt && active.tokenInfo) {
        const elapsed = Date.now() - new Date(active.lastVerifiedAt).getTime()
        if (elapsed < 5 * 60 * 1000) {
          this.tokenInfo = active.tokenInfo
          return active.tokenInfo
        }
      }

      const config = useRuntimeConfig()

      try {
        const response = await $fetch<ApiResponse<TokenVerifyData> & { valid?: boolean; reason?: string }>(`${config.public.apiBase}/api/auth/token/verify`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })

        if (response.success && response.valid) {
          this.tokenInfo = response.data
          const active = this.vault.items.find(i => i.id === this.vault.activeId)
          if (active) {
            active.tokenInfo = response.data
            active.lastVerifiedAt = nowIso()
            this.persistVault()
          }
          return response.data
        } else {
          // Token 确实无效（后端明确返回 valid=false）
          const err: any = new Error(response.reason || 'Token无效')
          err.tokenInvalid = true
          throw err
        }
      } catch (error: any) {
        // 保留 tokenInvalid 标记
        if (error.tokenInvalid) throw error
        // 网络/服务器错误，不标记为 tokenInvalid
        throw new Error(error.data?.reason || error.message || 'Token验证失败')
      }
    },

    // 刷新token(重新生成)
    async refreshToken(options?: { upload_limit?: number; expires_days?: number }) {
      this.clearToken()
      return await this.generateToken(options)
    },

    // 清除当前激活的token（不删除vault中的记录）
    clearToken() {
      this.vault.activeId = null
      this.persistVault()
      this.syncActiveFromVault()
    },

    // 清空整个 vault（退出登录时使用，仅清本地）
    clearVault() {
      this.vault.items = []
      this.vault.activeId = null
      this.persistVault()
      this.syncActiveFromVault()
    },

    // 从 localStorage 恢复token
    async restoreToken() {
      if (import.meta.client) {
        this.loadVault()
        this.importLegacySingleTokenIfNeeded()
        this.syncActiveFromVault()
        if (this.token) {
          try {
            await this.verifyToken()
          } catch (e: any) {
            // 仅在 Token 确实无效时自动移除（网络错误不移除）
            if (e?.tokenInvalid) {
              const failedId = this.vault.activeId
              if (failedId) {
                this.removeTokenFromVault(failedId)
              }
            }
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
        const response = await $fetch<ApiResponse<TokenUploadsData>>(`${config.public.apiBase}/api/auth/uploads`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.token}`
          },
          params: { page, limit, _t: Date.now() }
        })

        if (response.success) {
          if (response.data.total_uploads !== undefined) {
            // 更新当前 tokenInfo
            if (this.tokenInfo) {
              this.tokenInfo.upload_count = response.data.total_uploads
              this.tokenInfo.remaining_uploads = response.data.remaining_uploads
              this.tokenInfo.can_upload = response.data.can_upload
            }
            // 同步更新 vault 中的 tokenInfo
            const active = this.vault.items.find(i => i.id === this.vault.activeId)
            if (active && active.tokenInfo) {
              active.tokenInfo.upload_count = response.data.total_uploads
              active.tokenInfo.remaining_uploads = response.data.remaining_uploads
              active.tokenInfo.can_upload = response.data.can_upload
              this.persistVault()
            }
          }
          return response.data
        } else {
          throw new Error(response.error || '获取上传历史失败')
        }
      } catch (error: any) {
        throw new Error(error.data?.error || error.message || '获取上传历史失败')
      }
    },

    // 从服务器删除所有 vault 中的 Token（退出登录时使用）
    async deleteAllTokensFromServer(opts?: { deleteImages?: boolean }) {
      const config = useRuntimeConfig()
      const items = [...this.vault.items]
      const qs = opts?.deleteImages ? '?delete_images=true' : ''
      for (const item of items) {
        try {
          await $fetch(`${config.public.apiBase}/api/auth/token${qs}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${item.token}` }
          })
        } catch {
          // 静默忽略单个删除失败（Token 可能已失效）
        }
      }
      // 清空本地 vault
      this.vault.items = []
      this.vault.activeId = null
      this.persistVault()
      this.syncActiveFromVault()
    },

    // 从服务器删除 Token（级联删除，可选同时删除图片）
    async deleteTokenFromServer(vaultId: string, opts?: { deleteImages?: boolean }) {
      const item = this.vault.items.find(i => i.id === vaultId)
      if (!item) return

      const config = useRuntimeConfig()
      const qs = opts?.deleteImages ? '?delete_images=true' : ''
      await $fetch(`${config.public.apiBase}/api/auth/token${qs}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${item.token}` }
      })

      // 后端删除成功后，从本地 vault 移除
      this.removeTokenFromVault(vaultId)
    },

    // 更新相册描述（同步到服务器）
    async updateDescription(description: string) {
      if (!this.token) throw new Error('未提供Token')
      const config = useRuntimeConfig()
      const response = await $fetch<ApiResponse<{ token: string; description: string }>>(`${config.public.apiBase}/api/auth/token`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${this.token}` },
        body: { description }
      })
      if (!response?.success) throw new Error(response?.error || '更新失败')

      // 同步到本地vault
      const active = this.vault.items.find(i => i.id === this.vault.activeId)
      if (active) {
        active.albumName = description
        if (active.tokenInfo) active.tokenInfo.description = description
        this.persistVault()
      }
      if (this.tokenInfo) this.tokenInfo.description = description
      return response.data
    }
  }
})
