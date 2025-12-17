<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">存储设置</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">查看存储状态、切换默认存储、配置上传场景路由</p>
      </div>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="outline"
        :loading="loading"
        @click="loadAll"
      >
        刷新
      </UButton>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && backendNames.length === 0" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <!-- 环境变量覆盖提示 -->
      <div v-if="envOverride" class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
        <div class="flex items-center gap-2">
          <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <p class="text-sm text-amber-800 dark:text-amber-200">
            存储配置由环境变量 <code class="px-1 py-0.5 bg-amber-100 dark:bg-amber-800 rounded">STORAGE_CONFIG_JSON</code> 控制，无法通过界面修改。
          </p>
        </div>
      </div>

      <!-- 存储列表 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:server-stack" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">存储列表</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">已配置存储与健康状态</p>
              </div>
            </div>
            <UButton
              v-if="!envOverride"
              icon="heroicons:plus"
              color="primary"
              @click="openAddModal"
            >
              添加存储
            </UButton>
          </div>
        </template>

        <div class="space-y-3">
          <div v-if="backendNames.length === 0" class="text-sm text-stone-500 dark:text-stone-400">
            未发现已配置的存储（请检查 storage_config_json / STORAGE_CONFIG_JSON）。
          </div>
          <div
            v-for="name in backendNames"
            :key="name"
            class="flex items-center justify-between p-3 rounded-xl border border-stone-200 dark:border-neutral-700"
          >
            <div class="flex items-center gap-3">
              <div class="font-medium text-stone-900 dark:text-white">{{ name }}</div>
              <UBadge color="gray" variant="subtle">{{ backends[name]?.driver }}</UBadge>
              <UBadge v-if="name === activeBackend" color="amber" variant="solid">Active</UBadge>
            </div>
            <div class="flex items-center gap-2">
              <UBadge v-if="health[name] === true" color="green" variant="subtle">Healthy</UBadge>
              <UBadge v-else-if="health[name] === false" color="red" variant="subtle">Unhealthy</UBadge>
              <UBadge v-else color="gray" variant="subtle">Unknown</UBadge>
              <template v-if="!envOverride">
                <UButton
                  icon="heroicons:pencil-square"
                  color="gray"
                  variant="ghost"
                  size="xs"
                  @click="openEditModal(name)"
                />
                <UButton
                  icon="heroicons:trash"
                  color="red"
                  variant="ghost"
                  size="xs"
                  :disabled="name === activeBackend"
                  @click="confirmDelete(name)"
                />
              </template>
            </div>
          </div>
        </div>
      </UCard>

      <!-- 默认存储 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">默认存储</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">所有未指定场景规则的上传会跟随默认存储</p>
              </div>
            </div>
            <UButton color="primary" :loading="savingActive" @click="saveActive">保存</UButton>
          </div>
        </template>

        <USelect
          v-model="activeBackendDraft"
          :options="backendOptions"
          option-attribute="label"
          value-attribute="value"
        />
      </UCard>

      <!-- 上传场景路由 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:arrows-right-left" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">上传场景路由</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">为不同权限场景指定上传存储；选择"跟随默认"表示使用 Active</p>
              </div>
            </div>
            <UButton color="primary" variant="outline" :loading="savingPolicy" @click="savePolicy">保存</UButton>
          </div>
        </template>

        <div class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">游客上传</label>
              <USelect
                v-model="policy.guest"
                :options="sceneBackendOptions"
                option-attribute="label"
                value-attribute="value"
              />
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">匿名用户上传使用的存储</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Token 上传</label>
              <USelect
                v-model="policy.token"
                :options="sceneBackendOptions"
                option-attribute="label"
                value-attribute="value"
              />
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">使用 Token 上传使用的存储</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">群组上传</label>
              <USelect
                v-model="policy.group"
                :options="sceneBackendOptions"
                option-attribute="label"
                value-attribute="value"
              />
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">Telegram 群组上传使用的存储</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">管理员默认存储</label>
              <USelect
                v-model="policy.admin_default"
                :options="sceneBackendOptions"
                option-attribute="label"
                value-attribute="value"
              />
              <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">管理员上传时的默认存储</p>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">管理员可用存储</label>
            <p class="text-xs text-stone-500 dark:text-stone-400 mb-3">不勾选任何项表示允许所有已配置存储</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              <label
                v-for="name in backendNames"
                :key="name"
                class="flex items-center gap-2 p-2 rounded-lg border border-stone-200 dark:border-neutral-700 cursor-pointer hover:bg-stone-50 dark:hover:bg-neutral-800"
              >
                <input
                  type="checkbox"
                  class="accent-amber-500 w-4 h-4"
                  :checked="policy.admin_allowed.includes(name)"
                  @change="toggleAllowed(name)"
                />
                <span class="text-sm text-stone-800 dark:text-stone-200">{{ name }}</span>
                <UBadge color="gray" variant="subtle" size="xs">{{ backends[name]?.driver }}</UBadge>
              </label>
            </div>
          </div>
        </div>
      </UCard>

      <!-- 管理员上传测试 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-amber-500 to-amber-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">管理员上传</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">可选择指定存储上传图片</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">选择存储</label>
              <USelect
                v-model="uploadBackend"
                :options="adminUploadBackendOptions"
                option-attribute="label"
                value-attribute="value"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">选择文件</label>
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="block w-full text-sm text-stone-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 dark:file:bg-amber-900/20 dark:file:text-amber-400"
                @change="handleFileSelect"
              />
            </div>
          </div>

          <div v-if="selectedFile" class="p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <p class="text-sm text-stone-700 dark:text-stone-300">
              已选择: {{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})
            </p>
          </div>

          <UButton
            color="primary"
            :loading="uploading"
            :disabled="!selectedFile"
            @click="uploadFile"
          >
            <template #leading>
              <UIcon name="heroicons:cloud-arrow-up" />
            </template>
            上传
          </UButton>

          <div v-if="uploadResult" class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
            <p class="font-medium text-green-800 dark:text-green-200">上传成功</p>
            <p class="text-sm text-green-600 dark:text-green-300 mt-1 break-all">
              URL: <a :href="uploadResult.url" target="_blank" class="underline">{{ uploadResult.url }}</a>
            </p>
          </div>
        </div>
      </UCard>
    </template>

    <!-- 添加/编辑存储模态框 -->
    <UModal v-model="showBackendModal">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">
              {{ editingBackend ? '编辑存储' : '添加存储' }}
            </h3>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              size="xs"
              @click="showBackendModal = false"
            />
          </div>
        </template>

        <div class="space-y-4">
          <!-- 存储名称 -->
          <div>
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">存储名称</label>
            <UInput
              v-model="backendForm.name"
              placeholder="例如: my-s3"
              :disabled="!!editingBackend"
            />
            <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">唯一标识符，创建后不可修改</p>
          </div>

          <!-- 驱动类型 -->
          <div>
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">驱动类型</label>
            <USelect
              v-model="backendForm.driver"
              :options="driverOptions"
              option-attribute="label"
              value-attribute="value"
            />
          </div>

          <!-- Telegram 配置 -->
          <template v-if="backendForm.driver === 'telegram'">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Bot Token</label>
              <UInput v-model="backendForm.bot_token" type="password" :placeholder="editingBackend ? '留空保持不变' : '留空使用环境变量 BOT_TOKEN'" />
              <p v-if="editingBackend && backendForm.bot_token === '__MASKED__'" class="text-xs text-amber-600 dark:text-amber-400 mt-1">已配置（留空保持不变）</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Chat ID</label>
              <UInput v-model="backendForm.chat_id" placeholder="留空使用环境变量 STORAGE_CHAT_ID" />
            </div>

            <!-- 群组上传配置 -->
            <div class="pt-4 border-t border-stone-200 dark:border-neutral-700">
              <p class="font-medium text-stone-900 dark:text-white mb-4">群组上传设置</p>
              <div class="space-y-4">
                <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
                  <div>
                    <p class="text-sm font-medium text-stone-700 dark:text-stone-300">仅管理员可上传</p>
                    <p class="text-xs text-stone-500 dark:text-stone-400">限制只有指定管理员才能通过群组上传</p>
                  </div>
                  <UToggle v-model="groupUpload.admin_only" />
                </div>

                <div v-if="groupUpload.admin_only">
                  <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">管理员 ID</label>
                  <UInput v-model="groupUpload.admin_ids" placeholder="多个 ID 用逗号分隔" />
                  <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">Telegram 用户 ID，多个用逗号分隔</p>
                </div>

                <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
                  <div>
                    <p class="text-sm font-medium text-stone-700 dark:text-stone-300">自动回复链接</p>
                    <p class="text-xs text-stone-500 dark:text-stone-400">上传成功后自动回复图片链接</p>
                  </div>
                  <UToggle v-model="groupUpload.reply" />
                </div>

                <div v-if="groupUpload.reply">
                  <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">回复删除延迟（秒）</label>
                  <UInput v-model.number="groupUpload.delete_delay" type="number" min="0" placeholder="0 表示不自动删除" />
                </div>
              </div>
            </div>
          </template>

          <!-- Local 配置 -->
          <template v-if="backendForm.driver === 'local'">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">存储目录</label>
              <UInput v-model="backendForm.root_dir" placeholder="例如: /data/uploads" />
            </div>
          </template>

          <!-- S3 配置 -->
          <template v-if="backendForm.driver === 's3'">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Endpoint</label>
              <UInput v-model="backendForm.endpoint" placeholder="例如: https://s3.amazonaws.com" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Bucket</label>
              <UInput v-model="backendForm.bucket" placeholder="存储桶名称" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Access Key</label>
              <UInput v-model="backendForm.access_key" type="password" :placeholder="editingBackend ? '留空保持不变' : '访问密钥'" />
              <p v-if="editingBackend && backendForm.access_key === '__MASKED__'" class="text-xs text-amber-600 dark:text-amber-400 mt-1">已配置（留空保持不变）</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Secret Key</label>
              <UInput v-model="backendForm.secret_key" type="password" :placeholder="editingBackend ? '留空保持不变' : '密钥'" />
              <p v-if="editingBackend && backendForm.secret_key === '__MASKED__'" class="text-xs text-amber-600 dark:text-amber-400 mt-1">已配置（留空保持不变）</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Region</label>
              <UInput v-model="backendForm.region" placeholder="例如: us-east-1" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">公开 URL 前缀</label>
              <UInput v-model="backendForm.public_url_prefix" placeholder="例如: https://cdn.example.com" />
            </div>
            <div class="flex items-center gap-2">
              <input type="checkbox" v-model="backendForm.path_style" class="accent-amber-500 w-4 h-4" />
              <label class="text-sm text-stone-700 dark:text-stone-300">使用 Path Style</label>
            </div>
          </template>

          <!-- Rclone 配置 -->
          <template v-if="backendForm.driver === 'rclone'">
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">Remote 名称</label>
              <UInput v-model="backendForm.remote" placeholder="rclone 配置中的 remote 名称" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">基础路径</label>
              <UInput v-model="backendForm.base_path" placeholder="remote 下的基础路径" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">rclone 可执行文件</label>
              <UInput v-model="backendForm.rclone_bin" placeholder="默认: rclone" />
            </div>
            <div>
              <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">配置文件路径</label>
              <UInput v-model="backendForm.config_path" placeholder="留空使用默认配置" />
            </div>
          </template>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="outline" @click="showBackendModal = false">取消</UButton>
            <UButton color="primary" :loading="savingBackend" @click="saveBackend">
              {{ editingBackend ? '保存' : '添加' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 删除确认模态框 -->
    <UModal v-model="showDeleteModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">确认删除</h3>
        </template>
        <p class="text-stone-700 dark:text-stone-300">
          确定要删除存储 <strong>{{ deletingBackend }}</strong> 吗？此操作不可撤销。
        </p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="outline" @click="showDeleteModal = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="deleteBackend">删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
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
const savingActive = ref(false)
const savingPolicy = ref(false)
const uploading = ref(false)
const savingBackend = ref(false)
const deleting = ref(false)
const savingGroupUpload = ref(false)

// 环境变量覆盖标志
const envOverride = ref(false)

// 存储数据
const backends = ref<Record<string, { driver: string; active: boolean }>>({})
const health = ref<Record<string, boolean>>({})
const activeBackend = ref<string>('')
const activeBackendDraft = ref<string>('')

// 策略数据
const policy = ref<{
  guest: string
  token: string
  group: string
  admin_default: string
  admin_allowed: string[]
}>({
  guest: '',
  token: '',
  group: '',
  admin_default: '',
  admin_allowed: []
})

// 群组上传配置
const groupUpload = ref({
  admin_only: false,
  admin_ids: '',
  reply: true,
  delete_delay: 0
})

// 上传相关
const uploadBackend = ref<string>('')
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadResult = ref<{ url: string; filename: string; size: string } | null>(null)

// 存储管理模态框
const showBackendModal = ref(false)
const showDeleteModal = ref(false)
const editingBackend = ref<string | null>(null)
const deletingBackend = ref<string>('')

// 存储表单
const backendForm = ref<{
  name: string
  driver: string
  // telegram
  bot_token: string
  chat_id: string
  // local
  root_dir: string
  // s3
  endpoint: string
  bucket: string
  access_key: string
  secret_key: string
  region: string
  public_url_prefix: string
  path_style: boolean
  // rclone
  remote: string
  base_path: string
  rclone_bin: string
  config_path: string
}>({
  name: '',
  driver: 'telegram',
  bot_token: '',
  chat_id: '',
  root_dir: '',
  endpoint: '',
  bucket: '',
  access_key: '',
  secret_key: '',
  region: '',
  public_url_prefix: '',
  path_style: false,
  remote: '',
  base_path: '',
  rclone_bin: '',
  config_path: ''
})

// 驱动选项
const driverOptions = [
  { value: 'telegram', label: 'Telegram' },
  { value: 'local', label: '本地存储' },
  { value: 's3', label: 'S3 兼容存储' },
  { value: 'rclone', label: 'Rclone' }
]

// 存储配置详情（用于编辑）
const backendConfigs = ref<Record<string, any>>({})

// 计算属性
const backendNames = computed(() => Object.keys(backends.value || {}))
const backendOptions = computed(() =>
  backendNames.value.map((name) => ({
    value: name,
    label: `${name} (${backends.value[name]?.driver || 'unknown'})`
  }))
)
const sceneBackendOptions = computed(() => [
  { value: '', label: '跟随默认 (Active)' },
  ...backendOptions.value
])
const adminUploadBackendOptions = computed(() => {
  const allowed = policy.value.admin_allowed
  if (allowed.length === 0) {
    return [{ value: '', label: '使用管理员默认存储' }, ...backendOptions.value]
  }
  return [
    { value: '', label: '使用管理员默认存储' },
    ...backendOptions.value.filter((opt) => allowed.includes(opt.value))
  ]
})

// 格式化文件大小
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 加载所有数据
const loadAll = async () => {
  loading.value = true
  try {
    const [storageResp, healthResp, policyResp, configResp, settingsResp] = await Promise.all([
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/health`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/policy`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/config`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, { credentials: 'include' })
    ])

    backends.value = storageResp?.data?.backends || {}
    activeBackend.value = storageResp?.data?.active || ''
    activeBackendDraft.value = activeBackend.value
    health.value = healthResp?.data || {}

    if (policyResp?.data?.policy) {
      policy.value = {
        guest: policyResp.data.policy.guest || '',
        token: policyResp.data.policy.token || '',
        group: policyResp.data.policy.group || '',
        admin_default: policyResp.data.policy.admin_default || '',
        admin_allowed: policyResp.data.policy.admin_allowed || []
      }
    }

    // 加载配置详情
    envOverride.value = configResp?.data?.env_override || false
    backendConfigs.value = configResp?.data?.backends || {}

    // 加载群组上传配置
    if (settingsResp?.data) {
      const d = settingsResp.data
      groupUpload.value = {
        admin_only: d.group_upload_admin_only ?? false,
        admin_ids: d.group_admin_ids ?? '',
        reply: d.group_upload_reply ?? true,
        delete_delay: d.group_upload_delete_delay ?? 0
      }
    }
  } catch (e: any) {
    console.error('加载存储配置失败:', e)
    notification.error('加载失败', e?.data?.error || '无法获取存储配置')
  } finally {
    loading.value = false
  }
}

// 保存默认存储
const saveActive = async () => {
  if (!activeBackendDraft.value) return
  savingActive.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/active`, {
      method: 'POST',
      body: { backend: activeBackendDraft.value },
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '切换失败')
    notification.success('已保存', `默认存储已切换到 ${activeBackendDraft.value}`)
    await loadAll()
  } catch (e: any) {
    console.error('切换默认存储失败:', e)
    notification.error('保存失败', e?.data?.error || e?.message || '无法切换默认存储')
  } finally {
    savingActive.value = false
  }
}

// 保存策略
const savePolicy = async () => {
  savingPolicy.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/policy`, {
      method: 'PUT',
      body: { policy: policy.value },
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')
    notification.success('已保存', '上传场景路由已更新')
    await loadAll()
  } catch (e: any) {
    console.error('保存策略失败:', e)
    notification.error('保存失败', e?.data?.error || e?.message || '无法保存路由策略')
  } finally {
    savingPolicy.value = false
  }
}

// 保存群组上传配置
const saveGroupUpload = async (silent = false) => {
  savingGroupUpload.value = true
  try {
    const payload = {
      group_upload_admin_only: groupUpload.value.admin_only,
      group_admin_ids: groupUpload.value.admin_ids,
      group_upload_reply: groupUpload.value.reply,
      group_upload_delete_delay: groupUpload.value.delete_delay
    }
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      method: 'PUT',
      body: payload,
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')
  } catch (e: any) {
    console.error('保存群组上传配置失败:', e)
    if (!silent) {
      notification.error('保存失败', e?.data?.error || e?.message || '无法保存群组上传配置')
    }
    throw e
  } finally {
    savingGroupUpload.value = false
  }
}

// 切换管理员可用存储
const toggleAllowed = (name: string) => {
  const arr = policy.value.admin_allowed
  const idx = arr.indexOf(name)
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(name)
  }
}

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
    uploadResult.value = null
  }
}

// 上传文件
const uploadFile = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  uploadResult.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    if (uploadBackend.value) {
      formData.append('backend', uploadBackend.value)
    }

    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/upload`, {
      method: 'POST',
      body: formData,
      credentials: 'include'
    })

    if (!resp?.success) throw new Error(resp?.error || '上传失败')

    uploadResult.value = resp.data
    notification.success('上传成功', `文件已上传到 ${uploadBackend.value || '默认存储'}`)

    // 清空文件选择
    selectedFile.value = null
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (e: any) {
    console.error('上传失败:', e)
    notification.error('上传失败', e?.data?.error || e?.message || '无法上传文件')
  } finally {
    uploading.value = false
  }
}

// 重置表单
const resetBackendForm = () => {
  backendForm.value = {
    name: '',
    driver: 'telegram',
    bot_token: '',
    chat_id: '',
    root_dir: '',
    endpoint: '',
    bucket: '',
    access_key: '',
    secret_key: '',
    region: '',
    public_url_prefix: '',
    path_style: false,
    remote: '',
    base_path: '',
    rclone_bin: '',
    config_path: ''
  }
}

// 打开添加模态框
const openAddModal = () => {
  editingBackend.value = null
  resetBackendForm()
  showBackendModal.value = true
}

// 打开编辑模态框
const openEditModal = (name: string) => {
  editingBackend.value = name
  const cfg = backendConfigs.value[name] || {}
  backendForm.value = {
    name,
    driver: cfg.driver || 'telegram',
    bot_token: cfg.bot_token || '',
    chat_id: cfg.chat_id || '',
    root_dir: cfg.root_dir || '',
    endpoint: cfg.endpoint || '',
    bucket: cfg.bucket || '',
    access_key: cfg.access_key || '',
    secret_key: cfg.secret_key || '',
    region: cfg.region || '',
    public_url_prefix: cfg.public_url_prefix || '',
    path_style: cfg.path_style || false,
    remote: cfg.remote || '',
    base_path: cfg.base_path || '',
    rclone_bin: cfg.rclone_bin || '',
    config_path: cfg.config_path || ''
  }
  showBackendModal.value = true
}

// 构建存储配置对象
const buildBackendConfig = () => {
  const form = backendForm.value
  const config: Record<string, any> = { driver: form.driver }

  if (form.driver === 'telegram') {
    if (form.bot_token) config.bot_token = form.bot_token
    if (form.chat_id) config.chat_id = form.chat_id
  } else if (form.driver === 'local') {
    if (form.root_dir) config.root_dir = form.root_dir
  } else if (form.driver === 's3') {
    if (form.endpoint) config.endpoint = form.endpoint
    if (form.bucket) config.bucket = form.bucket
    if (form.access_key) config.access_key = form.access_key
    if (form.secret_key) config.secret_key = form.secret_key
    if (form.region) config.region = form.region
    if (form.public_url_prefix) config.public_url_prefix = form.public_url_prefix
    config.path_style = form.path_style
  } else if (form.driver === 'rclone') {
    if (form.remote) config.remote = form.remote
    if (form.base_path) config.base_path = form.base_path
    if (form.rclone_bin) config.rclone_bin = form.rclone_bin
    if (form.config_path) config.config_path = form.config_path
  }

  return config
}

// 保存存储
const saveBackend = async () => {
  const form = backendForm.value
  if (!form.name && !editingBackend.value) {
    notification.error('错误', '请输入存储名称')
    return
  }

  savingBackend.value = true
  try {
    const config = buildBackendConfig()
    const name = editingBackend.value || form.name

    if (editingBackend.value) {
      // 编辑
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends/${encodeURIComponent(name)}`, {
        method: 'PUT',
        body: { config },
        credentials: 'include'
      })
      if (!resp?.success) throw new Error(resp?.error || '更新失败')
    } else {
      // 添加
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends`, {
        method: 'POST',
        body: { name, config },
        credentials: 'include'
      })
      if (!resp?.success) throw new Error(resp?.error || '添加失败')
    }

    // 如果是 Telegram 驱动，同时保存群组上传配置
    if (form.driver === 'telegram') {
      await saveGroupUpload(true)
    }

    notification.success('已保存', `存储 ${name} ${editingBackend.value ? '更新' : '添加'}成功`)
    showBackendModal.value = false
    await loadAll()
  } catch (e: any) {
    console.error('保存存储失败:', e)
    notification.error('保存失败', e?.data?.error || e?.message || '无法保存存储配置')
  } finally {
    savingBackend.value = false
  }
}

// 确认删除
const confirmDelete = (name: string) => {
  deletingBackend.value = name
  showDeleteModal.value = true
}

// 删除存储
const deleteBackend = async () => {
  if (!deletingBackend.value) return

  deleting.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends/${encodeURIComponent(deletingBackend.value)}`, {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!resp?.success) throw new Error(resp?.error || '删除失败')
    notification.success('已删除', `存储 ${deletingBackend.value} 已删除`)
    showDeleteModal.value = false
    await loadAll()
  } catch (e: any) {
    console.error('删除存储失败:', e)
    notification.error('删除失败', e?.data?.error || e?.message || '无法删除存储')
  } finally {
    deleting.value = false
  }
}

// 页面加载
onMounted(() => {
  loadAll()
})
</script>
