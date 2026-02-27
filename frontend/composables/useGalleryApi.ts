import { useTokenStore } from '~/stores/token'
import { createGalleryApi } from './useGalleryApiFactory'
import { parseFetchErrorData, createAccessError, hasAccessFlags, createApiErrorHandler } from './useApiError'
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
  // 显示设置字段
  layout_mode?: 'masonry' | 'grid' | 'justified'
  theme_color?: string
  show_image_info?: boolean
  allow_download?: boolean
  sort_order?: 'newest' | 'oldest' | 'filename'
  nsfw_warning?: boolean
  custom_header_text?: string
  // 运营与 SEO 字段
  card_subtitle?: string
  editor_pick_weight?: number
  homepage_expose_enabled?: boolean
  seo_title?: string
  seo_description?: string
  seo_keywords?: string
  og_image_encrypted_id?: string | null
  has_password?: boolean
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

export interface GalleryAccessUpdateBody {
  access_mode?: 'public' | 'password' | 'token'
  password?: string
  hide_from_share_all?: boolean
}

export interface GalleryTokenAccessItem {
  token: string
  token_masked: string
  description?: string
  is_active?: boolean
  token_expired?: boolean
  expires_at?: string
  created_at?: string
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

  const updateAccess = async (galleryId: number, body: GalleryAccessUpdateBody) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/auth/galleries/${galleryId}/access`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body
    })
    if (!response.success) throw new Error(response.error || '更新访问控制失败')
    return response.data.gallery as Gallery
  }

  const getTokenAccess = async (galleryId: number) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/auth/galleries/${galleryId}/access-tokens`, {
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '获取 Token 授权列表失败')
    return response.data.items as GalleryTokenAccessItem[]
  }

  const addTokenAccess = async (galleryId: number, token: string) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/auth/galleries/${galleryId}/access-tokens`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: { token }
    })
    if (!response.success) throw new Error(response.error || '添加 Token 授权失败')
  }

  const removeTokenAccess = async (galleryId: number, token: string) => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/auth/galleries/${galleryId}/access-tokens`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
      body: { token }
    })
    if (!response.success) throw new Error(response.error || '撤销 Token 授权失败')
  }

  // ===================== 特有方法 =====================

  const handleAccessError = createApiErrorHandler({ fallbackMessage: '画集不存在或分享已关闭' })

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
      handleAccessError(e)
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
      handleAccessError(e)
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
    updateAccess,
    getTokenAccess,
    addTokenAccess,
    removeTokenAccess,
    getSharedGallery,
    unlockGallery,
    getShareAllGallery,
    unlockShareAllGallery
  }
}
