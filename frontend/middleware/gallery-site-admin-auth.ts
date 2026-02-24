/**
 * 画集后台管理认证中间件（命名路由中间件）
 * 1. 检查 session 认证状态 → 已认证放行
 * 2. 检查 URL 中的 auth_token → SSO token 验证
 * 3. 未认证 → 跳转登录页（登录页提供 SSO 和密码两种方式）
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (!import.meta.client) return

  const { checkAuth, authWithToken } = useGallerySiteAdmin()

  // 1. 检查现有 session
  try {
    const authInfo = await checkAuth()
    if (authInfo.authenticated) {
      useState<string>('gallery-site-admin-username', () => authInfo.username || '')
        .value = authInfo.username || ''
      return
    }
  } catch {
    // session 检查失败，继续
  }

  // 2. 检查 URL 中的 SSO auth_token
  const authToken = to.query.auth_token as string | undefined
  if (authToken) {
    try {
      await authWithToken(authToken)
      const authInfo = await checkAuth()
      useState<string>('gallery-site-admin-username', () => authInfo.username || '')
        .value = authInfo.username || ''
      // 移除 URL 中的 auth_token 参数
      const query = { ...to.query }
      delete query.auth_token
      return navigateTo({ path: to.path, query }, { replace: true })
    } catch {
      // token 验证失败，跳转登录页
      return navigateTo({
        path: '/gallery-site/admin/login',
        query: { redirect: to.path }
      }, { replace: true })
    }
  }

  // 3. 未认证，跳转登录页
  return navigateTo({
    path: '/gallery-site/admin/login',
    query: { redirect: to.fullPath }
  }, { replace: true })
})
