export const useImageApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  // 上传图片
  const uploadImages = async (
    files: File[],
    onProgress?: (progress: { label: string; percent: number }) => void
  ) => {
    const results = []

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const formData = new FormData()
      formData.append('file', file)

      if (onProgress) {
        onProgress({
          label: `上传中 (${i + 1}/${files.length})...`,
          percent: Math.round(((i + 1) / files.length) * 100)
        })
      }

      try {
        const response = await $fetch<any>(`${baseURL}/api/upload`, {
          method: 'POST',
          body: formData
        })

        if (response.success) {
          results.push(response.data)
        } else {
          throw new Error(response.message || '上传失败')
        }
      } catch (error: any) {
        throw new Error(error.message || `上传 ${file.name} 失败`)
      }
    }

    return results
  }

  // 获取统计信息
  const getStats = async () => {
    try {
      const response = await $fetch<any>(`${baseURL}/api/stats`)
      return response.data || {}
    } catch (error) {
      console.error('获取统计信息失败:', error)
      return {}
    }
  }

  // 获取管理员统计信息
  const getAdminStats = async () => {
    try {
      const response = await $fetch<any>('/api/admin/stats', {
        credentials: 'include'
      })
      return response.data || { stats: {}, config: {} }
    } catch (error) {
      console.error('获取管理员统计信息失败:', error)
      throw error
    }
  }

  // 获取图片列表
  const getImages = async (params: {
    page?: number
    limit?: number
    filter?: string
    search?: string
    sort?: string
  }) => {
    try {
      const response = await $fetch<any>('/api/admin/images', {
        params,
        credentials: 'include'
      })
      return response.data || { images: [], totalPages: 1, total: 0 }
    } catch (error) {
      console.error('获取图片列表失败:', error)
      throw error
    }
  }

  // 删除图片
  const deleteImages = async (ids: string[]) => {
    try {
      const response = await $fetch<any>('/api/admin/delete', {
        method: 'POST',
        body: { ids },
        credentials: 'include'
      })
      return response
    } catch (error) {
      console.error('删除图片失败:', error)
      throw error
    }
  }

  // 清理缓存
  const clearCache = async () => {
    try {
      const response = await $fetch<any>('/api/admin/clear-cache', {
        method: 'POST',
        credentials: 'include'
      })
      return response
    } catch (error) {
      console.error('清理缓存失败:', error)
      throw error
    }
  }

  return {
    uploadImages,
    getStats,
    getAdminStats,
    getImages,
    deleteImages,
    clearCache
  }
}
