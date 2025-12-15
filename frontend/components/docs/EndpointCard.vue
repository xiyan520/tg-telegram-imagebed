<template>
  <div :id="endpoint.id" class="scroll-mt-20">
    <UCard>
      <template #header>
        <div class="flex flex-col gap-2">
          <!-- 方法 + 路径 -->
          <div class="flex items-center gap-3 flex-wrap">
            <UBadge :color="methodColor" size="lg" class="font-mono">
              {{ endpoint.method }}
            </UBadge>
            <code class="text-sm text-stone-700 dark:text-stone-300">{{ endpoint.path }}</code>
            <UBadge v-if="endpoint.deprecated" color="red" variant="subtle" size="xs">
              已废弃
            </UBadge>
          </div>
          <!-- 标题 -->
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">
            {{ endpoint.title }}
          </h3>
          <!-- 摘要 -->
          <p v-if="endpoint.summary" class="text-sm text-stone-600 dark:text-stone-400">
            {{ endpoint.summary }}
          </p>
        </div>
      </template>

      <div class="space-y-6">
        <!-- 描述 -->
        <p v-if="endpoint.description" class="text-stone-700 dark:text-stone-300">
          {{ endpoint.description }}
        </p>

        <!-- 认证方式 -->
        <div v-if="endpoint.auth" class="flex items-center gap-2">
          <UIcon
            :name="endpoint.auth === 'bearer' ? 'heroicons:lock-closed' : 'heroicons:lock-open'"
            class="w-4 h-4"
            :class="endpoint.auth === 'bearer' ? 'text-amber-500' : 'text-green-500'"
          />
          <span class="text-sm text-stone-600 dark:text-stone-400">
            {{ endpoint.authDescription || (endpoint.auth === 'bearer' ? '需要 Bearer Token' : '无需认证') }}
          </span>
        </div>

        <!-- 参数表 -->
        <div v-if="endpoint.params && endpoint.params.length > 0">
          <h4 class="text-sm font-semibold text-stone-900 dark:text-white mb-2">请求参数</h4>
          <DocsParamsTable :params="endpoint.params" />
        </div>

        <!-- 代码示例 -->
        <div v-if="endpoint.codeExamples && endpoint.codeExamples.length > 0">
          <h4 class="text-sm font-semibold text-stone-900 dark:text-white mb-2">请求示例</h4>
          <UTabs :items="codeTabItems" class="w-full">
            <template #item="{ item }">
              <DocsCodeBlock :code="item.code" :language="item.language" />
            </template>
          </UTabs>
        </div>

        <!-- 响应示例 -->
        <div v-if="endpoint.responses && endpoint.responses.length > 0">
          <h4 class="text-sm font-semibold text-stone-900 dark:text-white mb-2">响应</h4>
          <div class="space-y-3">
            <div
              v-for="resp in endpoint.responses"
              :key="resp.status"
              class="border border-stone-200 dark:border-stone-700 rounded-lg overflow-hidden"
            >
              <div class="flex items-center gap-2 px-3 py-2 bg-stone-50 dark:bg-stone-800/50">
                <UBadge :color="getStatusColor(resp.status)" variant="subtle" size="xs">
                  {{ resp.status }}
                </UBadge>
                <span class="text-sm text-stone-600 dark:text-stone-400">{{ resp.description }}</span>
              </div>
              <div v-if="resp.example" class="p-0">
                <DocsCodeBlock :code="processTemplate(resp.example)" language="json" />
              </div>
            </div>
          </div>
        </div>

        <!-- 备注 -->
        <div v-if="endpoint.notes && endpoint.notes.length > 0">
          <h4 class="text-sm font-semibold text-stone-900 dark:text-white mb-2">备注</h4>
          <ul class="space-y-1">
            <li
              v-for="(note, idx) in endpoint.notes"
              :key="idx"
              class="flex items-start gap-2 text-sm text-stone-600 dark:text-stone-400"
            >
              <UIcon name="heroicons:information-circle" class="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
              <span>{{ note }}</span>
            </li>
          </ul>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { ApiEndpoint } from '~/data/apiDocs'
import { getMethodColor, replaceTemplateVars, DEFAULT_TEMPLATE_VALUES } from '~/data/apiDocs'

const props = defineProps<{
  endpoint: ApiEndpoint
  baseUrl: string
}>()

const methodColor = computed(() => getMethodColor(props.endpoint.method))

// 合并默认模板值与运行时 baseUrl
const templateValues = computed(() => ({
  ...DEFAULT_TEMPLATE_VALUES,
  baseUrl: props.baseUrl,
}))

const codeTabItems = computed(() => {
  return (props.endpoint.codeExamples || []).map((ex) => ({
    label: ex.label,
    code: processTemplate(ex.code),
    language: ex.language,
  }))
})

const processTemplate = (template: string): string => {
  return replaceTemplateVars(template, templateValues.value)
}

const getStatusColor = (status: number): string => {
  if (status >= 200 && status < 300) return 'green'
  if (status >= 300 && status < 400) return 'blue'
  if (status >= 400 && status < 500) return 'amber'
  return 'red'
}
</script>
