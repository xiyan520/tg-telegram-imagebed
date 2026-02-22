/**
 * 游客认证统一管理 composable
 * - P0: 统一登出逻辑（TG session + Token vault）
 * - P3: 公共设置跨组件共享（useState 单次加载）
 */
export const useGuestAuth = () => {
  const tokenStore = useTokenStore()
  const tgAuth = useTgAuthStore()
  const config = useRuntimeConfig()

  // 公共设置（跨组件共享，只加载一次）
  const publicSettings = useState('guestAuthSettings', () => ({
    tgAuthEnabled: false,
    tgAuthRequired: false,
    tgBindEnabled: false,
    loaded: false,
  }))

  // 计算属性：TG 功能是否有实际意义（排除场景 D）
  const tgEffective = computed(() =>
    publicSettings.value.tgAuthEnabled &&
    (publicSettings.value.tgAuthRequired || publicSettings.value.tgBindEnabled)
  )

  // 加载公共设置（幂等，已加载则跳过）
  const loadSettings = async (force = false) => {
    if (publicSettings.value.loaded && !force) return publicSettings.value
    try {
      const res = await $fetch<any>(`${config.public.apiBase}/api/public/settings`)
      if (res.success && res.data) {
        publicSettings.value.tgAuthEnabled = !!res.data.tg_auth_enabled
        publicSettings.value.tgAuthRequired = !!res.data.tg_auth_required_for_token
        publicSettings.value.tgBindEnabled = !!res.data.tg_bind_token_enabled
        publicSettings.value.loaded = true
      }
    } catch { /* 忽略 */ }
    return publicSettings.value
  }

  // 统一登出：清除 TG session + 清空本地 Token vault
  const logout = async () => {
    if (tgAuth.isLoggedIn) {
      await tgAuth.logout()
    }
    tokenStore.clearVault()
  }

  return { publicSettings, tgEffective, loadSettings, logout }
}
