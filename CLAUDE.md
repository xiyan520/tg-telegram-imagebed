# Telegram 云图床 Pro - 项目架构文档

> 大版本更新时同步更新 README.md

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask + Flask-CORS + waitress | 3.0 |
| 数据库 | SQLite3 (WAL模式) | 内置 |
| Bot SDK | python-telegram-bot | 21.0.1 |
| HTTP | requests + aiohttp | 2.31 / 3.9 |
| 前端框架 | Nuxt 3 (SPA, ssr=false) | 3.13 |
| UI | Nuxt UI (Tailwind CSS) | 2.18 |
| 状态管理 | Pinia | 2.2 |
| 工具库 | VueUse | 11.0 |
| 部署 | Docker 多阶段构建 | - |

## 目录结构

```
tg-telegram-imagebed/
├── main.py                    # 入口：Flask线程 + Bot线程（~230行）
├── requirements.txt
├── Dockerfile                 # 多阶段：node:20-alpine → python:3.11-slim
├── docker-compose.yml         # 单容器，端口18793，卷 ./data:/app/data
│
├── tg_imagebed/               # 后端 Python 包
│   ├── config.py              # 基础设施配置（路径/端口/日志，无业务配置）
│   ├── utils.py               # 工具函数（加密ID、MIME、缓存头、单实例锁）
│   ├── bot_control.py         # Bot Token热更新、重启信号（线程安全缓存）
│   ├── admin_module.py        # 管理员认证 + 统计/图片管理路由（Session Cookie）
│   ├── database/              # SQLite DAL 包（9张表，WAL模式，带重试装饰器）
│   │   ├── __init__.py        # 重导出全部公开函数，外部 import 零改动
│   │   ├── connection.py      # 连接管理 + 数据库初始化 + ALTER TABLE迁移
│   │   ├── files.py           # 文件 CRUD + 统计查询
│   │   ├── tokens.py          # Token 管理（用户 + 管理员）
│   │   ├── settings.py        # 系统设置 + 公告管理
│   │   ├── galleries.py       # 用户画集 + 访问控制 + 分享 + Token 授权
│   │   └── admin_galleries.py # 管理员画集（owner_type='admin'，无虚拟 token）
│   ├── bot/                   # Telegram Bot 包
│   │   ├── __init__.py        # 导出 start_telegram_bot_thread, _get/_set_bot_status
│   │   ├── state.py           # Bot 状态管理（全局状态字典 + 线程安全读写）
│   │   ├── media_batch.py     # 批量图片处理（media_group debounce 合并）
│   │   ├── handlers.py        # 消息处理器（/start + handle_photo）
│   │   └── runner.py          # Bot 主循环（轮询 + 指数退避 + 热重启）
│   ├── api/                   # Flask Blueprint 路由层
│   │   ├── __init__.py        # 4个蓝图注册：upload/images/admin/auth
│   │   ├── upload.py          # POST /api/upload（匿名上传，魔数校验）
│   │   ├── images.py          # GET /image/<id>（CDN重定向+ETag+Range+流式返回）
│   │   ├── admin.py           # /api/admin/* 入口（Session认证，副作用导入子模块）
│   │   ├── admin_setup.py     # 首次启动管理员设置
│   │   ├── admin_tokens.py    # Token 管理（CRUD + 批量操作 + 影响范围查询）
│   │   ├── admin_cdn.py       # CDN 管理
│   │   ├── admin_storage.py   # 存储配置
│   │   ├── admin_telegram.py  # Bot 配置
│   │   ├── admin_galleries.py # 管理员画集
│   │   ├── admin_helpers.py   # 共享辅助函数
│   │   ├── auth.py            # /api/auth/*（Token CRUD + Token上传）
│   │   ├── settings.py        # /api/admin/settings（系统设置）
│   │   └── galleries.py       # 用户画集API + 公开分享API
│   ├── services/              # 业务服务层
│   │   ├── __init__.py        # 导出 FileService, CDNService, TokenService
│   │   ├── file_service.py    # 上传核心：process_upload() + record_existing_telegram_file()
│   │   ├── cdn_service.py     # Cloudflare CDN集成（监控/预热/清除，队列调度）
│   │   └── token_service.py   # Token统一调度（级联删除/影响范围/批量操作）
│   └── storage/               # 多存储后端（策略模式）
│       ├── base.py            # 抽象基类 StorageBackend（put_bytes/download/delete）
│       ├── router.py          # StorageRouter（场景路由：guest/token/group/admin）
│       └── backends/
│           ├── telegram.py    # Telegram频道存储（默认）
│           ├── s3.py          # S3兼容存储
│           ├── local.py       # 本地文件系统
│           └── rclone.py      # Rclone远程存储
│
└── frontend/                  # Nuxt 3 SPA
    ├── nuxt.config.ts         # ssr:false, nitro preset:static
    ├── app.vue                # 根组件
    ├── middleware/auth.ts     # 管理后台路由守卫
    ├── plugins/api-error-handler.client.ts
    ├── stores/
    │   ├── auth.ts            # 管理员认证（login/logout/restoreAuth）
    │   ├── token.ts           # Token Vault（多Token本地管理+自动验证+无效清理）
    │   ├── adminUi.ts         # 侧边栏折叠状态
    │   └── notification.ts    # 通知队列（优先级/分组/自动超时）
    ├── composables/
    │   ├── useImageApi.ts     # 统计/图片管理
    │   ├── useUpload.ts       # 统一上传（自动检测模式+XHR进度）
    │   ├── useGalleryApi.ts   # 访客画廊API（含密码保护+访问控制错误解析）
    │   ├── useAdminGalleryApi.ts  # 管理员画廊API
    │   ├── useAdminMenu.ts    # 管理菜单数据
    │   ├── useLightToast.ts   # 轻量Toast通知
    │   ├── useNotification.ts # 通知composable
    │   └── useStatsRefresh.ts # 统计刷新事件总线
    ├── layouts/
    │   ├── default.vue        # 用户端布局（导航栏+网格背景）
    │   ├── admin.vue          # 管理后台布局（AdminShell）
    │   └── admin-login.vue    # 登录页布局
    ├── components/
    │   ├── admin/AdminShell.vue, AdminSidebar.vue, AdminTopbar.vue
    │   ├── album/             # 相册子组件
    │   │   ├── AlbumGalleryList.vue    # 画集列表（分页+创建入口）
    │   │   ├── AlbumGalleryDetail.vue  # 画集详情（图片网格+分享管理）
    │   │   ├── AlbumGalleryCard.vue    # 画集卡片
    │   │   ├── AlbumMyUploads.vue      # 我的上传（分页+灯箱）
    │   │   └── AlbumCreateGalleryModal.vue  # 创建画集弹窗
    │   ├── docs/Layout.vue, Sidebar.vue, EndpointCard.vue, ParamsTable.vue, CodeBlock.vue
    │   ├── GalleryLightbox.vue    # 灯箱（手势/缩放/键盘）
    │   ├── LightToast.vue         # 非阻塞通知
    │   ├── TokenVaultSwitcher.vue # Token管理器（验证+无效自动移除）
    │   ├── AnnouncementModal.vue
    │   └── AuthLoginModal.vue
    └── pages/
        ├── index.vue              # 首页（拖拽/粘贴上传）
        ├── setup.vue              # 首次启动管理员设置页
        ├── album.vue              # 相册（Token切换自动刷新+refreshKey机制）
        ├── gallery.vue, guest.vue # 重定向到 /album
        ├── docs.vue               # 交互式API文档
        ├── g/[token].vue          # 分享画廊（密码保护）
        ├── galleries/[token]/index.vue, [id].vue  # 全部分享
        └── admin/
            ├── index.vue          # 登录页
            ├── dashboard.vue      # 仪表板
            ├── images/index.vue   # 图片管理
            ├── tokens/index.vue, [id].vue  # Token管理（批量操作+交互保护）
            ├── galleries/index.vue, [id].vue  # 画集管理
            ├── settings.vue       # 系统设置
            ├── storage.vue        # 存储配置
            └── announcements/index.vue  # 公告管理
```
## 数据库模型（SQLite，9张表）

| 表名 | 主键 | 核心字段 | 用途 |
|------|------|---------|------|
| file_storage | encrypted_id(TEXT) | file_id, storage_backend, storage_key, cdn_cached, auth_token, access_count | 核心文件记录（含CDN状态/访问计数/多存储后端信息） |
| auth_tokens | token(TEXT) | upload_count, upload_limit, expires_at, is_active, description | Token认证（配额/有效期/使用统计） |
| galleries | id(AUTO) | owner_type, owner_token, access_mode, password_hash, share_token, cover_image | 画集（owner_type 区分 admin/token，支持 public/password/token/admin_only 访问模式） |
| gallery_images | (gallery_id, encrypted_id) | added_at | 画集-图片关联（CASCADE删除） |
| gallery_token_access | (gallery_id, token) | expires_at | 画集Token授权（CASCADE删除） |
| share_all_links | id(AUTO) | share_token, enabled, expires_at | 全局分享链接 |
| announcements | id(AUTO) | enabled, content | 系统公告 |
| admin_config | key(TEXT) | value | 管理员配置（用户名/密码哈希） |
| system_settings | key(TEXT) | value | 系统设置（运行时可修改，见下方配置清单） |

### 数据库配置

```
PRAGMA foreign_keys = ON       -- 启用外键约束
PRAGMA busy_timeout = 5000     -- 5秒锁超时
PRAGMA journal_mode = WAL      -- WAL模式（并发读写）
db_retry(max_attempts=3, base_delay=0.1, max_delay=2.0)  -- 指数退避重试
```

### 迁移策略

- `PRAGMA table_info()` 检查列存在性 → `ALTER TABLE ADD COLUMN` 增量迁移
- galleries 表重建迁移：关闭FK → 重命名旧表 → 创建新表 → 迁移数据 → 删除旧表 → 恢复FK

## 系统设置配置项（system_settings 表）

| 分类 | 键名 | 默认值 | 说明 |
|------|------|--------|------|
| Bot | telegram_bot_token | - | Telegram Bot Token（敏感） |
| 上传策略 | guest_upload_policy | open | open/token_only/admin_only |
| 上传策略 | guest_token_generation_enabled | 1 | 允许前端生成Token |
| 上传策略 | max_file_size_mb | 20 | 最大文件大小MB |
| 上传策略 | daily_upload_limit | 0 | 每日上传限制（0=无限） |
| Token | guest_token_max_upload_limit | 1000 | 游客Token最大上传数 |
| Token | guest_token_max_expires_days | 365 | 游客Token最大有效期天数 |
| 存储 | storage_active_backend | telegram | 活跃存储后端 |
| 存储 | storage_config_json | - | 存储后端配置JSON（敏感） |
| 存储 | storage_upload_policy_json | - | 上传策略JSON |
| CDN | cdn_enabled | 0 | Cloudflare CDN开关 |
| CDN | cloudflare_cdn_domain | - | CDN域名 |
| CDN | cloudflare_api_token | - | API Token（敏感） |
| CDN | cdn_redirect_enabled | 0 | CDN重定向开关 |
| 群组 | group_upload_admin_only | 0 | 群组上传仅管理员 |
| 群组 | group_admin_ids | - | 管理员ID列表（逗号分隔） |
| 同步 | tg_sync_delete_enabled | 1 | 删除时同步删除TG消息 |

## 启动流程

```
main()
├─ acquire_lock()                    # 单实例检查（文件锁）
├─ init_database()                   # 表创建(IF NOT EXISTS) + ALTER TABLE迁移 + 索引
├─ init_system_settings()            # 系统设置默认值初始化
├─ start_cdn_monitor()               # CDN监控线程（可选，队列调度）
├─ Thread(Flask/waitress)            # Web线程 :18793（4线程）
│   ├─ ProxyFix中间件
│   ├─ CORS分层策略（管理员API严格/公共API宽松）
│   └─ 注册蓝图：upload/images/admin/auth
└─ Thread(TelegramBot)               # Bot线程（独立运行，失败不影响Web）
    ├─ 轮询获取更新
    ├─ 指数退避重试（5s → 120s）
    └─ 409冲突检测 + 热重启支持
```

首次启动时，前端检测到 admin_config 表中无 username/password_hash，
自动重定向到 /setup 页面完成管理员账号设置。

## 关键业务流程

**上传**: 请求 → 魔数校验 → 权限检查 → StorageRouter.resolve_upload_backend(scene) → backend.put_bytes() → encrypt_file_id() → save_file_info() → CDN监控队列

**访问**: GET /image/{id} → DB查询 → CDN重定向判断 → ETag/304 → backend.download() → 流式返回（CDN模式长缓存/普通模式短缓存）

**认证**: 管理员=Session Cookie(@login_required) | 访客=Bearer Token(verify_auth_token) | 匿名=无认证（可关闭）

**Token级联删除**: file_storage.auth_token置空 → galleries.owner_token置空 → gallery_token_access清理 → auth_tokens删除

## 存储架构（策略模式）

```
StorageBackend (base.py)          ← 抽象接口: put_bytes/download/delete/healthcheck
  ├── TelegramBackend             ← 默认，通过Bot API上传到频道
  ├── S3Backend                   ← AWS S3/MinIO等兼容存储
  ├── LocalBackend                ← 本地文件系统
  └── RcloneBackend               ← Rclone支持的所有远程存储

StorageRouter (router.py)
  ├── 配置来源: 数据库 > 默认(telegram)
  ├── 场景路由: guest/token/group/admin → 不同后端
  ├── 实例缓存: 5秒TTL自动刷新
  └── 环境变量解析: env:VAR_NAME 引用
```

## 模块依赖关系

```
main.py (入口)
├─ config.py (基础配置：路径/端口/密钥)
├─ utils.py (工具函数：加密/MIME/缓存头/锁)
├─ database/ (数据访问层，参数化查询，db_retry装饰器)
├─ services/ (业务服务层)
│  ├─ file_service.py → storage/router.py → backends/*
│  ├─ cdn_service.py → database/settings
│  └─ token_service.py → database/tokens + files + galleries
├─ api/ (路由层，Blueprint)
│  ├─ upload/images/auth/galleries → services + database
│  └─ admin_*.py → admin_module.py(@login_required)
├─ bot/ (Telegram Bot，独立线程)
│  └─ handlers → services/file_service
└─ bot_control.py (Bot Token热更新)
```

依赖方向：API → Services → Database（单向，无循环依赖）

## 前端架构要点

**Token Vault 机制**（stores/token.ts）：
- 多Token本地管理，localStorage持久化（token_vault_v1）
- 旧版单Token自动迁移（guest_token → vault）
- 验证时区分 tokenInvalid（后端确认无效）vs 网络错误（不自动移除）
- verifyToken() 标记 `err.tokenInvalid = true` 仅在后端返回 `valid=false` 时

**Token切换刷新**（pages/album.vue）：
- watch(store.token) → refreshKey++ → 子组件 :key 绑定强制重建
- 子组件 onMounted 重新触发数据加载

**管理后台Token管理**（pages/admin/tokens/index.vue）：
- 批量操作：checkbox全选/单选 → 批量启用/禁用/删除
- 交互保护：创建后未复制Token关闭弹窗需确认、禁用需确认、删除显示影响范围
- 影响范围查询：GET /api/admin/tokens/{id}/impact → 关联图片数/画集数/授权数

## 编码规范

- 后端注释语言：中文
- 前端注释语言：中文
- 代码风格：后端PEP8，前端Vue3 Composition API + TypeScript
- 环境变量：仅 HTTP_PROXY/HTTPS_PROXY（系统代理），所有业务配置通过管理后台（数据库）管理
- 数据路径固定为 ./data/（DATABASE_PATH、LOG_FILE、.secret_key）
- 数据库迁移：init_database()中PRAGMA table_info + ALTER TABLE手动迁移
- 错误处理：后端db_retry装饰器处理SQLite锁，前端全局api-error-handler插件
- JSON响应格式统一：`{ success: bool, data/error: ... }`
- SQL安全：全部使用 `?` 参数化查询，无字符串拼接

## 已知架构问题

（历史问题已全部解决）

1. ~~**密码哈希不安全**~~ — 已替换为 werkzeug.security pbkdf2:sha256
2. ~~**file_service.py中upload_to_telegram()死代码**~~ — 已删除
3. ~~**Flask开发服务器用于生产**~~ — 已替换为 waitress
4. ~~**main.py过于臃肿(1017行)**~~ — Bot逻辑已拆分到 tg_imagebed/bot/（main.py ~230行）
5. ~~**SQLite未启用WAL模式**~~ — 已在 get_connection() 中启用

**待改进项（非阻塞）：**
- Token验证逻辑在 auth.py 和 galleries.py 中有重复，可提取到 auth_helpers.py
- 缺少审计日志表（管理员操作无记录）
- Bot仅支持Polling模式，未支持Webhook
- 文件删除为硬删除，无软删除机制

## 部署

- Docker多阶段构建：node:20-alpine(前端generate) → python:3.11-slim(后端)
- 单容器单进程多线程，端口18793，waitress 4线程
- 数据持久化：./data:/app/data（SQLite数据库+日志+密钥）
- 健康检查：GET /api/health（docker-compose 30秒间隔）
- 无需 .env 文件，所有业务配置通过管理后台设置
- 首次启动访问浏览器完成管理员账号设置
