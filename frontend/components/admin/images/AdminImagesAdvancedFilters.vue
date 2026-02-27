<template>
  <div class="flex h-full flex-col">
    <div class="border-b border-stone-200 px-4 py-3 dark:border-neutral-700">
      <h3 class="text-base font-semibold text-stone-900 dark:text-white">高级筛选</h3>
      <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">
        组合来源、时间范围、大小与访问量条件
      </p>
    </div>

    <div class="flex-1 overflow-y-auto px-4 py-4">
      <div class="space-y-4">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <UFormGroup label="来源">
            <USelect
              v-model="draft.source"
              :options="sourceOptions"
              option-attribute="label"
              value-attribute="value"
              size="sm"
            />
          </UFormGroup>

          <UFormGroup label="缓存状态">
            <USelect
              v-model="draft.cacheStatus"
              :options="cacheOptions"
              option-attribute="label"
              value-attribute="value"
              size="sm"
            />
          </UFormGroup>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <UFormGroup label="起始日期">
            <UInput v-model="draft.dateFrom" type="date" size="sm" />
          </UFormGroup>
          <UFormGroup label="结束日期">
            <UInput v-model="draft.dateTo" type="date" size="sm" />
          </UFormGroup>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <UFormGroup label="最小大小（MB）">
            <UInput v-model="draft.sizeMinMb" type="number" min="0" step="0.1" size="sm" placeholder="例如 0.5" />
          </UFormGroup>
          <UFormGroup label="最大大小（MB）">
            <UInput v-model="draft.sizeMaxMb" type="number" min="0" step="0.1" size="sm" placeholder="例如 20" />
          </UFormGroup>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <UFormGroup label="最小访问量">
            <UInput v-model="draft.accessMin" type="number" min="0" step="1" size="sm" placeholder="例如 10" />
          </UFormGroup>
          <UFormGroup label="最大访问量">
            <UInput v-model="draft.accessMax" type="number" min="0" step="1" size="sm" placeholder="例如 5000" />
          </UFormGroup>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between border-t border-stone-200 px-4 py-3 dark:border-neutral-700">
      <UButton color="gray" variant="ghost" icon="heroicons:arrow-path" @click="onReset">
        重置
      </UButton>
      <div class="flex items-center gap-2">
        <UButton color="gray" variant="ghost" @click="$emit('cancel')">
          取消
        </UButton>
        <UButton color="primary" icon="heroicons:funnel" @click="onApply">
          应用筛选
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AdminImagesAdvancedFilters } from '~/composables/useAdminImages'

const props = defineProps<{
  modelValue: AdminImagesAdvancedFilters
  sourceOptions: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: AdminImagesAdvancedFilters]
  apply: [value: AdminImagesAdvancedFilters]
  reset: []
  cancel: []
}>()

const createDefaults = (): AdminImagesAdvancedFilters => ({
  source: 'all',
  cacheStatus: 'all',
  dateFrom: '',
  dateTo: '',
  sizeMinMb: '',
  sizeMaxMb: '',
  accessMin: '',
  accessMax: '',
})

const cacheOptions = [
  { label: '全部', value: 'all' },
  { label: '仅已缓存', value: 'cached' },
  { label: '仅未缓存', value: 'uncached' },
]

const draft = ref<AdminImagesAdvancedFilters>({ ...props.modelValue })

watch(
  () => props.modelValue,
  (value) => {
    draft.value = { ...value }
  },
  { deep: true }
)

const onApply = () => {
  const payload = { ...draft.value }
  emit('update:modelValue', payload)
  emit('apply', payload)
}

const onReset = () => {
  const next = createDefaults()
  draft.value = next
  emit('update:modelValue', next)
  emit('reset')
}
</script>
