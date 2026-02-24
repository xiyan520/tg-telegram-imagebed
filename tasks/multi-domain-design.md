# 多域名系统架构设计

## 一、需求概述

1. 后台设置一个**默认域名**（管理后台、API、非图片访问）
2. 支持添加**多个图片域名**（专用于图片访问）
3. 上传后返回的 URL 使用图片域名
4. 默认域名和图片域名**分开显示**
5. 图片**只允许通过图片域名打开**（域名访问控制）

## 二、数据库设计

### 2.1 新建 `custom_domains` 表

```sql
CREATE TABLE IF NOT EXISTS custom_domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    domain_type TEXT NOT NULL DEFAULT 'image',  -- 'default' | 'image'
    is_active INTEGER DEFAULT 1,
    use_https INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    remark TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**约束规则**:
- `domain_type='default'` 最多只能有一条记录
- `domain_type='image'` 可以有多条
- `domain` 字段 UNIQUE，不允许重复
- 同一个域名不能同时是 default 和 image（如需要，可以添加两条记录）

### 2.2 新增系统设置项

在 `DEFAULT_SYSTEM_SETTINGS` 中添加：

| 键名 | 默认值 | 说明 |
|------|--------|------|
| `image_domain_restriction_enabled` | `'0'` | 图片域名限制开关（开启后图片只能通过图片域名访问） |

### 2.3 数据迁移

在 `init_database()` 中添加迁移逻辑：
- 如果 `custom_domains` 表不存在，创建它
- 如果 `cloudflare_cdn_domain` 有值且 `custom_domains` 表为空，将其迁移为一条 `domain_type='image'` 的记录
- 原有 CDN 设置（api_token, zone_id 等）保持不变，继续作为全局 CDN 配置

## 三、后端 API 设计

### 3.1 新建 `database/domains.py` — 域名 DAL

```python
# 核心函数
get_all_domains() -> List[Dict]           # 获取所有域名
get_domains_by_type(domain_type) -> List   # 按类型获取
get_active_image_domains() -> List[Dict]   # 获取所有活跃图片域名
get_default_domain() -> Optional[Dict]     # 获取默认域名
add_domain(domain, domain_type, ...) -> id # 添加域名
update_domain(id, ...) -> bool             # 更新域名
delete_domain(id) -> bool                  # 删除域名
set_default_domain(id) -> bool             # 设为默认（清除旧默认）
get_random_image_domain() -> Optional[str] # 随机获取一个活跃图片域名
```

### 3.2 新建 `api/admin_domains.py` — 管理员域名 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/domains` | 获取所有域名列表 |
| POST | `/api/admin/domains` | 添加域名 |
| PUT | `/api/admin/domains/<id>` | 更新域名信息 |
| DELETE | `/api/admin/domains/<id>` | 删除域名 |
| PUT | `/api/admin/domains/<id>/set-default` | 设为默认域名 |

### 3.3 公开 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/public/domains` | 获取活跃图片域名列表（供前端选择） |

### 3.4 修改现有模块

#### `utils.py` — 新增 `get_image_domain()`

```python
def get_image_domain(request=None) -> str:
    """获取图片域名（用于生成图片URL）
    优先级：活跃图片域名（随机） > 默认域名 > get_domain(request) 降级
    """
```

#### `api/images.py` — 域名访问控制

在 `serve_image()` 开头添加域名校验：
```python
# 如果开启了图片域名限制
if image_domain_restriction_enabled:
    host = request.headers.get('Host', '')
    if not is_allowed_image_domain(host):
        return Response('Forbidden: use image domain', status=403)
```

#### `api/upload.py` — URL 生成改用图片域名

```python
# 原: base_url = get_domain(request)
# 新: base_url = get_image_domain(request)
```

同样修改 `api/auth.py` 中的 Token 上传 URL 生成。

#### `api/images.py` — 列表/信息 API

`get_recent_api()` 和 `get_info()` 中的 URL 生成也改用 `get_image_domain()`。

## 四、前端设计

### 4.1 管理后台 — 域名管理区域

在 `pages/admin/settings.vue` 的域名配置区域改造：

```
┌─────────────────────────────────────────────┐
│ 域名管理                                      │
├─────────────────────────────────────────────┤
│                                              │
│ 默认域名（管理后台/API）                        │
│ ┌──────────────────────────────┐             │
│ │ admin.example.com     [默认] │  [删除]      │
│ └──────────────────────────────┘             │
│                                              │
│ 图片域名（图片访问专用）                        │
│ ┌──────────────────────────────┐             │
│ │ img1.example.com    [活跃]   │  [删除]      │
│ │ img2.example.com    [活跃]   │  [删除]      │
│ │ img3.example.com    [停用]   │  [删除]      │
│ └──────────────────────────────┘             │
│                                              │
│ [+ 添加域名]                                  │
│                                              │
│ ☐ 开启图片域名限制（图片只能通过图片域名访问）    │
│                                              │
├─────────────────────────────────────────────┤
│ CDN 配置（全局）                               │
│ ... 保持现有 CDN 配置不变 ...                   │
└─────────────────────────────────────────────┘
```

### 4.2 上传结果 URL

上传成功后，后端返回的 URL 已使用图片域名，前端直接展示即可。

### 4.3 composable — `useDomainsApi.ts`

```typescript
// 管理员域名管理 API
const getDomains = () => $fetch('/api/admin/domains')
const addDomain = (data) => $fetch('/api/admin/domains', { method: 'POST', body: data })
const updateDomain = (id, data) => $fetch(`/api/admin/domains/${id}`, { method: 'PUT', body: data })
const deleteDomain = (id) => $fetch(`/api/admin/domains/${id}`, { method: 'DELETE' })
const setDefault = (id) => $fetch(`/api/admin/domains/${id}/set-default`, { method: 'PUT' })
```

## 五、缓存策略

### 5.1 新增域名缓存

在 `utils.py` 中添加域名列表缓存（与现有 `_DOMAIN_SETTINGS_CACHE` 类似）：

```python
_DOMAINS_CACHE = {
    "ts": 0.0,
    "image_domains": [],    # 活跃图片域名列表
    "default_domain": "",   # 默认域名
}
```

TTL: 1 秒，与现有缓存一致。

### 5.2 缓存清除

新增 `clear_domains_cache()` 函数，在域名增删改时调用。
同时更新 `clear_domain_cache()` 也清除新缓存。

## 六、向后兼容

1. 原有 `cloudflare_cdn_domain` 设置保留，但标记为 deprecated
2. `get_domain()` 函数保持不变（用于管理后台等非图片场景）
3. 新增 `get_image_domain()` 专用于图片 URL 生成
4. 如果 `custom_domains` 表为空，所有行为降级到原有逻辑
5. CDN 配置（api_token, zone_id 等）保持全局，不按域名拆分

## 七、文件变更清单

### 新建文件
- `tg_imagebed/database/domains.py` — 域名 DAL
- `tg_imagebed/api/admin_domains.py` — 域名管理 API
- `frontend/composables/useDomainsApi.ts` — 前端域名 API

### 修改文件
- `tg_imagebed/database/__init__.py` — 导出域名函数
- `tg_imagebed/database/connection.py` — 添加 custom_domains 表创建 + 迁移
- `tg_imagebed/database/settings.py` — 添加新设置项默认值
- `tg_imagebed/api/__init__.py` — 注册域名 API 路由（挂载到 admin_bp）
- `tg_imagebed/api/images.py` — 添加域名访问控制 + URL 生成改用图片域名
- `tg_imagebed/api/upload.py` — URL 生成改用图片域名
- `tg_imagebed/api/auth.py` — Token 上传 URL 生成改用图片域名
- `tg_imagebed/api/settings.py` — 添加新设置项到响应格式
- `tg_imagebed/utils.py` — 新增 get_image_domain() + 域名缓存
- `frontend/pages/admin/settings.vue` — 域名管理 UI 改造
