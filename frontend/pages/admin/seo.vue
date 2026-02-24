<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">SEO 设置</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">配置网站名称、Logo、社交分享和页脚信息</p>
      </div>
      <div class="flex gap-2">
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadSettings"
        >
          刷新
        </UButton>
        <UButton
          icon="heroicons:check"
          color="primary"
          :loading="saving"
          @click="saveSettings"
        >
          保存
        </UButton>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !settingsLoaded" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <!-- 基础信息 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:globe-alt" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">基础信息</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">网站名称、描述和关键词</p>
            </div>
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="网站名称" hint="用于 Logo 文字、页面标题和页脚">
            <UInput v-model="form.seo_site_name" placeholder="图床 Pro" />
          </UFormGroup>
          <UFormGroup label="网站描述" hint="用于 meta description">
            <UTextarea v-model="form.seo_site_description" placeholder="专业的图片托管服务，基于Telegram云存储，支持Cloudflare CDN全球加速" :rows="2" />
          </UFormGroup>
          <UFormGroup label="网站关键词" hint="逗号分隔，用于 meta keywords">
            <UInput v-model="form.seo_site_keywords" placeholder="图床,免费图床,Telegram,云存储,CDN加速,图片托管" />
          </UFormGroup>
        </div>
      </UCard>

      <!-- Logo 与图标 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:photo" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Logo 与图标</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">自定义网站 Logo 和 Favicon</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="Logo 模式">
            <div class="flex gap-4">
              <URadio v-model="form.seo_logo_mode" value="icon" label="默认图标" />
              <URadio v-model="form.seo_logo_mode" value="custom" label="自定义图片" />
            </div>
          </UFormGroup>

          <template v-if="form.seo_logo_mode === 'custom'">
            <UFormGroup label="Logo 图片 URL">
              <UInput v-model="form.seo_logo_url" placeholder="https://example.com/logo.png" />
            </UFormGroup>
            <!-- Logo 预览 -->
            <div v-if="form.seo_logo_url" class="flex items-center gap-4 p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg">
              <span class="text-sm text-stone-500">预览：</span>
              <img :src="form.seo_logo_url" alt="Logo 预览" class="w-10 h-10 rounded-lg object-contain" @error="($event.target as HTMLImageElement).style.display = 'none'" />
            </div>
          </template>

          <UFormGroup label="Favicon URL" hint="留空使用默认图标">
            <UInput v-model="form.seo_favicon_url" placeholder="https://example.com/favicon.ico" />
          </UFormGroup>
        </div>
      </UCard>
      <!-- OG 社交分享 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:share" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">社交分享</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">Open Graph 和 Twitter Card 配置</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="OG 标题" hint="留空自动使用网站名称">
            <UInput v-model="form.seo_og_title" :placeholder="form.seo_site_name || '图床 Pro'" />
          </UFormGroup>
          <UFormGroup label="OG 描述" hint="留空自动使用网站描述">
            <UTextarea v-model="form.seo_og_description" :placeholder="form.seo_site_description || '专业的图片托管服务'" :rows="2" />
          </UFormGroup>
          <UFormGroup label="OG 图片 URL" hint="分享到社交平台时显示的图片">
            <UInput v-model="form.seo_og_image" placeholder="https://example.com/og-image.png" />
          </UFormGroup>

          <!-- OG 预览卡片 -->
          <div class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg space-y-2">
            <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider">分享预览</p>
            <div class="border border-stone-200 dark:border-neutral-700 rounded-lg overflow-hidden max-w-sm">
              <div v-if="form.seo_og_image" class="h-40 bg-stone-200 dark:bg-neutral-700">
                <img :src="form.seo_og_image" alt="OG 预览" class="w-full h-full object-cover" @error="($event.target as HTMLImageElement).style.display = 'none'" />
              </div>
              <div class="p-3">
                <p class="font-semibold text-sm text-stone-900 dark:text-white truncate">
                  {{ form.seo_og_title || form.seo_site_name || '图床 Pro' }}
                </p>
                <p class="text-xs text-stone-500 dark:text-stone-400 mt-1 line-clamp-2">
                  {{ form.seo_og_description || form.seo_site_description || '专业的图片托管服务' }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </UCard>
      <!-- 页脚设置 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-stone-500 to-stone-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:document-text" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">页脚设置</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">自定义页脚显示文字</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="页脚文字" hint="留空使用默认格式「© 年份 网站名称」">
            <UInput v-model="form.seo_footer_text" placeholder="© 2024 图床 Pro" />
          </UFormGroup>
          <!-- 页脚预览 -->
          <div class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">预览</p>
            <p class="text-center text-sm text-stone-400 dark:text-neutral-500">
              <template v-if="form.seo_footer_text">{{ form.seo_footer_text }}</template>
              <template v-else>&copy; {{ new Date().getFullYear() }} {{ form.seo_site_name || '图床 Pro' }}</template>
            </p>
          </div>
        </div>
      </UCard>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin' })

const config = useRuntimeConfig()
const toast = useLightToast()
const { loadSeoSettings } = useSeoSettings()

const loading = ref(false)
const saving = ref(false)
const settingsLoaded = ref(false)
// 表单数据
const form = ref({
  seo_site_name: '',
  seo_site_description: '',
  seo_site_keywords: '',
  seo_logo_mode: 'icon',
  seo_logo_url: '',
  seo_favicon_url: '',
  seo_og_title: '',
  seo_og_description: '',
  seo_og_image: '',
  seo_footer_text: '',
})

// 加载设置
const loadSettings = async () => {
  loading.value = true
  try {
    const res = await $fetch<any>(`${config.public.apiBase}/api/admin/system/settings`, {
      credentials: 'include',
    })
    if (res.success && res.data) {
      form.value.seo_site_name = res.data.seo_site_name || ''
      form.value.seo_site_description = res.data.seo_site_description || ''
      form.value.seo_site_keywords = res.data.seo_site_keywords || ''
      form.value.seo_logo_mode = res.data.seo_logo_mode || 'icon'
      form.value.seo_logo_url = res.data.seo_logo_url || ''
      form.value.seo_favicon_url = res.data.seo_favicon_url || ''
      form.value.seo_og_title = res.data.seo_og_title || ''
      form.value.seo_og_description = res.data.seo_og_description || ''
      form.value.seo_og_image = res.data.seo_og_image || ''
      form.value.seo_footer_text = res.data.seo_footer_text || ''
      settingsLoaded.value = true
    }
  } catch (error: any) {
    toast.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

// 保存设置
const saveSettings = async () => {
  saving.value = true
  try {
    const res = await $fetch<any>(`${config.public.apiBase}/api/admin/system/settings`, {
      method: 'PUT',
      credentials: 'include',
      body: { ...form.value },
    })
    if (res.success) {
      toast.success('SEO 设置已保存')
      // 刷新全局 SEO 设置
      await loadSeoSettings(true)
    } else {
      toast.error(res.error || '保存失败')
    }
  } catch (error: any) {
    toast.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>
