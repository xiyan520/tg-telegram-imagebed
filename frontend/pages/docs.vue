<template>
  <div class="max-w-7xl mx-auto pt-4 px-4">
    <!-- 页面标题 -->
    <div class="text-center space-y-4 mb-8">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        API 文档
      </h1>
      <p class="text-stone-600 dark:text-stone-400">
        使用我们的 API 轻松集成图片上传功能
      </p>
      <!-- 基础 URL 卡片 -->
      <div class="inline-flex items-center gap-3 px-5 py-3 bg-white dark:bg-neutral-800 border border-stone-200 dark:border-stone-700 rounded-xl shadow-sm">
        <span class="text-xs font-medium text-stone-400 uppercase tracking-wider">Base URL</span>
        <code class="px-3 py-1.5 bg-stone-100 dark:bg-stone-900 rounded-lg text-sm font-mono text-amber-600 dark:text-amber-400">
          {{ baseUrl }}
        </code>
        <UButton
          icon="heroicons:clipboard-document"
          color="gray"
          variant="ghost"
          size="xs"
          @click="copyBaseUrl"
        />
      </div>
      <!-- curl 快速示例 -->
      <div class="max-w-xl mx-auto text-left">
        <p class="text-xs text-stone-400 mb-1.5 ml-1">快速上传示例</p>
        <div class="relative group">
          <code class="block px-4 py-3 bg-stone-900 dark:bg-stone-950 text-green-400 text-xs font-mono rounded-lg overflow-x-auto">curl -F "file=@image.jpg" {{ baseUrl }}/api/upload</code>
          <UButton
            icon="heroicons:clipboard-document"
            color="gray"
            variant="ghost"
            size="xs"
            class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
            @click="copyCurlExample"
          />
        </div>
      </div>
    </div>

    <!-- 两栏布局 -->
    <DocsLayout :sections="apiSections">
      <div class="space-y-12">
        <!-- 快速开始 -->
        <UCard id="quickstart" class="scroll-mt-20">
          <template #header>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:rocket-launch" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-stone-900 dark:text-white">快速开始</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400">了解 API 基本用法</p>
              </div>
            </div>
          </template>

          <div class="space-y-4">
            <p class="text-stone-700 dark:text-stone-300">
              我们的 API 提供简单易用的图片上传服务。所有请求都使用标准 HTTP 方法。
            </p>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex items-start gap-3 p-4 bg-stone-50 dark:bg-stone-800/50 rounded-lg">
                <div class="w-8 h-8 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <UIcon name="heroicons:photo" class="w-4 h-4 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h4 class="font-semibold text-stone-900 dark:text-white mb-1">支持格式</h4>
                  <p class="text-sm text-stone-600 dark:text-stone-400">
                    JPG、PNG、GIF、WebP、AVIF、SVG
                  </p>
                </div>
              </div>
              <div class="flex items-start gap-3 p-4 bg-stone-50 dark:bg-stone-800/50 rounded-lg">
                <div class="w-8 h-8 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <UIcon name="heroicons:arrow-up-tray" class="w-4 h-4 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h4 class="font-semibold text-stone-900 dark:text-white mb-1">文件限制</h4>
                  <p class="text-sm text-stone-600 dark:text-stone-400">
                    单文件最大 20MB
                  </p>
                </div>
              </div>
            </div>

            <div class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div class="flex items-start gap-2">
                <UIcon name="heroicons:light-bulb" class="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5" />
                <div>
                  <p class="text-sm text-amber-800 dark:text-amber-200">
                    <strong>提示：</strong>如果系统启用了 Token 模式，匿名上传可能被禁用。
                    请先获取 Token 再进行上传。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </UCard>

        <!-- API 分组 -->
        <div v-for="section in apiSections" :key="section.id" class="space-y-6">
          <!-- 分组标题 -->
          <div :id="section.id" class="scroll-mt-20 flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-stone-600 to-stone-700 dark:from-stone-500 dark:to-stone-600 rounded-lg flex items-center justify-center">
              <UIcon :name="section.icon || 'heroicons:cube'" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 class="text-2xl font-bold text-stone-900 dark:text-white">{{ section.title }}</h2>
              <p v-if="section.description" class="text-sm text-stone-500 dark:text-stone-400">
                {{ section.description }}
              </p>
            </div>
          </div>

          <!-- 端点卡片 -->
          <div class="space-y-6">
            <DocsEndpointCard
              v-for="endpoint in section.endpoints"
              :key="endpoint.id"
              :endpoint="endpoint"
              :base-url="baseUrl"
            />
          </div>
        </div>

        <!-- 错误代码 -->
        <UCard id="error-codes" class="scroll-mt-20">
          <template #header>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-stone-900 dark:text-white">错误代码</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400">HTTP 状态码说明</p>
              </div>
            </div>
          </template>

          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-stone-50 dark:bg-stone-800/50">
                <tr>
                  <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">状态码</th>
                  <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">说明</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-200 dark:divide-stone-700">
                <tr v-for="code in errorCodes" :key="code.status">
                  <td class="px-4 py-2">
                    <UBadge :color="getStatusColor(code.status)" variant="subtle">
                      {{ code.status }}
                    </UBadge>
                  </td>
                  <td class="px-4 py-2 text-stone-600 dark:text-stone-400">{{ code.description }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </UCard>

        <!-- 在线测试 -->
        <UCard id="test" class="scroll-mt-20">
          <template #header>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:play" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-stone-900 dark:text-white">在线测试</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400">测试 API 上传功能</p>
              </div>
            </div>
          </template>

          <div class="space-y-4">
            <p class="text-stone-700 dark:text-stone-300">
              选择一张图片测试 API 上传功能
            </p>

            <!-- Token 输入（可选） -->
            <div class="flex items-center gap-3">
              <UInput
                v-model="testToken"
                placeholder="Token（可选，留空则匿名上传）"
                size="sm"
                class="flex-1"
                :ui="{ base: 'font-mono text-xs' }"
              />
            </div>

            <div>
              <input
                ref="testFileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="handleTestUpload"
              />
              <UButton
                icon="heroicons:cloud-arrow-up"
                color="primary"
                size="lg"
                :loading="testUploading"
                @click="testFileInput?.click()"
              >
                选择图片测试
              </UButton>
            </div>

            <!-- 上传成功预览 -->
            <div v-if="testResult && testResult.success && testResult.data" class="flex items-start gap-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <img
                :src="testResult.data.url"
                :alt="testResult.data.filename"
                class="w-20 h-20 object-cover rounded-lg border border-green-300 dark:border-green-700 flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <h4 class="font-semibold text-green-800 dark:text-green-200 mb-1">测试成功</h4>
                <p class="text-xs text-green-700 dark:text-green-300 truncate font-mono">{{ testResult.data.url }}</p>
                <DocsCodeBlock :code="JSON.stringify(testResult, null, 2)" language="json" class="mt-2" />
              </div>
            </div>

            <!-- 上传失败 -->
            <div v-else-if="testResult && !testResult.success" class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <h4 class="font-semibold mb-2 text-red-800 dark:text-red-200">测试失败</h4>
              <DocsCodeBlock :code="JSON.stringify(testResult, null, 2)" language="json" />
            </div>
          </div>
        </UCard>
      </div>
    </DocsLayout>
  </div>
</template>

<script setup lang="ts">
import { apiSections } from '~/data/apiDocs'

const config = useRuntimeConfig()
const toast = useLightToast()
const { copy: clipboardCopy } = useClipboardCopy()
const baseUrl = computed(() => config.public.apiBase || window.location.origin)

const testFileInput = ref<HTMLInputElement>()
const testUploading = ref(false)
const testResult = ref<any>(null)
const testToken = ref('')

const errorCodes = [
  { status: 200, description: '请求成功' },
  { status: 302, description: '重定向（CDN 跳转）' },
  { status: 400, description: '请求参数错误' },
  { status: 401, description: '未授权（Token 无效）' },
  { status: 403, description: '禁止访问（功能被禁用）' },
  { status: 404, description: '资源不存在' },
  { status: 413, description: '文件过大' },
  { status: 429, description: '请求过于频繁' },
  { status: 500, description: '服务器错误' },
]

const copyBaseUrl = () => {
  clipboardCopy(baseUrl.value, '基础 URL 已复制')
}

const copyCurlExample = () => {
  clipboardCopy(`curl -F "file=@image.jpg" ${baseUrl.value}/api/upload`, '已复制 curl 命令')
}

const getStatusColor = (status: number) => {
  if (status >= 200 && status < 300) return 'green' as const
  if (status >= 300 && status < 400) return 'blue' as const
  if (status >= 400 && status < 500) return 'amber' as const
  return 'red' as const
}

const handleTestUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return

  testUploading.value = true
  testResult.value = null

  try {
    // 根据是否填写 Token 选择不同的上传端点
    const file = target.files[0]
    const fd = new FormData()
    fd.append('file', file)

    const headers: Record<string, string> = {}
    let url = `${baseUrl.value}/api/upload`

    if (testToken.value.trim()) {
      url = `${baseUrl.value}/api/auth/upload`
      headers['Authorization'] = `Bearer ${testToken.value.trim()}`
    }

    const resp = await $fetch<any>(url, {
      method: 'POST',
      body: fd,
      headers,
    })

    testResult.value = {
      success: true,
      data: resp.data || resp,
    }
    toast.success('测试成功', '图片上传成功')
  } catch (error: any) {
    testResult.value = {
      success: false,
      error: error.data?.error || error.message,
    }
    toast.error('测试失败', error.data?.error || error.message)
  } finally {
    testUploading.value = false
    if (target) target.value = ''
  }
}
</script>
