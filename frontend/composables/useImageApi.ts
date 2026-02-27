import type {
  ApiResponse, PublicStats,
  AdminStatsData, AdminImagesData, AdminDeleteData,
  AdminDashboardActivityData, AdminActivityType, AdminImagesQuery
} from '~/types/api'

export const useImageApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase
  const getStats = async (): Promise<PublicStats> => {
    try {
      const response = await $fetch<ApiResponse<PublicStats>>(`${baseURL}/api/stats`)
      return response.data || {} as PublicStats
    } catch (error) {
      console.error('获取统计信息失败:', error)
      return {} as PublicStats
    }
  }

  // 获取管理员统计信息
  const getAdminStats = async (): Promise<AdminStatsData> => {
    try {
      const response = await $fetch<ApiResponse<AdminStatsData>>('/api/admin/stats', {
        credentials: 'include'
      })
      return response.data || { stats: {} as any, config: {} as any }
    } catch (error) {
      console.error('获取管理员统计信息失败:', error)
      throw error
    }
  }

  // 获取图片列表
  const getImages = async (params: AdminImagesQuery): Promise<AdminImagesData> => {
    try {
      const response = await $fetch<ApiResponse<AdminImagesData>>('/api/admin/images', {
        params,
        credentials: 'include'
      })
      return response.data || { images: [], totalPages: 1, total: 0, page: 1, limit: 20 }
    } catch (error) {
      console.error('获取图片列表失败:', error)
      throw error
    }
  }

  // 删除图片
  const deleteImages = async (ids: string[], opts?: { deleteStorage?: boolean }) => {
    try {
      const body: Record<string, any> = { ids }
      if (opts?.deleteStorage !== undefined) {
        body.delete_storage = opts.deleteStorage
      }
      const response = await $fetch<ApiResponse<AdminDeleteData>>('/api/admin/delete', {
        method: 'POST',
        body,
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
      const response = await $fetch<ApiResponse>('/api/admin/clear-cache', {
        method: 'POST',
        credentials: 'include'
      })
      return response
    } catch (error) {
      console.error('清理缓存失败:', error)
      throw error
    }
  }

  // 获取管理员仪表盘活动流
  const getAdminDashboardActivity = async (params: {
    type?: AdminActivityType
    page?: number
    limit?: number
  }): Promise<AdminDashboardActivityData> => {
    try {
      const response = await $fetch<ApiResponse<AdminDashboardActivityData>>('/api/admin/dashboard/activity', {
        params,
        credentials: 'include'
      })
      return response.data || {
        items: [],
        page: params.page || 1,
        limit: params.limit || 20,
        has_more: false,
        type: params.type || 'all'
      }
    } catch (error) {
      console.error('获取仪表盘活动流失败:', error)
      throw error
    }
  }

  return {
    getStats,
    getAdminStats,
    getAdminDashboardActivity,
    getImages,
    deleteImages,
    clearCache
  }
}
