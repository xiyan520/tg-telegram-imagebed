<template>
  <UModal :model-value="open" @update:model-value="emit('update:open', $event)">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">创建Token</h3>
            <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">
              创建成功后仅显示一次完整Token，请及时复制保存
            </p>
          </div>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="emit('close')" />
        </div>
      </template>

      <div class="space-y-4">
        <UFormGroup label="描述" hint="可选，用于备注Token用途">
          <UInput v-model="form.description" placeholder="例如：前端站点 / 服务器脚本" />
        </UFormGroup>

        <UFormGroup label="过期时间" hint="可选，不填写表示不过期">
          <UInput v-model="form.expires_at" type="datetime-local" />
        </UFormGroup>

        <UFormGroup label="上传限制" hint="达到限制后该Token将无法继续上传">
          <UInput v-model.number="form.upload_limit" type="number" min="0" max="1000000" placeholder="100" />
        </UFormGroup>

        <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
          <div>
            <p class="text-sm font-medium text-stone-900 dark:text-white">创建后启用</p>
            <p class="text-xs text-stone-500 dark:text-stone-400">关闭则创建为禁用状态</p>
          </div>
          <UToggle v-model="form.is_active" size="lg" />
        </div>

        <!-- 创建成功后显示完整 Token -->
        <div v-if="createdToken" class="p-4 border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 rounded-xl space-y-3">
          <div class="flex items-start gap-3">
            <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div class="flex-1">
              <p class="font-medium text-amber-900 dark:text-amber-200">完整Token（仅显示一次）</p>
              <p class="text-xs text-amber-700 dark:text-amber-300 mt-1">
                请立即复制保存。关闭弹窗后将无法再次查看完整Token。
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <code class="flex-1 font-mono text-xs p-3 rounded bg-white/70 dark:bg-neutral-900/40 break-all">
              {{ createdToken }}
            </code>
            <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" @click="emit('copyToken')">
              复制
            </UButton>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="emit('close')">关闭</UButton>
          <UButton color="primary" :loading="creating" :disabled="creating" @click="emit('create', form)">
            创建
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
export interface CreateTokenForm {
  description: string
  expires_at: string
  upload_limit: number
  is_active: boolean
}

const props = defineProps<{
  open: boolean
  creating: boolean
  createdToken: string | null
  initialForm: CreateTokenForm
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'close': []
  'create': [form: CreateTokenForm]
  'copyToken': []
}>()

// 本地表单状态，由父组件通过 initialForm 初始化
const form = reactive<CreateTokenForm>({ ...props.initialForm })

// 当父组件重置表单时同步
watch(() => props.initialForm, (val) => {
  Object.assign(form, val)
}, { deep: true })
</script>
