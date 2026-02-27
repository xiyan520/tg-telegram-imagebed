import type { Gallery, GalleryImage } from './useGalleryApi'
import type { ApiResponse } from '~/types/api'

/** $fetch 请求选项（认证相关） */
export interface GalleryApiFetchOptions {
  credentials?: RequestCredentials
  headers?: Record<string, string>
}

/** 工厂函数：根据 baseUrl 和认证方式生成通用画集 API 方法 */
export function createGalleryApi(baseUrl: string, getFetchOptions: () => GalleryApiFetchOptions) {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  // 获取画集列表
  const getGalleries = async (page = 1, limit = 50) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}`, {
      params: { page, limit },
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '获取画集列表失败')
    return response.data as { items: Gallery[]; total: number; page: number; limit: number }
  }

  // 创建画集
  const createGallery = async (name: string, description?: string) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}`, {
      method: 'POST',
      ...getFetchOptions(),
      body: { name, description }
    })
    if (!response?.success) throw new Error(response?.error || '创建画集失败')
    return response.data.gallery as Gallery
  }

  // 获取画集详情
  const getGallery = async (id: number) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${id}`, {
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '获取画集失败')
    return response.data.gallery as Gallery
  }

  // 更新画集
  const updateGallery = async (id: number, data: Partial<Gallery>) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${id}`, {
      method: 'PATCH',
      ...getFetchOptions(),
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新画集失败')
    return response.data.gallery as Gallery
  }

  // 删除画集
  const deleteGallery = async (id: number) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${id}`, {
      method: 'DELETE',
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '删除画集失败')
    return true
  }

  // 获取画集图片
  const getGalleryImages = async (galleryId: number, page = 1, limit = 50) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/images`, {
      params: { page, limit },
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '获取画集图片失败')
    return response.data as { items: GalleryImage[]; total: number; page: number; limit: number }
  }

  // 添加图片到画集
  const addImagesToGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/images`, {
      method: 'POST',
      ...getFetchOptions(),
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '添加图片失败')
    return response.data as { added: number; skipped: number; not_found: string[] }
  }

  // 从画集移除图片
  const removeImagesFromGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/images`, {
      method: 'DELETE',
      ...getFetchOptions(),
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '移除图片失败')
    return response.data.removed as number
  }

  // 开启/更新分享
  const enableShare = async (galleryId: number, expiresAt?: string) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/share`, {
      method: 'POST',
      ...getFetchOptions(),
      body: { enabled: true, expires_at: expiresAt }
    })
    if (!response?.success) throw new Error(response?.error || '开启分享失败')
    return response.data as { share_url: string; share_expires_at?: string }
  }

  // 关闭分享
  const disableShare = async (galleryId: number) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/share`, {
      method: 'DELETE',
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '关闭分享失败')
    return true
  }

  // 设置画集封面
  const setCover = async (galleryId: number, encryptedId: string) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/cover`, {
      method: 'PUT',
      ...getFetchOptions(),
      body: { encrypted_id: encryptedId }
    })
    if (!response?.success) throw new Error(response?.error || '设置封面失败')
    return response.data.gallery as Gallery
  }

  // 清除画集封面
  const clearCover = async (galleryId: number) => {
    const response = await $fetch<ApiResponse>(`${apiBase}${baseUrl}/${galleryId}/cover`, {
      method: 'DELETE',
      ...getFetchOptions()
    })
    if (!response?.success) throw new Error(response?.error || '清除封面失败')
    return response.data.gallery as Gallery
  }

  return {
    getGalleries,
    createGallery,
    getGallery,
    updateGallery,
    deleteGallery,
    getGalleryImages,
    addImagesToGallery,
    removeImagesFromGallery,
    enableShare,
    disableShare,
    setCover,
    clearCover
  }
}
