# 域名配置系统深度分析报告

## 一、核心数据模型

### 1.1 数据库层 (system_settings / admin_config 表)

域名相关的配置项全部存储在 `admin_config` 表中（键值对），由 `database/settings.py` 的 `DEFAULT_SYSTEM_SETTINGS` 定义默认值：

| 键名 | 默认值 | 说明 |
|------|--------|------|
| `cloudflare_cdn_domain` | `''` | **唯一的域名字段**，存储纯主机名（如 `img.example.com`） |
| `cdn_enabled` | `'0'` | CDN 开关，`'1'` 启用 |
| `cloudflare_api_token` | `''` | Cloudflare API Token |
| `cloudflare_zone_id` | `''` | Cloudflare Zone ID |
| `cloudflare_cache_level` | `'aggressive'` | 缓存策略 |
| `cloudflare_browser_ttl` | `'14400'` | 浏览器 TTL |
| `cloudflare_edge_ttl` | `'2592000'` | 边缘 TTL |
| `cdn_redirect_enabled` | `'0'` | CDN 重定向开关 |
| `cdn_redirect_max_count` | `'2'` | 最大重定向次数 |
| `cdn_redirect_delay` | `'10'` | 新文件延迟重定向秒数 |
| `cdn_monitor_enabled` | `'0'` | CDN 监控开关 |
| `enable_cache_warming` | `'0'` | 缓存预热开关 |
| `enable_smart_routing` | `'0'` | 智能路由开关 |
| `fallback_to_origin` | `'1'` | 回源兜底开关 |

**关键限制：只有一个 `cloudflare_cdn_domain` 字段，系统只支持单域名。**

### 1.2 读写接口

- `get_system_setting(key)` → 单个设置读取（`database/settings.py:185`）
- `get_all_system_settings()` → 全量读取（`database/settings.py:200`）
- `update_system_settings(dict)` → 批量更新（`database/settings.py:242`）
- `get_public_settings()` → 公开设置（不含域名，`database/settings.py:315`）

## 二、域名使用的三种模式

系统通过 `cloudflare_cdn_domain` + `cdn_enabled` 组合判断当前模式：

| 模式 | 条件 | 行为 |
|------|------|------|
| **CDN 模式** | `domain` 非空 + `cdn_enabled=True` | 强制 HTTPS，使用配置域名，长缓存，CDN 重定向 |
| **直连模式** | `domain` 非空 + `cdn_enabled=False` | 使用配置域名，保持请求 scheme，短缓存 |
| **默认模式** | `domain` 为空 | 使用请求 Host 头，短缓存 |

## 三、各模块域名逻辑详解

### 3.1 utils.py — `get_domain()` 核心函数

**位置**: `utils.py:298-356`

这是整个系统的域名解析核心，被上传、图片访问、API 信息等多处调用。

```
PLACEHOLDER_FLOW_DIAGRAM
```

**数据流**:
1. 调用 `_get_effective_domain_settings()` 从数据库读取 `cloudflare_cdn_domain` 和 `cdn_enabled`
2. 带 1 秒 TTL 缓存（`_DOMAIN_SETTINGS_CACHE`），避免频繁查库
3. 根据 request 对象判断 scheme（CF-Visitor > X-Forwarded-Proto > http）
4. 根据是否配置域名选择 host（配置域名 > X-Forwarded-Host > Host 头 > request.host）
5. CDN 模式强制 https，其他模式保持请求 scheme
6. 支持 X-Forwarded-Prefix 前缀

**关键特征**:
- **只返回一个域名**，无法区分"图片访问域名"和"管理后台域名"
- request 为 None 时（Bot 场景），有域名则返回 `https://{domain}`，否则回退到 `http://{LOCAL_IP}:{PORT}`
- `clear_domain_cache()` 用于设置更新后立即生效

### 3.2 api/images.py — 图片访问路由

**位置**: `images.py:29-34` (`_get_domain_mode`) 和 `images.py:51-211` (`serve_image`)

**`_get_domain_mode()`**: 独立于 `get_domain()` 的域名模式判断函数，直接从数据库读取，返回 `(domain, cdn_enabled, cdn_mode)` 三元组。

**`serve_image()` 中的域名逻辑**:

1. **CDN 回源检测** (`images.py:73`): 通过 `CF-Connecting-IP` 头判断是否为 CDN 回源请求
2. **CDN 域名匹配** (`images.py:83-84`): `host == cdn_domain` 判断请求是否来自 CDN 域名
3. **CDN 重定向** (`images.py:104-123`):
   - 条件：`cdn_redirect_enabled` + 非 CDN 回源 + 非 CDN 域名访问 + 非新文件 + 重定向次数未超限 + CDN 模式
   - 重定向 URL: `https://{cdn_domain}/image/{encrypted_id}`
   - 使用 302 临时重定向
4. **缓存策略** (`images.py:195-203`):
   - CDN 模式：新文件 `max-age=300`，旧文件 `max-age=31536000, immutable`
   - 非 CDN 模式：`max-age=3600`

**`get_recent_api()`** (`images.py:245-292`):
- 使用 `get_domain(request)` 生成 `image_url`
- CDN 模式额外返回 `cdn_url = https://{cdn_domain}/image/{id}`

**`get_info()`** (`images.py:295-327`):
- 返回 `domain: get_domain(request)` 和 `cdn_domain: https://{cdn_domain}`

### 3.3 api/settings.py — 管理员设置 API

**位置**: `settings.py:44-55` (`_normalize_cdn_domain`)

**域名标准化逻辑**:
1. 去除首尾空白
2. 如果包含 `://`，用 `urlsplit` 提取 netloc
3. 去除路径、查询参数、锚点
4. 拒绝包含 `@` 的值（防止 userinfo 注入）
5. 返回纯主机名

**设置保存流程** (`settings.py:206-577`):
1. 前端 PUT 请求 → 验证 → `update_system_settings()`
2. 如果更新了 `cloudflare_cdn_domain` 或 `cdn_enabled`，调用 `clear_domain_cache()` 清除缓存
3. 响应中通过 `_format_settings_for_response()` 格式化返回

**`_format_settings_for_response()`** (`settings.py:58-136`):
- `cloudflare_cdn_domain` 直接返回字符串
- `cloudflare_api_token` 只返回 `_set` 布尔值（安全考虑）
- `cdn_enabled` 转为布尔值

### 3.4 services/cdn_service.py — CDN 服务

**位置**: `cdn_service.py:40-79` (`_get_effective_cdn_settings`)

**独立的配置缓存**: `_CDN_SETTINGS_CACHE`，1 秒 TTL，缓存以下字段：
- `cdn_enabled`, `monitor_enabled`, `cdn_domain`, `api_token`, `zone_id`, `cache_warming_enabled`

**CloudflareCDN 类** (`cdn_service.py:104-320`):
- `_refresh_config()`: 从数据库刷新配置到实例属性
- `probe_encrypted_id()`: 构造 `https://{cdn_domain}/image/{id}` 进行探测
- `purge_cache()`: 通过 Cloudflare API 清除缓存
- `check_cdn_status()`: 检查图片是否被 CDN 缓存

**CDN 监控线程** (`cdn_service.py:340-513`):
- 使用 PriorityQueue 实现延迟调度
- 指数退避重试（5s → 120s）
- Token-based 去重机制

### 3.5 services/file_service.py — 上传服务

**位置**: `file_service.py:58-184` (`process_upload`)

**域名相关**: `process_upload()` 本身不处理域名，只返回 `encrypted_id`。URL 生成由调用方（`api/upload.py`、`api/auth.py`）负责。

返回值:
```python
{
    'encrypted_id': encrypted_id,
    'file_size': ...,
    'filename': ...,
    'mime_type': ...
}
```

### 3.6 api/upload.py — 上传 API

**位置**: `upload.py:127-128`

```python
base_url = get_domain(request)
permanent_url = f"{base_url}/image/{result['encrypted_id']}"
```

**URL 生成逻辑**: 调用 `get_domain(request)` 获取基础 URL，拼接 `/image/{id}` 路径。

### 3.7 frontend/composables/useUpload.ts — 前端上传

**位置**: `useUpload.ts:80-98`

前端上传不直接处理域名。上传 URL 使用 `config.public.apiBase`（Nuxt 运行时配置），上传成功后的图片 URL 由后端 API 响应返回。

### 3.8 frontend/pages/admin/settings.vue — 前端设置页

**位置**: `settings.vue:760-813` (settings ref 定义)

前端只维护一个 `cloudflare_cdn_domain` 字符串字段。域名模式通过计算属性判断：

```typescript
const currentMode = computed(() => {
  if (hasDomain.value && cdnEnabled.value) return 'cdn'
  if (hasDomain.value && !cdnEnabled.value) return 'direct'
  return 'default'
})
```

UI 展示三种模式标签：CDN 加速 / 自定义域名 / 默认模式。

## 四、数据流总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        admin_config 表                          │
│  cloudflare_cdn_domain = "img.example.com"                     │
│  cdn_enabled = "1"                                              │
└──────────────┬──────────────────────────────────────────────────┘
               │
    ┌──────────┼──────────────────────────────────┐
    │          │                                   │
    ▼          ▼                                   ▼
 utils.py   cdn_service.py                    images.py
 _get_effective_  _get_effective_cdn_         _get_domain_mode()
 domain_settings() settings()
    │          │                                   │
    ▼          ▼                                   ▼
 get_domain() CloudflareCDN._refresh_config() serve_image()
    │          │                                   │
    ├──────────┼───────────────────────────────────┤
    │          │                                   │
    ▼          ▼                                   ▼
 upload.py  cdn_monitor_worker              CDN 重定向/缓存策略
 URL 生成   探测/预热/清除                   302 → https://{domain}/image/{id}
```

## 五、当前限制与多域名改造要点

### 5.1 单域名限制

1. **数据库层**: 只有一个 `cloudflare_cdn_domain` 键值对
2. **缓存层**: `_DOMAIN_SETTINGS_CACHE` 和 `_CDN_SETTINGS_CACHE` 都只缓存一个域名
3. **URL 生成**: `get_domain()` 只返回一个 base URL
4. **CDN 服务**: `CloudflareCDN` 实例只绑定一个域名
5. **前端**: settings.vue 只有一个域名输入框

### 5.2 域名读取点汇总（需改造）

| 文件 | 函数/位置 | 读取方式 | 用途 |
|------|-----------|----------|------|
| `utils.py:269-295` | `_get_effective_domain_settings()` | DB + 1s 缓存 | 域名+CDN状态 |
| `utils.py:298-356` | `get_domain(request)` | 调用上面函数 | URL 生成 |
| `images.py:29-34` | `_get_domain_mode()` | 直接 DB 查询 | 域名模式判断 |
| `cdn_service.py:40-79` | `_get_effective_cdn_settings()` | DB + 1s 缓存 | CDN 全量配置 |
| `cdn_service.py:126-139` | `CloudflareCDN._refresh_config()` | 调用上面函数 | CDN 实例配置 |
| `settings.py:266-268` | PUT handler | 前端提交 | 域名保存 |
| `settings.py:73` | `_format_settings_for_response()` | 从 settings dict | API 响应 |

### 5.3 域名使用点汇总（需改造）

| 文件 | 行号 | 使用方式 |
|------|------|----------|
| `upload.py:127-128` | `get_domain(request)` + `/image/{id}` | 上传后 URL |
| `images.py:47` | `get_domain(request)` | 404 页面 API base |
| `images.py:113` | `f"https://{cdn_domain}/image/{id}"` | CDN 重定向 URL |
| `images.py:253-266` | `get_domain(request)` + CDN URL | 最近上传列表 |
| `images.py:308-309` | `get_domain(request)` + CDN domain | 服务器信息 |
| `images.py:339` | `get_domain(request)` | 健康检查 |
| `images.py:358` | `get_domain(request)` | robots.txt sitemap |
| `cdn_service.py:217` | `f"https://{cdn_domain}/image/{id}"` | CDN 探测 URL |
| Bot handlers | `get_domain(None)` | Bot 回复中的图片 URL |

### 5.4 三处独立的配置缓存

1. **`utils.py:_DOMAIN_SETTINGS_CACHE`** — 域名 + cdn_enabled（1s TTL）
2. **`cdn_service.py:_CDN_SETTINGS_CACHE`** — CDN 全量配置（1s TTL）
3. **`cdn_service.py:CloudflareCDN._cfg_ts`** — CDN 实例级配置（1s TTL）

三处缓存独立运作，`clear_domain_cache()` 只清除第一处。

### 5.5 多域名改造核心挑战

1. **数据模型**: 需要从单键值对扩展为域名列表/表，每个域名需要独立的 CDN 配置
2. **域名选择逻辑**: `get_domain()` 需要支持根据请求 Host 匹配对应域名配置
3. **CDN 服务**: 需要支持多个 Zone ID / API Token 的场景（不同域名可能在不同 CF 账号）
4. **缓存一致性**: 三处缓存需要统一管理
5. **前端 UI**: 从单输入框改为域名列表管理
6. **向后兼容**: 需要迁移现有单域名配置到新数据结构
