<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">公告管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">管理系统公告内容和显示状态</p>
      </div>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="outline"
        :loading="loading"
        @click="loadAnnouncement"
      >
        刷新
      </UButton>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !announcement.id" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <!-- 公告状态 -->
      <UCard>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon
              :name="announcement.enabled ? 'heroicons:check-circle' : 'heroicons:x-circle'"
              :class="announcement.enabled ? 'text-green-500' : 'text-stone-400'"
              class="w-8 h-8"
            />
            <div>
              <p class="font-semibold text-stone-900 dark:text-white text-lg">
                {{ announcement.enabled ? '公告已启用' : '公告已禁用' }}
              </p>
              <p class="text-sm text-stone-500 dark:text-stone-400">
                {{ announcement.enabled ? '用户访问网站时会看到此公告' : '公告不会显示给用户' }}
              </p>
            </div>
          </div>
          <UToggle v-model="announcement.enabled" size="lg" />
        </div>
      </UCard>

      <!-- 公告内容编辑 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:pencil-square" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">公告内容</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">支持 HTML 格式</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UTextarea
            v-model="announcement.content"
            :rows="12"
            placeholder="请输入公告内容，支持HTML格式..."
            class="font-mono text-sm"
          />
          <p class="text-xs text-stone-500 dark:text-stone-400">
            提示：可以使用HTML标签来格式化内容，例如 &lt;strong&gt;、&lt;p&gt;、&lt;ul&gt; 等
          </p>
        </div>
      </UCard>

      <!-- 快速模板 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:document-duplicate" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">快速模板</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">点击使用预设模板</p>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            v-for="(template, index) in announcementTemplates"
            :key="index"
            class="p-4 text-left rounded-xl border-2 border-stone-200 dark:border-neutral-700 hover:border-amber-400 dark:hover:border-amber-500 transition-colors"
            @click="useTemplate(template.content)"
          >
            <p class="font-medium text-stone-900 dark:text-white">{{ template.name }}</p>
            <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">{{ template.description }}</p>
          </button>
        </div>
      </UCard>

      <!-- 预览 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:eye" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">预览效果</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">实时预览公告显示效果</p>
            </div>
          </div>
        </template>

        <div class="border-2 border-dashed border-stone-300 dark:border-neutral-600 rounded-xl p-6 min-h-[120px]">
          <div
            v-if="announcement.content"
            class="prose dark:prose-invert max-w-none"
            v-html="announcement.content"
          ></div>
          <div v-else class="text-center py-8 text-stone-500">
            暂无公告内容
          </div>
        </div>
      </UCard>

      <!-- 公告信息 -->
      <UCard v-if="announcement.id">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-xs text-stone-500 dark:text-stone-400">公告 ID</p>
            <p class="text-sm font-medium text-stone-900 dark:text-white mt-1">
              #{{ announcement.id }}
            </p>
          </div>
          <div>
            <p class="text-xs text-stone-500 dark:text-stone-400">创建时间</p>
            <p class="text-sm font-medium text-stone-900 dark:text-white mt-1">
              {{ formatDate(announcement.created_at) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-stone-500 dark:text-stone-400">更新时间</p>
            <p class="text-sm font-medium text-stone-900 dark:text-white mt-1">
              {{ formatDate(announcement.updated_at) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-stone-500 dark:text-stone-400">状态</p>
            <UBadge
              :color="announcement.enabled ? 'green' : 'gray'"
              variant="subtle"
              class="mt-1"
            >
              {{ announcement.enabled ? '已启用' : '已禁用' }}
            </UBadge>
          </div>
        </div>
      </UCard>

      <!-- 操作按钮 -->
      <div class="flex justify-end gap-3 pt-4">
        <UButton color="gray" variant="outline" @click="resetAnnouncement">
          重置
        </UButton>
        <UButton color="primary" :loading="saving" @click="saveAnnouncement">
          <template #leading>
            <UIcon name="heroicons:check" />
          </template>
          保存公告
        </UButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

// 状态
const loading = ref(false)
const saving = ref(false)

// 公告数据
const announcement = ref({
  id: 0,
  enabled: true,
  content: '',
  created_at: null as string | null,
  updated_at: null as string | null
})

const originalAnnouncement = ref<typeof announcement.value | null>(null)

// 公告模板
const announcementTemplates = [
  {
    name: '欢迎公告',
    description: '介绍图床功能和特点',
    content: `<div class="space-y-4">
  <h3 class="text-xl font-bold text-stone-900 dark:text-white">欢迎使用 Telegram 云图床</h3>
  <div class="space-y-2 text-stone-700 dark:text-stone-300">
    <p>🎉 <strong>无限制使用：</strong>无上传数量限制，无时间限制</p>
    <p>🚀 <strong>CDN加速：</strong>全球CDN加速，访问更快</p>
    <p>🔒 <strong>安全可靠：</strong>基于Telegram云存储，永久保存</p>
    <p>💎 <strong>Token模式：</strong>生成专属Token，管理您的图片</p>
  </div>
</div>`
  },
  {
    name: '维护通知',
    description: '系统维护或升级通知',
    content: `<div class="space-y-3">
  <h3 class="text-xl font-bold text-red-600 dark:text-red-400">系统维护通知</h3>
  <p class="text-stone-700 dark:text-stone-300">
    系统将于 <strong>2024年12月1日 22:00-23:00</strong> 进行维护升级，期间服务可能会短暂中断。
  </p>
  <p class="text-stone-700 dark:text-stone-300">
    维护期间已上传的图片不受影响，请合理安排上传时间。感谢您的理解与支持！
  </p>
</div>`
  },
  {
    name: '功能更新',
    description: '新功能上线通知',
    content: `<div class="space-y-3">
  <h3 class="text-xl font-bold text-blue-600 dark:text-blue-400">新功能上线</h3>
  <p class="text-stone-700 dark:text-stone-300">我们很高兴地宣布以下新功能已上线：</p>
  <ul class="list-disc list-inside space-y-1 text-stone-700 dark:text-stone-300">
    <li>支持批量上传图片</li>
    <li>新增图片压缩功能</li>
    <li>优化CDN加速性能</li>
    <li>支持自定义Token管理</li>
  </ul>
  <p class="text-stone-700 dark:text-stone-300">快来体验吧！</p>
</div>`
  }
]

// 加载公告
const loadAnnouncement = async () => {
  loading.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
      credentials: 'include'
    })

    if (response.success && response.data) {
      announcement.value = { ...response.data }
      originalAnnouncement.value = { ...response.data }
    }
  } catch (error: any) {
    console.error('加载公告失败:', error)
    notification.error('加载失败', error.data?.error || '无法加载公告信息')
  } finally {
    loading.value = false
  }
}

// 保存公告
const saveAnnouncement = async () => {
  if (!announcement.value.content.trim()) {
    notification.warning('提示', '请输入公告内容')
    return
  }

  saving.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
      method: 'POST',
      credentials: 'include',
      body: {
        enabled: announcement.value.enabled,
        content: announcement.value.content
      }
    })

    if (response.success) {
      notification.success('保存成功', '公告已更新')
      await loadAnnouncement()
    }
  } catch (error: any) {
    console.error('保存公告失败:', error)
    notification.error('保存失败', error.data?.error || '无法保存公告')
  } finally {
    saving.value = false
  }
}

// 重置公告
const resetAnnouncement = () => {
  if (originalAnnouncement.value) {
    announcement.value = { ...originalAnnouncement.value }
    notification.info('已重置', '公告内容已恢复')
  }
}

// 使用模板
const useTemplate = (content: string) => {
  announcement.value.content = content
  notification.success('模板已应用', '您可以继续编辑内容')
}

// 格式化日期
const formatDate = (dateString: string | null) => {
  if (!dateString) return '--'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 页面加载
onMounted(() => {
  loadAnnouncement()
})
</script>
