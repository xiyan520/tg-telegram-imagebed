<template>
  <div class="relative isolate overflow-hidden rounded-[2rem]">
    <div class="pointer-events-none absolute inset-0 rounded-[2rem] bg-[radial-gradient(circle_at_12%_20%,rgba(251,191,36,0.18),transparent_35%),radial-gradient(circle_at_88%_8%,rgba(249,115,22,0.14),transparent_38%),radial-gradient(circle_at_50%_100%,rgba(245,158,11,0.1),transparent_50%)]" />

    <div class="relative mx-auto max-w-7xl space-y-8 overflow-x-clip px-3 pb-14 pt-6 sm:px-4 md:space-y-10">
      <section class="relative overflow-hidden rounded-3xl border border-amber-200/70 bg-gradient-to-br from-amber-50 via-white to-orange-50 p-4 shadow-sm dark:border-amber-400/30 dark:from-stone-900 dark:via-stone-900 dark:to-stone-800 sm:p-6 md:p-10">
        <div class="absolute -right-24 -top-28 h-56 w-56 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-500/20" />
        <div class="absolute -bottom-28 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full bg-orange-300/25 blur-3xl dark:bg-orange-500/20" />

        <div class="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div class="min-w-0 space-y-6">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge color="amber" variant="subtle" size="sm">Developer Docs</UBadge>
              <UBadge color="gray" variant="soft" size="sm">Version {{ docsVersion }}</UBadge>
            </div>

            <div class="min-w-0 space-y-3">
              <h1 class="break-words text-2xl font-bold leading-tight text-stone-900 dark:text-white sm:text-3xl md:text-5xl">
                {{ docsCenterTitle }}
              </h1>
              <p class="max-w-2xl break-words text-sm leading-6 text-stone-600 dark:text-stone-300 md:text-base">
                这套文档按真实接入流程重排：先跑通上传，再扩展 Token 与资源查询。你可以直接从右侧指标预估接入规模，下面每个模块都支持快速跳转。
              </p>
            </div>

            <div class="flex flex-wrap gap-3">
              <UButton icon="heroicons:clipboard-document" color="primary" @click="copyBaseUrl">
                复制 Base URL
              </UButton>
              <UButton icon="heroicons:rocket-launch" color="gray" variant="soft" @click="jumpToAnchor('quickstart')">
                查看快速开始
              </UButton>
              <UButton icon="heroicons:beaker" color="gray" variant="ghost" @click="jumpToAnchor('test')">
                直接在线调试
              </UButton>
            </div>

            <div class="min-w-0 rounded-2xl border border-stone-200/80 bg-white/85 p-4 dark:border-stone-700 dark:bg-stone-900/85">
              <div class="mb-3 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
                <span class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-400">Base URL</span>
                <code class="max-w-full break-all rounded-md bg-stone-100 px-2 py-1 font-mono text-xs text-amber-600 dark:bg-stone-800 dark:text-amber-300">{{ baseUrl }}</code>
              </div>
              <DocsCodeBlock :code="heroCurlExample" language="bash" />
            </div>
          </div>

          <div class="min-w-0 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div
              v-for="stat in heroStats"
              :key="stat.label"
              class="rounded-2xl border border-amber-200/70 bg-white/80 p-4 shadow-sm dark:border-amber-400/25 dark:bg-stone-900/80"
            >
              <div class="mb-3 flex items-center justify-between">
                <span class="text-sm font-medium text-stone-600 dark:text-stone-300">{{ stat.label }}</span>
                <UIcon :name="stat.icon" class="h-5 w-5 text-amber-500 dark:text-amber-300" />
              </div>
              <p class="text-3xl font-bold text-stone-900 dark:text-white">{{ stat.value }}</p>
              <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">{{ stat.tip }}</p>
            </div>
          </div>
        </div>
      </section>

      <section id="quickstart" class="scroll-mt-24 space-y-4 rounded-2xl border border-stone-200 bg-white/80 p-4 dark:border-stone-700 dark:bg-stone-900/80 sm:p-5 md:p-6">
        <div class="flex min-w-0 flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div class="min-w-0">
            <h2 class="break-words text-2xl font-bold text-stone-900 dark:text-white">场景化快速开始</h2>
            <p class="break-words text-sm text-stone-600 dark:text-stone-400">先选策略再写代码，匿名上传和 Token 上传各有使用场景。</p>
          </div>
          <span class="text-xs text-stone-500 dark:text-stone-400">最后更新：{{ docsUpdatedAt }}</span>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <article
            v-for="scenario in quickStartScenarios"
            :key="scenario.id"
            class="min-w-0 rounded-xl border border-stone-200 bg-stone-50/70 p-4 dark:border-stone-700 dark:bg-stone-800/40"
          >
            <div class="mb-3 flex flex-wrap items-center gap-2">
              <UBadge :color="scenario.badgeColor" variant="soft">{{ scenario.badge }}</UBadge>
              <code class="max-w-full break-all rounded-md bg-white px-2 py-1 font-mono text-xs text-stone-600 dark:bg-stone-900 dark:text-stone-300">{{ scenario.endpoint }}</code>
            </div>
            <h3 class="break-words text-lg font-semibold text-stone-900 dark:text-white">{{ scenario.title }}</h3>
            <p class="mb-3 mt-1 break-words text-sm text-stone-600 dark:text-stone-400">{{ scenario.description }}</p>
            <DocsCodeBlock :code="scenario.code" language="bash" />
            <div class="mt-3 flex min-w-0 justify-end">
              <UButton size="xs" color="gray" variant="ghost" icon="heroicons:clipboard-document" class="w-full justify-center sm:w-auto" @click="copySnippet(scenario.code)">
                复制命令
              </UButton>
            </div>
          </article>
        </div>
      </section>

      <section class="space-y-4">
        <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 class="text-2xl font-bold text-stone-900 dark:text-white">接口地图</h2>
          <p class="text-sm text-stone-500 dark:text-stone-400">点击任意分组可快速定位到对应端点区域。</p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <button
            v-for="section in sectionHighlights"
            :key="section.id"
            type="button"
            class="rounded-xl border border-stone-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-sm dark:border-stone-700 dark:bg-stone-900 dark:hover:border-amber-500/50"
            @click="jumpToAnchor(section.id)"
          >
            <div class="mb-2 flex items-start justify-between gap-3">
              <div class="flex items-center gap-2">
                <UIcon :name="section.icon || 'heroicons:cube'" class="h-5 w-5 text-amber-500 dark:text-amber-300" />
                <h3 class="font-semibold text-stone-900 dark:text-white">{{ section.title }}</h3>
              </div>
              <UBadge color="gray" variant="soft">{{ section.endpointCount }}</UBadge>
            </div>
            <p class="line-clamp-2 text-sm text-stone-600 dark:text-stone-400">{{ section.description || '暂无描述' }}</p>
            <div class="mt-3 flex flex-wrap gap-1.5">
              <UBadge
                v-for="method in section.methods"
                :key="method"
                :color="getMethodBadgeColor(method)"
                variant="subtle"
                size="xs"
              >
                {{ method }}
              </UBadge>
            </div>
          </button>
        </div>
      </section>

      <DocsLayout :sections="apiSections">
        <div class="space-y-10">
          <section
            v-for="section in apiSections"
            :key="section.id"
            class="space-y-5 rounded-2xl border border-stone-200 bg-white/70 p-3 dark:border-stone-700 dark:bg-stone-900/60 sm:p-4 md:p-5"
          >
            <div :id="section.id" class="scroll-mt-24 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div class="flex items-start gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 text-white shadow-sm">
                  <UIcon :name="section.icon || 'heroicons:cube'" class="h-5 w-5" />
                </div>
                <div>
                  <h2 class="text-2xl font-bold text-stone-900 dark:text-white">{{ section.title }}</h2>
                  <p v-if="section.description" class="mt-1 text-sm text-stone-600 dark:text-stone-400">{{ section.description }}</p>
                </div>
              </div>
              <UBadge color="gray" variant="soft" size="sm" class="self-start">{{ section.endpoints.length }} 个端点</UBadge>
            </div>

            <div class="space-y-5">
              <DocsEndpointCard
                v-for="endpoint in section.endpoints"
                :key="endpoint.id"
                :endpoint="endpoint"
                :base-url="baseUrl"
              />
            </div>
          </section>

          <section id="error-codes" class="scroll-mt-24 rounded-2xl border border-stone-200 bg-white/80 p-4 dark:border-stone-700 dark:bg-stone-900/80 sm:p-5 md:p-6">
            <div class="mb-4 flex items-center gap-3">
              <div class="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-red-500 to-red-600 text-white shadow-sm">
                <UIcon name="heroicons:exclamation-triangle" class="h-5 w-5" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-stone-900 dark:text-white">错误代码速查</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400">常见 HTTP 响应状态整理</p>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="code in errorCodes"
                :key="code.status"
                class="rounded-xl border border-stone-200 bg-stone-50/70 p-3 dark:border-stone-700 dark:bg-stone-800/40"
              >
                <div class="mb-2">
                  <UBadge :color="getStatusColor(code.status)" variant="subtle">{{ code.status }}</UBadge>
                </div>
                <p class="text-sm text-stone-700 dark:text-stone-300">{{ code.description }}</p>
              </div>
            </div>
          </section>

          <section id="test" class="scroll-mt-24 rounded-2xl border border-stone-200 bg-white/80 p-4 dark:border-stone-700 dark:bg-stone-900/80 sm:p-5 md:p-6">
            <div class="mb-5 flex items-center gap-3">
              <div class="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 text-white shadow-sm">
                <UIcon name="heroicons:beaker" class="h-5 w-5" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-stone-900 dark:text-white">在线调试沙箱</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400">即刻上传一张图，验证你当前环境连通性。</p>
              </div>
            </div>

            <div class="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <div class="space-y-4">
                <p class="text-sm leading-6 text-stone-600 dark:text-stone-300">
                  不填 Token 走匿名上传，填写后自动切换到 <code class="rounded bg-stone-100 px-1 py-0.5 font-mono text-xs dark:bg-stone-800">Bearer</code> 上传通道。
                </p>

                <UInput
                  v-model="testToken"
                  placeholder="可选：Bearer Token，留空则匿名上传"
                  size="sm"
                  :ui="{ base: 'font-mono text-xs' }"
                />

                <div class="flex flex-wrap items-center gap-3">
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
                    选择图片并测试
                  </UButton>
                  <span class="text-xs text-stone-500 dark:text-stone-400">支持 JPG / PNG / GIF / WebP / AVIF / SVG</span>
                </div>

                <div class="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
                  如果返回 401 或 403，先检查系统是否开启匿名上传或 Token 功能，再确认 Token 是否过期。
                </div>
              </div>

              <div class="space-y-3">
                <div v-if="!testResult" class="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-stone-300 bg-stone-50/80 p-4 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-800/30 dark:text-stone-400">
                  上传后会在这里展示响应数据和图片预览。
                </div>

                <div
                  v-else-if="testResult.success"
                  class="space-y-3 rounded-xl border border-green-200 bg-green-50/60 p-4 dark:border-green-500/40 dark:bg-green-500/10"
                >
                  <div class="flex items-start gap-3">
                    <img
                      v-if="previewImageUrl"
                      :src="previewImageUrl"
                      :alt="previewImageName"
                      class="h-20 w-20 flex-shrink-0 rounded-lg border border-green-300 object-cover dark:border-green-700"
                    />
                    <div class="min-w-0 flex-1">
                      <h4 class="font-semibold text-green-800 dark:text-green-200">测试成功</h4>
                      <p v-if="previewImageUrl" class="truncate font-mono text-xs text-green-700 dark:text-green-300">{{ previewImageUrl }}</p>
                    </div>
                  </div>
                  <DocsCodeBlock :code="JSON.stringify(testResult, null, 2)" language="json" />
                </div>

                <div
                  v-else
                  class="space-y-3 rounded-xl border border-red-200 bg-red-50/70 p-4 dark:border-red-500/40 dark:bg-red-500/10"
                >
                  <h4 class="font-semibold text-red-800 dark:text-red-200">测试失败</h4>
                  <DocsCodeBlock :code="JSON.stringify(testResult, null, 2)" language="json" />
                </div>
              </div>
            </div>
          </section>
        </div>
      </DocsLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HttpMethod } from '~/data/apiDocs'
import { apiSections, getMethodColor } from '~/data/apiDocs'

interface TestUploadResult {
  success: boolean
  data?: Record<string, any>
  error?: string
}

const config = useRuntimeConfig()
const requestUrl = useRequestURL()
const toast = useLightToast()
const { copy: clipboardCopy } = useClipboardCopy()
const { displayName } = useSeoSettings()

const docsSiteName = computed(() => displayName.value.trim() || '图床 Pro')
const docsCenterTitle = computed(() => `${docsSiteName.value} API 文档中心`)

const baseUrl = computed(() => (config.public.apiBase || requestUrl.origin).replace(/\/$/, ''))

const testFileInput = ref<HTMLInputElement>()
const testUploading = ref(false)
const testResult = ref<TestUploadResult | null>(null)
const testToken = ref('')

const docsVersion = '2.0'
const docsUpdatedAt = '2026-02'

const endpointCount = computed(() => apiSections.reduce((sum, section) => sum + section.endpoints.length, 0))
const tokenSecuredCount = computed(() =>
  apiSections.reduce(
    (sum, section) => sum + section.endpoints.filter((endpoint) => endpoint.auth === 'bearer').length,
    0
  )
)
const publicCount = computed(() => endpointCount.value - tokenSecuredCount.value)

const heroStats = computed(() => [
  {
    label: 'API 分组',
    value: apiSections.length,
    icon: 'heroicons:squares-2x2',
    tip: '按业务域拆分文档结构',
  },
  {
    label: '端点总数',
    value: endpointCount.value,
    icon: 'heroicons:command-line',
    tip: '覆盖上传、查询、Token、状态',
  },
  {
    label: '公开端点',
    value: publicCount.value,
    icon: 'heroicons:lock-open',
    tip: '无需 Bearer 可直接访问',
  },
  {
    label: 'Token 端点',
    value: tokenSecuredCount.value,
    icon: 'heroicons:lock-closed',
    tip: '需携带 Authorization 头',
  },
])

const quickStartScenarios = computed(() => [
  {
    id: 'anonymous-upload',
    badge: '匿名策略',
    badgeColor: 'green' as const,
    title: '无需 Token，直接上传',
    endpoint: '/api/upload',
    description: '适合开放站点或内部临时上传。若系统策略限制匿名上传，会返回 403。',
    code: `curl -X POST "${baseUrl.value}/api/upload" \\\n  -F "file=@image.jpg"`,
  },
  {
    id: 'token-upload',
    badge: 'Token 策略',
    badgeColor: 'amber' as const,
    title: '先拿 Token，再上传',
    endpoint: '/api/auth/upload',
    description: '适合配额控制和访问审计。Token 模式能限制上传次数和有效期。',
    code: `curl -X POST "${baseUrl.value}/api/auth/upload" \\\n  -H "Authorization: Bearer guest_xxxxx" \\\n  -F "file=@image.jpg"`,
  },
])

const heroCurlExample = computed(() => quickStartScenarios.value[0]?.code || '')

const sectionHighlights = computed(() =>
  apiSections.map((section) => ({
    id: section.id,
    title: section.title,
    description: section.description,
    icon: section.icon,
    endpointCount: section.endpoints.length,
    methods: Array.from(new Set(section.endpoints.map((endpoint) => endpoint.method))),
  }))
)

const errorCodes = [
  { status: 200, description: '请求成功' },
  { status: 302, description: '资源可能被重定向到 CDN' },
  { status: 400, description: '请求参数错误或缺失' },
  { status: 401, description: 'Token 缺失、格式错误或已失效' },
  { status: 403, description: '功能被禁用或访问策略不允许' },
  { status: 404, description: '目标资源不存在' },
  { status: 413, description: '上传文件体积超过限制' },
  { status: 429, description: '请求过于频繁，触发限流' },
  { status: 500, description: '服务器内部错误' },
]

const previewImageUrl = computed(() => {
  if (!testResult.value?.success || !testResult.value.data) return ''
  return (
    testResult.value.data.url ||
    testResult.value.data.image_url ||
    ''
  )
})

const previewImageName = computed(() => {
  if (!testResult.value?.success || !testResult.value.data) return 'upload-result'
  return (
    testResult.value.data.filename ||
    testResult.value.data.original_filename ||
    'upload-result'
  )
})

const resolveApiUrl = (path: string): string => {
  const targetPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl.value}${targetPath}`
}

const copyBaseUrl = () => {
  clipboardCopy(baseUrl.value, '基础 URL 已复制')
}

const copySnippet = (code: string) => {
  clipboardCopy(code, '示例命令已复制')
}

const jumpToAnchor = (id: string) => {
  if (!import.meta.client) return
  const element = document.getElementById(id)
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const getStatusColor = (status: number) => {
  if (status >= 200 && status < 300) return 'green' as const
  if (status >= 300 && status < 400) return 'blue' as const
  if (status >= 400 && status < 500) return 'amber' as const
  return 'red' as const
}

const getMethodBadgeColor = (method: HttpMethod) => {
  return getMethodColor(method) as 'blue' | 'green' | 'amber' | 'red' | 'gray'
}

const handleTestUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return

  testUploading.value = true
  testResult.value = null

  try {
    const file = target.files[0]
    const fd = new FormData()
    fd.append('file', file)

    const token = testToken.value.trim()
    const headers: Record<string, string> = {}
    let uploadUrl = resolveApiUrl('/api/upload')

    if (token) {
      uploadUrl = resolveApiUrl('/api/auth/upload')
      headers.Authorization = `Bearer ${token}`
    }

    const resp = await $fetch<any>(uploadUrl, {
      method: 'POST',
      body: fd,
      headers,
    })

    testResult.value = {
      success: true,
      data: resp?.data || resp,
    }
    toast.success('测试成功', '图片上传成功')
  } catch (error: any) {
    const errorMessage =
      error?.data?.error ||
      error?.data?.message ||
      error?.message ||
      '未知错误'

    testResult.value = {
      success: false,
      error: errorMessage,
      data: error?.data,
    }
    toast.error('测试失败', errorMessage)
  } finally {
    testUploading.value = false
    target.value = ''
  }
}
</script>
