import { useTokenStore } from '~/stores/token'
import { createGalleryApi } from './useGalleryApiFactory'
import type { ApiResponse } from '~/types/api'

export interface Gallery {
  id: number
  owner_type?: string
  owner_token?: string
  name: string
  description?: string
  image_count: number
  cover_image?: string
  cover_url?: string
  share_enabled: boolean
  share_token?: string
  share_url?: string
  share_expires_at?: string
  access_mode?: string
  hide_from_share_all?: boolean
  created_at: string
  updated_at: string
}

export interface GalleryImage {
  encrypted_id: string
  original_filename: string
  file_size: number
  created_at: string
  cdn_cached: boolean
  cdn_url?: string
  mime_type: string
  image_url: string
  added_at: string
}

export const useGalleryApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  let _tokenStore: ReturnType<typeof useTokenStore> | null = null
  const getGuestStore = () => {
    if (!_tokenStore) _tokenStore = useTokenStore()
    return _tokenStore
  }

  const getAuthHeaders = () => {
    const token = getGuestStore().token
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // 通过工厂函数获取通用方法
  const base = createGalleryApi('/api/auth/galleries', () => ({
    headers: getAuthHeaders()
  }))

  // 覆盖 getGalleries：需要额外的 token 检查
  const getGalleries = async (page = 1, limit = 50) => {
    const token = getGuestStore().token
    if (!token) throw new Error('未提供Token')
    return base.getGalleries(page, limit)
  }

  // 覆盖 addImagesToGallery：返回值多了 not_owned 字段
  const addImagesToGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/auth/galleries/${galleryId}/images`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: { encrypted_ids: encryptedIds }
    })
    if (!response.success) throw new Error(response.error || '添加图片失败')
    return response.data as { added: number; skipped: number; not_found: string[]; not_owned: string[] }
  }

  // ===================== 特有方法 =====================

  // 解析 FetchError 响应数据（处理字符串/对象/嵌套结构）
  const parseFetchErrorData = (e: any): Record<string, any> => {
    const raw = e?.data ?? e?.response?._data
    if (raw == null) return {}
    if (typeof raw === 'string') {
      try { return JSON.parse(raw) } catch { return { error: raw } }
    }
    // 处理嵌套 { data: {...} } 结构
    if (raw.data && typeof raw.data === 'object') return raw.data
    return raw
  }

  // 创建带访问控制信息的错误
  const createAccessError = (data: Record<string, any>, fallbackMsg: string, originalError?: any): Error & Record<string, any> => {
    const err: any = new Error(data.error || originalError?.message || fallbackMsg)
    err.requires_password = data.requires_password
    err.requires_token = data.requires_token
    err.gallery_id = data.gallery_id
    err.gallery_name = data.gallery_name
    return err
  }

  // 检查错误是否已包含访问控制信息
  const hasAccessFlags = (e: any): boolean =>
    e && typeof e === 'object' && ('requires_token' in e || 'requires_password' in e)

  // 获取分享画集（公开访问）
  const getSharedGallery = async (shareToken: string, page = 1, limit = 50) => {
    try {
      const response = await $fetch<ApiResponse>(`${baseURL}/api/shared/galleries/${shareToken}`, {
        params: { page, limit },
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (!response.success) {
        const err: any = new Error(response.error || '画集不存在或分享已关闭')
        err.requires_password = response.requires_password
        err.requires_token = response.requires_token
        err.gallery_id = response.gallery_id
        err.gallery_name = response.gallery_name
        throw err
      }
      return response.data as {
        gallery: { name: string; description?: string; image_count: number }
        images: GalleryImage[]
        total: number
        page: number
        limit: number
        has_more: boolean
      }
    } catch (e: any) {
      if (hasAccessFlags(e)) throw e
      const data = parseFetchErrorData(e)
      throw createAccessError(data, '画集不存在或分享已关闭', e)
    }
  }

  // 密码解锁画集
  const unlockGallery = async (shareToken: string, password: string) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/shared/galleries/${shareToken}/unlock`, {
      method: 'POST',
      body: { password },
      credentials: 'include'
    })
    if (!response.success) throw new Error(response.error || '密码错误')
    return true
  }

  // ===================== 全部分享 API =====================

  // 获取全部分享中的单个画集
  const getShareAllGallery = async (shareAllToken: string, galleryId: number, page = 1, limit = 50) => {
    try {
      const response = await $fetch<ApiResponse>(`${baseURL}/api/shared/all/${shareAllToken}/galleries/${galleryId}`, {
        params: { page, limit },
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (!response.success) {
        const err: any = new Error(response.error || '画集不存在或分享已关闭')
        err.requires_password = response.requires_password
        err.requires_token = response.requires_token
        err.gallery_id = response.gallery_id
        err.gallery_name = response.gallery_name
        throw err
      }
      return response.data as {
        gallery: { id: number; name: string; description?: string; image_count: number; access_mode: string }
        images: GalleryImage[]
        total: number
        page: number
        limit: number
        has_more: boolean
      }
    } catch (e: any) {
      if (hasAccessFlags(e)) throw e
      const data = parseFetchErrorData(e)
      throw createAccessError(data, '画集不存在或分享已关闭', e)
    }
  }

  // 全部分享中解锁画集
  const unlockShareAllGallery = async (shareAllToken: string, galleryId: number, password: string) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/shared/all/${shareAllToken}/galleries/${galleryId}/unlock`, {
      method: 'POST',
      body: { password },
      credentials: 'include'
    })
    if (!response.success) throw new Error(response.error || '密码错误')
    return true
  }

  return {
    ...base,
    getGalleries,
    addImagesToGallery,
    getSharedGallery,
    unlockGallery,
    getShareAllGallery,
    unlockShareAllGallery
  }
}
