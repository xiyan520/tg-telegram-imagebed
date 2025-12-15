/**
 * 后台管理导航菜单数据和工具函数
 */

export type AdminPermission = 'admin'

export type ActiveMatch =
  | { type: 'exact' }
  | { type: 'prefix'; prefixes: string[] }

export interface AdminMenuItem {
  key: string
  label: string
  to: string
  icon: string
  permissions: AdminPermission[]
  activeMatch: ActiveMatch
  badge?: string | number
}

// 导航菜单数据
export const adminMenu: AdminMenuItem[] = [
  {
    key: 'dashboard',
    label: '仪表板',
    to: '/admin/dashboard',
    icon: 'heroicons:squares-2x2',
    permissions: ['admin'],
    activeMatch: { type: 'exact' },
  },
  {
    key: 'images',
    label: '图片管理',
    to: '/admin/images',
    icon: 'heroicons:photo',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/images'] },
  },
  {
    key: 'tokens',
    label: 'Token管理',
    to: '/admin/tokens',
    icon: 'heroicons:key',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/tokens'] },
  },
  {
    key: 'settings',
    label: '系统设置',
    to: '/admin/settings',
    icon: 'heroicons:cog-6-tooth',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/settings'] },
  },
  {
    key: 'storage',
    label: '存储设置',
    to: '/admin/storage',
    icon: 'heroicons:server-stack',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/storage'] },
  },
  {
    key: 'announcements',
    label: '公告管理',
    to: '/admin/announcements',
    icon: 'heroicons:megaphone',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/announcements'] },
  },
]

/**
 * 判断菜单项是否激活
 */
export function isMenuActive(routePath: string, item: AdminMenuItem): boolean {
  if (item.activeMatch.type === 'exact') {
    return routePath === item.to
  }
  return item.activeMatch.prefixes.some(
    (p) => routePath === p || routePath.startsWith(p + '/')
  )
}

/**
 * 根据认证状态过滤菜单
 */
export function filterMenuByAuth(isAuthed: boolean): AdminMenuItem[] {
  return isAuthed ? adminMenu : []
}

/**
 * 组合式函数：获取管理菜单
 */
export function useAdminMenu() {
  const route = useRoute()
  const authStore = useAuthStore()

  // 过滤后的菜单
  const menu = computed(() => filterMenuByAuth(authStore.isAuthenticated))

  // 当前激活的菜单项
  const activeKey = computed(() => {
    const path = route.path
    const activeItem = adminMenu.find((item) => isMenuActive(path, item))
    return activeItem?.key || ''
  })

  // 检查菜单项是否激活
  const isActive = (item: AdminMenuItem) => {
    return isMenuActive(route.path, item)
  }

  return {
    menu,
    activeKey,
    isActive,
    adminMenu,
  }
}
