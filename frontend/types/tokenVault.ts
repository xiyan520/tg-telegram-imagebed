/**
 * Token Vault 类型定义
 * 支持本地存储多个Token并切换
 */

/** Token验证信息 */
export interface TokenInfo {
  upload_count: number
  upload_limit: number
  remaining_uploads: number
  expires_at: string
  created_at: string
  last_used: string | null
  can_upload?: boolean
  description?: string | null
  tg_user_id?: number | null
}

/** Token Vault 单项 */
export interface TokenVaultItem {
  id: string
  token: string
  albumName: string
  addedAt: string
  lastSelectedAt?: string
  lastVerifiedAt?: string
  tokenInfo?: TokenInfo
}

/** Token Vault 持久化结构 v1 */
export interface TokenVaultPersistedV1 {
  version: 1
  activeId: string | null
  items: TokenVaultItem[]
}
