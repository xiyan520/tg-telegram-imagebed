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

  // 用 Map 按文件名跟踪 XHR，避免多文件并发时的竞态问题
  const _xhrMap = new Map<string, XMLHttpRequest>()

  /** 单文件 XHR 上传（支持实时进度），返回独立的 abort 函数 */
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
  ): { promise: Promise<ApiResponse<UploadResult | TokenUploadResult>>; abort: () => void } => {
    const xhr = new XMLHttpRequest()
    // 以文件名+时间戳作为 key，支持同名文件并发
    const key = `${file.name}_${Date.now()}_${opts.idx}`
    _xhrMap.set(key, xhr)

    const cleanup = () => _xhrMap.delete(key)

    const promise = new Promise<ApiResponse<UploadResult | TokenUploadResult>>((resolve, reject) => {
      const fd = new FormData()
      fd.append('file', file)

      xhr.addEventListener('load', () => {
        cleanup()
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
      xhr.addEventListener('error', () => { cleanup(); reject(new Error('网络错误')) })
      xhr.addEventListener('abort', () => { cleanup(); reject(new Error('上传已取消')) })

      if (opts.onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && opts.onProgress) {
            const filePercent = Math.round((e.loaded / e.total) * 100)
            const overall = Math.round(((opts.idx + filePercent / 100) / opts.total) * 100)
            opts.onProgress({
              label: `上传中 (${opts.idx + 1}/${opts.total})...`,
              percent: overall
            })
          }
        })
      }

      xhr.open('POST', url)
      if (opts.withCredentials) xhr.withCredentials = true
      if (opts.headers) {
        for (const [k, v] of Object.entries(opts.headers)) xhr.setRequestHeader(k, v)
      }
      xhr.send(fd)
    })

    const abort = () => {
      if (_xhrMap.has(key)) {
        xhr.abort()
        cleanup()
      }
    }

    return { promise, abort }
  }

  /** 中止所有当前上传请求 */
  const abortUpload = () => {
    for (const xhr of _xhrMap.values()) {
      xhr.abort()
    }
    _xhrMap.clear()
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
      const { promise } = _xhrUpload(url, files[i], {
        headers, withCredentials, idx: i, total: files.length, onProgress
      })
      const resp = await promise
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
