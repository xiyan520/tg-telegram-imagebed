<template>
  <div class="relative space-y-6 pb-10">
    <div class="pointer-events-none absolute -top-20 right-0 h-44 w-44 rounded-full bg-amber-200/30 blur-3xl dark:bg-amber-700/15" />
    <div class="pointer-events-none absolute top-56 -left-10 h-40 w-40 rounded-full bg-orange-200/25 blur-3xl dark:bg-orange-700/10" />

    <AdminPageHeader
      title="存储设置"
      eyebrow="Config"
      icon="heroicons:server-stack"
      description="管理后端、路由策略与上传验证"
    >
      <template #actions>
        <UButton icon="heroicons:arrow-path" color="gray" variant="outline" :loading="loading" @click="loadAll">
          刷新
        </UButton>
        <UButton icon="heroicons:arrow-uturn-left" color="gray" variant="outline" :disabled="!isAnyDirty" @click="resetUnsaved">
          重置未保存
        </UButton>
        <UButton icon="heroicons:check" color="primary" :loading="savingAll" @click="saveAllChanges">
          保存全部
          <UBadge v-if="dirtyCount > 0" color="amber" variant="solid" size="xs" class="ml-1.5">{{ dirtyCount }}</UBadge>
        </UButton>
      </template>
    </AdminPageHeader>

    <div v-if="loading && !initialLoaded" class="flex justify-center py-12">
      <div class="h-12 w-12 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
    </div>

    <template v-else>
      <div class="space-y-4">
        <AdminStorageTopNav
          class="hidden lg:block"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />
        <AdminStorageMobileNavDrawer
          class="lg:hidden"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />

        <AdminStorageSectionCard
          :id="sectionDomId('overview')"
          title="概览与状态"
          description="总体状态和环境覆盖信息"
          icon="heroicons:signal"
          :show-save="false"
        >
          <div class="space-y-4">
            <div
              v-if="envOverride"
              class="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-sm text-amber-800 dark:border-amber-800/80 dark:bg-amber-900/20 dark:text-amber-200"
            >
              配置由 <code class="rounded bg-amber-100 px-1 py-0.5 text-xs dark:bg-amber-800/60">STORAGE_CONFIG_JSON</code>
              接管，后端新增/编辑/删除会受限。
            </div>
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-2 sm:gap-3 xl:grid-cols-4">
              <div class="rounded-xl border border-stone-200/70 bg-white/80 p-2.5 dark:border-neutral-700/70 dark:bg-neutral-900/70 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400 sm:text-xs sm:tracking-[0.16em]">后端总数</p>
                <p class="mt-1 text-lg font-semibold text-stone-900 dark:text-white sm:text-2xl">{{ backendNames.length }}</p>
              </div>
              <div class="rounded-xl border border-emerald-200/70 bg-emerald-50/80 p-2.5 dark:border-emerald-800/70 dark:bg-emerald-900/20 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-emerald-700 dark:text-emerald-300 sm:text-xs sm:tracking-[0.16em]">健康后端</p>
                <p class="mt-1 text-lg font-semibold text-emerald-800 dark:text-emerald-200 sm:text-2xl">{{ healthyCount }}</p>
              </div>
              <div class="rounded-xl border border-rose-200/70 bg-rose-50/80 p-2.5 dark:border-rose-800/70 dark:bg-rose-900/20 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-rose-700 dark:text-rose-300 sm:text-xs sm:tracking-[0.16em]">异常后端</p>
                <p class="mt-1 text-lg font-semibold text-rose-800 dark:text-rose-200 sm:text-2xl">{{ unhealthyCount }}</p>
              </div>
              <div class="col-span-2 rounded-xl border border-stone-200/70 bg-white/80 p-2.5 dark:border-neutral-700/70 dark:bg-neutral-900/70 sm:col-span-1 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400 sm:text-xs sm:tracking-[0.16em]">默认存储</p>
                <p class="mt-1 truncate text-base font-semibold text-stone-900 dark:text-white sm:text-xl">{{ activeBackend || '--' }}</p>
                <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">驱动：{{ activeDriver }}</p>
              </div>
            </div>
          </div>
        </AdminStorageSectionCard>

        <AdminStorageSectionCard
          :id="sectionDomId('backends')"
          title="存储管理"
          description="新增、编辑、删除后端"
          icon="heroicons:circle-stack"
          :show-save="false"
        >
          <template #actions>
            <UButton icon="heroicons:plus" color="primary" :disabled="envOverride" @click="openAddModal">
              添加存储
            </UButton>
          </template>

          <div class="space-y-3">
            <div
              v-if="backendNames.length === 0"
              class="rounded-xl border border-dashed border-stone-300/80 bg-stone-50/80 p-4 text-sm text-stone-500 dark:border-neutral-700/80 dark:bg-neutral-800/60 dark:text-stone-400"
            >
              未发现已配置存储后端。
            </div>
            <div
              v-for="name in backendNames"
              :key="name"
              class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 shadow-sm dark:border-neutral-700/70 dark:bg-neutral-900/70"
            >
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0 space-y-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="truncate text-base font-semibold text-stone-900 dark:text-white">{{ name }}</p>
                    <UBadge color="gray" variant="subtle">{{ backends[name]?.driver || 'unknown' }}</UBadge>
                    <UBadge v-if="name === activeBackend" color="amber" variant="solid">Active</UBadge>
                  </div>
                  <p class="text-xs text-stone-500 dark:text-stone-400">
                    {{ health[name] === true ? 'Healthy' : health[name] === false ? 'Unhealthy' : 'Unknown' }}
                  </p>
                </div>
                <div class="flex items-center gap-1.5">
                  <UButton icon="heroicons:pencil-square" color="gray" variant="ghost" size="xs" :disabled="envOverride" @click="openEditModal(name)" />
                  <UButton icon="heroicons:trash" color="red" variant="ghost" size="xs" :disabled="envOverride || name === activeBackend" @click="confirmDelete(name)" />
                </div>
              </div>
            </div>
          </div>
        </AdminStorageSectionCard>

        <AdminStorageSectionCard
          :id="sectionDomId('policy')"
          title="默认存储与路由策略"
          description="控制场景路由和管理员可用后端"
          icon="heroicons:arrows-right-left"
          :dirty="Boolean(dirtyMap.policy)"
          :saving="Boolean(sectionSaving.policy)"
          @save="saveSection('policy')"
        >
          <div class="space-y-6">
            <UFormGroup label="默认存储（Active）">
              <USelect v-model="activeBackendDraft" :options="backendOptions" option-attribute="label" value-attribute="value" />
            </UFormGroup>

            <div class="grid gap-4 md:grid-cols-2">
              <UFormGroup label="游客上传">
                <USelect v-model="policy.guest" :options="sceneBackendOptions" option-attribute="label" value-attribute="value" />
              </UFormGroup>
              <UFormGroup label="Token 上传">
                <USelect v-model="policy.token" :options="sceneBackendOptions" option-attribute="label" value-attribute="value" />
              </UFormGroup>
              <UFormGroup label="群组上传">
                <USelect v-model="policy.group" :options="sceneBackendOptions" option-attribute="label" value-attribute="value" />
              </UFormGroup>
              <UFormGroup label="管理员默认上传">
                <USelect v-model="policy.admin_default" :options="sceneBackendOptions" option-attribute="label" value-attribute="value" />
              </UFormGroup>
            </div>

            <div>
              <p class="text-sm font-medium text-stone-700 dark:text-stone-300">管理员可用存储</p>
              <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">不勾选表示允许全部后端</p>
              <div class="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                <label
                  v-for="name in backendNames"
                  :key="name"
                  class="flex cursor-pointer items-center gap-2 rounded-lg border border-stone-200/80 bg-white/80 p-2.5 hover:bg-stone-50 dark:border-neutral-700/80 dark:bg-neutral-900/70 dark:hover:bg-neutral-800/80"
                >
                  <input type="checkbox" class="h-4 w-4 accent-amber-500" :checked="policy.admin_allowed.includes(name)" @change="toggleAllowed(name)">
                  <span class="text-sm text-stone-800 dark:text-stone-200">{{ name }}</span>
                  <UBadge color="gray" variant="subtle" size="xs">{{ backends[name]?.driver }}</UBadge>
                </label>
              </div>
            </div>
          </div>
        </AdminStorageSectionCard>

        <AdminStorageSectionCard
          :id="sectionDomId('danger_upload')"
          title="删除与上传测试"
          description="删除联动和管理员上传验证"
          icon="heroicons:cloud-arrow-up"
          :dirty="Boolean(dirtyMap.danger_upload)"
          :saving="Boolean(sectionSaving.danger_upload)"
          @save="saveSection('danger_upload')"
        >
          <div class="space-y-4">
            <div class="rounded-2xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/70">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-stone-800 dark:text-stone-200">同步删除 TG 消息</p>
                  <p class="text-xs text-stone-500 dark:text-stone-400">后台删除图片时同步删除 Telegram 消息</p>
                </div>
                <UToggle v-model="syncDeleteEnabled" />
              </div>
            </div>

            <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
              <p class="text-sm font-medium text-stone-900 dark:text-white">管理员上传测试</p>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <UFormGroup label="上传到指定存储">
                  <USelect v-model="uploadBackend" :options="adminUploadBackendOptions" option-attribute="label" value-attribute="value" />
                </UFormGroup>
                <UFormGroup label="选择图片文件">
                  <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
                    class="block w-full text-sm text-stone-500 file:mr-3 file:rounded-lg file:border-0 file:bg-amber-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-amber-700 hover:file:bg-amber-100 dark:file:bg-amber-900/20 dark:file:text-amber-300"
                    @change="handleFileSelect"
                  >
                </UFormGroup>
              </div>

              <div v-if="selectedFile" class="mt-3 rounded-lg border border-stone-200/80 bg-stone-50/80 p-2.5 text-sm text-stone-700 dark:border-neutral-700/80 dark:bg-neutral-800/70 dark:text-stone-200">
                已选择：{{ selectedFile.name }}（{{ formatSize(selectedFile.size) }}）
              </div>

              <div class="mt-3">
                <UButton color="primary" :loading="uploading" :disabled="!selectedFile" class="w-full sm:w-auto" @click="uploadFile">
                  <template #leading><UIcon name="heroicons:cloud-arrow-up" /></template>
                  立即上传
                </UButton>
              </div>

              <div
                v-if="uploadResult"
                class="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 text-sm text-emerald-800 dark:border-emerald-800/70 dark:bg-emerald-900/20 dark:text-emerald-200"
              >
                <p class="font-medium">上传成功</p>
                <p class="mt-1 break-all">URL: <a :href="uploadResult.url" target="_blank" class="underline">{{ uploadResult.url }}</a></p>
              </div>
            </div>
          </div>
        </AdminStorageSectionCard>
      </div>
    </template>

    <AdminStorageBackendWizardModal
      v-model="showBackendModal"
      :editing-backend="editingBackend"
      :form="backendDraftForm"
      :group-upload="backendDraftGroupUpload"
      :private-upload="backendDraftPrivateUpload"
      :saving="savingBackend"
      @submit="saveBackendFromWizard"
    />

    <UModal v-model="showDeleteModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">确认删除</h3>
        </template>
        <p class="text-stone-700 dark:text-stone-300">确定要删除存储 <strong>{{ deletingBackend }}</strong> 吗？</p>
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
import { nextTick } from 'vue'
import type {
  StorageBackendForm,
  StorageDirtyMap,
  StorageGroupUploadForm,
  StoragePrivateUploadForm,
  StorageSectionItem,
  StorageSectionKey,
} from '~/types/admin-storage'

definePageMeta({ layout: 'admin', middleware: 'auth' })

interface BackendInfo { driver: string; active?: boolean }
interface UploadResult { url: string; encrypted_id?: string; filename: string; size: string }
interface StoragePolicy { guest: string; token: string; group: string; admin_default: string; admin_allowed: string[] }

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const stableStringify = (value: any): string => {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  const keys = Object.keys(value).sort()
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`
}

const createDefaultPolicy = (): StoragePolicy => ({ guest: '', token: '', group: '', admin_default: '', admin_allowed: [] })
const createDefaultGroupUpload = (): StorageGroupUploadForm => ({ admin_only: false, admin_ids: '', tg_bound_only: false, reply: true, delete_delay: 0 })
const createDefaultPrivateUpload = (): StoragePrivateUploadForm => ({ enabled: true, mode: 'open', admin_ids: '' })
const createDefaultBackendForm = (): StorageBackendForm => ({
  name: '', driver: 'telegram', bot_token: '', chat_id: '', root_dir: '', endpoint: '', bucket: '',
  access_key: '', secret_key: '', region: '', public_url_prefix: '', path_style: false,
  remote: '', base_path: '', rclone_bin: '', config_path: '', use_as_bot: false,
})

const sectionItems: StorageSectionItem[] = [
  { key: 'overview', label: '概览', description: '总体状态', icon: 'heroicons:signal' },
  { key: 'backends', label: '存储管理', description: '后端列表', icon: 'heroicons:circle-stack' },
  { key: 'policy', label: '路由策略', description: '默认与场景规则', icon: 'heroicons:arrows-right-left' },
  { key: 'danger_upload', label: '删除与上传', description: '联动与测试', icon: 'heroicons:cloud-arrow-up' },
]

const loading = ref(false)
const initialLoaded = ref(false)
const savingAll = ref(false)
const sectionSaving = ref<Partial<Record<StorageSectionKey, boolean>>>({})
const savingBackend = ref(false)
const deleting = ref(false)
const uploading = ref(false)

const envOverride = ref(false)
const backends = ref<Record<string, BackendInfo>>({})
const backendConfigs = ref<Record<string, any>>({})
const health = ref<Record<string, boolean>>({})
const activeBackend = ref('')
const activeBackendDraft = ref('')
const policy = ref<StoragePolicy>(createDefaultPolicy())
const originalPolicy = ref<StoragePolicy>(createDefaultPolicy())
const syncDeleteEnabled = ref(true)
const originalSyncDeleteEnabled = ref(true)
const groupUpload = ref<StorageGroupUploadForm>(createDefaultGroupUpload())
const privateUpload = ref<StoragePrivateUploadForm>(createDefaultPrivateUpload())

const showBackendModal = ref(false)
const showDeleteModal = ref(false)
const editingBackend = ref<string | null>(null)
const deletingBackend = ref('')
const backendDraftForm = ref<StorageBackendForm>(createDefaultBackendForm())
const backendDraftGroupUpload = ref<StorageGroupUploadForm>(createDefaultGroupUpload())
const backendDraftPrivateUpload = ref<StoragePrivateUploadForm>(createDefaultPrivateUpload())

const uploadBackend = ref('')
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadResult = ref<UploadResult | null>(null)

const activeSection = ref<StorageSectionKey>('overview')
let sectionObserver: IntersectionObserver | null = null

const backendNames = computed(() => Object.keys(backends.value || {}))
const backendOptions = computed(() => backendNames.value.map((name) => ({ value: name, label: `${name} (${backends.value[name]?.driver || 'unknown'})` })))
const sceneBackendOptions = computed(() => [{ value: '', label: '跟随默认 (Active)' }, ...backendOptions.value])
const adminUploadBackendOptions = computed(() => {
  const allowed = policy.value.admin_allowed
  if (allowed.length === 0) return [{ value: '', label: '使用管理员默认存储' }, ...backendOptions.value]
  return [{ value: '', label: '使用管理员默认存储' }, ...backendOptions.value.filter((opt) => allowed.includes(opt.value))]
})
const healthyCount = computed(() => backendNames.value.filter((name) => health.value[name] === true).length)
const unhealthyCount = computed(() => backendNames.value.filter((name) => health.value[name] === false).length)
const activeDriver = computed(() => (activeBackend.value ? backends.value[activeBackend.value]?.driver || '--' : '--'))

const dirtyMap = computed<StorageDirtyMap>(() => ({
  overview: false,
  backends: false,
  policy: activeBackendDraft.value !== activeBackend.value || stableStringify(policy.value) !== stableStringify(originalPolicy.value),
  danger_upload: syncDeleteEnabled.value !== originalSyncDeleteEnabled.value,
}))
const dirtyCount = computed(() => Object.values(dirtyMap.value).filter(Boolean).length)
const isAnyDirty = computed(() => dirtyCount.value > 0)
const sectionDomId = (key: StorageSectionKey) => `storage-section-${key}`

const formatSize = (bytes: number): string => bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`

const loadAll = async () => {
  loading.value = true
  try {
    const [storageResp, healthResp, policyResp, configResp, settingsResp] = await Promise.all([
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/health`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/policy`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/config`, { credentials: 'include' }),
      $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, { credentials: 'include' }),
    ])

    backends.value = storageResp?.data?.backends || {}
    activeBackend.value = storageResp?.data?.active || ''
    activeBackendDraft.value = activeBackend.value
    health.value = healthResp?.data || {}
    envOverride.value = Boolean(configResp?.data?.env_override)
    backendConfigs.value = configResp?.data?.backends || {}

    policy.value = {
      guest: policyResp?.data?.policy?.guest || '',
      token: policyResp?.data?.policy?.token || '',
      group: policyResp?.data?.policy?.group || '',
      admin_default: policyResp?.data?.policy?.admin_default || '',
      admin_allowed: policyResp?.data?.policy?.admin_allowed || [],
    }
    originalPolicy.value = clone(policy.value)

    const d = settingsResp?.data || {}
    groupUpload.value = { admin_only: d.group_upload_admin_only ?? false, admin_ids: d.group_admin_ids ?? '', tg_bound_only: d.group_upload_tg_bound_only ?? false, reply: d.group_upload_reply ?? true, delete_delay: d.group_upload_delete_delay ?? 0 }
    privateUpload.value = { enabled: d.bot_private_upload_enabled ?? true, mode: d.bot_private_upload_mode ?? 'open', admin_ids: d.bot_private_admin_ids ?? '' }
    syncDeleteEnabled.value = d.tg_sync_delete_enabled ?? true
    originalSyncDeleteEnabled.value = syncDeleteEnabled.value
    initialLoaded.value = true
  } catch (e: any) {
    console.error('加载存储配置失败:', e)
    notification.error('加载失败', e?.data?.error || '无法获取存储配置')
  } finally {
    loading.value = false
  }
}

const saveActiveIfNeeded = async (): Promise<boolean> => {
  if (activeBackendDraft.value === activeBackend.value) return false
  if (!activeBackendDraft.value) throw new Error('请选择默认存储')
  const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/active`, { method: 'POST', body: { backend: activeBackendDraft.value }, credentials: 'include' })
  if (!resp?.success) throw new Error(resp?.error || '默认存储保存失败')
  activeBackend.value = activeBackendDraft.value
  return true
}

const savePolicyIfNeeded = async (): Promise<boolean> => {
  if (stableStringify(policy.value) === stableStringify(originalPolicy.value)) return false
  const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/policy`, { method: 'PUT', body: { policy: policy.value }, credentials: 'include' })
  if (!resp?.success) throw new Error(resp?.error || '路由策略保存失败')
  originalPolicy.value = clone(policy.value)
  return true
}

const saveSyncDeleteIfNeeded = async (): Promise<boolean> => {
  if (syncDeleteEnabled.value === originalSyncDeleteEnabled.value) return false
  const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, { method: 'PUT', body: { tg_sync_delete_enabled: syncDeleteEnabled.value }, credentials: 'include' })
  if (!resp?.success) throw new Error(resp?.error || '删除联动保存失败')
  originalSyncDeleteEnabled.value = syncDeleteEnabled.value
  return true
}

const saveSection = async (key: StorageSectionKey) => {
  sectionSaving.value[key] = true
  try {
    if (key === 'policy') {
      const a = await saveActiveIfNeeded()
      const p = await savePolicyIfNeeded()
      if (!a && !p) notification.info('无变更', '默认存储和路由策略没有变化')
      else { notification.success('已保存', '默认存储与路由策略已更新'); await loadAll() }
    }
    if (key === 'danger_upload') {
      const changed = await saveSyncDeleteIfNeeded()
      if (!changed) notification.info('无变更', '删除联动设置没有变化')
      else notification.success('已保存', '删除联动设置已更新')
    }
  } catch (e: any) {
    console.error(`保存分组失败 [${key}]:`, e)
    notification.error('保存失败', e?.data?.error || e?.message || '分组保存失败')
  } finally {
    sectionSaving.value[key] = false
  }
}

const saveAllChanges = async () => {
  savingAll.value = true
  try {
    const a = await saveActiveIfNeeded()
    const p = await savePolicyIfNeeded()
    const s = await saveSyncDeleteIfNeeded()
    if (!a && !p && !s) { notification.info('无变更', '当前没有需要保存的内容'); return }
    notification.success('已保存', '存储设置已全部更新')
    await loadAll()
  } catch (e: any) {
    console.error('保存全部失败:', e)
    notification.error('保存失败', e?.data?.error || e?.message || '无法保存全部设置')
  } finally {
    savingAll.value = false
  }
}

const resetUnsaved = () => {
  activeBackendDraft.value = activeBackend.value
  policy.value = clone(originalPolicy.value)
  syncDeleteEnabled.value = originalSyncDeleteEnabled.value
  notification.info('已重置', '未保存修改已恢复')
}

const toggleAllowed = (name: string) => {
  const next = new Set(policy.value.admin_allowed)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  policy.value.admin_allowed = Array.from(next)
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files?.length) { selectedFile.value = target.files[0]; uploadResult.value = null }
}

const uploadFile = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  uploadResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    if (uploadBackend.value) formData.append('backend', uploadBackend.value)
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/upload`, { method: 'POST', body: formData, credentials: 'include' })
    if (!resp?.success) throw new Error(resp?.error || '上传失败')
    uploadResult.value = resp.data
    notification.success('上传成功', `文件已上传到 ${uploadBackend.value || '管理员默认存储'}`)
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  } catch (e: any) {
    console.error('上传失败:', e)
    notification.error('上传失败', e?.data?.error || e?.message || '无法上传文件')
  } finally { uploading.value = false }
}

const openAddModal = () => {
  editingBackend.value = null
  backendDraftForm.value = createDefaultBackendForm()
  backendDraftGroupUpload.value = clone(groupUpload.value)
  backendDraftPrivateUpload.value = clone(privateUpload.value)
  showBackendModal.value = true
}

const openEditModal = (name: string) => {
  const cfg = backendConfigs.value[name] || {}
  editingBackend.value = name
  backendDraftForm.value = {
    name, driver: cfg.driver || 'telegram', bot_token: cfg.bot_token || '', chat_id: cfg.chat_id || '',
    root_dir: cfg.root_dir || '', endpoint: cfg.endpoint || '', bucket: cfg.bucket || '', access_key: cfg.access_key || '',
    secret_key: cfg.secret_key || '', region: cfg.region || '', public_url_prefix: cfg.public_url_prefix || '',
    path_style: cfg.path_style || false, remote: cfg.remote || '', base_path: cfg.base_path || '', rclone_bin: cfg.rclone_bin || '',
    config_path: cfg.config_path || '', use_as_bot: cfg.is_bot || false,
  }
  backendDraftGroupUpload.value = clone(groupUpload.value)
  backendDraftPrivateUpload.value = clone(privateUpload.value)
  showBackendModal.value = true
}

const buildBackendConfig = (form: StorageBackendForm) => {
  const config: Record<string, any> = { driver: form.driver }
  if (form.driver === 'telegram') { if (form.bot_token) config.bot_token = form.bot_token; if (form.chat_id) config.chat_id = form.chat_id }
  if (form.driver === 'local') { if (form.root_dir) config.root_dir = form.root_dir }
  if (form.driver === 's3') {
    if (form.endpoint) config.endpoint = form.endpoint
    if (form.bucket) config.bucket = form.bucket
    if (form.access_key) config.access_key = form.access_key
    if (form.secret_key) config.secret_key = form.secret_key
    if (form.region) config.region = form.region
    if (form.public_url_prefix) config.public_url_prefix = form.public_url_prefix
    config.path_style = Boolean(form.path_style)
  }
  if (form.driver === 'rclone') {
    if (form.remote) config.remote = form.remote
    if (form.base_path) config.base_path = form.base_path
    if (form.rclone_bin) config.rclone_bin = form.rclone_bin
    if (form.config_path) config.config_path = form.config_path
  }
  return config
}

const saveGroupUpload = async (nextGroupUpload: StorageGroupUploadForm, nextPrivateUpload: StoragePrivateUploadForm, silent = false) => {
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      method: 'PUT',
      body: {
        group_upload_admin_only: nextGroupUpload.admin_only,
        group_admin_ids: nextGroupUpload.admin_ids,
        group_upload_tg_bound_only: nextGroupUpload.tg_bound_only,
        group_upload_reply: nextGroupUpload.reply,
        group_upload_delete_delay: nextGroupUpload.delete_delay,
        bot_private_upload_enabled: nextPrivateUpload.enabled,
        bot_private_upload_mode: nextPrivateUpload.mode,
        bot_private_admin_ids: nextPrivateUpload.admin_ids,
      },
      credentials: 'include',
    })
    if (!resp?.success) throw new Error(resp?.error || '保存失败')
    groupUpload.value = clone(nextGroupUpload)
    privateUpload.value = clone(nextPrivateUpload)
  } catch (e: any) {
    console.error('保存 Telegram 上传设置失败:', e)
    if (!silent) notification.error('保存失败', e?.data?.error || e?.message || '无法保存 Telegram 上传设置')
    throw e
  }
}

const saveBackendFromWizard = async (payload: { form: StorageBackendForm; groupUpload: StorageGroupUploadForm; privateUpload: StoragePrivateUploadForm }) => {
  const form = clone(payload.form)
  const name = (editingBackend.value || form.name || '').trim()
  if (!name) { notification.error('错误', '请输入存储名称'); return }
  savingBackend.value = true
  try {
    const config = buildBackendConfig(form)
    if (editingBackend.value) {
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends/${encodeURIComponent(name)}`, { method: 'PUT', body: { config, use_as_bot: form.use_as_bot }, credentials: 'include' })
      if (!resp?.success) throw new Error(resp?.error || '更新失败')
    } else {
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends`, { method: 'POST', body: { name, config, use_as_bot: form.use_as_bot }, credentials: 'include' })
      if (!resp?.success) throw new Error(resp?.error || '添加失败')
    }
    if (form.driver === 'telegram') await saveGroupUpload(payload.groupUpload, payload.privateUpload, true)
    notification.success('已保存', `存储 ${name} ${editingBackend.value ? '更新' : '添加'}成功`)
    showBackendModal.value = false
    await loadAll()
  } catch (e: any) {
    console.error('保存存储失败:', e)
    notification.error('保存失败', e?.data?.error || e?.message || '无法保存存储配置')
  } finally { savingBackend.value = false }
}

const confirmDelete = (name: string) => { deletingBackend.value = name; showDeleteModal.value = true }
const deleteBackend = async () => {
  if (!deletingBackend.value) return
  deleting.value = true
  try {
    const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/storage/backends/${encodeURIComponent(deletingBackend.value)}`, { method: 'DELETE', credentials: 'include' })
    if (!resp?.success) throw new Error(resp?.error || '删除失败')
    notification.success('已删除', `存储 ${deletingBackend.value} 已删除`)
    showDeleteModal.value = false
    await loadAll()
  } catch (e: any) {
    console.error('删除存储失败:', e)
    notification.error('删除失败', e?.data?.error || e?.message || '无法删除存储')
  } finally { deleting.value = false }
}

const scrollToSection = (key: StorageSectionKey) => {
  activeSection.value = key
  if (!import.meta.client) return
  const target = document.getElementById(sectionDomId(key))
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const initSectionObserver = () => {
  if (!import.meta.client) return
  sectionObserver?.disconnect()
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
    if (!visible) return
    const matched = sectionItems.find((item) => sectionDomId(item.key) === visible.target.id)
    if (matched) activeSection.value = matched.key
  }, { root: null, rootMargin: '-15% 0px -65% 0px', threshold: [0.2, 0.4, 0.7] })
  for (const item of sectionItems) {
    const el = document.getElementById(sectionDomId(item.key))
    if (el) sectionObserver.observe(el)
  }
}

onMounted(async () => {
  await loadAll()
  await nextTick()
  initSectionObserver()
})
onBeforeUnmount(() => {
  sectionObserver?.disconnect()
  sectionObserver = null
})
</script>
