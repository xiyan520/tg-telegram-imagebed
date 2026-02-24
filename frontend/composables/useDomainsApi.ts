/**
 * 域名管理 API composable
 * 提供域名的增删改查、设为默认等操作
 */

// 域名数据类型
export interface DomainItem {
  id: number
  domain: string
  domain_type: 'default' | 'image' | 'gallery'
  is_active: number | boolean
  use_https: number | boolean
  is_default: number | boolean
  sort_order: number
  remark: string
  created_at: string
  updated_at: string
}

export interface AddDomainData {
  domain: string
  domain_type: string
  use_https?: boolean
  remark?: string
}

export function useDomainsApi() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''

  // 获取所有域名（管理员）
  const getDomains = async (): Promise<DomainItem[]> => {
    const res = await $fetch<any>(`${apiBase}/api/admin/domains`, {
      credentials: 'include'
    })
    if (res.success) return res.data || []
    throw new Error(res.error || '获取域名列表失败')
  }

  // 添加域名
  const addDomain = async (data: AddDomainData) => {
    const res = await $fetch<any>(`${apiBase}/api/admin/domains`, {
      method: 'POST',
      credentials: 'include',
      body: data
    })
    if (!res.success) throw new Error(res.error || '添加域名失败')
    return res.data
  }

  // 更新域名
  const updateDomain = async (id: number, data: Partial<AddDomainData & { is_active: boolean }>) => {
    const res = await $fetch<any>(`${apiBase}/api/admin/domains/${id}`, {
      method: 'PUT',
      credentials: 'include',
      body: data
    })
    if (!res.success) throw new Error(res.error || '更新域名失败')
    return res.data
  }

  // 删除域名
  const deleteDomain = async (id: number) => {
    const res = await $fetch<any>(`${apiBase}/api/admin/domains/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!res.success) throw new Error(res.error || '删除域名失败')
    return res.data
  }

  // 设为默认域名
  const setDefaultDomain = async (id: number) => {
    const res = await $fetch<any>(`${apiBase}/api/admin/domains/${id}/set-default`, {
      method: 'PUT',
      credentials: 'include'
    })
    if (!res.success) throw new Error(res.error || '设置默认域名失败')
    return res.data
  }

  // 获取公开图片域名列表
  const getPublicDomains = async (): Promise<DomainItem[]> => {
    const res = await $fetch<any>(`${apiBase}/api/public/domains`)
    if (res.success) return res.data || []
    throw new Error(res.error || '获取公开域名列表失败')
  }

  return { getDomains, addDomain, updateDomain, deleteDomain, setDefaultDomain, getPublicDomains }
}
