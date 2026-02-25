/**
 * API 错误处理工厂
 * 统一处理访问控制相关的错误解析和创建
 */

export interface AccessControlError extends Error {
  requires_password?: boolean
  requires_token?: boolean
  gallery_id?: number
  gallery_name?: string
}

export interface ApiErrorHandlerOptions {
  /** 默认错误消息 */
  fallbackMessage: string
}

/**
 * 解析 FetchError 响应数据（处理字符串/对象/嵌套结构）
 */
export const parseFetchErrorData = (e: any): Record<string, any> => {
  const raw = e?.data ?? e?.response?._data
  if (raw == null) return {}
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return { error: raw } }
  }
  // 处理嵌套 { data: {...} } 结构
  if (raw.data && typeof raw.data === 'object') return raw.data
  return raw
}

/**
 * 创建带访问控制信息的错误
 */
export const createAccessError = (
  data: Record<string, any>,
  fallbackMsg: string,
  originalError?: any
): AccessControlError => {
  const err: any = new Error(data.error || originalError?.message || fallbackMsg)
  err.requires_password = data.requires_password
  err.requires_token = data.requires_token
  err.gallery_id = data.gallery_id
  err.gallery_name = data.gallery_name
  return err as AccessControlError
}

/**
 * 检查错误是否已包含访问控制信息
 */
export const hasAccessFlags = (e: any): boolean =>
  e && typeof e === 'object' && ('requires_token' in e || 'requires_password' in e)

/**
 * 创建 API 错误处理器工厂函数
 * 用于统一处理访问控制错误的 catch 块
 */
export const createApiErrorHandler = (options: ApiErrorHandlerOptions) => {
  return (e: any): never => {
    if (hasAccessFlags(e)) throw e
    const data = parseFetchErrorData(e)
    throw createAccessError(data, options.fallbackMessage, e)
  }
}
