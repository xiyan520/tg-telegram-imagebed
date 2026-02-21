import type { Gallery, GalleryImage } from './useGalleryApi'

export const useAdminGalleryApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  const getGalleries = async (page = 1, limit = 50) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries`, {
      params: { page, limit },
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取画集列表失败')
    return response.data as { items: Gallery[]; total: number; page: number; limit: number }
  }

  const createGallery = async (name: string, description?: string) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries`, {
      method: 'POST',
      credentials: 'include',
      body: { name, description }
    })
    if (!response?.success) throw new Error(response?.error || '创建画集失败')
    return response.data.gallery as Gallery
  }

  const getGallery = async (id: number) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${id}`, {
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取画集失败')
    return response.data.gallery as Gallery
  }

  const updateGallery = async (id: number, data: { name?: string; description?: string }) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${id}`, {
      method: 'PATCH',
      credentials: 'include',
      body: data
    })
    if (!response?.success) throw new Error(response?.error || '更新画集失败')
    return response.data.gallery as Gallery
  }

  const deleteGallery = async (id: number) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '删除画集失败')
    return true
  }

  const getGalleryImages = async (galleryId: number, page = 1, limit = 50) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/images`, {
      params: { page, limit },
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '获取画集图片失败')
    return response.data as { items: GalleryImage[]; total: number; page: number; limit: number }
  }

  const addImagesToGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/images`, {
      method: 'POST',
      credentials: 'include',
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '添加图片失败')
    return response.data as { added: number; skipped: number; not_found: string[] }
  }

  const removeImagesFromGallery = async (galleryId: number, encryptedIds: string[]) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/images`, {
      method: 'DELETE',
      credentials: 'include',
      body: { encrypted_ids: encryptedIds }
    })
    if (!response?.success) throw new Error(response?.error || '移除图片失败')
    return response.data.removed as number
  }

  const enableShare = async (galleryId: number, expiresAt?: string) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/share`, {
      method: 'POST',
      credentials: 'include',
      body: { enabled: true, expires_at: expiresAt }
    })
    if (!response?.success) throw new Error(response?.error || '开启分享失败')
    return response.data as { share_url: string; share_expires_at?: string }
  }

  const disableShare = async (galleryId: number) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/share`, {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '关闭分享失败')
    return true
  }

  const setCover = async (galleryId: number, encryptedId: string) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/cover`, {
      method: 'PUT',
      credentials: 'include',
      body: { encrypted_id: encryptedId }
    })
    if (!response?.success) throw new Error(response?.error || '设置封面失败')
    return response.data.gallery as Gallery
  }

  const clearCover = async (galleryId: number) => {
    const response = await $fetch<any>(`${baseURL}/api/admin/galleries/${galleryId}/cover`, {
      method: 'DELETE',
      credentials: 'include'
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
