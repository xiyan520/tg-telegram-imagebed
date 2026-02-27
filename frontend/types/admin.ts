/**
 * 管理后台相关类型定义
 */

/** Token 管理列表项 */
export interface AdminTokenItem {
  id: number
  token_masked: string
  description?: string | null
  created_at: string
  expires_at?: string | null
  upload_count: number
  upload_limit?: number | null
  is_active: boolean
  is_expired?: boolean
  tg_user_id?: number | null
  tg_username?: string | null
  tg_first_name?: string | null
  last_used?: string | null
}

/** Token 列表分页响应 */
export interface TokenListData {
  page: number
  page_size: number
  total: number
  items: AdminTokenItem[]
}

export type TokenSortBy = 'created_at' | 'upload_count' | 'expires_at' | 'last_used'
export type TokenSortOrder = 'asc' | 'desc'

export interface AdminTokenMetrics {
  total: number
  active: number
  expired: number
  disabled: number
  tg_bound: number
}

export interface AdminTokenDetail extends AdminTokenItem {
  token: string
  ip_address?: string | null
  user_agent?: string | null
  tg_last_name?: string | null
}

export interface AdminTokenOverviewSummary {
  upload_total: number
  gallery_total: number
  access_total: number
  last_upload_at?: string | null
  last_gallery_at?: string | null
}

export interface AdminTokenOverview extends AdminTokenDetail {
  summary?: AdminTokenOverviewSummary
}
