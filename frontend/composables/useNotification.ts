/**
 * 统一通知框架 - 基于 Pinia Store
 * 完全不阻止页面交互，专为解决点击穿透问题设计
 *
 * 核心特性：
 * 1. 容器 pointer-events: none - 完全不阻止交互
 * 2. 只有通知卡片本身可交互（关闭按钮、操作按钮）
 * 3. 智能时长 - 根据屏幕尺寸自动调整
 * 4. 美观动画 - 从右侧滑入/滑出
 * 5. 支持进度条、操作按钮、分组等高级功能
 */

import { useNotificationStore } from '~/stores/notification'

export const useNotification = () => {
  const store = useNotificationStore()

  return {
    // 状态
    notifications: computed(() => store.sortedNotifications),

    // 基础方法
    add: store.add.bind(store),
    remove: store.remove.bind(store),
    clear: store.clear.bind(store),
    clearGroup: store.clearGroup.bind(store),
    update: store.update.bind(store),
    updateProgress: store.updateProgress.bind(store),

    // 快捷方法
    success: store.success.bind(store),
    error: store.error.bind(store),
    warning: store.warning.bind(store),
    info: store.info.bind(store),
    loading: store.loading.bind(store)
  }
}

// 保持向后兼容的别名
export const useLightToast = useNotification
