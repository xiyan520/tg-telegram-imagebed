import { useGuestTokenStore } from '~/stores/guestToken'

export interface Gallery {
  id: number
  name: string
  description?: string
  image_count: number
  cover_image?: string
  cover_url?: string
  share_enabled: boolean
  share_token?: string
  share_url?: string
  share_expires_at?: string
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

  let _guestStore: ReturnType<typeof useGuestTokenStore> | null = null
  const getGuestStore = () => {
    if (!_guestStore) _guestStore = useGuestTokenStore()
    return _guestStore
  }

  const getAuthHeaders = () => {
    const token = getGuestStore().token
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // 获取画集列表
  const getGalleries = async (page = 1, limit = 50) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries`, {
      params: { page, limit },
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '获取画集列表失败')
    return response.data as { items: Gallery[]; total: number; page: number; limit: number }
  }

  // 创建画集
  const createGallery = async (name: string, description?: string) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: { name, description }
    })
    if (!response.success) throw new Error(response.error || '创建画集失败')
    return response.data.gallery as Gallery
  }

  // 获取画集详情
  const getGallery = async (id: number) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${id}`, {
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '获取画集失败')
    return response.data.gallery as Gallery
  }

  // 更新画集
  const updateGallery = async (id: number, data: { name?: string; description?: string }) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${id}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: data
    })
    if (!response.success) throw new Error(response.error || '更新画集失败')
    return response.data.gallery as Gallery
  }

  // 删除画集
  const deleteGallery = async (id: number) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '删除画集失败')
    return true
  }

  // 获取画集图片
  const getGalleryImages = async (galleryId: number, page = 1, limit = 50) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${galleryId}/images`, {
      params: { page, limit },
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '获取画集图片失败')
    return response.data as { items: GalleryImage[]; total: number; page: number; limit: number }
  }

  // 添加图片到画集
  const addImagesToGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${galleryId}/images`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: { encrypted_ids: encryptedIds }
    })
    if (!response.success) throw new Error(response.error || '添加图片失败')
    return response.data as { added: number; skipped: number; not_found: string[]; not_owned: string[] }
  }

  // 从画集移除图片
  const removeImagesFromGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${galleryId}/images`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
      body: { encrypted_ids: encryptedIds }
    })
    if (!response.success) throw new Error(response.error || '移除图片失败')
    return response.data.removed as number
  }

  // 开启/更新分享
  const enableShare = async (galleryId: number, expiresAt?: string) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${galleryId}/share`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: { enabled: true, expires_at: expiresAt }
    })
    if (!response.success) throw new Error(response.error || '开启分享失败')
    return response.data as { share_url: string; share_expires_at?: string }
  }

  // 关闭分享
  const disableShare = async (galleryId: number) => {
    const response = await $fetch<any>(`${baseURL}/api/auth/galleries/${galleryId}/share`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    })
    if (!response.success) throw new Error(response.error || '关闭分享失败')
    return true
  }

  // 获取分享画集（公开访问）
  const getSharedGallery = async (shareToken: string, page = 1, limit = 50) => {
    const response = await $fetch<any>(`${baseURL}/api/shared/galleries/${shareToken}`, {
      params: { page, limit },
      credentials: 'include'
    })
    if (!response.success) {
      const err: any = new Error(response.error || '画集不存在或分享已关闭')
      err.requires_password = response.requires_password
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
  }

  // 密码解锁画集
  const unlockGallery = async (shareToken: string, password: string) => {
    const response = await $fetch<any>(`${baseURL}/api/shared/galleries/${shareToken}/unlock`, {
      method: 'POST',
      body: { password },
      credentials: 'include'
    })
    if (!response.success) throw new Error(response.error || '密码错误')
    return true
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
    getSharedGallery,
    unlockGallery
  }
}
