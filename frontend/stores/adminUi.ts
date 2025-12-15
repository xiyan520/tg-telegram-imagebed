/**
 * 后台管理界面 UI 状态管理
 * 管理侧边栏折叠、移动端抽屉等 UI 状态
 */
import { defineStore } from 'pinia'

const STORAGE_KEY = 'admin_sidebar_collapsed'

export const useAdminUiStore = defineStore('adminUi', {
  state: () => ({
    // 桌面端侧边栏折叠状态
    sidebarCollapsed: false,
    // 移动端侧边栏抽屉开关
    mobileSidebarOpen: false,
  }),

  actions: {
    // 切换侧边栏折叠状态
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      this.persist()
    },

    // 设置侧边栏折叠状态
    setSidebarCollapsed(collapsed: boolean) {
      this.sidebarCollapsed = collapsed
      this.persist()
    },

    // 打开移动端侧边栏
    openMobileSidebar() {
      this.mobileSidebarOpen = true
    },

    // 关闭移动端侧边栏
    closeMobileSidebar() {
      this.mobileSidebarOpen = false
    },

    // 切换移动端侧边栏
    toggleMobileSidebar() {
      this.mobileSidebarOpen = !this.mobileSidebarOpen
    },

    // 从 localStorage 恢复状态
    restore() {
      if (import.meta.client) {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored !== null) {
          this.sidebarCollapsed = stored === 'true'
        }
      }
    },

    // 持久化到 localStorage
    persist() {
      if (import.meta.client) {
        localStorage.setItem(STORAGE_KEY, String(this.sidebarCollapsed))
      }
    },
  },
})
