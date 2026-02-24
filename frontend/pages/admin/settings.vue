<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">系统设置</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">配置域名、CDN 加速和上传策略</p>
      </div>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="outline"
        :loading="loading"
        @click="loadSettings"
      >
        刷新
      </UButton>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !settingsLoaded" class="flex justify-center py-12">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else>
      <!-- 域名配置 -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-stone-500 to-stone-600 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:globe-alt" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-stone-900 dark:text-white">域名配置</h3>
                <p class="text-xs text-stone-500 dark:text-stone-400">配置图床访问域名</p>
              </div>
            </div>
            <!-- 当前模式标签 -->
            <div
              class="px-3 py-1.5 rounded-full text-xs font-medium"
              :class="currentModeClass"
            >
              {{ currentModeLabel }}
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="图床域名">
            <UInput v-model="settings.cloudflare_cdn_domain" placeholder="例如: img.example.com" />
            <template #hint>
              <span class="text-xs text-stone-500">用于生成图片链接的域名，留空则使用当前访问域名</span>
            </template>
          </UFormGroup>

          <!-- 模式说明 -->
          <div class="p-4 rounded-xl" :class="currentModeBackground">
            <div class="flex items-start gap-3">
              <UIcon :name="currentModeIcon" class="w-5 h-5 flex-shrink-0 mt-0.5" :class="currentModeIconColor" />
              <div>
                <p class="font-medium" :class="currentModeTitleColor">{{ currentModeTitle }}</p>
                <p class="text-sm mt-1" :class="currentModeDescColor">{{ currentModeDescription }}</p>
              </div>
            </div>
          </div>
        </div>
      </UCard>

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
        </div>
      </UCard>

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

      <!-- 保存按钮 -->
      <div class="flex justify-end gap-3 pt-4">
        <UButton color="gray" variant="outline" @click="resetSettings">
          重置
        </UButton>
        <UButton color="primary" :loading="saving" @click="saveSettings">
          <template #leading>
            <UIcon name="heroicons:check" />
          </template>
          保存设置
        </UButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const loading = ref(false)
const saving = ref(false)
const revokingTokens = ref(false)
const settingsLoaded = ref(false)

const settings = ref({
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
})

const originalSettings = ref<typeof settings.value | null>(null)

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

// 域名模式计算属性
const hasDomain = computed(() => !!settings.value.cloudflare_cdn_domain?.trim())

const proxyPlaceholder = computed(() => {
  if (settings.value.proxy_url_set) return '已设置（留空清除，回退到环境变量）'
  if (settings.value.proxy_env_set) return '环境变量已配置（此处可覆盖）'
  return 'http://host:port'
})
const cdnEnabled = computed(() => settings.value.cdn_enabled)

// 当前模式: cdn | direct | default
const currentMode = computed(() => {
  if (hasDomain.value && cdnEnabled.value) return 'cdn'
  if (hasDomain.value && !cdnEnabled.value) return 'direct'
  return 'default'
})

const currentModeLabel = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'CDN 加速'
    case 'direct': return '自定义域名'
    default: return '默认模式'
  }
})

const currentModeClass = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    case 'direct': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    default: return 'bg-stone-100 text-stone-600 dark:bg-neutral-700 dark:text-stone-400'
  }
})

const currentModeBackground = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'bg-green-50 dark:bg-green-900/20'
    case 'direct': return 'bg-blue-50 dark:bg-blue-900/20'
    default: return 'bg-stone-50 dark:bg-neutral-800'
  }
})

const currentModeIcon = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'heroicons:bolt'
    case 'direct': return 'heroicons:globe-alt'
    default: return 'heroicons:server'
  }
})

const currentModeIconColor = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'text-green-500'
    case 'direct': return 'text-blue-500'
    default: return 'text-stone-400'
  }
})

const currentModeTitleColor = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'text-green-800 dark:text-green-200'
    case 'direct': return 'text-blue-800 dark:text-blue-200'
    default: return 'text-stone-700 dark:text-stone-300'
  }
})

const currentModeDescColor = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'text-green-600 dark:text-green-300'
    case 'direct': return 'text-blue-600 dark:text-blue-300'
    default: return 'text-stone-500 dark:text-stone-400'
  }
})

const currentModeTitle = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return 'CDN 加速模式'
    case 'direct': return '自定义域名模式'
    default: return '默认模式'
  }
})

const currentModeDescription = computed(() => {
  switch (currentMode.value) {
    case 'cdn': return '图片将通过 Cloudflare CDN 加速访问，降低源站压力并提升全球访问速度'
    case 'direct': return '图片链接使用自定义域名，直接访问源站，无 CDN 缓存加速'
    default: return '使用当前访问域名生成图片链接，适合本地开发或单域名部署场景'
  }
})

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
    notification.info('已重置', '设置已恢复到上次保存的状态')
  }
}

const revokeTokens = async (type: 'guest' | 'all') => {
  const confirmMessage = type === 'all'
    ? '确定要禁用所有 Token 吗？此操作不可撤销。'
    : '确定要禁用所有游客 Token 吗？此操作不可撤销。'

  if (!confirm(confirmMessage)) {
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

onMounted(() => {
  loadSettings()
})
</script>
