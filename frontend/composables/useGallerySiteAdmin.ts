import type { ApiResponse } from '~/types/api'

/** 画集后台认证状态 */
export interface GallerySiteAuthInfo {
  authenticated: boolean
  username?: string
}

/** 画集后台设置 */
export interface GallerySiteSettings {
  gallery_site_name: string
  gallery_site_description: string
  gallery_site_enabled: boolean
  gallery_site_images_per_page: number
}

/** 画集后台 - 画集项 */
export interface AdminGallerySiteItem {
  id: number
  name: string
  description?: string
  card_subtitle?: string
  editor_pick_weight?: number
  homepage_expose_enabled?: boolean
  seo_title?: string
  seo_description?: string
  seo_keywords?: string
  og_image_encrypted_id?: string | null
  layout_mode?: 'masonry' | 'grid' | 'justified'
  theme_color?: string
  show_image_info?: boolean
  allow_download?: boolean
  sort_order?: 'newest' | 'oldest' | 'filename'
  nsfw_warning?: boolean
  custom_header_text?: string
  image_count: number
  cover_url?: string
  cover_image?: string
  share_enabled: boolean
  share_token?: string
  share_url?: string
  access_mode: string
  has_password?: boolean
  hide_from_share_all?: boolean
  created_at: string
  updated_at: string
}

/** 画集后台 - 画集列表响应 */
interface AdminGalleriesResponse {
  items: AdminGallerySiteItem[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

/** 画集详情响应 */
interface GalleryDetailResponse {
  gallery: AdminGallerySiteItem
  images: {
    items: GalleryImageItem[]
    total: number
    page: number
    per_page: number
    has_more: boolean
  }
}

/** 画集图片项 */
export interface GalleryImageItem {
  encrypted_id: string
  original_filename?: string
  file_size?: number
  mime_type?: string
  created_at?: string
  added_at?: string
  url?: string
  cdn_url?: string
  cdn_cached?: boolean
}

/** Token 授权项 */
export interface TokenAccessItem {
  token: string
  token_masked: string
  description?: string
  is_active?: boolean
  token_expired?: boolean
  expires_at?: string
  created_at?: string
}

export interface GallerySiteHomeConfig {
  hero_mode: 'auto' | 'manual'
  hero_gallery_id?: number | null
  mobile_items_per_section: number
  desktop_items_per_section: number
  enable_recent_strip: boolean
}

export interface GallerySiteHomeSection {
  id: number
  section_key: string
  title: string
  subtitle?: string
  description?: string
  enabled: boolean
  display_order: number
  max_items: number
  source_mode: 'hybrid' | 'manual' | 'auto'
  auto_sort: 'updated_desc' | 'image_count_desc' | 'editor_pick_desc' | 'created_desc' | 'name_asc'
  auto_window_days: number
  items?: AdminGallerySiteItem[]
  item_ids?: number[]
}

/**
 * 画集后台管理 API 封装
 * 用于画集域名下的管理后台，需要 SSO 认证
 */
export const useGallerySiteAdmin = () => {
  const config = useRuntimeConfig()
  const baseURL = (config.public.apiBase || '').replace(/\/$/, '')

  const resolveApiPath = (path: string) => {
    if (!baseURL) return path
    if (baseURL.endsWith('/api') && path.startsWith('/api/')) {
      return `${baseURL}${path.slice(4)}`
    }
    return `${baseURL}${path}`
  }

  /** 检查认证状态 */
  const checkAuth = async (): Promise<GallerySiteAuthInfo> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/check'), {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '检查认证状态失败')
    return response.data as GallerySiteAuthInfo
  }

  /** 使用 SSO token 认证 */
  const authWithToken = async (token: string): Promise<void> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/auth'), {
      method: 'POST',
      credentials: 'include',
      body: { token }
    })
    if (!response?.success) throw new Error(response?.error || 'SSO 认证失败')
  }

  /** 登出 */
  const logout = async (): Promise<void> => {
    await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/logout'), {
      method: 'POST',
      credentials: 'include'
    })
  }

  /** 获取站点设置 */
  const getSettings = async (): Promise<GallerySiteSettings> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/settings'), {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取设置失败')
    return response.data as GallerySiteSettings
  }

  /** 更新站点设置 */
  const updateSettings = async (data: Partial<GallerySiteSettings>): Promise<void> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/settings'), {
      method: 'PUT',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新设置失败')
  }

  /** 获取画集列表 */
  const getGalleries = async (page = 1, perPage = 20): Promise<AdminGalleriesResponse> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/galleries'), {
      credentials: 'include',
      params: { page, per_page: perPage }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集列表失败')
    return response.data as AdminGalleriesResponse
  }

  /** 更新画集 */
  const updateGallery = async (id: number, data: Partial<AdminGallerySiteItem> & {
    share_enabled?: boolean
    access_mode?: string
    name?: string
    description?: string
    layout_mode?: 'masonry' | 'grid' | 'justified'
    theme_color?: string
    show_image_info?: boolean
    allow_download?: boolean
    sort_order?: 'newest' | 'oldest' | 'filename'
    nsfw_warning?: boolean
    custom_header_text?: string
    editor_pick_weight?: number
    homepage_expose_enabled?: boolean
    card_subtitle?: string
    seo_title?: string
    seo_description?: string
    seo_keywords?: string
    og_image_encrypted_id?: string | null
  }): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}`), {
      method: 'PATCH',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新画集失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 获取画集详情（含图片列表） */
  const getGalleryDetail = async (id: number, page = 1, perPage = 50): Promise<GalleryDetailResponse> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/detail`), {
      credentials: 'include',
      params: { page, per_page: perPage }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集详情失败')
    return response.data as GalleryDetailResponse
  }

  /** 删除画集 */
  const deleteGallery = async (id: number): Promise<void> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}`), {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '删除画集失败')
  }

  /** 开启分享 */
  const enableShare = async (id: number): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/share`), {
      method: 'POST',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '开启分享失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 关闭分享 */
  const disableShare = async (id: number): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/share`), {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '关闭分享失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 更新访问控制 */
  const updateAccess = async (id: number, data: { access_mode?: string; password?: string; hide_from_share_all?: boolean }): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/access`), {
      method: 'PATCH',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新访问控制失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 获取 Token 授权列表 */
  const getTokenAccess = async (id: number): Promise<TokenAccessItem[]> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/access-tokens`), {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取 Token 授权列表失败')
    return (response.data as any).items as TokenAccessItem[]
  }

  /** 添加 Token 授权 */
  const addTokenAccess = async (id: number, token: string): Promise<void> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/access-tokens`), {
      method: 'POST',
      credentials: 'include',
      body: { token }
    })
    if (!response?.success) throw new Error(response?.error || '添加 Token 授权失败')
  }

  /** 撤销 Token 授权 */
  const removeTokenAccess = async (id: number, token: string): Promise<void> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/access-tokens`), {
      method: 'DELETE',
      credentials: 'include',
      body: { token }
    })
    if (!response?.success) throw new Error(response?.error || '撤销 Token 授权失败')
  }

  /** 获取画集图片列表 */
  const getGalleryImages = async (id: number, page = 1, perPage = 50) => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/images`), {
      credentials: 'include',
      params: { page, per_page: perPage }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集图片失败')
    return response.data as { items: GalleryImageItem[]; total: number; page: number; per_page: number; has_more: boolean }
  }

  /** 添加图片到画集 */
  const addImagesToGallery = async (id: number, encryptedIds: string[]) => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/images`), {
      method: 'POST',
      credentials: 'include',
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '添加图片失败')
    return response.data as { added: number; skipped: number; not_found: string[] }
  }

  /** 从画集移除图片 */
  const removeImagesFromGallery = async (id: number, encryptedIds: string[]) => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/images`), {
      method: 'DELETE',
      credentials: 'include',
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '移除图片失败')
    return (response.data as any).removed as number
  }

  /** 设置画集封面 */
  const setCover = async (id: number, encryptedId: string): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/cover`), {
      method: 'PUT',
      credentials: 'include',
      body: { encrypted_id: encryptedId }
    })
    if (!response?.success) throw new Error(response?.error || '设置封面失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 清除画集封面 */
  const clearCover = async (id: number): Promise<AdminGallerySiteItem> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/galleries/${id}/cover`), {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '清除封面失败')
    return (response.data as any).gallery as AdminGallerySiteItem
  }

  /** 获取首页全局编排配置 */
  const getHomeConfigAdmin = async (): Promise<GallerySiteHomeConfig> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/home-config'), {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取首页配置失败')
    return response.data as GallerySiteHomeConfig
  }

  /** 更新首页全局编排配置 */
  const updateHomeConfigAdmin = async (data: Partial<GallerySiteHomeConfig>): Promise<GallerySiteHomeConfig> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/home-config'), {
      method: 'PUT',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新首页配置失败')
    return response.data as GallerySiteHomeConfig
  }

  /** 获取首页分区配置 */
  const getHomeSections = async (): Promise<GallerySiteHomeSection[]> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/admin/home-sections'), {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取首页分区失败')
    return (response.data as any).sections as GallerySiteHomeSection[]
  }

  /** 更新首页分区 */
  const updateHomeSection = async (sectionKey: string, data: Partial<GallerySiteHomeSection>): Promise<GallerySiteHomeSection> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/home-sections/${sectionKey}`), {
      method: 'PATCH',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新首页分区失败')
    return (response.data as any).section as GallerySiteHomeSection
  }

  /** 替换首页分区手动编排项 */
  const replaceHomeSectionItems = async (sectionKey: string, galleryIds: number[]) => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/admin/home-sections/${sectionKey}/items`), {
      method: 'PUT',
      credentials: 'include',
      body: { gallery_ids: galleryIds }
    })
    if (!response?.success) throw new Error(response?.error || '更新分区编排失败')
    return response.data as {
      section: GallerySiteHomeSection
      saved_gallery_ids: number[]
      ignored_gallery_ids: number[]
    }
  }

  return {
    checkAuth, authWithToken, logout,
    getSettings, updateSettings,
    getGalleries, updateGallery,
    getGalleryDetail, deleteGallery,
    enableShare, disableShare,
    updateAccess,
    getTokenAccess, addTokenAccess, removeTokenAccess,
    getGalleryImages, addImagesToGallery, removeImagesFromGallery,
    setCover, clearCover,
    getHomeConfigAdmin, updateHomeConfigAdmin,
    getHomeSections, updateHomeSection, replaceHomeSectionItems
  }
}
