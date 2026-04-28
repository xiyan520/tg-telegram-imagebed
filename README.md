# Telegram 云图床 Pro

<div align="center">

基于 Telegram 云存储 + Cloudflare CDN 的现代化图床解决方案

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://hub.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://www.python.org/)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.13-00DC82)](https://nuxt.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [部署指南](#-部署指南) • [配置说明](#-配置说明)

</div>

---

## 📸 界面预览

### 前端界面
![Frontend](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEbe68687b)

### 管理后台
![Backend](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEd13739b4)

---

## ✨ 功能特性

### 核心功能
- 🚀 **Telegram 云存储** — 利用 Telegram 无限存储空间，零成本图片托管
- ⚡ **Cloudflare CDN** — 全球加速，智能路由，缓存预热
- 🎨 **现代化前端** — Nuxt 3 + Vue 3 + Nuxt UI，拖拽/粘贴/点击上传
- 📱 **响应式设计** — 完美适配桌面端和移动端
- 🌙 **深色模式** — 内置深色主题支持

### 存储与分发
- 🗄️ **多存储后端** — Telegram / S3 / 本地 / Rclone 四种存储驱动，按场景路由
- 🔄 **CDN 智能路由** — 自动选择最优节点，ETag/304 缓存，Range 分片传输
- 🔥 **缓存预热** — 多地域主动预热 CDN 缓存，实时监控缓存状态

### Token 与相册
- 🎫 **Token 系统** — 游客 Token 上传，支持配额和有效期管理
- 🔑 **Token Vault** — 多 Token 本地管理，一键切换，自动验证与无效清理
- 🖼️ **画集系统** — 创建画集、管理图片、设置封面，支持四种访问模式
- 🔗 **分享链接** — 单画集分享 / 全部分享，支持密码保护和 Token 授权

### 管理与安全
- 🔐 **管理后台** — 完整的管理员功能，首次启动引导式设置
- 📈 **数据统计** — 实时统计和监控仪表板
- 👥 **群组上传** — 支持 Telegram 群组/频道上传，自动回复链接
- 📚 **交互式 API 文档** — 内置 `/docs` 页面，多语言代码示例
- 📢 **系统公告** — 管理员可发布公告通知用户
- 🛡️ **登录安全** — 渐进式锁定（5次失败 → 5/15/30分钟锁定）

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose（推荐）
- 或 Python 3.11+ & Node.js 20+
- Telegram Bot Token + 频道 ID

### 3 分钟快速部署

#### 1. 创建 docker-compose.yml

```yaml
services:
  telegram-imagebed:
    image: lost4/tg-telegram-imagebed:latest
    container_name: telegram-imagebed
    ports:
      - "18793:18793"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
```

#### 2. 启动服务

```bash
docker-compose up -d
```

#### 3. 首次设置

访问 `http://你的服务器IP:18793`，系统自动跳转到设置页面：

1. **设置管理员账号** — 输入用户名和密码（≥8字符，含大小写/数字/特殊字符）
2. **配置 Telegram Bot** — 在管理后台 → Bot 配置中填入 Bot Token 和频道 ID
3. **开始使用** — 返回首页即可上传图片

> 所有业务配置（Bot Token、CDN、存储、上传策略等）均通过管理后台设置，无需 `.env` 文件。

---

## 📦 部署指南

### Docker 部署（推荐）

#### 使用 Docker Compose

```yaml
services:
  telegram-imagebed:
    image: lost4/tg-telegram-imagebed:latest
    container_name: telegram-imagebed
    ports:
      - "18793:18793"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
```

```bash
docker-compose up -d
```

#### 使用 Docker 命令

```bash
docker run -d \
  --name telegram-imagebed \
  -p 18793:18793 \
  -v ./data:/app/data \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  lost4/tg-telegram-imagebed:latest
```

### 手动部署

#### 后端部署

```bash
# 1. 克隆项目
git clone https://github.com/lostiv/tg-telegram-imagebed.git
cd tg-telegram-imagebed

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动后端
python main.py
```

#### 前端部署

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 构建静态文件
npm run generate

# 4. 将 .output/public/ 下的文件部署到后端 static/ 目录
```

> Docker 多阶段构建会自动完成前端构建和集成，手动部署仅用于开发调试。

### 数据持久化

所有数据存储在 `./data/` 目录下：

| 文件 | 说明 |
|------|------|
| `telegram_imagebed.db` | SQLite 数据库（WAL 模式） |
| `telegram_imagebed.log` | 运行日志 |
| `.secret_key` | 加密密钥（首次自动生成） |
| `.instance_lock` | 单实例锁文件 |

---

## ⚙️ 配置说明

### 配置方式

本项目采用 **管理后台配置** 模式，所有业务配置通过 Web 界面管理，存储在数据库 `system_settings` 表中。无需 `.env` 文件。

首次启动后，在管理后台中配置以下内容：

### 1. Telegram Bot 配置

1. 在 Telegram 中与 [@BotFather](https://t.me/BotFather) 对话，发送 `/newbot` 创建机器人
2. 获取 Bot Token
3. 创建一个 Telegram 频道，将 Bot 添加为管理员
4. 通过 [@VersaToolsBot](https://t.me/VersaToolsBot) 获取频道 ID
5. 在管理后台 → Bot 配置中填入 Bot Token 和频道 ID

![BotFather Token](https://github.com/user-attachments/assets/04f01289-205c-43e0-ba03-d9ab3465e349)

### 2. Cloudflare CDN 配置（可选）

在管理后台 → 系统设置中启用 CDN 并填入：
- CDN 域名（不含 `https://`）
- Cloudflare API Token（需要 Cache Purge + Zone Read 权限）

#### Cloudflare 缓存规则

在 Cloudflare Dashboard 中配置缓存规则，确保 `/image/*` 路径被缓存：

**方法一：Page Rules**
- URL 模式：`你的域名/image/*`
- Cache Level: Cache Everything
- Edge Cache TTL: 1 month

**方法二：Cache Rules（新版）**
```
When: URI Path contains "/image/"
Then: Eligible for cache, Edge TTL 30 days
```

#### DNS 配置

添加 A 记录指向服务器 IP，确保 Proxy status 为橙色云朵（已代理）。

### 3. 管理后台可配置项

| 分类 | 配置项 | 默认值 | 说明 |
|------|--------|--------|------|
| Bot | Telegram Bot Token | — | Bot Token |
| Bot | 存储频道 ID | — | 频道/群组 ID |
| 上传策略 | 游客上传策略 | `open` | `open` / `token_only` / `admin_only` |
| 上传策略 | 最大文件大小 | 20 MB | 1–1024 MB |
| 上传策略 | 每日上传限制 | 0（无限） | 按来源或 Token 统计 |
| Token | Token 生成开关 | 开启 | 是否允许游客创建 Token |
| Token | 最大上传数 | 1000 | 单个 Token 最大上传次数 |
| Token | 最大有效期 | 365 天 | 单个 Token 最大有效天数 |
| 存储 | 活跃存储后端 | telegram | telegram / s3 / local / rclone |
| 存储 | 上传场景路由 | — | 游客/Token/群组/管理员 → 不同后端 |
| CDN | CDN 开关 | 关闭 | Cloudflare CDN |
| CDN | CDN 域名 | — | 不含 `https://` |
| CDN | CDN 重定向 | 关闭 | 自动重定向到 CDN |
| 群组 | 群组上传仅管理员 | 否 | 限制群组上传权限 |
| 群组 | 管理员 ID 列表 | — | 逗号分隔 |
| 同步 | 删除同步 TG 消息 | 开启 | 删除图片时同步删除 TG 消息 |

### 4. 环境变量（仅基础设施）

项目仅使用少量环境变量用于基础设施配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HTTP_PROXY` / `HTTPS_PROXY` | — | 系统代理（可选） |

> 所有业务配置（Bot Token、CDN、存储、上传策略等）均通过管理后台设置，不通过环境变量。

### 5. 多存储配置

系统支持四种存储驱动，在管理后台 → 存储配置中可视化管理：

| 驱动 | 说明 | 必需参数 |
|------|------|----------|
| `telegram` | Telegram 频道存储（默认） | Bot Token, 频道 ID |
| `s3` | S3 兼容存储（AWS/MinIO 等） | endpoint, bucket, access_key, secret_key |
| `local` | 本地文件系统 | root_dir |
| `rclone` | Rclone 远程存储 | remote |

支持按上传场景路由到不同后端（游客 → Telegram，管理员 → S3 等）。

---

## 🏗️ 技术栈

### 后端
| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Flask + Flask-CORS | 3.0 |
| 生产服务器 | waitress | 3.0 |
| 数据库 | SQLite3（WAL 模式） | 内置 |
| Bot SDK | python-telegram-bot | 21.0.1 |
| HTTP | requests + aiohttp | 2.31 / 3.9 |
| 语言 | Python | 3.11+ |

### 前端
| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Nuxt 3（SPA, ssr=false） | 3.13 |
| UI 库 | Nuxt UI（Tailwind CSS） | 2.18 |
| 状态管理 | Pinia | 2.2 |
| 工具库 | VueUse | 11.0 |
| 语言 | TypeScript | — |

### 部署
- Docker 多阶段构建：node:20-alpine（前端 generate）→ python:3.11-slim（后端）
- 单容器多线程，端口 18793，waitress 4 线程
- 健康检查：`GET /api/health`（30 秒间隔）

---

## 📖 API 文档

完整的交互式 API 文档请访问：`http://your-domain/docs`

### 主要接口

#### 匿名上传

```bash
curl -X POST http://your-domain/api/upload \
  -F "file=@image.jpg"
```

#### Token 上传

```bash
curl -X POST http://your-domain/api/auth/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@image.jpg"
```

#### 创建 Token

```bash
curl -X POST http://your-domain/api/auth/token/generate \
  -H "Content-Type: application/json" \
  -d '{"upload_limit": 100, "expires_days": 30, "description": "my album"}'
```

#### 验证 Token

```bash
curl -X POST http://your-domain/api/auth/token/verify \
  -H "Authorization: Bearer <token>"
```

#### 获取图片

```bash
curl http://your-domain/image/<encrypted_id>
```

#### 获取统计信息

```bash
curl http://your-domain/api/stats
```

#### 画集相关

```bash
# 获取 Token 的画集列表
curl http://your-domain/api/auth/galleries \
  -H "Authorization: Bearer <token>"

# 创建画集
curl -X POST http://your-domain/api/auth/galleries \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "我的画集", "access_mode": "public"}'

# 访问分享画集
curl http://your-domain/api/shared/galleries/<share_token>
```

**响应格式：**
```json
{
  "success": true,
  "data": {
    "url": "https://your-domain.com/image/xxx",
    "filename": "image.jpg",
    "size": "1.2 MB",
    "upload_time": "2025-01-01 12:00:00",
    "remaining_uploads": 99
  }
}
```

---

## 🔧 常见问题

### Q: 首次启动后如何配置？
A: 访问 `http://服务器IP:18793`，系统自动跳转到设置页面。设置管理员账号后，在管理后台配置 Bot Token 和频道 ID。

### Q: 图片无法访问？
A: 检查 Telegram Bot 是否有频道管理员权限，在管理后台确认 Bot Token 和频道 ID 配置正确。

### Q: CDN 不生效？
A:
1. 确认管理后台已启用 CDN 并填入正确的域名
2. 检查 Cloudflare 缓存规则是否已配置（`/image/*` 路径）
3. 验证 API Token 权限是否足够（Cache Purge + Zone Read）
4. 查看后端日志确认 CDN 状态

### Q: 如何修改管理员密码？
A: 登录管理后台，在系统设置页面修改密码。

### Q: Docker 容器无法启动？
A:
1. 确保端口 18793 未被占用
2. 确保 `./data` 目录有写入权限
3. 查看容器日志：`docker logs telegram-imagebed`

### Q: 群组上传不工作？
A:
1. 确保 Bot 已添加到群组并有管理员权限
2. 在管理后台检查群组上传是否已启用
3. 如果设置了仅管理员上传，确认用户 ID 在管理员列表中

### Q: Token 上传记录不显示？
A: 确保上传时使用的是 Token 模式（Bearer Token 认证）。当同时登录管理员和持有 Token 时，系统优先使用 Token 模式上传以确保记录关联正确。

---

## 📝 更新日志

### 最新更新

#### v2.0.5 — TOTP 二次验证与安全增强
- ✅ 管理员后台增加 TOTP 二次验证功能（pyotp + qrcode）
- ✅ 登录流程改为两步验证：密码 + 动态验证码
- ✅ 管理员用户中心新增「安全」选项卡，支持扫码绑定/验证启用/禁用
- ✅ 修复 TOTP 验证 token 竞态条件（原子标记防重放）
- ✅ QR 码仅在设置阶段可用，防止密钥二次暴露
- ✅ Docker 环境新增 TZ=Asia/Shanghai 时区配置
- ✅ 修正仓库地址（Docker: lost4, GitHub: lostiv）

#### v2.0.4 — Bug 修复与稳定性提升
- 修复 3 处中文注释/日志乱码（文件编码回写错误）
- 修复 Bot 实例引用的线程安全问题（跨线程读写竞态）
- 修复 CDN 服务配置缓存的 TOCTOU 竞态条件
- 修复 CDN 会话代理设置的非线程安全写入
- 修复图片删除时数据库事务内执行外部 API 调用（长时间持锁）
- 修复管理员 API CORS Origin 未经验证即回显（安全加固）
- 修复 AVIF 文件头检测过于宽松（子串匹配改为 4 字节边界精确匹配）
- 修复 CDN 缓存清除 URL 解析缺陷（改用 urlparse）
- 修复 CDN 预热 limit=0 被静默转为默认值
- 修复 Token 服务 json.loads("") 崩溃及异常处理不一致
- 移除 admin_module.py 中重复的 get_static_file_version 死代码
- 清理 Telegram 标题中的文件名换行符

#### 首页组件重构
- ✅ `pages/index.vue` 从 846 行精简为 ~70 行容器组件
- ✅ 拆分为 4 个子组件：HomeUploadZone / HomeUploadResults / HomeUploadHistory / HomeImagePreview
- ✅ 新增 `useClipboardCopy` composable，兼容非 HTTPS 环境
- ✅ 上传模式优先级修正：Token 优先于 Admin，确保上传记录正确关联

#### Token Vault 多 Token 管理
- ✅ 支持多个 Token 本地管理，localStorage 持久化
- ✅ 一键切换活跃 Token，自动验证有效性
- ✅ 旧版单 Token 自动迁移到 Vault
- ✅ 智能清理：仅在后端确认无效时移除，网络错误不移除

#### 画集表重构
- ✅ `galleries` 表新增 `owner_type` 列（`admin` / `token`），移除 FK 约束
- ✅ 管理员画集直接 `owner_type='admin'`，无需虚拟 token
- ✅ 自动迁移：旧表重建 + admin token 行转换 + 清理虚拟记录

#### 数据库模块重构
- ✅ `database.py`（2800行）拆分为 `database/` 包结构（6 个子模块）
- ✅ 按职责划分：连接管理、文件 CRUD、Token、系统设置、画集、管理员画集
- ✅ 通过 `__init__.py` 重导出，外部 import 零改动

#### 多存储支持
- ✅ 支持 Telegram / S3 / 本地 / Rclone 四种存储驱动
- ✅ 管理后台可视化配置存储
- ✅ 支持上传场景路由（游客/Token/群组/管理员 → 不同后端）
- ✅ 存储健康状态监控

#### Token 系统
- ✅ 游客可创建上传 Token，支持配额和有效期
- ✅ Token 上传记录查询
- ✅ 管理后台 Token 管理（批量操作 + 影响范围查询 + 级联删除）

#### API 文档重构
- ✅ 数据驱动的组件化文档页面
- ✅ 多语言代码示例（cURL / JavaScript / Python / PHP）
- ✅ 侧边栏导航与滚动定位

#### 群组上传功能
- ✅ 支持 Telegram 群组/频道直接上传
- ✅ 可配置仅管理员上传
- ✅ 自动回复 CDN 链接

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 📮 联系方式

如有问题，请提交 [Issue](https://github.com/lostiv/tg-telegram-imagebed/issues)
