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
}

/** Token 列表分页响应 */
export interface TokenListData {
  page: number
  page_size: number
  total: number
  items: AdminTokenItem[]
}
