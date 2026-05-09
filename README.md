# tg-telegram-imagebed

基于 Telegram 存储的单进程图床服务，后端使用 Flask，前端使用 Nuxt 静态构建，支持管理后台、Token 上传、TG 认证、画集分享、Cloudflare CDN，以及按场景切换的多存储后端。

项目当前的核心是“内建存储驱动 + 后台配置 + 第三方生态适配”，不是运行时自动发现的通用插件平台。也就是说，项目本身提供的是内建驱动和社区生态接入点，而不是可随意热插拔的 Python 插件总线。

## 你先看这个

> [!IMPORTANT]
> - 业务配置默认走管理后台和数据库，不是传统 `.env` 驱动模式。
> - 当前上传入口只接受图片文件，不是任意文件床。
> - Telegram 存储默认可用，但超过约 `20 MB` 的大文件想走稳，建议补齐 `API ID + API Hash` 让后端自动切到 Kurigram / MTProto。
> - 如果你前面挂了 Nginx、宝塔、Ingress、CDN 回源之类的反向代理，出现 `413 Request Entity Too Large`，大概率不是项目炸了，是你的网关体积限制没放开。相关社区反馈见 [Issue #19](https://github.com/xiyan520/tg-telegram-imagebed/issues/19)。

## 功能概览

- Telegram 图床主链路，支持 Bot API 和 Kurigram / MTProto 双通道。
- 内建 4 种存储驱动：`telegram`、`local`、`s3`、`rclone`。
- 上传场景路由：可分别为 `guest / token / group / admin` 指定不同后端。
- 管理后台：系统设置、存储配置、Token 管理、CDN 配置、画集管理、应用更新。
- 游客上传、Token 上传、TG 登录绑定、TG 用户限额与会话控制。
- Telegram Bot：轮询 / Webhook、群组上传、私聊上传、上传历史、删除控制。
- Cloudflare CDN：缓存监控、重定向、延迟回源、图片专用域名限制。
- 画集系统：公开 / 私有 / Token / 密码访问模式。
- 前端内置 `/docs` 文档页和 `/api/health` 健康检查。

## 架构说明

项目运行形态比较直接：

- Flask 提供 API 和图片访问。
- Nuxt 前端构建为静态文件后，由 Flask 同端口托管。
- Telegram Bot 在线程中运行，不影响 Web 服务主流程。
- 存储由 `StorageRouter` 按配置选择后端，并把每条文件记录绑定到具体后端。

这意味着两件事：

1. 旧文件不会因为你切换了活跃后端就“失忆”，因为每条记录都记着自己的 `storage_backend`。
2. README 里凡是写“插件”的地方，都应该区分清楚“项目内建存储驱动”和“社区外部客户端 / CMS 适配插件”。

## 快速开始

### 方式一：直接用仓库自带 Docker Compose

```bash
git clone https://github.com/xiyan520/tg-telegram-imagebed.git
cd tg-telegram-imagebed
docker compose up -d --build
```

默认对外端口是 `18793`，启动后访问：

```text
http://127.0.0.1:18793
```

首次进入会进入管理员初始化流程。完成后按下面顺序配置最稳：

1. 创建管理员账号。
2. 进入“存储配置”，先把 Telegram 后端配起来。
3. 填入 `Bot Token` 和目标 `chat_id`。
4. 如果你要稳定处理 `20 MB+` 图片，顺手把 `API ID`、`API Hash` 也补上。
5. 按需配置游客上传策略、Token、TG 认证、CDN、画集站点等。

### 方式二：本地手动运行

要求：

- Python `3.11`
- Node.js `20`
- npm

后端：

```bash
pip install -r requirements.txt
python main.py
```

前端静态构建：

```bash
cd frontend
npm install
npm run generate
```

注意：前端构建产物必须在 `frontend/.output/public`。你要是只跑了 `python main.py`，没构建前端，后端能起来，但首页会直接告诉你“前端文件未找到”。

## 配置模型

### 1. 业务配置

绝大多数配置都保存在数据库 `admin_config` 表里，通过管理后台修改，包括：

- Telegram Bot 配置
- 存储后端与上传路由策略
- 最大文件大小
- 游客上传策略与 Token 限制
- TG 认证
- 群组 / 私聊上传
- Cloudflare CDN
- 画集站点
- SEO / 应用更新

### 2. 环境变量

环境变量不是完全没用，但现在主要承担“基础设施兜底”角色：

| 变量名 | 用途 | 说明 |
| --- | --- | --- |
| `ALLOWED_ORIGINS` | 管理后台 / TG 认证跨域白名单 | 默认 `*` 仅对公共 API 宽松，管理员接口仍会退回本地白名单 |
| `HTTP_PROXY` / `HTTPS_PROXY` | 系统代理 | 后端请求 Telegram / 外部服务时可复用 |
| `BOT_TOKEN` / `TELEGRAM_BOT_TOKEN` | Bot Token 兜底 | 数据库未配置时才会回退读取 |

另外，存储配置 JSON 里支持 `env:VAR_NAME` 形式引用环境变量。

### 3. 数据目录

请务必持久化 `./data`，里面至少有这些关键文件：

| 路径 | 说明 |
| --- | --- |
| `data/telegram_imagebed.db` | SQLite 数据库 |
| `data/telegram_imagebed.log` | 运行日志 |
| `data/.secret_key` | 会话与密钥持久化文件 |
| `data/uploads/` | 使用 `local` 后端时的本地存储目录 |
| `data/tmp/` | Kurigram 大文件下载的临时目录 |

## 存储后端

### 已内建的驱动

| 驱动 | 标识 | 说明 | 额外注意 |
| --- | --- | --- | --- |
| Telegram | `telegram` | 默认主链路，支持 Bot API / Kurigram | `chat_id` 必填；大文件建议配置 `api_id + api_hash` |
| Local | `local` | 保存到服务器本地目录 | 需要保证路径可写 |
| S3 Compatible | `s3` | 适配 AWS S3、MinIO、R2、OSS 等 | 仓库默认依赖里**没有** `boto3`，需额外安装 |
| rclone | `rclone` | 复用 rclone 支持的远程存储 | 运行环境内必须已有 `rclone` 二进制和 remote 配置 |

### Telegram 大文件说明

Telegram 后端实际有两条通道：

- 小文件优先走 Bot API。
- 文件大于约 `20 MB` 且你配置了 `API ID + API Hash` 时，后端会自动切到 Kurigram / MTProto。

如果你只配置了 `Bot Token + chat_id`：

- 项目仍然能正常工作。
- 但大文件上传能力会受 Bot API 限制影响，稳定性和上限不如 MTProto 通道。

### 上传场景路由

后台可分别为以下场景指定目标后端：

- `guest`
- `token`
- `group`
- `admin`

管理员上传还可以在允许列表内手动选后端，这个设计比“全局只有一个存储桶”灵活得多。

## 支持的图片格式

当前上传链路会做扩展名白名单和魔数校验，默认支持：

```text
jpg, jpeg, png, gif, webp, bmp, avif, tiff, tif, ico
```

注意：

- 项目当前不是任意文件托管方案。
- 默认也不接受 `svg`。
- 反代和 Telegram 配额是两码事，别看后台把大小调大了，就以为外层网关也会自动放行。

## API 与页面入口

| 路径 | 说明 |
| --- | --- |
| `/` | 前端首页 |
| `/docs` | 内置 API 文档页 |
| `/api/health` | 健康检查 |
| `/api/upload` | 匿名上传 |
| `/api/auth/upload` | Token 上传 |
| `/api/admin/upload` | 管理员上传 |
| `/image/<encrypted_id>` | 图片访问入口 |

更多接口请直接查看站内 `/docs` 页面，并以页面内容为准。

## Cloudflare CDN

项目支持 Cloudflare CDN，但不是只填个域名就算完事。要想用顺手，至少得搞明白三层逻辑：

1. 后台里要开启 CDN 并填对域名 / Token。
2. Cloudflare 侧要给 `/image/*` 做缓存规则。
3. 如果开启了 CDN 重定向，项目会根据缓存状态、新上传延迟时间等条件决定是否 302 到 CDN 域名。

建议你额外注意：

- 新上传文件默认会有一段短缓存 / 延迟回源窗口。
- 图片域名限制和管理后台域名不是一个概念，别配串了。
- 如果你前面还有反代，上传失败优先检查网关体积限制而不是瞎怀疑 Cloudflare。

## 第三方生态与适配插件

### 1. Typecho 插件：PicUp

社区已经有现成的 Typecho 适配插件，可直接把本项目当作上传后端之一使用。

- 仓库：<https://github.com/lhl77/Typecho-Plugin-PicUp>
- 文档：<https://blog.lhl.one/artical/1026.html>
- 相关讨论：<https://github.com/xiyan520/tg-telegram-imagebed/issues/20>

根据 issue 和作者文档，`PicUp` 已支持 `tgimagebed` 驱动，覆盖匿名上传和 Token 上传场景。

### 2. GioPic / fileup.dev

`fileup.dev` 对应的是 GioPic 浏览器端生态，定位是“多节点上传 + 自定义插件”的客户端方案：

- 官网：<https://fileup.dev/>

目前更合适的表述是：

- 它属于第三方客户端生态。
- 它支持自定义插件 / 节点扩展。
- 是否内置了针对 `tg-telegram-imagebed` 的现成适配，取决于 GioPic 侧的发布版本和插件实现。

因此，更准确的描述是“可作为第三方适配入口”，而不是“本项目官方内置插件”。

## 注意事项

### 1. `413 Request Entity Too Large`

这个报错通常有 3 个来源：

- 项目后台设置里的 `max_file_size_mb`
- Telegram 上传链路本身的限制
- 你前面的 Nginx / Ingress / 面板网关体积限制

如果你用了 Nginx，至少确认类似配置已放开：

```nginx
client_max_body_size 100M;
```

### 2. `ALLOWED_ORIGINS`

默认 `*` 只对公共 API 比较宽松。管理员接口和 TG 认证接口带 Cookie，生产环境如果前后端跨域部署，记得显式设置 `ALLOWED_ORIGINS`，否则容易出现跨域和会话问题。

### 3. S3 与 rclone 不是默认即插即用

- `s3` 后端需要额外安装 `boto3`
- `rclone` 后端需要宿主机或镜像内存在 `rclone` 命令

如果你用的是仓库默认 Dockerfile，这俩都不是自动带上的。

### 4. 单实例运行

项目有锁文件机制，不建议同一份数据目录同时启动多个实例，否则 SQLite、Bot 线程和会话状态都可能发生冲突。

### 5. 切换后端不会迁移旧文件

后台切换“活跃后端”只影响新上传文件。旧文件仍按数据库里记录的 `storage_backend` 去取，所以不会自动搬迁，也不会替你做数据迁移。

## 开发说明

### 目录结构

```text
.
├─ main.py
├─ tg_imagebed/
│  ├─ api/
│  ├─ bot/
│  ├─ database/
│  ├─ services/
│  └─ storage/
├─ frontend/
├─ data/
└─ tests/
```

### 常用命令

```bash
# 后端
pip install -r requirements.txt
python main.py

# 前端
cd frontend
npm install
npm run generate

# Docker
docker compose up -d --build
```

## 常见问题

### 没有配置 Telegram Bot，网站能不能先跑起来？

能。Web 服务可以先起来，Bot 会等待后续配置。

### 为什么我把最大文件大小调大了，上传还是 413？

大概率是你的反向代理没放开体积限制，应用内设置和 Nginx / Ingress 不是同一个东西。

### 为什么我配置了 S3，结果后端说不可用？

先检查是不是没安装 `boto3`。仓库默认依赖里不带它。

### 为什么我配置了 rclone 还是报错？

先确认运行环境里真有 `rclone` 命令，而且 remote 配置也能读到。

### 为什么首页打开提示前端文件未找到？

你没构建前端，或者构建产物不在 `frontend/.output/public`。

## 许可证

MIT
