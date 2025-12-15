<template>
  <Teleport to="body">
    <div class="notification-container">
      <TransitionGroup name="notification" tag="div">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          :class="['notification-card', `notification-${notification.type}`]"
        >
          <!-- 图标 -->
          <div class="notification-icon">
            <UIcon :name="getIcon(notification.type)" class="w-5 h-5" />
          </div>

          <!-- 内容 -->
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div v-if="notification.description" class="notification-description">
              {{ notification.description }}
            </div>

            <!-- 进度条 -->
            <div v-if="notification.progress" class="notification-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${(notification.progress.current / notification.progress.total) * 100}%` }"
                ></div>
              </div>
              <div v-if="notification.progress.showPercentage" class="progress-text">
                {{ Math.round((notification.progress.current / notification.progress.total) * 100) }}%
              </div>
            </div>

            <!-- 操作按钮 -->
            <div v-if="notification.actions && notification.actions.length > 0" class="notification-actions">
              <button
                v-for="(action, index) in notification.actions"
                :key="index"
                :class="['action-button', `action-${action.variant || 'primary'}`]"
                @click="handleAction(action)"
              >
                {{ action.label }}
              </button>
            </div>
          </div>

          <!-- 关闭按钮 -->
          <button
            v-if="notification.closable"
            class="notification-close"
            @click="removeNotification(notification.id)"
          >
            <UIcon name="heroicons:x-mark" class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationStore } from '~/stores/notification'
import type { NotificationAction } from '~/stores/notification'

const store = useNotificationStore()
const notifications = computed(() => store.sortedNotifications)

const getIcon = (type: string) => {
  const icons = {
    success: 'heroicons:check-circle',
    error: 'heroicons:x-circle',
    warning: 'heroicons:exclamation-triangle',
    info: 'heroicons:information-circle',
    loading: 'heroicons:arrow-path'
  }
  return icons[type as keyof typeof icons] || icons.info
}

const removeNotification = (id: string) => {
  store.remove(id)
}

const handleAction = async (action: NotificationAction) => {
  await action.onClick()
}
</script>

<style scoped>
/* 容器 - 完全不阻止交互 */
.notification-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 99999;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-width: 420px;
}

/* 通知卡片 - 只有卡片本身可交互 */
.notification-card {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.125rem 1.25rem;
  border-radius: 1rem;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  border-left: 5px solid;
  min-width: 340px;
  backdrop-filter: blur(16px) saturate(180%);
  background: rgba(255, 255, 255, 0.95);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.notification-card:hover {
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px) scale(1.01);
}

/* 暗色模式 */
.dark .notification-card {
  background: rgba(31, 41, 55, 0.95);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.5),
    0 10px 10px -5px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.05);
}

.dark .notification-card:hover {
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.7),
    0 0 0 1px rgba(255, 255, 255, 0.1);
}

/* 成功 - 使用绿色，与主题的琥珀色形成对比 */
.notification-success {
  border-left-color: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%);
}

.dark .notification-success {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(31, 41, 55, 0.95) 100%);
}

.notification-success .notification-icon {
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
  padding: 0.5rem;
  border-radius: 0.625rem;
}

/* 错误 - 使用红色 */
.notification-error {
  border-left-color: #ef4444;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%);
}

.dark .notification-error {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(31, 41, 55, 0.95) 100%);
}

.notification-error .notification-icon {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
  padding: 0.5rem;
  border-radius: 0.625rem;
}

/* 警告 - 使用琥珀色，与主题色协调 */
.notification-warning {
  border-left-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%);
}

.dark .notification-warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(31, 41, 55, 0.95) 100%);
}

.notification-warning .notification-icon {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  padding: 0.5rem;
  border-radius: 0.625rem;
}

/* 信息 - 使用青色 */
.notification-info {
  border-left-color: #06b6d4;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%);
}

.dark .notification-info {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.12) 0%, rgba(31, 41, 55, 0.95) 100%);
}

.notification-info .notification-icon {
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.12);
  padding: 0.5rem;
  border-radius: 0.625rem;
}

/* 加载中 - 使用琥珀色 */
.notification-loading {
  border-left-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%);
}

.dark .notification-loading {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(31, 41, 55, 0.95) 100%);
}

.notification-loading .notification-icon {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  padding: 0.5rem;
  border-radius: 0.625rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 图标 */
.notification-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.notification-card:hover .notification-icon {
  transform: scale(1.08);
}

/* 内容 */
.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: #111827;
  line-height: 1.375rem;
  letter-spacing: -0.01em;
}

.dark .notification-title {
  color: #f9fafb;
}

.notification-description {
  font-size: 0.8125rem;
  color: #6b7280;
  margin-top: 0.375rem;
  line-height: 1.375rem;
}

.dark .notification-description {
  color: #9ca3af;
}

/* 进度条 */
.notification-progress {
  margin-top: 0.75rem;
}

.progress-bar {
  height: 4px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.dark .progress-bar {
  background: rgba(255, 255, 255, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b 0%, #f97316 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.375rem;
  text-align: right;
}

.dark .progress-text {
  color: #9ca3af;
}

/* 操作按钮 */
.notification-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.action-button {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.action-primary {
  background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  color: white;
}

.action-primary:hover {
  background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
  transform: translateY(-1px);
}

.action-secondary {
  background: rgba(0, 0, 0, 0.05);
  color: #374151;
}

.dark .action-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #d1d5db;
}

.action-secondary:hover {
  background: rgba(0, 0, 0, 0.1);
}

.dark .action-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
}

.action-ghost {
  background: transparent;
  color: #6b7280;
}

.action-ghost:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #374151;
}

.dark .action-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #d1d5db;
}

/* 关闭按钮 */
.notification-close {
  flex-shrink: 0;
  padding: 0.25rem;
  border-radius: 0.375rem;
  color: #9ca3af;
  transition: all 0.2s;
  cursor: pointer;
  background: transparent;
  border: none;
}

.notification-close:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #6b7280;
  transform: scale(1.1);
}

.dark .notification-close:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #d1d5db;
}

/* 动画 */
.notification-enter-active {
  animation: notification-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.notification-leave-active {
  animation: notification-out 0.25s cubic-bezier(0.4, 0, 1, 1);
}

@keyframes notification-in {
  from {
    opacity: 0;
    transform: translateX(100%) scale(0.85);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes notification-out {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(100%) scale(0.85);
  }
}

/* 响应式 */
@media (max-width: 640px) {
  .notification-container {
    top: auto;
    bottom: 1rem;
    left: 1rem;
    right: 1rem;
    max-width: none;
  }

  .notification-card {
    min-width: auto;
    width: 100%;
  }
}

/* 中等分辨率优化 */
@media (min-width: 641px) and (max-height: 1000px) {
  .notification-container {
    top: 0.75rem;
    right: 0.75rem;
    max-width: 360px;
  }

  .notification-card {
    min-width: 280px;
    padding: 0.875rem 1rem;
  }
}

/* 大屏幕优化 */
@media (min-width: 1440px) and (min-height: 1000px) {
  .notification-container {
    max-width: 440px;
  }

  .notification-card {
    min-width: 360px;
  }
}
</style>
