import { defineStore } from 'pinia'

export interface NotificationAction {
  label: string
  onClick: () => void | Promise<void>
  variant?: 'primary' | 'secondary' | 'ghost'
}

export interface NotificationProgress {
  current: number
  total: number
  showPercentage?: boolean
}

export interface Notification {
  id: string
  title: string
  description?: string
  type: 'success' | 'error' | 'warning' | 'info' | 'loading'
  timeout?: number | false  // false 表示持久化
  closable?: boolean
  actions?: NotificationAction[]
  progress?: NotificationProgress
  group?: string
  priority?: 'low' | 'normal' | 'high'
}

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    notifications: [] as Notification[]
  }),

  getters: {
    // 按优先级和时间排序
    sortedNotifications: (state) => {
      return [...state.notifications].sort((a, b) => {
        const priorityOrder = { high: 3, normal: 2, low: 1 }
        const aPriority = priorityOrder[a.priority || 'normal']
        const bPriority = priorityOrder[b.priority || 'normal']
        return bPriority - aPriority
      })
    },

    // 按组分组
    groupedNotifications: (state) => {
      const groups: Record<string, Notification[]> = {}
      state.notifications.forEach(notification => {
        const group = notification.group || 'default'
        if (!groups[group]) {
          groups[group] = []
        }
        groups[group].push(notification)
      })
      return groups
    }
  },

  actions: {
    // 生成唯一ID
    generateId(): string {
      return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    },

    // 获取最优超时时间
    getOptimalTimeout(): number {
      if (typeof window === 'undefined') return 2000

      const width = window.innerWidth
      const height = window.innerHeight

      if (width < 640) return 2000
      if (width < 1440 || height < 1000) return 1500
      return 2500
    },

    // 添加通知
    add(options: Omit<Notification, 'id'>): string {
      const notification: Notification = {
        id: this.generateId(),
        ...options,
        timeout: options.timeout !== undefined ? options.timeout : this.getOptimalTimeout(),
        closable: options.closable !== undefined ? options.closable : true,
        priority: options.priority || 'normal'
      }

      this.notifications.push(notification)

      // 自动移除（如果设置了超时）
      if (notification.timeout && notification.timeout > 0) {
        setTimeout(() => {
          this.remove(notification.id)
        }, notification.timeout)
      }

      return notification.id
    },

    // 移除通知
    remove(id: string) {
      const index = this.notifications.findIndex(n => n.id === id)
      if (index !== -1) {
        this.notifications.splice(index, 1)
      }
    },

    // 清除所有通知
    clear() {
      this.notifications = []
    },

    // 清除指定组的通知
    clearGroup(group: string) {
      this.notifications = this.notifications.filter(n => n.group !== group)
    },

    // 更新通知
    update(id: string, updates: Partial<Notification>) {
      const notification = this.notifications.find(n => n.id === id)
      if (notification) {
        Object.assign(notification, updates)
      }
    },

    // 更新进度
    updateProgress(id: string, current: number, total: number) {
      const notification = this.notifications.find(n => n.id === id)
      if (notification && notification.progress) {
        notification.progress.current = current
        notification.progress.total = total
      }
    },

    // 快捷方法：成功
    success(title: string, description?: string, options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'description'>>): string {
      return this.add({
        title,
        description,
        type: 'success',
        ...options
      })
    },

    // 快捷方法：错误
    error(title: string, description?: string, options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'description'>>): string {
      return this.add({
        title,
        description,
        type: 'error',
        timeout: options?.timeout || this.getOptimalTimeout() * 1.5,
        ...options
      })
    },

    // 快捷方法：警告
    warning(title: string, description?: string, options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'description'>>): string {
      return this.add({
        title,
        description,
        type: 'warning',
        ...options
      })
    },

    // 快捷方法：信息
    info(title: string, description?: string, options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'description'>>): string {
      return this.add({
        title,
        description,
        type: 'info',
        ...options
      })
    },

    // 快捷方法：加载中
    loading(title: string, description?: string, options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'description'>>): string {
      return this.add({
        title,
        description,
        type: 'loading',
        timeout: false,  // 加载通知默认持久化
        closable: false,  // 加载通知默认不可关闭
        ...options
      })
    }
  }
})
