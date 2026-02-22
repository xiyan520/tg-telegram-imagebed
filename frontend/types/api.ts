/**
 * 前端 API 类型定义
 * 基于后端实际返回的 JSON 结构
 */

// ===================== 通用响应 =====================

/** 通用 API 响应包装 */
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// ===================== 上传相关 =====================

/** 匿名上传结果（POST /api/upload） */
export interface UploadResult {
  url: string
  filename: string
  size: string
  upload_time: string
}

/** Token 上传结果（POST /api/auth/upload） */
export interface TokenUploadResult extends UploadResult {
  remaining_uploads: number
}

// ===================== 图片相关 =====================

/** 公共统计信息（GET /api/stats） */
export interface PublicStats {
  totalFiles: string
  totalSize: string
  todayUploads: string
  uptime: string
}

/** 管理员统计信息（GET /api/admin/stats） */
export interface AdminStatsData {
  stats: AdminStats
  config: AdminConfig
}

export interface AdminStats {
  totalImages: number
  totalSize: string
  todayUploads: number
  cdnCached: number
}

export interface AdminConfig {
  cdnStatus: string
  cdnDomain: string
  uptime: string
  groupUpload: string
  cdnMonitor: string
}

/** 管理员图片列表项（GET /api/admin/images） */
export interface AdminImageItem {
  encrypted_id: string
  file_id: string
  original_filename: string
  file_size: number
  source: string
  created_at: string
  username: string
  access_count: number
  last_accessed: string | null
  upload_time: number
  cdn_cached: boolean
  cdn_cache_time: string | null
  mime_type: string
  is_group_upload: number
  cdn_hit_count: number
  direct_hit_count: number
  url: string
  cdn_url: string | null
  id: string
  filename: string
  size: number
  uploadTime: string
  cached: boolean
}

/** 管理员图片列表响应 */
export interface AdminImagesData {
  images: AdminImageItem[]
  totalPages: number
  total: number
  page: number
  limit: number
}

/** 管理员删除图片响应 */
export interface AdminDeleteData {
  deleted: number
  tg_deleted: number
  message: string
}

// ===================== Token 认证相关 =====================

/** Token 生成结果（POST /api/auth/token/generate） */
export interface TokenGenerateResult {
  token: string
  upload_limit: number
  expires_days: number
  expires_at: string | null
  message: string
}

/** Token 验证结果（POST /api/auth/token/verify） */
export interface TokenVerifyData {
  upload_count: number
  upload_limit: number
  remaining_uploads: number
  can_upload: boolean
  description: string | null
  expires_at: string
  created_at: string
  last_used: string | null
  tg_user_id?: number | null
}

/** Token 上传历史响应（GET /api/auth/uploads） */
export interface TokenUploadsData {
  uploads: TokenUploadItem[]
  total_uploads: number
  upload_limit: number
  remaining_uploads: number
  can_upload: boolean
  page: number
  limit: number
  has_more: boolean
}

export interface TokenUploadItem {
  encrypted_id: string
  original_filename: string
  file_size: number
  created_at: string
  mime_type: string
  image_url: string
  cdn_cached: number
}

// ===================== 管理员登录相关 =====================

/** 管理员登录结果（POST /api/admin/login） */
export interface AdminLoginData {
  token: string
  username: string
}

/** 管理员登录检查（GET /api/admin/check） */
export interface AdminCheckResponse {
  authenticated: boolean
  username?: string
}

/** 管理员登录失败响应 */
export interface AdminLoginErrorResponse {
  success: false
  message: string
  locked?: boolean
  retry_after?: number
  remaining_attempts?: number
}

/** 管理员凭据更新响应 */
export interface AdminUpdateCredentialsData {
  success: boolean
  message: string
  updated_username: boolean
  updated_password: boolean
}
