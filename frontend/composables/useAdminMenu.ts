/**
 * 后台管理导航菜单数据和工具函数
 */

export type AdminPermission = 'admin'
export type AdminMenuGroupKey = 'monitor' | 'resources' | 'config'

export type ActiveMatch =
  | { type: 'exact' }
  | { type: 'prefix'; prefixes: string[] }

export interface AdminMenuItem {
  key: string
  label: string
  to: string
  icon: string
  groupKey: AdminMenuGroupKey
  permissions: AdminPermission[]
  activeMatch: ActiveMatch
  mobilePrimary?: boolean
  badge?: string | number
}

export interface AdminMenuGroup {
  key: AdminMenuGroupKey
  label: string
  items: AdminMenuItem[]
}

export const adminMenuGroupsMeta: Array<{ key: AdminMenuGroupKey; label: string }> = [
  { key: 'monitor', label: '监控' },
  { key: 'resources', label: '资源' },
  { key: 'config', label: '配置' },
]

// 导航菜单数据
export const adminMenu: AdminMenuItem[] = [
  {
    key: 'dashboard',
    label: '仪表板',
    to: '/admin/dashboard',
    icon: 'heroicons:squares-2x2',
    groupKey: 'monitor',
    mobilePrimary: true,
    permissions: ['admin'],
    activeMatch: { type: 'exact' },
  },
  {
    key: 'images',
    label: '图片管理',
    to: '/admin/images',
    icon: 'heroicons:photo',
    groupKey: 'resources',
    mobilePrimary: true,
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/images'] },
  },
  {
    key: 'tokens',
    label: 'Token管理',
    to: '/admin/tokens',
    icon: 'heroicons:key',
    groupKey: 'resources',
    mobilePrimary: true,
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/tokens'] },
  },
  {
    key: 'galleries',
    label: '画集管理',
    to: '/admin/galleries',
    icon: 'heroicons:rectangle-stack',
    groupKey: 'resources',
    mobilePrimary: true,
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/galleries'] },
  },
  {
    key: 'settings',
    label: '系统设置',
    to: '/admin/settings',
    icon: 'heroicons:cog-6-tooth',
    groupKey: 'config',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/settings'] },
  },
  {
    key: 'seo',
    label: 'SEO 设置',
    to: '/admin/seo',
    icon: 'heroicons:magnifying-glass',
    groupKey: 'config',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/seo'] },
  },
  {
    key: 'storage',
    label: '存储设置',
    to: '/admin/storage',
    icon: 'heroicons:server-stack',
    groupKey: 'config',
    permissions: ['admin'],
    activeMatch: { type: 'prefix', prefixes: ['/admin/storage'] },
  },
  {
    key: 'announcements',
    label: '公告管理',
    to: '/admin/announcements',
    icon: 'heroicons:megaphone',
    groupKey: 'config',
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

export function groupMenuItems(items: AdminMenuItem[]): AdminMenuGroup[] {
  return adminMenuGroupsMeta
    .map(meta => ({
      key: meta.key,
      label: meta.label,
      items: items.filter(item => item.groupKey === meta.key)
    }))
    .filter(group => group.items.length > 0)
}

/**
 * 组合式函数：获取管理菜单
 */
export function useAdminMenu() {
  const route = useRoute()
  const authStore = useAuthStore()

  // 过滤后的菜单
  const menu = computed(() => filterMenuByAuth(authStore.isAuthenticated))
  const groupedMenu = computed(() => groupMenuItems(menu.value))
  const mobilePrimaryMenu = computed(() => menu.value.filter(item => item.mobilePrimary).slice(0, 4))
  const mobileSecondaryMenu = computed(() => menu.value.filter(item => !mobilePrimaryMenu.value.some(primary => primary.key === item.key)))

  // 当前激活的菜单项
  const activeKey = computed(() => {
    const path = route.path
    const activeItem = menu.value.find((item) => isMenuActive(path, item))
    return activeItem?.key || ''
  })

  // 检查菜单项是否激活
  const isActive = (item: AdminMenuItem) => {
    return isMenuActive(route.path, item)
  }

  return {
    menu,
    groupedMenu,
    mobilePrimaryMenu,
    mobileSecondaryMenu,
    activeKey,
    isActive,
    adminMenu,
  }
}
