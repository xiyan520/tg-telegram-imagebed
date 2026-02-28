<template>
  <div class="relative space-y-6 pb-10">
    <div class="pointer-events-none absolute -top-20 right-0 h-44 w-44 rounded-full bg-amber-200/30 blur-3xl dark:bg-amber-700/15" />
    <div class="pointer-events-none absolute top-56 -left-10 h-40 w-40 rounded-full bg-orange-200/25 blur-3xl dark:bg-orange-700/10" />
    <AdminPageHeader
      title="系统设置"
      eyebrow="Config"
      icon="heroicons:cog-6-tooth"
      description="配置域名、CDN 加速和上传策略"
    >
      <template #actions>
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
          color="gray"
          variant="outline"
          icon="heroicons:arrow-uturn-left"
          :disabled="!isAnyDirty"
          @click="resetSettings"
        >
          重置未保存
        </UButton>
        <UButton color="primary" icon="heroicons:check" :loading="saving || policySaving || gallerySiteSettingsSaving" @click="saveAllSettings">
          保存全部
          <UBadge v-if="dirtyCount > 0" color="amber" variant="solid" size="xs" class="ml-1.5">
            {{ dirtyCount }}
          </UBadge>
        </UButton>
      </template>
    </AdminPageHeader>

    <!-- 加载状态 -->
    <div v-if="loading && !settingsLoaded" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <div class="space-y-4">
        <AdminSettingsTopNav
          class="hidden lg:block"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />
        <AdminSettingsMobileNavDrawer
          class="lg:hidden"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />

        <AdminSettingsSectionCard
            :id="sectionDomId('domains')"
            title="域名与路由"
            description="域名列表、画集入口和图片访问路由策略"
            icon="heroicons:globe-alt"
            :dirty="Boolean(dirtyMap.domains)"
            :saving="Boolean(sectionSaving.domains)"
            @save="saveSection('domains')"
        >
      <!-- 域名管理 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-stone-500 to-stone-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:globe-alt" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">域名管理</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">管理默认域名和图片域名</p>
              </div>
            </div>
            <UButton icon="heroicons:plus" color="primary" size="sm" @click="openAddDomainModal">
              添加域名
            </UButton>
          </div>
        </template>

        <div class="space-y-6">
          <!-- 加载状态 -->
          <div v-if="domainsLoading && domains.length === 0" class="flex justify-center py-6">
            <div class="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <template v-else>
            <!-- 默认域名 -->
            <div>
              <p class="text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">默认域名（管理后台 / API）</p>
              <div v-if="defaultDomains.length > 0" class="space-y-2">
                <div
                  v-for="d in defaultDomains"
                  :key="d.id"
                  class="flex items-center justify-between p-3 rounded-xl border border-stone-200 dark:border-neutral-700"
                >
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-stone-900 dark:text-white">{{ d.domain }}{{ d.port ? ':' + d.port : '' }}</span>
                    <UBadge color="amber" variant="solid" size="xs">默认</UBadge>
                    <UBadge :color="d.use_https ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ d.use_https ? 'HTTPS' : 'HTTP' }}
                    </UBadge>
                    <span v-if="d.remark" class="text-xs text-stone-400 dark:text-stone-500">{{ d.remark }}</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <UButton icon="heroicons:pencil-square" color="blue" variant="ghost" size="xs" title="编辑" @click="openEditDomainModal(d)" />
                    <UButton icon="heroicons:trash" color="red" variant="ghost" size="xs" @click="confirmDeleteDomain(d)" />
                  </div>
                </div>
              </div>
              <div v-else class="p-3 bg-stone-50 dark:bg-neutral-800 rounded-xl text-sm text-stone-500 dark:text-stone-400">
                未设置默认域名，将使用当前访问域名
              </div>
            </div>

            <!-- 图片域名列表 -->
            <div>
              <p class="text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">图片域名（图片访问专用）</p>
              <div v-if="imageDomains.length > 0" class="space-y-2">
                <div
                  v-for="d in imageDomains"
                  :key="d.id"
                  class="flex items-center justify-between p-3 rounded-xl border border-stone-200 dark:border-neutral-700"
                >
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-medium text-stone-900 dark:text-white">{{ d.domain }}{{ d.port ? ':' + d.port : '' }}</span>
                    <UBadge :color="d.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ d.is_active ? '活跃' : '停用' }}
                    </UBadge>
                    <UBadge :color="d.use_https ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ d.use_https ? 'HTTPS' : 'HTTP' }}
                    </UBadge>
                    <span v-if="d.remark" class="text-xs text-stone-400 dark:text-stone-500">{{ d.remark }}</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <UButton
                      :icon="d.is_active ? 'heroicons:pause' : 'heroicons:play'"
                      :color="d.is_active ? 'gray' : 'green'"
                      variant="ghost"
                      size="xs"
                      :title="d.is_active ? '停用' : '启用'"
                      @click="toggleDomainActive(d)"
                    />
                    <UButton
                      icon="heroicons:star"
                      color="amber"
                      variant="ghost"
                      size="xs"
                      title="设为默认"
                      @click="handleSetDefault(d)"
                    />
                    <UButton icon="heroicons:pencil-square" color="blue" variant="ghost" size="xs" title="编辑" @click="openEditDomainModal(d)" />
                    <UButton
                      icon="heroicons:trash"
                      color="red"
                      variant="ghost"
                      size="xs"
                      @click="confirmDeleteDomain(d)"
                    />
                  </div>
                </div>
              </div>
              <div v-else class="p-3 bg-stone-50 dark:bg-neutral-800 rounded-xl text-sm text-stone-500 dark:text-stone-400">
                暂无图片域名，上传后将使用默认域名或当前访问域名生成链接
              </div>
            </div>

            <!-- 画集域名列表 -->
            <div>
              <p class="text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">画集域名（画集站点专用）</p>
              <div v-if="galleryDomains.length > 0" class="space-y-2">
                <div
                  v-for="d in galleryDomains"
                  :key="d.id"
                  class="flex items-center justify-between p-3 rounded-xl border border-stone-200 dark:border-neutral-700"
                >
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-medium text-stone-900 dark:text-white">{{ d.domain }}{{ d.port ? ':' + d.port : '' }}</span>
                    <UBadge color="violet" variant="subtle" size="xs">画集</UBadge>
                    <UBadge :color="d.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ d.is_active ? '活跃' : '停用' }}
                    </UBadge>
                    <UBadge :color="d.use_https ? 'green' : 'gray'" variant="subtle" size="xs">
                      {{ d.use_https ? 'HTTPS' : 'HTTP' }}
                    </UBadge>
                    <span v-if="d.remark" class="text-xs text-stone-400 dark:text-stone-500">{{ d.remark }}</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <UButton
                      :icon="d.is_active ? 'heroicons:pause' : 'heroicons:play'"
                      :color="d.is_active ? 'gray' : 'green'"
                      variant="ghost"
                      size="xs"
                      :title="d.is_active ? '停用' : '启用'"
                      @click="toggleDomainActive(d)"
                    />
                    <UButton icon="heroicons:pencil-square" color="blue" variant="ghost" size="xs" title="编辑" @click="openEditDomainModal(d)" />
                    <UButton
                      icon="heroicons:trash"
                      color="red"
                      variant="ghost"
                      size="xs"
                      @click="confirmDeleteDomain(d)"
                    />
                  </div>
                </div>
              </div>
              <div v-else class="p-3 bg-stone-50 dark:bg-neutral-800 rounded-xl text-sm text-stone-500 dark:text-stone-400">
                暂无画集域名，添加后可通过该域名访问画集站点
              </div>
            </div>

            <!-- 画集站点设置（仅在没有独立画集域名时显示，有独立域名时通过画集站点的管理按钮进入） -->
            <div v-if="!activeGalleryDomain" class="space-y-4 p-4 bg-amber-50/50 dark:bg-amber-900/10 border border-amber-200/60 dark:border-amber-800/40 rounded-xl">
              <div class="flex items-center gap-2 mb-3">
                <UIcon name="heroicons:cog-6-tooth" class="w-4 h-4 text-amber-500" />
                <p class="text-sm font-medium text-stone-700 dark:text-stone-300">画集站点设置</p>
                <UBadge color="amber" variant="subtle" size="xs">无独立域名</UBadge>
              </div>
              <UFormGroup label="站点名称" class="max-w-sm">
                <UInput v-model="gallerySiteSettings.name" placeholder="画集" size="sm" />
              </UFormGroup>
              <UFormGroup label="站点描述" class="max-w-md">
                <UInput v-model="gallerySiteSettings.description" placeholder="精选图片画集" size="sm" />
              </UFormGroup>
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-stone-700 dark:text-stone-300">启用画集站点</p>
                  <p class="text-xs text-stone-500 dark:text-stone-400">关闭后画集公开浏览功能不可用</p>
                </div>
                <UToggle v-model="gallerySiteSettings.enabled" />
              </div>
              <div class="flex justify-end">
                <UButton
                  color="amber"
                  variant="soft"
                  size="sm"
                  :loading="gallerySiteSettingsSaving"
                  @click="saveGallerySiteSettings"
                >
                  保存画集设置
                </UButton>
              </div>
            </div>

            <!-- 有独立画集域名时的提示 -->
            <div v-else class="flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">画集站点已启用独立域名</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  请通过画集站点页面顶部的"管理"按钮进入后台设置
                </p>
              </div>
              <UButton
                color="amber"
                variant="soft"
                icon="heroicons:arrow-top-right-on-square"
                :loading="gallerySiteEntryLoading"
                @click="openGallerySiteAdmin"
              >
                打开画集站点
              </UButton>
            </div>

            <!-- 图片域名限制开关 -->
            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">图片域名限制</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  开启后，图片只能通过图片域名访问，其他域名返回 403
                </p>
              </div>
              <UToggle v-model="settings.image_domain_restriction_enabled" size="lg" />
            </div>
          </template>
        </div>
      </UCard>

      <!-- 域名场景路由 -->
      <UCard v-if="activeImageDomains.length >= 2">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-violet-500 to-violet-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:arrows-right-left" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">域名场景路由</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">为不同上传场景指定图片域名，留空则随机选择</p>
              </div>
            </div>
            <UButton color="primary" size="sm" :loading="policySaving" @click="saveDomainPolicy">
              <template #leading>
                <UIcon name="heroicons:check" />
              </template>
              保存
            </UButton>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UFormGroup label="游客上传（Web 匿名）">
            <USelect
              v-model="domainPolicy.guest"
              :options="domainPolicyOptions"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>
          <UFormGroup label="Token 上传">
            <USelect
              v-model="domainPolicy.token"
              :options="domainPolicyOptions"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>
          <UFormGroup label="群组/频道上传">
            <USelect
              v-model="domainPolicy.group"
              :options="domainPolicyOptions"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>
          <UFormGroup label="管理员默认">
            <USelect
              v-model="domainPolicy.admin_default"
              :options="domainPolicyOptions"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

      <!-- 添加/编辑域名弹窗 -->
      <UModal v-model="showDomainModal">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">{{ isEditMode ? '编辑域名' : '添加域名' }}</h3>
              <UButton icon="heroicons:x-mark" color="gray" variant="ghost" size="xs" @click="showDomainModal = false" />
            </div>
          </template>

          <div class="space-y-4">
            <UFormGroup label="域名">
              <UInput v-model="domainForm.domain" placeholder="例如: img.example.com" />
            </UFormGroup>

            <UFormGroup label="端口" help="留空表示不指定端口，访问时不带端口号">
              <UInput
                v-model.number="domainForm.port"
                type="number"
                placeholder="例如: 8080（留空则不使用）"
                :min="1"
                :max="65535"
              />
            </UFormGroup>

            <UFormGroup label="类型">
              <USelect
                v-model="domainForm.domain_type"
                :options="domainTypeOptions"
                option-attribute="label"
                value-attribute="value"
              />
            </UFormGroup>

            <div class="flex items-center justify-between p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
              <div>
                <p class="text-sm font-medium text-stone-700 dark:text-stone-300">使用 HTTPS</p>
              </div>
              <UToggle v-model="domainForm.use_https" />
            </div>

            <UFormGroup label="备注">
              <UInput v-model="domainForm.remark" placeholder="可选备注" />
            </UFormGroup>
          </div>

          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton color="gray" variant="outline" @click="showDomainModal = false">取消</UButton>
              <UButton color="primary" :loading="domainSaving" @click="handleSaveDomain">{{ isEditMode ? '保存' : '添加' }}</UButton>
            </div>
          </template>
        </UCard>
      </UModal>

      <!-- 删除域名确认弹窗 -->
      <UModal v-model="showDeleteDomainModal">
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">确认删除</h3>
          </template>
          <p class="text-stone-700 dark:text-stone-300">
            确定要删除域名 <strong>{{ deletingDomain?.domain }}</strong> 吗？
          </p>
          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton color="gray" variant="outline" @click="showDeleteDomainModal = false">取消</UButton>
              <UButton color="red" :loading="domainDeleting" @click="handleDeleteDomain">删除</UButton>
            </div>
          </template>
        </UCard>
      </UModal>

      <UModal v-model="confirmModalOpen" :ui="{ width: 'sm:max-w-md' }">
        <UCard>
          <template #header>
            <div class="flex items-center gap-2">
              <UIcon name="heroicons:exclamation-triangle" class="h-5 w-5 text-amber-500" />
              <span class="font-semibold text-stone-900 dark:text-white">{{ confirmModalTitle }}</span>
            </div>
          </template>
          <p class="text-sm text-stone-600 dark:text-stone-400">{{ confirmModalMessage }}</p>
          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton color="gray" variant="ghost" @click="onConfirmCancel">取消</UButton>
              <UButton color="primary" @click="onConfirmOk">确认</UButton>
            </div>
          </template>
        </UCard>
      </UModal>

        <AdminSettingsSectionCard
            :id="sectionDomId('cdn')"
            title="CDN 加速"
            description="Cloudflare 域名、缓存策略与转发能力"
            icon="heroicons:bolt"
            :dirty="Boolean(dirtyMap.cdn)"
            :saving="Boolean(sectionSaving.cdn)"
            @save="saveSection('cdn')"
        >
      <!-- CDN 配置 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:bolt" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">CDN 加速</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">配置 Cloudflare CDN 加速</p>
              </div>
            </div>
            <UToggle v-model="settings.cdn_enabled" size="lg" />
          </div>
        </template>

        <!-- CDN 未开启提示 -->
        <div v-if="!settings.cdn_enabled" class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
          <div class="flex items-center gap-3">
            <UIcon name="heroicons:information-circle" class="w-5 h-5 text-stone-400" />
            <p class="text-sm text-stone-500 dark:text-stone-400">
              CDN 加速未开启。开启后可通过 Cloudflare 加速图片访问并降低源站压力。
            </p>
          </div>
        </div>

        <!-- CDN 配置详情 -->
        <div v-else class="space-y-6">
          <!-- 基础配置 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <UFormGroup label="Zone ID">
              <UInput v-model="settings.cloudflare_zone_id" placeholder="Cloudflare Zone ID" />
            </UFormGroup>

            <UFormGroup label="API Token">
              <UInput
                v-model="settings.cloudflare_api_token"
                type="password"
                :placeholder="settings.cloudflare_api_token_set ? '已设置（留空保持不变）' : '输入 Cloudflare API Token'"
              />
              <template #hint>
                <span v-if="settings.cloudflare_api_token_set" class="text-xs text-green-600 dark:text-green-400">
                  已配置 API Token
                </span>
                <span v-else class="text-xs text-amber-600 dark:text-amber-400">
                  未配置 API Token
                </span>
              </template>
            </UFormGroup>

            <UFormGroup label="缓存策略">
              <USelect
                v-model="settings.cloudflare_cache_level"
                :options="policyOptions.cloudflare_cache_level"
                option-attribute="label"
                value-attribute="value"
              />
            </UFormGroup>
          </div>

          <!-- TTL 配置 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <UFormGroup label="浏览器 TTL（秒）">
              <UInput v-model.number="settings.cloudflare_browser_ttl" type="number" min="0" />
              <template #hint>
                <span class="text-xs text-stone-500">默认 14400（4小时）</span>
              </template>
            </UFormGroup>

            <UFormGroup label="边缘 TTL（秒）">
              <UInput v-model.number="settings.cloudflare_edge_ttl" type="number" min="0" />
              <template #hint>
                <span class="text-xs text-stone-500">默认 2592000（30天）</span>
              </template>
            </UFormGroup>
          </div>

          <!-- 功能开关 -->
          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">智能路由</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  根据文件缓存状态智能选择访问路径
                </p>
              </div>
              <UToggle v-model="settings.enable_smart_routing" size="lg" />
            </div>

            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">回源兜底</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  CDN 访问失败时自动回源
                </p>
              </div>
              <UToggle v-model="settings.fallback_to_origin" size="lg" />
            </div>

            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">缓存预热</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  上传后自动预热 CDN 缓存
                </p>
              </div>
              <UToggle v-model="settings.enable_cache_warming" size="lg" />
            </div>

            <div v-if="settings.enable_cache_warming" class="pl-4 border-l-2 border-amber-500">
              <UFormGroup label="预热延迟（秒）">
                <UInput v-model.number="settings.cache_warming_delay" type="number" min="0" class="w-32" />
              </UFormGroup>
            </div>

            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">CDN 监控</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  监控文件缓存状态
                </p>
              </div>
              <UToggle v-model="settings.cdn_monitor_enabled" size="lg" />
            </div>

            <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">CDN 重定向</p>
                <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                  已缓存文件重定向到 CDN
                </p>
              </div>
              <UToggle v-model="settings.cdn_redirect_enabled" size="lg" />
            </div>

            <div v-if="settings.cdn_redirect_enabled" class="pl-4 border-l-2 border-amber-500 space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="最大重定向次数">
                  <UInput v-model.number="settings.cdn_redirect_max_count" type="number" min="1" />
                </UFormGroup>
                <UFormGroup label="新文件延迟（秒）">
                  <UInput v-model.number="settings.cdn_redirect_delay" type="number" min="0" />
                  <template #hint>
                    <span class="text-xs text-stone-500">新上传文件等待多久后才重定向</span>
                  </template>
                </UFormGroup>
              </div>
            </div>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('guest_policy')"
            title="游客上传策略"
            description="控制匿名上传行为与既有 Token 处理方式"
            icon="heroicons:users"
            :dirty="Boolean(dirtyMap.guest_policy)"
            :saving="Boolean(sectionSaving.guest_policy)"
            @save="saveSection('guest_policy')"
        >
      <!-- 游客上传策略 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:users" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">游客上传策略</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">控制非管理员用户的上传权限</p>
            </div>
          </div>
        </template>

        <div class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">上传策略</label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                v-for="option in policyOptions.guest_upload_policy"
                :key="option.value"
                class="relative p-4 rounded-xl border-2 cursor-pointer transition-all"
                :class="[
                  settings.guest_upload_policy === option.value
                    ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20'
                    : 'border-stone-200 dark:border-neutral-700 hover:border-stone-300 dark:hover:border-neutral-600'
                ]"
                @click="settings.guest_upload_policy = option.value"
              >
                <div class="flex items-start gap-3">
                  <div
                    class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5"
                    :class="[
                      settings.guest_upload_policy === option.value
                        ? 'border-amber-500 bg-amber-500'
                        : 'border-stone-300 dark:border-neutral-600'
                    ]"
                  >
                    <UIcon
                      v-if="settings.guest_upload_policy === option.value"
                      name="heroicons:check"
                      class="w-3 h-3 text-white"
                    />
                  </div>
                  <div>
                    <p class="font-medium text-stone-900 dark:text-white">{{ option.label }}</p>
                    <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">{{ option.description }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">允许游客生成 Token</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                关闭后，游客无法自行生成新的上传 Token
              </p>
            </div>
            <UToggle
              v-model="settings.guest_token_generation_enabled"
              size="lg"
              :disabled="settings.guest_upload_policy === 'admin_only'"
            />
          </div>

          <div v-if="settings.guest_upload_policy !== 'open'">
            <label class="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">
              已有 Token 处理策略
            </label>
            <USelect
              v-model="settings.guest_existing_tokens_policy"
              :options="policyOptions.guest_existing_tokens_policy"
              option-attribute="label"
              value-attribute="value"
            />
            <p class="text-xs text-stone-500 dark:text-stone-400 mt-2">
              当切换到限制模式时，如何处理已经生成的 Token
            </p>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('token_limits')"
            title="Token 限制"
            description="游客 Token 的数量、有效期与 IP 限额"
            icon="heroicons:key"
            :dirty="Boolean(dirtyMap.token_limits)"
            :saving="Boolean(sectionSaving.token_limits)"
            @save="saveSection('token_limits')"
        >
      <!-- Token 限制设置 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:key" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Token 限制</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置游客 Token 的上传数量和有效期限制</p>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <UFormGroup label="单个 Token 最大上传数">
            <UInput
              v-model.number="settings.guest_token_max_upload_limit"
              type="number"
              min="1"
              max="1000000"
              placeholder="1000"
            />
            <template #hint>
              <span class="text-xs text-stone-500">游客生成的 Token 最多可上传的图片数量</span>
            </template>
          </UFormGroup>

          <UFormGroup label="Token 最大有效期（天）">
            <UInput
              v-model.number="settings.guest_token_max_expires_days"
              type="number"
              min="1"
              max="36500"
              placeholder="365"
            />
            <template #hint>
              <span class="text-xs text-stone-500">游客生成的 Token 最长有效天数</span>
            </template>
          </UFormGroup>

          <UFormGroup label="非 TG 用户每 IP Token 上限">
            <UInput
              v-model.number="settings.max_guest_tokens_per_ip"
              type="number"
              min="1"
              max="100"
              placeholder="3"
            />
            <template #hint>
              <span class="text-xs text-stone-500">未通过 TG 登录的用户，每个 IP 最多可生成的 Token 数量</span>
            </template>
          </UFormGroup>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('upload_limits')"
            title="上传限制"
            description="文件大小、每日配额和可用后缀白名单"
            icon="heroicons:cloud-arrow-up"
            :dirty="Boolean(dirtyMap.upload_limits)"
            :saving="Boolean(sectionSaving.upload_limits)"
            @save="saveSection('upload_limits')"
        >
      <!-- 上传限制 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">上传限制</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置文件大小和每日上传数量限制</p>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <UFormGroup label="最大文件大小（MB）">
            <UInput
              v-model.number="settings.max_file_size_mb"
              type="number"
              min="1"
              max="100"
              placeholder="20"
            />
            <template #hint>
              <span class="text-xs text-stone-500">单个文件的最大上传大小，范围 1-100 MB</span>
            </template>
          </UFormGroup>

          <UFormGroup label="每日上传限制">
            <UInput
              v-model.number="settings.daily_upload_limit"
              type="number"
              min="0"
              max="1000000"
              placeholder="0"
            />
            <template #hint>
              <span class="text-xs text-stone-500">每日最大上传数量，0 表示不限制</span>
            </template>
          </UFormGroup>
        </div>

        <UFormGroup label="允许的文件类型">
          <UInput
            v-model="settings.allowed_extensions"
            placeholder="jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico"
          />
          <template #hint>
            <span class="text-xs text-stone-500">
              逗号分隔的文件后缀，内置后缀（jpg/jpeg/png/gif/webp/bmp）始终生效。添加 svg 请注意 XSS 风险。
            </span>
          </template>
        </UFormGroup>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('bot')"
            title="Bot 功能与回复"
            description="交互开关、inline 按钮、回复模板与链接格式"
            icon="heroicons:chat-bubble-left-right"
            :dirty="Boolean(dirtyMap.bot)"
            :saving="Boolean(sectionSaving.bot)"
            @save="saveSection('bot')"
        >
      <!-- Bot 功能配置 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:chat-bubble-left-right" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Bot 功能</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置 Telegram Bot 的交互功能</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <UFormGroup label="Bot 更新模式">
              <USelect
                v-model="settings.bot_update_mode"
                :options="botUpdateModeOptions"
                option-attribute="label"
                value-attribute="value"
              />
              <template #hint>
                <span class="text-xs text-stone-500">Polling 适合单机，Webhook 适合公网反代部署</span>
              </template>
            </UFormGroup>

            <UFormGroup label="/settoken 有效期（秒）">
              <UInput
                v-model.number="settings.bot_settoken_ttl_seconds"
                type="number"
                min="30"
                max="3600"
                placeholder="600"
              />
              <template #hint>
                <span class="text-xs text-stone-500">回调按钮过期时间，范围 30-3600 秒</span>
              </template>
            </UFormGroup>
          </div>

          <UFormGroup v-if="settings.bot_update_mode === 'webhook'" label="Webhook 基础 URL">
            <UInput
              v-model="settings.bot_webhook_url"
              placeholder="https://example.com"
            />
            <template #hint>
              <div class="flex flex-wrap items-center gap-2 text-xs text-stone-500">
                <span>仅填写基础域名，系统会自动拼接 webhook 路径</span>
                <UButton
                  type="button"
                  size="2xs"
                  color="gray"
                  variant="ghost"
                  icon="heroicons:question-mark-circle"
                  @click="showWebhookGuide = !showWebhookGuide"
                >
                  如何获取
                </UButton>
              </div>
            </template>

            <div v-if="showWebhookGuide" class="mt-2 rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-xs text-amber-800 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200">
              <p class="font-medium">Webhook 基础 URL 填写说明</p>
              <p class="mt-1">1. 填你的公网可访问站点根地址，不要带路径。</p>
              <p>2. 常见就是当前图床外网地址，例如：<code>https://img.example.com</code>。</p>
              <p>3. 保存后系统会自动生成完整地址：<code>/api/auth/tg/webhook/&lt;secret&gt;</code>，无需手动拼接。</p>
              <p>4. 本地 <code>http://127.0.0.1</code> 这类内网地址 Telegram 访问不到，不能用于 webhook。</p>
            </div>
          </UFormGroup>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">模板严格模式</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                开启后，自定义回复模板渲染失败时不回退默认模板
              </p>
            </div>
            <UToggle v-model="settings.bot_template_strict_mode" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">Caption 自定义文件名</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                发送图片时附带说明文字作为文件名
              </p>
            </div>
            <UToggle v-model="settings.bot_caption_filename_enabled" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">上传成功 Inline 按钮</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                私聊上传成功后显示"打开链接"和"删除"按钮
              </p>
            </div>
            <UToggle v-model="settings.bot_inline_buttons_enabled" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">用户自助删除</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                允许用户通过 /delete 命令和 inline 按钮删除自己的图片
              </p>
            </div>
            <UToggle v-model="settings.bot_user_delete_enabled" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">上传历史查询</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                允许用户通过 /myuploads 查看个人上传记录
              </p>
            </div>
            <UToggle v-model="settings.bot_myuploads_enabled" size="lg" />
          </div>

          <div v-if="settings.bot_myuploads_enabled" class="pl-4 border-l-2 border-blue-500">
            <UFormGroup label="每页显示数量">
              <UInput
                v-model.number="settings.bot_myuploads_page_size"
                type="number"
                min="1"
                max="50"
                placeholder="8"
                class="w-32"
              />
              <template #hint>
                <span class="text-xs text-stone-500">上传历史每页显示的图片数量（1-50）</span>
              </template>
            </UFormGroup>
          </div>

          <!-- Bot 回复配置分隔线 -->
          <div class="border-t border-stone-200 dark:border-neutral-700 pt-4">
            <p class="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">上传成功回复配置</p>
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">显示文件大小</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                上传成功回复中显示文件大小（如 155.0 KB）
              </p>
            </div>
            <UToggle v-model="settings.bot_reply_show_size" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">显示文件名</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                上传成功回复中显示原始文件名
              </p>
            </div>
            <UToggle v-model="settings.bot_reply_show_filename" size="lg" />
          </div>

          <div class="pl-4 border-l-2 border-blue-500 space-y-4">
            <UFormGroup label="链接复制格式">
              <div class="flex flex-wrap gap-3 mt-1">
                <label v-for="fmt in linkFormatOptions" :key="fmt.value" class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    :checked="isLinkFormatEnabled(fmt.value)"
                    class="rounded border-stone-300 text-amber-500 focus:ring-amber-500"
                    @change="toggleLinkFormat(fmt.value)"
                  />
                  <span class="text-sm text-stone-700 dark:text-stone-300">{{ fmt.label }}</span>
                </label>
              </div>
              <template #hint>
                <span class="text-xs text-stone-500">勾选的格式会在上传成功消息中显示为 inline 按钮，方便用户复制</span>
              </template>
            </UFormGroup>

            <UFormGroup label="自定义回复模板">
              <UTextarea
                v-model="settings.bot_reply_template"
                placeholder="留空使用默认模板。支持变量：{url} {size} {filename} {id}"
                :rows="3"
                :maxlength="500"
              />
              <template #hint>
                <span class="text-xs text-stone-500">
                  可用变量：<code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">{url}</code>
                  <code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">{size}</code>
                  <code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">{filename}</code>
                  <code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">{id}</code>
                  · 最多 500 字符
                </span>
              </template>
            </UFormGroup>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('tg_auth')"
            title="Telegram 认证"
            description="登录绑定策略与验证码、会话有效期配置"
            icon="heroicons:shield-check"
            :dirty="Boolean(dirtyMap.tg_auth)"
            :saving="Boolean(sectionSaving.tg_auth)"
            @save="saveSection('tg_auth')"
        >
      <!-- TG 认证配置 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:shield-check" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">TG 认证</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">通过 Telegram Bot 认证用户身份</p>
              </div>
            </div>
            <UToggle v-model="settings.tg_auth_enabled" size="lg" :disabled="!settings.bot_token_configured" />
          </div>
        </template>

        <div v-if="!settings.bot_token_configured" class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl">
          <div class="flex items-center gap-3">
            <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-amber-500" />
            <p class="text-sm text-amber-700 dark:text-amber-400">
              TG 认证需要先配置 Telegram Bot Token。请在「Telegram 设置」中配置 Bot Token 后再开启。
            </p>
          </div>
        </div>

        <div v-else-if="!settings.tg_auth_enabled" class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
          <div class="flex items-center gap-3">
            <UIcon name="heroicons:information-circle" class="w-5 h-5 text-stone-400" />
            <p class="text-sm text-stone-500 dark:text-stone-400">
              TG 认证未启用。开启后用户可通过 Telegram Bot 登录 Web 端，Token 将绑定 TG 账号。
            </p>
          </div>
        </div>

        <div v-else class="space-y-4">
          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">Token 生成需要 TG 登录</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                开启后，用户必须先通过 TG 登录才能生成新 Token
              </p>
            </div>
            <UToggle v-model="settings.tg_auth_required_for_token" size="lg" />
          </div>

          <div class="flex items-center justify-between p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div>
              <p class="font-medium text-stone-900 dark:text-white">Token 绑定 TG 用户</p>
              <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
                开启后，已 TG 登录的用户生成 Token 时自动绑定，也支持手动绑定已有 Token
              </p>
              <p v-if="settings.tg_auth_required_for_token" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
                强制 TG 登录时，Token 自动绑定
              </p>
            </div>
            <UToggle
              v-model="settings.tg_bind_token_enabled"
              size="lg"
              :disabled="settings.tg_auth_required_for_token"
            />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <UFormGroup label="每用户 Token 上限">
              <UInput v-model.number="settings.tg_max_tokens_per_user" type="number" min="1" max="100" placeholder="5" />
            </UFormGroup>
            <UFormGroup label="验证码有效期（分钟）">
              <UInput v-model.number="settings.tg_login_code_expire_minutes" type="number" min="1" max="60" placeholder="5" />
            </UFormGroup>
            <UFormGroup label="会话有效期（天）">
              <UInput v-model.number="settings.tg_session_expire_days" type="number" min="1" max="365" placeholder="30" />
            </UFormGroup>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('proxy_and_tokens')"
            title="网络代理与 Token 操作"
            description="代理配置与批量禁用 Token 的风险操作"
            icon="heroicons:globe-americas"
            :dirty="Boolean(dirtyMap.proxy_and_tokens)"
            :saving="Boolean(sectionSaving.proxy_and_tokens)"
            @save="saveSection('proxy_and_tokens')"
        >
      <!-- 网络代理 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-teal-500 to-teal-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:globe-americas" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">网络代理</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置 HTTP/HTTPS 代理，用于 Telegram Bot 和存储后端的网络请求</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="代理地址">
            <UInput
              v-model="settings.proxy_url"
              type="password"
              :placeholder="proxyPlaceholder"
            />
            <template #hint>
              <span v-if="settings.proxy_url_set" class="text-xs text-green-600 dark:text-green-400">
                当前使用数据库配置的代理
              </span>
              <span v-else-if="settings.proxy_env_set" class="text-xs text-blue-600 dark:text-blue-400">
                当前使用环境变量配置的代理
              </span>
              <span v-else class="text-xs text-stone-500 dark:text-stone-400">
                未配置代理
              </span>
            </template>
          </UFormGroup>

          <div class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-xl">
            <div class="flex items-start gap-3">
              <UIcon name="heroicons:information-circle" class="w-5 h-5 text-stone-400 flex-shrink-0 mt-0.5" />
              <div class="text-sm text-stone-500 dark:text-stone-400">
                <p>格式：<code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">http://host:port</code> 或 <code class="px-1 py-0.5 bg-stone-200 dark:bg-neutral-700 rounded text-xs">http://user:pass@host:port</code></p>
                <p class="mt-1">留空则清除数据库代理设置，回退到环境变量。修改后需重启 Bot 才能对 Telegram 连接生效。</p>
              </div>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Token 管理 -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:shield-exclamation" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Token 管理</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">批量禁用已生成的 Token</p>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div class="flex items-start gap-3">
              <UIcon name="heroicons:exclamation-triangle" class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p class="font-medium text-red-800 dark:text-red-200">危险操作</p>
                <p class="text-sm text-red-600 dark:text-red-300 mt-1">
                  禁用 Token 后，使用这些 Token 的用户将无法继续上传图片。此操作不可撤销。
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
            <UButton
              color="red"
              variant="soft"
              :loading="revokingTokens"
              @click="revokeTokens('guest')"
            >
              <template #leading>
                <UIcon name="heroicons:user-minus" />
              </template>
              禁用所有游客 Token
            </UButton>
            <UButton
              color="red"
              variant="outline"
              :loading="revokingTokens"
              @click="revokeTokens('all')"
            >
              <template #leading>
                <UIcon name="heroicons:no-symbol" />
              </template>
              禁用所有 Token
            </UButton>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>

        <AdminSettingsSectionCard
            :id="sectionDomId('about_update')"
            title="关于与更新"
            description="版本信息与 Release 热更新"
            icon="heroicons:arrow-path"
            :dirty="Boolean(dirtyMap.about_update)"
            :saving="Boolean(sectionSaving.about_update)"
            @save="saveSection('about_update')"
        >
      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:information-circle" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">版本信息</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">展示当前运行状态与环境能力</p>
              </div>
            </div>
            <UButton
              color="gray"
              variant="outline"
              size="sm"
              icon="heroicons:arrow-path"
              :loading="updateInfoLoading || updateStatusLoading"
              @click="refreshUpdatePanel"
            >
              刷新状态
            </UButton>
          </div>
        </template>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
            <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">应用版本</p>
            <p class="mt-1 text-base font-semibold text-stone-900 dark:text-white">{{ updateInfo.app_version || '--' }}</p>
          </div>
          <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
            <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">当前版本</p>
            <p class="mt-1 text-base font-semibold text-stone-900 dark:text-white">{{ updateInfo.current_version || settings.app_update_last_version || settings.app_update_last_commit || '--' }}</p>
          </div>
          <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
            <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">更新模式</p>
            <p class="mt-1 text-base font-semibold text-stone-900 dark:text-white">
              {{ updateInfo.update_source === 'release' ? 'Release Artifact' : (updateInfo.update_source || '--') }}
            </p>
          </div>
          <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
            <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">最近状态</p>
            <UBadge :color="updateStatusColor(updateTask.state)" variant="subtle" class="mt-1">
              {{ updateTask.state || settings.app_update_last_status || 'idle' }}
            </UBadge>
          </div>
        </div>

        <div class="mt-4 rounded-xl border border-stone-200/80 bg-stone-50/70 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/60">
          <p class="text-sm font-medium text-stone-900 dark:text-white">环境检查</p>
          <div class="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <div :class="envBadgeClass(updateInfo.release_supported)">release: {{ updateInfo.release_supported ? 'OK' : '不可用' }}</div>
            <div :class="envBadgeClass(updateInfo.pip_available)">pip: {{ updateInfo.pip_available ? 'OK' : '缺失' }}</div>
            <div :class="envBadgeClass(updateCheck.asset_found)">asset: {{ updateCheck.asset_found ? 'OK' : '未检查/缺失' }}</div>
            <div :class="envBadgeClass(updateCheck.sha_found)">sha256: {{ updateCheck.sha_found ? 'OK' : '未检查/缺失' }}</div>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-down" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-stone-900 dark:text-white">Release 更新配置</h3>
              <p class="text-xs text-stone-500 dark:text-stone-400">固定官方仓库与资产名，使用校验文件保证完整性</p>
            </div>
          </div>
        </template>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormGroup label="更新源（固定）">
            <UInput :model-value="settings.app_update_source" disabled />
          </UFormGroup>
          <UFormGroup label="Release 仓库（固定）">
            <UInput :model-value="settings.app_update_release_repo" disabled />
          </UFormGroup>
          <UFormGroup label="更新包文件名（固定）">
            <UInput :model-value="settings.app_update_release_asset_name" disabled />
          </UFormGroup>
          <UFormGroup label="校验文件名（固定）">
            <UInput :model-value="settings.app_update_release_sha_name" disabled />
          </UFormGroup>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:arrow-path-rounded-square" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">更新操作</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">检查最新 Release 并执行自动更新</p>
              </div>
            </div>
            <UBadge :color="updateStatusColor(updateTask.state)" variant="subtle">
              {{ updateTask.state || 'idle' }}
            </UBadge>
          </div>
        </template>

        <div class="space-y-4">
          <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs text-stone-500 dark:text-stone-400">本地版本</p>
              <p class="mt-1 font-medium text-stone-900 dark:text-white">{{ updateCheck.current_version || updateInfo.current_version || '--' }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs text-stone-500 dark:text-stone-400">最新版本</p>
              <p class="mt-1 font-medium text-stone-900 dark:text-white">{{ updateCheck.latest_version || '--' }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs text-stone-500 dark:text-stone-400">Release 标签</p>
              <p class="mt-1 font-medium text-stone-900 dark:text-white">{{ updateCheck.release_tag || '--' }}</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <UButton
              color="gray"
              variant="outline"
              icon="heroicons:magnifying-glass-circle"
              :loading="updateChecking"
              :disabled="updateBusy"
              @click="checkForUpdates"
            >
              检查更新
            </UButton>
            <UButton
              color="primary"
              icon="heroicons:arrow-down-tray"
              :loading="updateRunning"
              :disabled="updateBusy || !canRunHotUpdate"
              @click="runHotUpdate"
            >
              一键更新
            </UButton>
            <span v-if="!canRunHotUpdate" class="text-xs text-rose-600 dark:text-rose-400">
              当前环境不满足 Release 热更新条件（需 release + pip + 完整资产）
            </span>
          </div>

          <div v-if="updateTask.message || settings.app_update_last_error" class="rounded-xl border border-stone-200/80 bg-stone-50/70 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/60">
            <p class="text-sm font-medium text-stone-900 dark:text-white">任务信息</p>
            <p class="mt-1 text-sm text-stone-600 dark:text-stone-300">{{ updateTask.message || '暂无任务信息' }}</p>
            <p v-if="updateTask.error || settings.app_update_last_error" class="mt-1 text-sm text-rose-600 dark:text-rose-400 break-all">
              {{ updateTask.error || settings.app_update_last_error }}
            </p>
          </div>

          <div v-if="updateTask.logs?.length" class="rounded-xl border border-stone-200/80 bg-stone-900 p-3 text-xs text-stone-200 dark:border-neutral-700/80">
            <p class="mb-2 font-medium text-stone-100">更新日志</p>
            <div class="max-h-56 space-y-1 overflow-y-auto font-mono">
              <p v-for="(line, idx) in updateTask.logs" :key="idx">{{ line }}</p>
            </div>
          </div>
        </div>
      </UCard>
        </AdminSettingsSectionCard>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'
import type { DomainItem } from '~/composables/useDomainsApi'
import type {
  AdminSystemSettings,
  DomainPolicyForm,
  SettingsSectionItem,
  SettingsSectionKey,
} from '~/types/admin-settings'

definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()
const domainsApi = useDomainsApi()

const loading = ref(false)
const saving = ref(false)
const revokingTokens = ref(false)
const settingsLoaded = ref(false)

const settings = ref<AdminSystemSettings>({
  // 游客上传策略
  guest_upload_policy: 'open',
  guest_token_generation_enabled: true,
  guest_existing_tokens_policy: 'keep',
  guest_token_max_upload_limit: 1000,
  guest_token_max_expires_days: 365,
  max_file_size_mb: 20,
  daily_upload_limit: 0,
  // CDN 配置
  cdn_enabled: false,
  cloudflare_cdn_domain: '',
  cloudflare_api_token: '',
  cloudflare_api_token_set: false,
  cloudflare_zone_id: '',
  cloudflare_cache_level: 'aggressive',
  cloudflare_browser_ttl: 14400,
  cloudflare_edge_ttl: 2592000,
  enable_smart_routing: false,
  fallback_to_origin: true,
  enable_cache_warming: false,
  cache_warming_delay: 5,
  cdn_monitor_enabled: false,
  cdn_redirect_enabled: false,
  cdn_redirect_max_count: 2,
  cdn_redirect_delay: 10,
  // Bot 功能开关
  bot_caption_filename_enabled: true,
  bot_inline_buttons_enabled: true,
  bot_user_delete_enabled: true,
  bot_myuploads_enabled: true,
  bot_myuploads_page_size: 8,
  bot_update_mode: 'polling',
  bot_webhook_url: '',
  bot_settoken_ttl_seconds: 600,
  bot_template_strict_mode: false,
  // Bot 回复配置
  bot_reply_link_formats: 'url',
  bot_reply_template: '',
  bot_reply_show_size: true,
  bot_reply_show_filename: false,
  // 网络代理
  proxy_url: '',
  proxy_url_set: false,
  proxy_env_set: false,
  // 允许的文件后缀
  allowed_extensions: 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico',
  // TG 认证
  tg_auth_enabled: false,
  bot_token_configured: false,
  tg_auth_required_for_token: false,
  tg_bind_token_enabled: false,
  tg_max_tokens_per_user: 5,
  tg_login_code_expire_minutes: 5,
  tg_session_expire_days: 30,
  // 非 TG 用户 Token 限制
  max_guest_tokens_per_ip: 3,
  // 图片域名限制
  image_domain_restriction_enabled: false,
  // 热更新（Release Artifact）
  app_update_source: 'release',
  app_update_release_repo: 'xiyan520/tg-telegram-imagebed',
  app_update_release_asset_name: 'tg-imagebed-release.zip',
  app_update_release_sha_name: 'tg-imagebed-release.zip.sha256',
  // 兼容旧字段
  app_update_repo_url: 'https://github.com/xiyan520/tg-telegram-imagebed.git',
  app_update_branch: 'main',
  app_update_last_status: 'idle',
  app_update_last_error: '',
  app_update_last_version: '',
  app_update_last_commit: '',
  app_update_last_run_at: '',
  app_update_last_duration_ms: 0,
})

const originalSettings = ref<AdminSystemSettings | null>(null)

const sectionItems: SettingsSectionItem[] = [
  { key: 'domains', label: '域名与路由', description: '域名、画集入口、路由策略', icon: 'heroicons:globe-alt' },
  { key: 'cdn', label: 'CDN 加速', description: 'Cloudflare 缓存与重定向', icon: 'heroicons:bolt' },
  { key: 'guest_policy', label: '游客策略', description: '匿名上传与已有 Token 处理', icon: 'heroicons:users' },
  { key: 'token_limits', label: 'Token 限制', description: '数量、有效期和 IP 限额', icon: 'heroicons:key' },
  { key: 'upload_limits', label: '上传限制', description: '大小、每日配额、文件类型', icon: 'heroicons:cloud-arrow-up' },
  { key: 'bot', label: 'Bot 功能', description: '交互能力和回复模板', icon: 'heroicons:chat-bubble-left-right' },
  { key: 'tg_auth', label: 'TG 认证', description: '登录绑定与会话参数', icon: 'heroicons:shield-check' },
  { key: 'proxy_and_tokens', label: '代理与风险操作', description: '网络代理与批量禁用', icon: 'heroicons:shield-exclamation' },
  { key: 'about_update', label: '关于与更新', description: '版本信息与 Release 热更新', icon: 'heroicons:arrow-path' },
]

const sectionFieldGroups: Record<SettingsSectionKey, string[]> = {
  domains: ['image_domain_restriction_enabled'],
  cdn: [
    'cdn_enabled',
    'cloudflare_cdn_domain',
    'cloudflare_api_token',
    'cloudflare_zone_id',
    'cloudflare_cache_level',
    'cloudflare_browser_ttl',
    'cloudflare_edge_ttl',
    'enable_smart_routing',
    'fallback_to_origin',
    'enable_cache_warming',
    'cache_warming_delay',
    'cdn_monitor_enabled',
    'cdn_redirect_enabled',
    'cdn_redirect_max_count',
    'cdn_redirect_delay',
  ],
  guest_policy: ['guest_upload_policy', 'guest_token_generation_enabled', 'guest_existing_tokens_policy'],
  token_limits: ['guest_token_max_upload_limit', 'guest_token_max_expires_days', 'max_guest_tokens_per_ip'],
  upload_limits: ['max_file_size_mb', 'daily_upload_limit', 'allowed_extensions'],
  bot: [
    'bot_caption_filename_enabled',
    'bot_inline_buttons_enabled',
    'bot_user_delete_enabled',
    'bot_myuploads_enabled',
    'bot_myuploads_page_size',
    'bot_update_mode',
    'bot_webhook_url',
    'bot_settoken_ttl_seconds',
    'bot_template_strict_mode',
    'bot_reply_link_formats',
    'bot_reply_template',
    'bot_reply_show_size',
    'bot_reply_show_filename',
  ],
  tg_auth: [
    'tg_auth_enabled',
    'tg_auth_required_for_token',
    'tg_bind_token_enabled',
    'tg_max_tokens_per_user',
    'tg_login_code_expire_minutes',
    'tg_session_expire_days',
  ],
  proxy_and_tokens: ['proxy_url'],
  about_update: ['app_update_source'],
}

const activeSection = ref<SettingsSectionKey>('domains')
const sectionSaving = ref<Partial<Record<SettingsSectionKey, boolean>>>({})

const sectionDomId = (key: SettingsSectionKey) => `settings-section-${key}`

const policyOptions = ref({
  guest_upload_policy: [
    { value: 'open', label: '完全开放', description: '允许匿名上传和 Token 上传' },
    { value: 'token_only', label: '仅 Token', description: '禁止匿名上传，允许 Token 上传' },
    { value: 'admin_only', label: '仅管理员', description: '禁止所有游客上传' },
  ],
  guest_existing_tokens_policy: [
    { value: 'keep', label: '保留有效', description: '关闭游客模式后，已有 Token 仍可使用' },
    { value: 'disable_guest', label: '禁用游客 Token', description: '关闭时禁用所有游客生成的 Token' },
    { value: 'disable_all', label: '禁用所有 Token', description: '关闭时禁用所有 Token' },
  ],
  cloudflare_cache_level: [
    { value: 'basic', label: '基础' },
    { value: 'aggressive', label: '激进' },
    { value: 'simplified', label: '简化' },
  ],
})

// 链接格式选项
const linkFormatOptions = [
  { value: 'url', label: 'URL 直链' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'html', label: 'HTML' },
  { value: 'bbcode', label: 'BBCode' },
]

const botUpdateModeOptions = [
  { value: 'polling', label: 'Polling（长轮询）' },
  { value: 'webhook', label: 'Webhook（推送）' },
]
const showWebhookGuide = ref(false)

const isLinkFormatEnabled = (fmt: string) => {
  const formats = (settings.value.bot_reply_link_formats || 'url').split(',').map((s: string) => s.trim())
  return formats.includes(fmt)
}

const toggleLinkFormat = (fmt: string) => {
  const formats = (settings.value.bot_reply_link_formats || 'url').split(',').map((s: string) => s.trim()).filter(Boolean)
  const idx = formats.indexOf(fmt)
  if (idx >= 0) {
    // 至少保留一个格式
    if (formats.length > 1) {
      formats.splice(idx, 1)
    }
  } else {
    formats.push(fmt)
  }
  settings.value.bot_reply_link_formats = formats.join(',')
}

// 域名模式计算属性（CDN 配置卡片仍需使用）
const proxyPlaceholder = computed(() => {
  if (settings.value.proxy_url_set) return '已设置（留空清除，回退到环境变量）'
  if (settings.value.proxy_env_set) return '环境变量已配置（此处可覆盖）'
  return 'http://host:port'
})

type UpdateRuntimeInfo = {
  app_version: string
  current_version: string
  update_source: string
  release_repo: string
  release_asset_name: string
  release_sha_name: string
  release_supported: boolean
  repo_allowed: boolean
  pip_available: boolean
}

type UpdateCheckResult = {
  current_version: string
  latest_version: string
  release_tag: string
  release_name: string
  published_at: string
  asset_found: boolean
  sha_found: boolean
  has_update: boolean
}

type UpdateTaskState = {
  task_id: string
  state: string
  message: string
  error: string
  logs: string[]
}

const updateInfoLoading = ref(false)
const updateChecking = ref(false)
const updateRunning = ref(false)
const updateStatusLoading = ref(false)
const updateStatusTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const updateInfo = ref<UpdateRuntimeInfo>({
  app_version: '',
  current_version: '',
  update_source: '',
  release_repo: '',
  release_asset_name: '',
  release_sha_name: '',
  release_supported: false,
  repo_allowed: false,
  pip_available: false,
})

const updateCheck = ref<UpdateCheckResult>({
  current_version: '',
  latest_version: '',
  release_tag: '',
  release_name: '',
  published_at: '',
  asset_found: false,
  sha_found: false,
  has_update: false,
})

const updateTask = ref<UpdateTaskState>({
  task_id: '',
  state: '',
  message: '',
  error: '',
  logs: [],
})

const updateBusy = computed(() => {
  return ['running', 'downloading', 'verifying', 'applying', 'rolling_back', 'restarting'].includes(updateTask.value.state)
})

const canRunHotUpdate = computed(() => {
  return Boolean(
    updateInfo.value.release_supported &&
    updateInfo.value.pip_available &&
    updateCheck.value.asset_found &&
    updateCheck.value.sha_found
  )
})

const envBadgeClass = (ok: boolean) => {
  return ok
    ? 'rounded-lg bg-emerald-100 px-2 py-1 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
    : 'rounded-lg bg-rose-100 px-2 py-1 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'
}

const updateStatusColor = (state?: string) => {
  switch (state) {
    case 'success':
      return 'green'
    case 'running':
    case 'downloading':
    case 'verifying':
    case 'applying':
    case 'restarting':
      return 'amber'
    case 'rolled_back':
      return 'orange'
    case 'failed':
      return 'red'
    default:
      return 'gray'
  }
}

const clearUpdateStatusPoll = () => {
  if (!updateStatusTimer.value) return
  clearTimeout(updateStatusTimer.value)
  updateStatusTimer.value = null
}

const scheduleUpdateStatusPoll = () => {
  clearUpdateStatusPoll()
  if (!updateBusy.value) return
  updateStatusTimer.value = setTimeout(async () => {
    await loadUpdateStatus()
    scheduleUpdateStatusPoll()
  }, 2000)
}

const loadUpdateInfo = async () => {
  updateInfoLoading.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/update/info`, {
      credentials: 'include'
    })
    if (res?.success && res.data) {
      updateInfo.value = {
        app_version: res.data.app_version || '',
        current_version: res.data.current_version || '',
        update_source: res.data.update_source || '',
        release_repo: res.data.release_repo || '',
        release_asset_name: res.data.release_asset_name || '',
        release_sha_name: res.data.release_sha_name || '',
        release_supported: Boolean(res.data.release_supported),
        repo_allowed: Boolean(res.data.repo_allowed),
        pip_available: Boolean(res.data.pip_available),
      }
      settings.value.app_update_source = res.data.update_source || settings.value.app_update_source
      settings.value.app_update_release_repo = res.data.release_repo || settings.value.app_update_release_repo
      settings.value.app_update_release_asset_name = res.data.release_asset_name || settings.value.app_update_release_asset_name
      settings.value.app_update_release_sha_name = res.data.release_sha_name || settings.value.app_update_release_sha_name
    }
  } catch (error: any) {
    notification.error('更新信息加载失败', error?.data?.error || error?.message || '无法获取更新运行信息')
  } finally {
    updateInfoLoading.value = false
  }
}

const loadUpdateStatus = async () => {
  updateStatusLoading.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/update/status`, {
      credentials: 'include'
    })
    if (res?.success && res.data) {
      updateTask.value = {
        task_id: res.data.task_id || '',
        state: res.data.state || '',
        message: res.data.message || '',
        error: res.data.error || '',
        logs: Array.isArray(res.data.logs) ? res.data.logs : [],
      }
      if (res.data.current_version) {
        settings.value.app_update_last_version = res.data.current_version
        settings.value.app_update_last_commit = res.data.current_version
      }
      if (res.data.runtime?.current_version) {
        updateInfo.value.current_version = res.data.runtime.current_version
      }
    }
  } catch (error: any) {
    console.error('加载更新任务状态失败:', error)
  } finally {
    updateStatusLoading.value = false
  }
}

const checkForUpdates = async () => {
  updateChecking.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/update/check`, {
      method: 'POST',
      credentials: 'include',
    })
    if (res?.success && res.data) {
      updateCheck.value = {
        current_version: res.data.current_version || '',
        latest_version: res.data.latest_version || '',
        release_tag: res.data.release_tag || '',
        release_name: res.data.release_name || '',
        published_at: res.data.published_at || '',
        asset_found: Boolean(res.data.asset_found),
        sha_found: Boolean(res.data.sha_found),
        has_update: Boolean(res.data.has_update),
      }
      notification.success('检查完成', res.data.has_update ? `发现新版本 ${res.data.latest_version}` : '当前已是最新版本')
    }
  } catch (error: any) {
    notification.error('检查失败', error?.data?.error || error?.message || '无法检查更新')
  } finally {
    updateChecking.value = false
  }
}

const runHotUpdate = async () => {
  if (!canRunHotUpdate.value) {
    notification.error('环境不满足', '当前环境无法执行 Release 热更新')
    return
  }
  updateRunning.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/update/run`, {
      method: 'POST',
      credentials: 'include',
    })
    if (res?.success) {
      notification.success('已启动', '更新任务已开始执行，请等待自动重启')
      await loadUpdateStatus()
      scheduleUpdateStatusPoll()
    } else {
      notification.warning('任务未启动', res?.message || '已有任务在运行')
    }
  } catch (error: any) {
    const statusCode = Number(error?.statusCode || error?.response?.status || 0)
    const message = error?.data?.message || error?.data?.error || error?.message || '无法启动更新任务'
    if (statusCode === 409) {
      notification.warning('任务未启动', message || '已有任务在运行')
      return
    }
    notification.error('启动失败', message)
  } finally {
    updateRunning.value = false
  }
}

const refreshUpdatePanel = async () => {
  await Promise.all([loadUpdateInfo(), loadUpdateStatus()])
}

const loadSettings = async () => {
  loading.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      credentials: 'include'
    })

    if (response.success) {
      const data = response.data
      // 只提取 settings ref 中已定义的字段，避免 storage.vue 管理的字段被混入
      const filtered: Record<string, any> = {}
      for (const key of Object.keys(settings.value)) {
        if (key in data) {
          filtered[key] = data[key]
        }
      }
      settings.value = {
        ...settings.value,
        ...filtered,
        cloudflare_api_token: '',
        proxy_url: '',
      }
      originalSettings.value = { ...settings.value }
      settingsLoaded.value = true

      if (response.policy_options) {
        policyOptions.value = { ...policyOptions.value, ...response.policy_options }
      }
    }
  } catch (error: any) {
    console.error('加载设置失败:', error)
    notification.error('加载失败', error.data?.error || '无法加载系统设置')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    const payload = {
      ...settings.value,
      apply_token_policy: settings.value.guest_upload_policy !== 'open'
    }
    if (!payload.cloudflare_api_token) {
      delete (payload as any).cloudflare_api_token
    }
    // proxy_url：未输入新值时不发送（避免覆盖已有配置）
    // 但如果后端已有代理且用户主动清空，需要发送空字符串以清除
    if (!payload.proxy_url && !settings.value.proxy_url_set) {
      delete (payload as any).proxy_url
    }

    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
      method: 'PUT',
      credentials: 'include',
      body: payload
    })

    if (response.success) {
      notification.success('保存成功', response.message || '系统设置已更新')
      // 同样用白名单过滤响应数据
      const respData = response.data || {}
      const filteredResp: Record<string, any> = {}
      for (const key of Object.keys(settings.value)) {
        if (key in respData) {
          filteredResp[key] = respData[key]
        }
      }
      settings.value = { ...settings.value, ...filteredResp, cloudflare_api_token: '', proxy_url: '' }
      originalSettings.value = { ...settings.value }

      if (response.tokens_disabled > 0) {
        notification.info('Token 已处理', `已禁用 ${response.tokens_disabled} 个 Token`)
      }
    }
  } catch (error: any) {
    console.error('保存设置失败:', error)
    notification.error('保存失败', error.data?.error || '无法保存系统设置')
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  if (originalSettings.value) {
    settings.value = { ...originalSettings.value }
    try {
      const policy = JSON.parse(domainPolicySnapshot.value || '{}')
      domainPolicy.value = {
        guest: policy.guest || '',
        token: policy.token || '',
        group: policy.group || '',
        admin_default: policy.admin_default || '',
      }
      const gallery = JSON.parse(gallerySettingsSnapshot.value || '{}')
      gallerySiteSettings.value = {
        name: gallery.name || '',
        description: gallery.description || '',
        enabled: gallery.enabled !== false,
      }
    } catch {
      // ignore parse errors and keep in-memory values
    }
    notification.info('已重置', '设置已恢复到上次保存的状态')
  }
}

const saveSection = async (sectionKey: SettingsSectionKey) => {
  sectionSaving.value[sectionKey] = true
  try {
    if (sectionKey === 'domains') {
      await saveSettings()
      if (activeImageDomains.value.length >= 2) {
        await saveDomainPolicy()
      }
      if (!activeGalleryDomain.value) {
        await saveGallerySiteSettings()
      }
      return
    }
    await saveSettings()
  } finally {
    sectionSaving.value[sectionKey] = false
  }
}

const saveAllSettings = async () => {
  await saveSettings()
  if (activeImageDomains.value.length >= 2 && domainPolicySnapshot.value !== buildDomainPolicySnapshot()) {
    await saveDomainPolicy()
  }
  if (!activeGalleryDomain.value && gallerySettingsSnapshot.value !== buildGallerySettingsSnapshot()) {
    await saveGallerySiteSettings()
  }
}

const confirmModalOpen = ref(false)
const confirmModalTitle = ref('')
const confirmModalMessage = ref('')
const confirmModalResolve = ref<((value: boolean) => void) | null>(null)

const askConfirm = (title: string, message: string): Promise<boolean> => {
  confirmModalTitle.value = title
  confirmModalMessage.value = message
  confirmModalOpen.value = true
  return new Promise((resolve) => {
    confirmModalResolve.value = resolve
  })
}

const onConfirmOk = () => {
  confirmModalOpen.value = false
  confirmModalResolve.value?.(true)
  confirmModalResolve.value = null
}

const onConfirmCancel = () => {
  confirmModalOpen.value = false
  confirmModalResolve.value?.(false)
  confirmModalResolve.value = null
}

const revokeTokens = async (type: 'guest' | 'all') => {
  const confirmMessage = type === 'all'
    ? '确定要禁用所有 Token 吗？此操作不可撤销。'
    : '确定要禁用所有游客 Token 吗？此操作不可撤销。'

  const confirmed = await askConfirm('确认批量禁用', confirmMessage)
  if (!confirmed) {
    return
  }

  revokingTokens.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/tokens/revoke`, {
      method: 'POST',
      credentials: 'include',
      body: { type }
    })

    if (response.success) {
      notification.success('操作成功', response.message)
    }
  } catch (error: any) {
    console.error('禁用 Token 失败:', error)
    notification.error('操作失败', error.data?.error || '无法禁用 Token')
  } finally {
    revokingTokens.value = false
  }
}

// P1-a: tg_auth_required 开启时自动联动 tg_bind_token_enabled
watch(() => settings.value.tg_auth_required_for_token, (required) => {
  if (required) {
    settings.value.tg_bind_token_enabled = true
  }
})

// Bot 未配置时强制关闭 TG 认证
watch(() => settings.value.bot_token_configured, (configured) => {
  if (!configured) {
    settings.value.tg_auth_enabled = false
  }
})

// ---- 域名管理 ----

const domains = ref<DomainItem[]>([])
const domainsLoading = ref(false)
const domainSaving = ref(false)
const domainDeleting = ref(false)
const showDomainModal = ref(false)
const showDeleteDomainModal = ref(false)
const deletingDomain = ref<DomainItem | null>(null)
const isEditMode = ref(false)
const editingDomainId = ref<number | null>(null)

const domainForm = ref({
  domain: '',
  port: null as number | null,
  domain_type: 'image',
  use_https: true,
  remark: ''
})

const domainTypeOptions = [
  { value: 'default', label: '默认域名（管理后台/API）' },
  { value: 'image', label: '图片域名（图片访问专用）' },
  { value: 'gallery', label: '画集域名（画集站点专用）' },
]

// 计算属性：默认域名列表
const defaultDomains = computed(() => domains.value.filter(d => d.domain_type === 'default'))

// 计算属性：图片域名列表
const imageDomains = computed(() => domains.value.filter(d => d.domain_type === 'image'))

// 计算属性：画集域名列表
const galleryDomains = computed(() => domains.value.filter(d => d.domain_type === 'gallery'))

// 计算属性：活跃画集域名（用于"进入画集管理"按钮）
const activeGalleryDomain = computed(() => galleryDomains.value.find(d => d.is_active))

// 画集管理入口（打开画集站点首页）
const gallerySiteEntryLoading = ref(false)
const openGallerySiteAdmin = async () => {
  gallerySiteEntryLoading.value = true
  try {
    // 1. 生成 SSO token（让画集域名自动建立管理员 session）
    const tokenRes = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/gallery-auth-token`, {
      method: 'POST',
      credentials: 'include'
    })
    // 2. 获取画集域名 URL
    const entryRes = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/gallery-site/entry`, {
      credentials: 'include'
    })
    if (!entryRes?.success || !entryRes.data?.url) {
      throw new Error(entryRes?.error || '获取画集域名失败')
    }
    // 3. 带 SSO token 打开画集站点（自动建立 session，管理按钮可见）
    let url = entryRes.data.url
    if (tokenRes?.success && tokenRes.data?.token) {
      url += `/gallery-site/admin?auth_token=${tokenRes.data.token}`
    }
    window.open(url, '_blank')
  } catch (e: any) {
    notification.error('操作失败', e.message || '无法打开画集站点')
  } finally {
    gallerySiteEntryLoading.value = false
  }
}

// 画集站点内联设置（无独立域名时在主站设置）
const gallerySiteSettings = ref({
  name: '',
  description: '',
  enabled: true,
})
const gallerySiteSettingsSaving = ref(false)

const loadGallerySiteSettings = async () => {
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/gallery-site/admin/settings`, {
      credentials: 'include'
    })
    if (res?.success && res.data) {
      gallerySiteSettings.value.name = res.data.gallery_site_name || ''
      gallerySiteSettings.value.description = res.data.gallery_site_description || ''
      gallerySiteSettings.value.enabled = String(res.data.gallery_site_enabled) !== '0'
      syncGallerySettingsSnapshot()
    }
  } catch {
    // 静默失败
  }
}

const saveGallerySiteSettings = async () => {
  gallerySiteSettingsSaving.value = true
  try {
    await $fetch(`${runtimeConfig.public.apiBase}/api/gallery-site/admin/settings`, {
      method: 'PUT',
      credentials: 'include',
      body: {
        gallery_site_name: gallerySiteSettings.value.name,
        gallery_site_description: gallerySiteSettings.value.description,
        gallery_site_enabled: gallerySiteSettings.value.enabled ? '1' : '0',
      }
    })
    syncGallerySettingsSnapshot()
    notification.success('保存成功', '画集站点设置已更新')
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法保存画集站点设置')
  } finally {
    gallerySiteSettingsSaving.value = false
  }
}

// 加载域名列表
const loadDomains = async () => {
  domainsLoading.value = true
  try {
    domains.value = await domainsApi.getDomains()
    syncDomainsSnapshot()
  } catch (e: any) {
    console.error('加载域名列表失败:', e)
  } finally {
    domainsLoading.value = false
  }
}

// 打开添加域名弹窗
const openAddDomainModal = () => {
  isEditMode.value = false
  editingDomainId.value = null
  domainForm.value = { domain: '', port: null, domain_type: 'image', use_https: true, remark: '' }
  showDomainModal.value = true
}

// 打开编辑域名弹窗
const openEditDomainModal = (d: DomainItem) => {
  isEditMode.value = true
  editingDomainId.value = d.id
  domainForm.value = {
    domain: d.domain,
    port: d.port || null,
    domain_type: d.domain_type,
    use_https: !!d.use_https,
    remark: d.remark || ''
  }
  showDomainModal.value = true
}

// 保存域名（统一处理添加和编辑）
const handleSaveDomain = async () => {
  if (!domainForm.value.domain.trim()) {
    notification.error('错误', '请输入域名')
    return
  }
  domainSaving.value = true
  try {
    if (isEditMode.value && editingDomainId.value) {
      await domainsApi.updateDomain(editingDomainId.value, {
        domain: domainForm.value.domain,
        port: domainForm.value.port,
        domain_type: domainForm.value.domain_type,
        use_https: domainForm.value.use_https,
        remark: domainForm.value.remark,
      })
      notification.success('更新成功', `域名 ${domainForm.value.domain} 已更新`)
    } else {
      await domainsApi.addDomain({
        domain: domainForm.value.domain,
        port: domainForm.value.port,
        domain_type: domainForm.value.domain_type,
        use_https: domainForm.value.use_https,
        remark: domainForm.value.remark,
      })
      notification.success('添加成功', `域名 ${domainForm.value.domain} 已添加`)
    }
    showDomainModal.value = false
    await loadDomains()
  } catch (e: any) {
    notification.error(isEditMode.value ? '更新失败' : '添加失败', e.message || '操作失败')
  } finally {
    domainSaving.value = false
  }
}

// 端口输入处理：空值转为 null
watch(() => domainForm.value.port, (val) => {
  if (val === 0 || val === '' || isNaN(val as any)) {
    domainForm.value.port = null
  }
})

// 切换域名启用/停用
const toggleDomainActive = async (d: DomainItem) => {
  try {
    await domainsApi.updateDomain(d.id, { is_active: !d.is_active })
    notification.success('已更新', `域名 ${d.domain} 已${d.is_active ? '停用' : '启用'}`)
    await loadDomains()
  } catch (e: any) {
    notification.error('操作失败', e.message || '无法更新域名状态')
  }
}

// 设为默认域名
const handleSetDefault = async (d: DomainItem) => {
  try {
    await domainsApi.setDefaultDomain(d.id)
    notification.success('已设置', `${d.domain} 已设为默认域名`)
    await loadDomains()
  } catch (e: any) {
    notification.error('操作失败', e.message || '无法设置默认域名')
  }
}

// 确认删除域名
const confirmDeleteDomain = (d: DomainItem) => {
  deletingDomain.value = d
  showDeleteDomainModal.value = true
}

// 删除域名
const handleDeleteDomain = async () => {
  if (!deletingDomain.value) return
  domainDeleting.value = true
  try {
    await domainsApi.deleteDomain(deletingDomain.value.id)
    notification.success('已删除', `域名 ${deletingDomain.value.domain} 已删除`)
    showDeleteDomainModal.value = false
    await loadDomains()
  } catch (e: any) {
    notification.error('删除失败', e.message || '无法删除域名')
  } finally {
    domainDeleting.value = false
  }
}

// ---- 域名场景路由 ----
const domainPolicy = ref<DomainPolicyForm>({
  guest: '',
  token: '',
  group: '',
  admin_default: '',
})
const policySaving = ref(false)

const domainsSnapshot = ref('')
const domainPolicySnapshot = ref('')
const gallerySettingsSnapshot = ref('')

const serializeValue = (value: any) => JSON.stringify(value)

const buildDomainsSnapshot = () => {
  const normalized = domains.value
    .map((d) => ({
      id: d.id,
      domain: d.domain,
      port: d.port || null,
      domain_type: d.domain_type,
      use_https: Boolean(d.use_https),
      is_active: Boolean(d.is_active),
      remark: d.remark || '',
    }))
    .sort((a, b) => a.id - b.id)
  return serializeValue(normalized)
}

const buildDomainPolicySnapshot = () => serializeValue({
  guest: domainPolicy.value.guest || '',
  token: domainPolicy.value.token || '',
  group: domainPolicy.value.group || '',
  admin_default: domainPolicy.value.admin_default || '',
})

const buildGallerySettingsSnapshot = () => serializeValue({
  name: gallerySiteSettings.value.name || '',
  description: gallerySiteSettings.value.description || '',
  enabled: Boolean(gallerySiteSettings.value.enabled),
})

const syncDomainsSnapshot = () => {
  domainsSnapshot.value = buildDomainsSnapshot()
}

const syncDomainPolicySnapshot = () => {
  domainPolicySnapshot.value = buildDomainPolicySnapshot()
}

const syncGallerySettingsSnapshot = () => {
  gallerySettingsSnapshot.value = buildGallerySettingsSnapshot()
}

const { dirtyMap, dirtyCount, isAnyDirty } = useSettingsDirtyState({
  current: settings,
  original: originalSettings,
  groups: sectionFieldGroups,
  extras: {
    domains: () => (
      domainsSnapshot.value !== buildDomainsSnapshot()
      || domainPolicySnapshot.value !== buildDomainPolicySnapshot()
      || gallerySettingsSnapshot.value !== buildGallerySettingsSnapshot()
    ),
  },
})

syncDomainsSnapshot()
syncDomainPolicySnapshot()
syncGallerySettingsSnapshot()

// 活跃图片域名（用于场景路由选项）
const activeImageDomains = computed(() => imageDomains.value.filter(d => d.is_active))

// 场景路由下拉选项
const domainPolicyOptions = computed(() => {
  const opts = [{ value: '', label: '随机选择' }]
  for (const d of activeImageDomains.value) {
    opts.push({ value: d.domain, label: d.domain })
  }
  return opts
})

// 加载域名策略
const loadDomainPolicy = async () => {
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/domains/policy`, {
      credentials: 'include'
    })
    if (res.success && res.data) {
      domainPolicy.value = {
        guest: res.data.guest || '',
        token: res.data.token || '',
        group: res.data.group || '',
        admin_default: res.data.admin_default || '',
      }
      syncDomainPolicySnapshot()
    }
  } catch (e: any) {
    console.error('加载域名策略失败:', e)
  }
}

// 保存域名策略
const saveDomainPolicy = async () => {
  policySaving.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/domains/policy`, {
      method: 'PUT',
      credentials: 'include',
      body: domainPolicy.value
    })
    if (res.success) {
      syncDomainPolicySnapshot()
      notification.success('保存成功', '域名场景路由策略已更新')
    }
  } catch (e: any) {
    notification.error('保存失败', e.data?.error || e.message || '无法保存域名策略')
  } finally {
    policySaving.value = false
  }
}

const scrollToSection = (key: SettingsSectionKey) => {
  activeSection.value = key
  if (!import.meta.client) return
  const target = document.getElementById(sectionDomId(key))
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

let sectionObserver: IntersectionObserver | null = null

const initSectionObserver = () => {
  if (!import.meta.client) return
  sectionObserver?.disconnect()
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
    if (!visible) return
    const id = visible.target.id
    const matched = sectionItems.find((item) => sectionDomId(item.key) === id)
    if (matched) {
      activeSection.value = matched.key
    }
  }, {
    root: null,
    rootMargin: '-15% 0px -65% 0px',
    threshold: [0.2, 0.4, 0.7],
  })

  for (const item of sectionItems) {
    const el = document.getElementById(sectionDomId(item.key))
    if (el) sectionObserver.observe(el)
  }
}

onMounted(async () => {
  await Promise.all([
    loadSettings(),
    loadDomains(),
    loadDomainPolicy(),
    loadGallerySiteSettings(),
    loadUpdateInfo(),
    loadUpdateStatus(),
  ])
  scheduleUpdateStatusPoll()
  await nextTick()
  initSectionObserver()
})

onBeforeUnmount(() => {
  clearUpdateStatusPoll()
  sectionObserver?.disconnect()
  sectionObserver = null
})
</script>
