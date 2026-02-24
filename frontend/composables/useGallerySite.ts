import type { ApiResponse } from '~/types/api'

/** 画集站点模式信息 */
export interface SiteModeInfo {
  mode: 'gallery' | 'default'
  site_name?: string
  site_description?: string
}

/** 画集站点 - 画集列表项 */
export interface GallerySiteItem {
  id: number
  name: string
  description?: string
  image_count: number
  cover_image?: string
  cover_url?: string
  created_at: string
  updated_at: string
}

/** 画集站点 - 图片项 */
export interface GallerySiteImage {
  encrypted_id: string
  original_filename: string
  file_size: number
  mime_type: string
  created_at: string
  added_at: string
  url: string
}

/** 画集站点 - 统计数据 */
export interface GallerySiteStats {
  gallery_count: number
  image_count: number
}

/** 画集站点 - 画集列表响应 */
interface GalleriesResponse {
  items: GallerySiteItem[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

/** 画集站点 - 画集详情响应 */
interface GalleryDetailResponse {
  gallery: GallerySiteItem
  images: {
    items: GallerySiteImage[]
    total: number
    page: number
    per_page: number
    has_more: boolean
  }
}

/**
 * 画集站点公开 API 封装
 * 用于画集域名下的公开浏览，无需认证
 */
export const useGallerySiteApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  /** 检测站点模式 */
  const getSiteMode = async (): Promise<SiteModeInfo> => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/public/site-mode`)
    if (!response?.success) throw new Error(response?.error || '检测站点模式失败')
    return response.data as SiteModeInfo
  }

  /** 获取公开画集列表 */
  const getGalleries = async (page = 1, perPage = 20): Promise<GalleriesResponse> => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/gallery-site/galleries`, {
      params: { page, per_page: perPage }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集列表失败')
    return response.data as GalleriesResponse
  }

  /** 获取画集详情 + 图片列表 */
  const getGallery = async (id: number, page = 1): Promise<GalleryDetailResponse> => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/gallery-site/galleries/${id}`, {
      params: { page }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集详情失败')
    return response.data as GalleryDetailResponse
  }

  /** 获取精选画集 */
  const getFeatured = async (limit = 6): Promise<GallerySiteItem[]> => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/gallery-site/featured`, {
      params: { limit }
    })
    if (!response?.success) throw new Error(response?.error || '获取精选画集失败')
    return response.data as GallerySiteItem[]
  }

  /** 获取站点统计 */
  const getStats = async (): Promise<GallerySiteStats> => {
    const response = await $fetch<ApiResponse>(`${baseURL}/api/gallery-site/stats`)
    if (!response?.success) throw new Error(response?.error || '获取统计失败')
    return response.data as GallerySiteStats
  }

  return { getSiteMode, getGalleries, getGallery, getFeatured, getStats }
}
