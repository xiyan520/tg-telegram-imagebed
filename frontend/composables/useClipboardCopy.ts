/**
 * 通用剪贴板复制（兼容非 HTTPS 环境）
 * 非安全上下文直接走同步 execCommand，避免异步后丢失用户手势
 */
export const useClipboardCopy = () => {
  const toast = useLightToast()

  const execCopy = (text: string): boolean => {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    let ok = false
    try { ok = document.execCommand('copy') } catch { /* ignore */ }
    document.body.removeChild(ta)
    return ok
  }

  const copy = async (text: string, successMsg = '已复制') => {
    // 非安全上下文（HTTP 非 localhost）直接走同步 execCommand
    if (!window.isSecureContext) {
      if (execCopy(text)) {
        toast.success(successMsg)
        return true
      }
      toast.error('复制失败', '请手动复制内容')
      return false
    }

    // 安全上下文优先 Clipboard API
    try {
      await navigator.clipboard.writeText(text)
      toast.success(successMsg)
      return true
    } catch {
      // Clipboard API 失败（如权限被拒），同步回退
      if (execCopy(text)) {
        toast.success(successMsg)
        return true
      }
      toast.error('复制失败', '请手动复制内容')
      return false
    }
  }

  return { copy }
}
