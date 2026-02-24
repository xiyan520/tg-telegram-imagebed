<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div>
      <h1 class="text-2xl font-bold text-stone-900 dark:text-white">站点设置</h1>
      <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">配置画集站点的基本信息</p>
    </div>

    <!-- 加载骨架屏 -->
    <UCard v-if="loading">
      <div class="space-y-6">
        <div v-for="i in 4" :key="i" class="space-y-2">
          <USkeleton class="h-4 w-24" />
          <USkeleton class="h-10 w-full" />
        </div>
      </div>
    </UCard>

    <!-- 设置表单 -->
    <UCard v-else>
      <template #header>
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
            <UIcon name="heroicons:cog-6-tooth" class="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">基本设置</h3>
            <p class="text-xs text-stone-500 dark:text-stone-400">画集站点的名称、描述和显示配置</p>
          </div>
        </div>
      </template>

      <div class="space-y-6">
        <UFormGroup label="站点名称">
          <UInput v-model="form.gallery_site_name" placeholder="输入站点名称" />
        </UFormGroup>

        <UFormGroup label="站点描述">
          <UTextarea v-model="form.gallery_site_description" placeholder="输入站点描述" :rows="3" />
        </UFormGroup>

        <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
          <div>
            <p class="font-medium text-stone-900 dark:text-white">启用站点</p>
            <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">关闭后画集站点将不可访问</p>
          </div>
          <UToggle v-model="form.gallery_site_enabled" size="lg" />
        </div>

        <UFormGroup label="每页图片数">
          <UInput
            v-model.number="form.gallery_site_images_per_page"
            type="number"
            :min="1"
            :max="100"
            placeholder="20"
          />
          <template #hint>
            <span class="text-xs text-stone-500">画集详情页每页显示的图片数量（1-100）</span>
          </template>
        </UFormGroup>
      </div>

      <template #footer>
        <div class="flex justify-end">
          <UButton color="primary" :loading="saving" @click="handleSave">
            <template #leading>
              <UIcon name="heroicons:check" />
            </template>
            保存设置
          </UButton>
        </div>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteSettings } from '~/composables/useGallerySiteAdmin'

definePageMeta({
  layout: 'gallery-site-admin',
  middleware: 'gallery-site-admin-auth'
})

const { getSettings, updateSettings } = useGallerySiteAdmin()
const notification = useNotification()

const loading = ref(true)
const saving = ref(false)
const form = ref<GallerySiteSettings>({
  gallery_site_name: '',
  gallery_site_description: '',
  gallery_site_enabled: true,
  gallery_site_images_per_page: 20
})

const loadData = async () => {
  loading.value = true
  try {
    form.value = await getSettings()
  } catch (e: any) {
    notification.error('加载失败', e.message || '无法加载站点设置')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await updateSettings(form.value)
    notification.success('保存成功', '站点设置已更新')
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法保存站点设置')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>
