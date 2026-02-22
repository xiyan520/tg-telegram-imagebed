/**
 * 统一上传 composable
 *
 * 自动检测上传模式（token Bearer → admin Session → anonymous），
 * 统一 XHR 进度回调，Token 模式上传后自动 verifyToken()。
 */

import type { ApiResponse, UploadResult, TokenUploadResult } from '~/types/api'

export interface UploadProgress {
  label: string
  percent: number
}

export const useUpload = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  const tokenStore = useTokenStore()

  // 当前活跃的 XHR 实例引用，用于支持取消上传
  let _currentXhr: XMLHttpRequest | null = null

  /** 单文件 XHR 上传（支持实时进度） */
  const _xhrUpload = (
    url: string,
    file: File,
    opts: {
      headers?: Record<string, string>
      withCredentials?: boolean
      idx: number
      total: number
      onProgress?: (p: UploadProgress) => void
    }
  ): Promise<ApiResponse<UploadResult | TokenUploadResult>> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      _currentXhr = xhr
      const fd = new FormData()
      fd.append('file', file)

      xhr.addEventListener('load', () => {
        _currentXhr = null
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)) }
          catch { reject(new Error('解析响应失败')) }
        } else {
          try {
            const d = JSON.parse(xhr.responseText)
            reject(new Error(d.error || `上传失败: ${xhr.status}`))
          } catch { reject(new Error(`上传失败: ${xhr.status}`)) }
        }
      })
      xhr.addEventListener('error', () => { _currentXhr = null; reject(new Error('网络错误')) })
      xhr.addEventListener('abort', () => { _currentXhr = null; reject(new Error('上传已取消')) })

      xhr.open('POST', url)
      if (opts.withCredentials) xhr.withCredentials = true
      if (opts.headers) {
        for (const [k, v] of Object.entries(opts.headers)) xhr.setRequestHeader(k, v)
      }
      xhr.send(fd)
    })
  }

  /** 中止当前上传请求 */
  const abortUpload = () => {
    if (_currentXhr) {
      _currentXhr.abort()
      _currentXhr = null
    }
  }

  /** 上传文件列表，自动检测模式 */
  const uploadFiles = async (
    files: File[],
    onProgress?: (p: UploadProgress) => void
  ): Promise<(UploadResult | TokenUploadResult)[]> => {
    const results: (UploadResult | TokenUploadResult)[] = []

    // 确定上传 URL 和认证方式
    // Token 优先：确保上传记录关联到 token，便于在上传历史和相册中查看
    let url: string
    let headers: Record<string, string> = {}
    let withCredentials = false
    let mode: 'admin' | 'token' | 'anonymous'

    if (tokenStore.hasToken) {
      url = `${config.public.apiBase}/api/auth/upload`
      headers = { Authorization: `Bearer ${tokenStore.token}` }
      mode = 'token'
    } else if (authStore.isAuthenticated) {
      url = `${config.public.apiBase}/api/admin/upload`
      withCredentials = true
      mode = 'admin'
    } else {
      url = `${config.public.apiBase}/api/upload`
      mode = 'anonymous'
    }

    for (let i = 0; i < files.length; i++) {
      const resp = await _xhrUpload(url, files[i], {
        headers, withCredentials, idx: i, total: files.length, onProgress
      })
      if (resp.success) results.push(resp.data)
    }

    // Token 模式上传后自动刷新配额
    if (mode === 'token') {
      await tokenStore.verifyToken().catch(() => {})
    }

    return results
  }

  return { uploadFiles, abortUpload }
}
