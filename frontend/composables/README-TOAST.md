# 统一Toast通知框架使用指南

## 概述

项目已统一使用 `useToastOptimized()` 作为唯一的通知框架，解决了所有分辨率下的点击穿透问题。

## 核心特性

✅ **智能时长** - 根据屏幕尺寸自动调整显示时间
- 小屏幕（<640px）：1.5秒
- 中等分辨率（1300x954等）：0.8秒（快速消失，避免阻挡）
- 大屏幕（≥1440px）：2秒

✅ **简洁API** - 提供快捷方法，代码更简洁
✅ **点击穿透** - 配合独立容器，完全不阻止页面交互
✅ **自动优化** - 移除冗余描述，提升用户体验

## 使用方法

### 1. 导入框架

```typescript
// ❌ 旧方式 - 不要再使用
const toast = useToast()

// ✅ 新方式 - 统一使用优化框架
const toast = useToastOptimized()
```

### 2. 快捷方法（推荐）

```typescript
// 成功提示
toast.success('已复制')
toast.success('操作成功')

// 错误提示
toast.error('操作失败', '详细错误信息')
toast.error('加载失败', error.message)

// 警告提示
toast.warning('请注意', '这是一个警告')

// 信息提示
toast.info('提示', '这是一条信息')
```

### 3. 完整配置（需要时）

```typescript
toast.add({
  title: '标题',
  description: '描述',
  color: 'green',
  timeout: 1000  // 自定义时长（可选）
})
```

## 迁移指南

### 替换示例

#### 示例 1：简单成功提示

```typescript
// ❌ 旧代码
const toast = useToast()
toast.add({
  title: '已复制',
  description: 'URL 已复制到剪贴板',
  color: 'green',
  timeout: 500
})

// ✅ 新代码
const toast = useToastOptimized()
toast.success('已复制')
```

#### 示例 2：错误提示

```typescript
// ❌ 旧代码
toast.add({
  title: '错误',
  description: error.message || '操作失败',
  color: 'red'
})

// ✅ 新代码
toast.error('操作失败', error.message)
```

#### 示例 3：退出登录

```typescript
// ❌ 旧代码
toast.add({
  title: '已退出',
  description: 'Token已清除',
  color: 'green'
})

// ✅ 新代码
toast.success('已退出')
```

## 批量替换步骤

### 步骤 1：替换导入

在每个 `.vue` 文件中：

```typescript
// 查找
const toast = useToast()

// 替换为
const toast = useToastOptimized()
```

### 步骤 2：简化调用

根据上面的示例，将 `toast.add()` 替换为快捷方法。

## 已完成迁移的文件

- ✅ `pages/gallery.vue` - 已完成

## 待迁移的文件

- ⏳ `pages/index.vue` - 上传页面（约20处）
- ⏳ `pages/guest.vue` - Token模式页面（约10处）
- ⏳ `pages/docs.vue` - API文档页面（约2处）
- ⏳ `pages/admin/index.vue` - 管理员登录（约2处）
- ⏳ `pages/admin/dashboard.vue` - 管理面板（约5处）
- ⏳ `layouts/admin.vue` - 管理员布局（约3处）

## 技术细节

### 屏幕尺寸检测

```typescript
const getScreenSize = () => {
  const width = window.innerWidth
  const height = window.innerHeight

  if (width < 640) return 'small'           // 手机
  if (width < 1440 || height < 1000) return 'medium'  // 中等分辨率
  return 'large'                            // 大屏幕
}
```

### 时长计算

```typescript
const getOptimalTimeout = (customTimeout?: number) => {
  if (customTimeout !== undefined) return customTimeout

  const screenSize = getScreenSize()
  switch (screenSize) {
    case 'small': return 1500   // 1.5秒
    case 'medium': return 800   // 0.8秒（关键！）
    case 'large': return 2000   // 2秒
  }
}
```

## 配合独立容器

Toast通知已经在 `app.vue` 中配置为独立容器：

```vue
<div class="toast-container-wrapper">
  <UNotifications />
</div>
```

配合CSS的 `pointer-events: none` 设置，实现完全的点击穿透。

## 常见问题

### Q: 为什么中等分辨率只显示0.8秒？

A: 在1300x954等中等分辨率下，屏幕空间有限，快速消失可以避免长时间阻挡操作区域，提升用户体验。

### Q: 可以自定义显示时长吗？

A: 可以。所有方法都支持传入自定义时长：

```typescript
toast.success('已复制', 2000)  // 显示2秒
toast.error('错误', '详情', 3000)  // 显示3秒
```

### Q: 如何禁用自动消失？

A: 传入 `timeout: 0` 或 `timeout: undefined`：

```typescript
toast.add({
  title: '重要提示',
  timeout: 0  // 不自动消失
})
```

## 最佳实践

1. **优先使用快捷方法** - 代码更简洁，自动优化
2. **避免冗余描述** - 标题已经足够清晰时，不需要描述
3. **信任自动时长** - 框架已经针对不同屏幕优化，通常不需要自定义
4. **错误提示可以稍长** - 框架自动将错误提示时长设为1.5倍

## 维护说明

如需调整时长策略，修改 `composables/useToastOptimized.ts` 中的 `getOptimalTimeout` 函数即可，所有页面自动生效。
