<template>
  <UModal v-model="open" :ui="{ width: 'sm:max-w-4xl' }">
    <UCard :ui="{ body: { base: 'overflow-y-auto' }, ring: '', divide: 'divide-y divide-gray-100 dark:divide-gray-800' }" class="flex max-h-[88vh] flex-col">
      <template #header>
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">Storage Wizard</p>
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">
              {{ isEditing ? '编辑存储' : '添加存储' }}
            </h3>
          </div>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="open = false"
          />
        </div>
      </template>

      <div class="space-y-4">
        <div class="overflow-x-auto pb-1">
          <div class="flex min-w-max items-center gap-2">
            <button
              v-for="(step, index) in stepItems"
              :key="step.key"
              type="button"
              class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all"
              :class="index === stepIndex
                ? 'bg-amber-100 text-amber-800 ring-1 ring-amber-200 dark:bg-amber-900/30 dark:text-amber-200 dark:ring-amber-800/70'
                : index < stepIndex
                  ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:ring-emerald-800/60'
                  : 'bg-stone-100 text-stone-600 ring-1 ring-stone-200 dark:bg-neutral-800 dark:text-stone-300 dark:ring-neutral-700'"
              @click="jumpToStep(index)"
            >
              <UIcon :name="step.icon" class="h-3.5 w-3.5" />
              <span>{{ step.label }}</span>
            </button>
          </div>
        </div>

        <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/70">
          <template v-if="currentStep.key === 'basic'">
            <div class="grid gap-4 md:grid-cols-2">
              <UFormGroup label="存储名称" hint="创建后不可修改，仅支持字母/数字/_/-">
                <UInput
                  v-model="localForm.name"
                  placeholder="例如: my-s3"
                  :disabled="isEditing"
                />
              </UFormGroup>
              <UFormGroup label="驱动类型" hint="决定后续参数表单">
                <USelect
                  v-model="localForm.driver"
                  :options="driverOptions"
                  option-attribute="label"
                  value-attribute="value"
                />
              </UFormGroup>
            </div>
          </template>

          <template v-else-if="currentStep.key === 'driver'">
            <div class="space-y-4">
              <div class="rounded-xl border border-amber-200/70 bg-amber-50/70 p-3 text-xs text-amber-700 dark:border-amber-800/70 dark:bg-amber-900/20 dark:text-amber-200">
                当前驱动：<span class="font-semibold">{{ driverLabel }}</span>
              </div>

              <template v-if="localForm.driver === 'telegram'">
                <div class="grid gap-4 md:grid-cols-2">
                  <UFormGroup label="Bot Token" hint="新增时可留空使用环境变量 BOT_TOKEN">
                    <UInput v-model="localForm.bot_token" type="password" :placeholder="isEditing ? '留空保持不变' : '留空使用环境变量 BOT_TOKEN'" />
                    <p v-if="maskedState.bot_token && !localForm.bot_token" class="mt-1 text-xs text-amber-600 dark:text-amber-400">
                      已配置（留空保持不变）
                    </p>
                  </UFormGroup>
                  <UFormGroup label="Chat ID" hint="留空使用环境变量 STORAGE_CHAT_ID">
                    <UInput v-model="localForm.chat_id" placeholder="例如: -1001234567890" />
                  </UFormGroup>
                </div>
              </template>

              <template v-else-if="localForm.driver === 'local'">
                <UFormGroup label="存储目录" hint="建议使用绝对路径">
                  <UInput v-model="localForm.root_dir" placeholder="例如: /data/uploads" />
                </UFormGroup>
              </template>

              <template v-else-if="localForm.driver === 's3'">
                <div class="grid gap-4 md:grid-cols-2">
                  <UFormGroup label="Endpoint">
                    <UInput v-model="localForm.endpoint" placeholder="例如: https://s3.amazonaws.com" />
                  </UFormGroup>
                  <UFormGroup label="Bucket">
                    <UInput v-model="localForm.bucket" placeholder="存储桶名称" />
                  </UFormGroup>
                  <UFormGroup label="Access Key">
                    <UInput v-model="localForm.access_key" type="password" :placeholder="isEditing ? '留空保持不变' : '访问密钥'" />
                    <p v-if="maskedState.access_key && !localForm.access_key" class="mt-1 text-xs text-amber-600 dark:text-amber-400">
                      已配置（留空保持不变）
                    </p>
                  </UFormGroup>
                  <UFormGroup label="Secret Key">
                    <UInput v-model="localForm.secret_key" type="password" :placeholder="isEditing ? '留空保持不变' : '密钥'" />
                    <p v-if="maskedState.secret_key && !localForm.secret_key" class="mt-1 text-xs text-amber-600 dark:text-amber-400">
                      已配置（留空保持不变）
                    </p>
                  </UFormGroup>
                  <UFormGroup label="Region">
                    <UInput v-model="localForm.region" placeholder="例如: us-east-1" />
                  </UFormGroup>
                  <UFormGroup label="公开 URL 前缀">
                    <UInput v-model="localForm.public_url_prefix" placeholder="例如: https://cdn.example.com" />
                  </UFormGroup>
                  <div class="md:col-span-2">
                    <UCheckbox v-model="localForm.path_style" label="使用 Path Style" />
                  </div>
                </div>
              </template>

              <template v-else-if="localForm.driver === 'rclone'">
                <div class="grid gap-4 md:grid-cols-2">
                  <UFormGroup label="Remote 名称">
                    <UInput v-model="localForm.remote" placeholder="rclone 配置中的 remote 名称" />
                  </UFormGroup>
                  <UFormGroup label="基础路径">
                    <UInput v-model="localForm.base_path" placeholder="remote 下的基础路径" />
                  </UFormGroup>
                  <UFormGroup label="rclone 可执行文件">
                    <UInput v-model="localForm.rclone_bin" placeholder="默认: rclone" />
                  </UFormGroup>
                  <UFormGroup label="配置文件路径">
                    <UInput v-model="localForm.config_path" placeholder="留空使用默认配置" />
                  </UFormGroup>
                </div>
              </template>
            </div>
          </template>

          <template v-else-if="currentStep.key === 'advanced'">
            <div class="space-y-4">
              <template v-if="localForm.driver === 'telegram'">
                <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-800/60">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-stone-900 dark:text-white">同时用作机器人</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">保存时将 Token 同步到 Telegram 机器人配置</p>
                    </div>
                    <UToggle v-model="localForm.use_as_bot" />
                  </div>
                </div>

                <div class="space-y-3 rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-800/60">
                  <p class="text-sm font-medium text-stone-900 dark:text-white">群组上传设置</p>
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm text-stone-700 dark:text-stone-300">仅管理员可上传</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">关闭后可按绑定关系控制</p>
                    </div>
                    <UToggle v-model="localGroupUpload.admin_only" />
                  </div>

                  <UFormGroup v-if="localGroupUpload.admin_only" label="管理员 ID">
                    <UInput v-model="localGroupUpload.admin_ids" placeholder="多个 ID 用逗号分隔" />
                  </UFormGroup>

                  <div v-if="!localGroupUpload.admin_only" class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm text-stone-700 dark:text-stone-300">仅 TG 绑定用户可上传</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">限制仅绑定 Token 的 TG 用户上传</p>
                    </div>
                    <UToggle v-model="localGroupUpload.tg_bound_only" />
                  </div>

                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm text-stone-700 dark:text-stone-300">自动回复链接</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">上传成功后自动回复可访问链接</p>
                    </div>
                    <UToggle v-model="localGroupUpload.reply" />
                  </div>

                  <UFormGroup v-if="localGroupUpload.reply" label="回复删除延迟（秒）">
                    <UInput v-model.number="localGroupUpload.delete_delay" type="number" min="0" placeholder="0 表示不自动删除" />
                  </UFormGroup>
                </div>

                <div class="space-y-3 rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-800/60">
                  <p class="text-sm font-medium text-stone-900 dark:text-white">私聊上传设置</p>
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm text-stone-700 dark:text-stone-300">允许私聊上传</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">关闭后私聊 Bot 上传不可用</p>
                    </div>
                    <UToggle v-model="localPrivateUpload.enabled" />
                  </div>
                  <UFormGroup v-if="localPrivateUpload.enabled" label="上传权限">
                    <USelect
                      v-model="localPrivateUpload.mode"
                      :options="privateUploadModeOptions"
                      option-attribute="label"
                      value-attribute="value"
                    />
                  </UFormGroup>
                  <UFormGroup v-if="localPrivateUpload.enabled && localPrivateUpload.mode === 'admin_only'" label="管理员 ID">
                    <UInput v-model="localPrivateUpload.admin_ids" placeholder="多个 ID 用逗号分隔" />
                  </UFormGroup>
                </div>
              </template>

              <template v-else>
                <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-4 text-sm text-stone-600 dark:border-neutral-700/80 dark:bg-neutral-800/70 dark:text-stone-300">
                  当前驱动无需额外高级开关。你可以直接进入确认步骤保存配置。
                </div>
              </template>
            </div>
          </template>

          <template v-else>
            <div class="space-y-3">
              <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/70">
                <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">基础信息</p>
                <div class="mt-2 grid gap-2 text-sm text-stone-700 dark:text-stone-300 md:grid-cols-2">
                  <p><span class="text-stone-500 dark:text-stone-400">存储名称：</span>{{ localForm.name || '--' }}</p>
                  <p><span class="text-stone-500 dark:text-stone-400">驱动类型：</span>{{ driverLabel }}</p>
                </div>
              </div>

              <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/70">
                <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">驱动参数摘要</p>
                <div class="mt-2 space-y-1 text-sm text-stone-700 dark:text-stone-300">
                  <template v-if="localForm.driver === 'telegram'">
                    <p>Bot Token：{{ maskedState.bot_token && !localForm.bot_token ? '保持原配置' : (localForm.bot_token ? '已填写新值' : '未填写') }}</p>
                    <p>Chat ID：{{ localForm.chat_id || '留空' }}</p>
                  </template>
                  <template v-else-if="localForm.driver === 'local'">
                    <p>存储目录：{{ localForm.root_dir || '留空' }}</p>
                  </template>
                  <template v-else-if="localForm.driver === 's3'">
                    <p>Endpoint：{{ localForm.endpoint || '留空' }}</p>
                    <p>Bucket：{{ localForm.bucket || '留空' }}</p>
                    <p>Access Key：{{ maskedState.access_key && !localForm.access_key ? '保持原配置' : (localForm.access_key ? '已填写新值' : '未填写') }}</p>
                    <p>Secret Key：{{ maskedState.secret_key && !localForm.secret_key ? '保持原配置' : (localForm.secret_key ? '已填写新值' : '未填写') }}</p>
                  </template>
                  <template v-else>
                    <p>Remote：{{ localForm.remote || '留空' }}</p>
                    <p>基础路径：{{ localForm.base_path || '留空' }}</p>
                  </template>
                </div>
              </div>

              <div v-if="localForm.driver === 'telegram'" class="rounded-xl border border-amber-200/80 bg-amber-50/70 p-3 text-xs text-amber-700 dark:border-amber-800/70 dark:bg-amber-900/20 dark:text-amber-200">
                将同步应用 Telegram 机器人相关高级设置（群组上传与私聊上传策略）。
              </div>
            </div>
          </template>
        </div>

        <p v-if="stepError" class="text-sm text-rose-500">{{ stepError }}</p>
      </div>

      <template #footer>
        <div class="flex flex-wrap items-center justify-between gap-2 pb-1">
          <UButton color="gray" variant="outline" :disabled="stepIndex === 0" @click="prevStep">
            上一步
          </UButton>
          <div class="flex items-center gap-2">
            <UButton color="gray" variant="ghost" @click="open = false">
              取消
            </UButton>
            <UButton
              v-if="!isLastStep"
              color="primary"
              @click="nextStep"
            >
              下一步
            </UButton>
            <UButton
              v-else
              color="primary"
              :loading="saving"
              @click="submit"
            >
              {{ isEditing ? '保存存储' : '添加存储' }}
            </UButton>
          </div>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import type {
  StorageBackendForm,
  StorageDriverType,
  StorageGroupUploadForm,
  StoragePrivateUploadForm,
  StorageWizardStepKey,
} from '~/types/admin-storage'

const props = withDefaults(defineProps<{
  modelValue: boolean
  editingBackend: string | null
  form: StorageBackendForm
  groupUpload: StorageGroupUploadForm
  privateUpload: StoragePrivateUploadForm
  saving?: boolean
}>(), {
  saving: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (
    e: 'submit',
    payload: {
      form: StorageBackendForm
      groupUpload: StorageGroupUploadForm
      privateUpload: StoragePrivateUploadForm
    }
  ): void
}>()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const stepItems: Array<{ key: StorageWizardStepKey, label: string, icon: string }> = [
  { key: 'basic', label: '基础信息', icon: 'heroicons:identification' },
  { key: 'driver', label: '驱动参数', icon: 'heroicons:wrench-screwdriver' },
  { key: 'advanced', label: '高级设置', icon: 'heroicons:adjustments-horizontal' },
  { key: 'confirm', label: '确认保存', icon: 'heroicons:check-badge' },
]

const driverOptions: Array<{ value: StorageDriverType, label: string }> = [
  { value: 'telegram', label: 'Telegram' },
  { value: 'local', label: '本地存储' },
  { value: 's3', label: 'S3 兼容存储' },
  { value: 'rclone', label: 'Rclone' },
]

const privateUploadModeOptions = [
  { label: '所有人可上传', value: 'open' },
  { label: '仅 TG 绑定用户', value: 'tg_bound' },
  { label: '仅指定管理员', value: 'admin_only' },
]

const stepIndex = ref(0)
const stepError = ref('')

const isEditing = computed(() => Boolean(props.editingBackend))
const currentStep = computed(() => stepItems[stepIndex.value])
const isLastStep = computed(() => stepIndex.value === stepItems.length - 1)
const driverLabel = computed(() => driverOptions.find((item) => item.value === localForm.value.driver)?.label || localForm.value.driver)

const clonePlain = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const localForm = ref<StorageBackendForm>(clonePlain(props.form))
const localGroupUpload = ref<StorageGroupUploadForm>(clonePlain(props.groupUpload))
const localPrivateUpload = ref<StoragePrivateUploadForm>(clonePlain(props.privateUpload))
const maskedState = ref({
  bot_token: false,
  access_key: false,
  secret_key: false,
})

const resetLocalState = () => {
  stepIndex.value = 0
  stepError.value = ''

  const nextForm = clonePlain(props.form)
  maskedState.value = {
    bot_token: nextForm.bot_token === '__MASKED__',
    access_key: nextForm.access_key === '__MASKED__',
    secret_key: nextForm.secret_key === '__MASKED__',
  }

  if (maskedState.value.bot_token) nextForm.bot_token = ''
  if (maskedState.value.access_key) nextForm.access_key = ''
  if (maskedState.value.secret_key) nextForm.secret_key = ''

  localForm.value = nextForm
  localGroupUpload.value = clonePlain(props.groupUpload)
  localPrivateUpload.value = clonePlain(props.privateUpload)
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) resetLocalState()
  }
)

watch(
  () => localForm.value.driver,
  () => {
    stepError.value = ''
  }
)

const validateStep = (): boolean => {
  stepError.value = ''
  const form = localForm.value

  if (currentStep.value.key === 'basic') {
    if (!isEditing.value) {
      if (!form.name.trim()) {
        stepError.value = '请输入存储名称'
        return false
      }
      if (!/^[a-zA-Z0-9_-]{1,32}$/.test(form.name.trim())) {
        stepError.value = '存储名称仅支持字母、数字、下划线和连字符，长度 1-32'
        return false
      }
    }
    if (!form.driver) {
      stepError.value = '请选择驱动类型'
      return false
    }
  }

  if (currentStep.value.key === 'driver') {
    if (form.driver === 'local' && !form.root_dir.trim()) {
      stepError.value = '本地存储请填写存储目录'
      return false
    }
    if (form.driver === 's3' && !form.bucket.trim()) {
      stepError.value = 'S3 存储请填写 Bucket'
      return false
    }
    if (form.driver === 'rclone' && !form.remote.trim()) {
      stepError.value = 'Rclone 存储请填写 Remote 名称'
      return false
    }
  }

  if (currentStep.value.key === 'advanced') {
    if (form.driver === 'telegram' && localGroupUpload.value.admin_only && localGroupUpload.value.admin_ids.trim()) {
      const ids = localGroupUpload.value.admin_ids.split(',').map((x) => x.trim()).filter(Boolean)
      if (ids.some((x) => Number.isNaN(Number(x)))) {
        stepError.value = '群组管理员 ID 必须是逗号分隔的数字'
        return false
      }
    }
    if (form.driver === 'telegram' && localPrivateUpload.value.mode === 'admin_only' && localPrivateUpload.value.admin_ids.trim()) {
      const ids = localPrivateUpload.value.admin_ids.split(',').map((x) => x.trim()).filter(Boolean)
      if (ids.some((x) => Number.isNaN(Number(x)))) {
        stepError.value = '私聊管理员 ID 必须是逗号分隔的数字'
        return false
      }
    }
  }

  return true
}

const jumpToStep = (index: number) => {
  if (index <= stepIndex.value) {
    stepIndex.value = index
    stepError.value = ''
    return
  }

  if (index > stepIndex.value + 1) return

  if (!validateStep()) return
  stepIndex.value = index
}

const prevStep = () => {
  if (stepIndex.value === 0) return
  stepIndex.value -= 1
  stepError.value = ''
}

const nextStep = () => {
  if (!validateStep()) return
  if (stepIndex.value < stepItems.length - 1) {
    stepIndex.value += 1
  }
}

const submit = () => {
  if (!validateStep()) return

  const form = clonePlain(localForm.value)
  if (maskedState.value.bot_token && !form.bot_token.trim()) form.bot_token = '__MASKED__'
  if (maskedState.value.access_key && !form.access_key.trim()) form.access_key = '__MASKED__'
  if (maskedState.value.secret_key && !form.secret_key.trim()) form.secret_key = '__MASKED__'

  emit('submit', {
    form,
    groupUpload: clonePlain(localGroupUpload.value),
    privateUpload: clonePlain(localPrivateUpload.value),
  })
}
</script>
