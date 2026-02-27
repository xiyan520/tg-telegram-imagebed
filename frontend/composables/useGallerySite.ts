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
  card_subtitle?: string
  editor_pick_weight?: number
  image_count: number
  cover_image?: string
  cover_url?: string
  share_url?: string | null
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

export interface GalleryHomeConfig {
  hero_mode: 'auto' | 'manual'
  hero_gallery_id?: number | null
  mobile_items_per_section: number
  desktop_items_per_section: number
  enable_recent_strip: boolean
}

export interface GalleryHomeSection {
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
  items: GallerySiteItem[]
  item_ids?: number[]
}

export interface GalleryHomePayload {
  config: GalleryHomeConfig
  sections: GalleryHomeSection[]
  hero: GallerySiteItem | null
  recent_items: GallerySiteItem[]
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
  const baseURL = (config.public.apiBase || '').replace(/\/$/, '')

  const resolveApiPath = (path: string) => {
    if (!baseURL) return path
    if (baseURL.endsWith('/api') && path.startsWith('/api/')) {
      return `${baseURL}${path.slice(4)}`
    }
    return `${baseURL}${path}`
  }

  /** 检测站点模式 */
  const getSiteMode = async (): Promise<SiteModeInfo> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/public/site-mode'))
    if (!response?.success) throw new Error(response?.error || '检测站点模式失败')
    return response.data as SiteModeInfo
  }

  /** 获取公开画集列表 */
  const getGalleries = async (page = 1, perPage = 20): Promise<GalleriesResponse> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/galleries'), {
      params: { page, per_page: perPage }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集列表失败')
    return response.data as GalleriesResponse
  }

  /** 获取画集详情 + 图片列表 */
  const getGallery = async (id: number, page = 1): Promise<GalleryDetailResponse> => {
    const response = await $fetch<ApiResponse>(resolveApiPath(`/api/gallery-site/galleries/${id}`), {
      params: { page }
    })
    if (!response?.success) throw new Error(response?.error || '获取画集详情失败')
    return response.data as GalleryDetailResponse
  }

  /** 获取精选画集 */
  const getFeatured = async (limit = 6): Promise<GallerySiteItem[]> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/featured'), {
      params: { limit }
    })
    if (!response?.success) throw new Error(response?.error || '获取精选画集失败')
    return response.data as GallerySiteItem[]
  }

  /** 获取站点统计 */
  const getStats = async (): Promise<GallerySiteStats> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/stats'))
    if (!response?.success) throw new Error(response?.error || '获取统计失败')
    return response.data as GallerySiteStats
  }

  /** 获取首页编排数据 */
  const getHomeConfig = async (): Promise<GalleryHomePayload> => {
    const response = await $fetch<ApiResponse>(resolveApiPath('/api/gallery-site/home-config'))
    if (!response?.success) throw new Error(response?.error || '获取首页编排失败')
    return response.data as GalleryHomePayload
  }

  return { getSiteMode, getGalleries, getGallery, getFeatured, getStats, getHomeConfig }
}
