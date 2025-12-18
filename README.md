# Telegram 云图床 Pro

<div align="center">

基于 Telegram 云存储 + Cloudflare CDN 的现代化图床解决方案

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://hub.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com/)
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
- 🚀 **Telegram 云存储** - 利用 Telegram 无限存储空间
- ⚡ **Cloudflare CDN** - 全球加速，智能路由优化
- 🎨 **现代化前端** - 基于 Nuxt 3 + Vue 3 + Nuxt UI
- 📱 **响应式设计** - 完美适配桌面端和移动端
- 🌙 **深色模式** - 内置深色主题支持

### 高级特性
- 🔄 **智能路由** - 自动选择最优 CDN 节点
- 🔥 **缓存预热** - 多地域主动预热 CDN 缓存
- 📊 **CDN 监控** - 实时监控缓存状态
- 👥 **群组上传** - 支持 Telegram 群组/频道上传
- 🔐 **管理后台** - 完整的管理员功能
- 📈 **数据统计** - 实时统计和监控
- 🖼️ **图片画廊** - 优雅的图片浏览体验
- 📚 **API 文档** - 完整的 RESTful API
- 🗄️ **多存储支持** - Telegram / S3 / 本地 / Rclone 四种存储驱动
- 🎫 **Token 系统** - 游客 Token 上传，支持配额和有效期管理

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose（推荐）
- 或 Python 3.8+ & Node.js 18+
- Telegram Bot Token
- Cloudflare 账号（可选，用于 CDN 加速）

### 5 分钟快速部署

#### 1. 下载配置文件

```bash
wget https://raw.githubusercontent.com/xiyan520/tg-telegram-imagebed/main/.env.example -O .env
wget https://raw.githubusercontent.com/xiyan520/tg-telegram-imagebed/main/docker-compose.yml
```

#### 2. 编辑 `.env` 文件

```bash
nano .env
```

填入必要配置（详见[配置说明](#-配置说明)）：
```env
BOT_TOKEN=你的_Bot_Token
STORAGE_CHAT_ID=你的_频道_ID
CLOUDFLARE_CDN_DOMAIN=你的域名
CLOUDFLARE_API_TOKEN=你的_API_Token
CLOUDFLARE_ZONE_ID=你的_Zone_ID
```

#### 3. 启动服务

```bash
docker-compose up -d
```

#### 4. 访问应用

- 前端界面: `http://你的服务器IP:18793`
- 管理后台: `http://你的服务器IP:18793/admin`
- 默认账号: `admin` / 密码通过环境变量 `ADMIN_PASSWORD` 设置，或首次启动时随机生成（查看日志获取）

---

## 📦 部署指南

### Docker 部署（推荐）

#### 使用 Docker Compose

```yaml
services:
  telegram-imagebed:
    image: xiyan520/tg-telegram-imagebed:latest
    container_name: telegram-imagebed
    ports:
      - "18793:18793"
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

```bash
docker-compose up -d
```

#### 使用 Docker 命令

```bash
docker run -d \
  --name telegram-imagebed \
  -p 18793:18793 \
  --env-file .env \
  -v ./data:/app/data \
  --restart unless-stopped \
  xiyan520/tg-telegram-imagebed:latest
```

### 手动部署

#### 后端部署

```bash
# 1. 克隆项目
git clone https://github.com/xiyan520/tg-telegram-imagebed.git
cd tg-telegram-imagebed

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
nano .env

# 4. 启动后端
python main.py
```

#### 前端部署

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 配置环境变量
cp .env.example .env
nano .env

# 4. 构建生产版本
npm run build

# 5. 启动服务
npm run preview
```

---

## ⚙️ 配置说明

### 必需配置

#### 1. 获取 Telegram Bot Token

1. 在 Telegram 中与 [@BotFather](https://t.me/BotFather) 对话
2. 发送 `/newbot` 创建新机器人
3. 按提示设置名称和用户名
4. 获取 `BOT_TOKEN`

![BotFather Token](https://github.com/user-attachments/assets/04f01289-205c-43e0-ba03-d9ab3465e349)

#### 2. 获取频道 Chat ID

1. 创建一个 Telegram 频道（Channel）
2. 将 Bot 添加为频道管理员
3. 通过 [@VersaToolsBot](https://t.me/VersaToolsBot) 或 [@GetTheirIDBot](https://t.me/GetTheirIDBot) 获取频道 ID

![Add Admin](https://github.com/user-attachments/assets/cedea4c7-8b31-42e0-98a1-8a72ff69528f)

![Chat ID](https://github.com/user-attachments/assets/59fe8b20-c969-4d13-8e46-e58c0e8b9e79)

### Cloudflare CDN 配置（推荐）

#### 1. 创建 API Token

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **My Profile** → **API Tokens**
3. 点击 **Create Token**
4. 选择 **Edit zone DNS** 模板或自定义权限：
   - Zone - Cache Purge - Purge
   - Zone - Zone - Read
5. 复制生成的 Token

![Create Token](https://img.jivon.de/image/QWdBQ0FnVUFBeGtCcbe0c6fe)

#### 2. 获取 Zone ID

1. 在 Cloudflare Dashboard 选择你的域名
2. 在右侧找到 **Zone ID**
3. 复制 Zone ID

#### 3. 配置 Cloudflare 缓存规则（重要！）

为了让 CDN 正常工作，需要在 Cloudflare 中设置缓存规则：

##### 方法一：使用 Page Rules（推荐）

1. 进入域名管理页面
2. 点击 **Rules** → **Page Rules**
3. 创建新规则，URL 模式：`你的域名/image/*`
4. 添加以下设置：
   - **Cache Level**: Cache Everything
   - **Edge Cache TTL**: 1 month
   - **Browser Cache TTL**: 4 hours
5. 保存规则

##### 方法二：使用 Cache Rules（新版）

1. 进入域名管理页面
2. 点击 **Caching** → **Cache Rules**
3. 创建新规则：
   ```
   When incoming requests match:
   - URI Path contains "/image/"

   Then:
   - Cache eligibility: Eligible for cache
   - Edge TTL: 30 days
   - Browser TTL: 4 hours
   ```

##### 方法三：使用 Transform Rules（可选）

如果需要自定义缓存头，可以添加 Transform Rules：

1. 进入 **Rules** → **Transform Rules** → **Modify Response Header**
2. 创建规则：
   ```
   When incoming requests match:
   - URI Path contains "/image/"

   Then:
   - Set static: Cache-Control = public, max-age=2592000
   ```

#### 4. 配置 DNS（如果使用自定义域名）

1. 添加 A 记录指向你的服务器 IP
2. 确保 **Proxy status** 为橙色云朵（已代理）
3. 等待 DNS 生效

### 环境变量完整列表

#### Telegram 配置

| 变量名 | 必需 | 说明 | 示例值 |
|--------|------|------|--------|
| `BOT_TOKEN` | ✅ | Bot Token | `123456:ABCdefGHIjkl` |
| `STORAGE_CHAT_ID` | ✅ | 频道/群组 ID | `-1001234567890` |

#### Cloudflare CDN 配置

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `CLOUDFLARE_CDN_DOMAIN` | ⭐ | - | CDN 域名（不含 https://） |
| `CLOUDFLARE_API_TOKEN` | ⭐ | - | API Token |
| `CLOUDFLARE_ZONE_ID` | ⭐ | - | Zone ID |
| `CDN_ENABLED` | ❌ | `true` | 是否启用 CDN |
| `CLOUDFLARE_CACHE_LEVEL` | ❌ | `aggressive` | 缓存级别 |
| `CLOUDFLARE_BROWSER_TTL` | ❌ | `14400` | 浏览器缓存时间（秒） |
| `CLOUDFLARE_EDGE_TTL` | ❌ | `2592000` | 边缘缓存时间（秒） |
| `ENABLE_SMART_ROUTING` | ❌ | `true` | 智能路由 |
| `ENABLE_CACHE_WARMING` | ❌ | `true` | 缓存预热 |
| `CACHE_WARMING_DELAY` | ❌ | `5` | 预热延迟（秒） |

#### 群组上传配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ENABLE_GROUP_UPLOAD` | `true` | 是否启用群组上传 |
| `GROUP_UPLOAD_ADMIN_ONLY` | `false` | 是否仅管理员可上传 |
| `GROUP_ADMIN_IDS` | - | 管理员 ID 列表（逗号分隔） |
| `GROUP_UPLOAD_REPLY` | `true` | 是否自动回复 CDN 链接 |
| `GROUP_UPLOAD_DELETE_DELAY` | `0` | 回复消息删除延迟（秒），0 表示不删除 |

#### 多存储配置

系统支持四种存储驱动，可通过环境变量或管理后台配置：

| 变量名 | 说明 |
|--------|------|
| `STORAGE_CONFIG_JSON` | JSON 格式的存储配置（优先级最高，设置后无法通过界面修改） |

**存储配置示例：**

```json
{
  "telegram": {
    "driver": "telegram",
    "bot_token": "123456:ABC...",
    "chat_id": "-1001234567890"
  },
  "my-s3": {
    "driver": "s3",
    "endpoint": "https://s3.amazonaws.com",
    "bucket": "my-bucket",
    "access_key": "AKIAXXXXXXXX",
    "secret_key": "xxxxxxxx",
    "region": "us-east-1",
    "public_url_prefix": "https://cdn.example.com"
  },
  "local": {
    "driver": "local",
    "root_dir": "/data/uploads"
  },
  "rclone-remote": {
    "driver": "rclone",
    "remote": "myremote",
    "base_path": "/images"
  }
}
```

**支持的存储驱动：**

| 驱动 | 说明 | 必需参数 |
|------|------|----------|
| `telegram` | Telegram 频道存储 | `bot_token`, `chat_id`（可从环境变量继承） |
| `s3` | S3 兼容存储 | `endpoint`, `bucket`, `access_key`, `secret_key` |
| `local` | 本地文件系统 | `root_dir` |
| `rclone` | Rclone 远程存储 | `remote` |

#### Token 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GUEST_TOKEN_GENERATION_ENABLED` | `true` | 是否允许游客创建 Token |
| `GUEST_TOKEN_MAX_UPLOAD_LIMIT` | `1000` | Token 最大上传次数上限 |
| `GUEST_TOKEN_MAX_EXPIRES_DAYS` | `365` | Token 最大有效天数 |

#### 上传策略配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GUEST_UPLOAD_POLICY` | `open` | 游客上传策略：`open` / `token_only` / `admin_only` |
| `MAX_FILE_SIZE_MB` | `20` | 单文件最大大小（MB） |
| `DAILY_UPLOAD_LIMIT` | `0` | 每日上传限制（0 表示不限制） |

#### 其他配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SECRET_KEY` | - | 加密密钥（请使用强密码） |
| `PORT` | `18793` | Web 服务端口 |
| `DATABASE_PATH` | `./telegram_imagebed.db` | 数据库路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `DEFAULT_ADMIN_USERNAME` | `admin` | 默认管理员用户名 |
| `DEFAULT_ADMIN_PASSWORD` | `admin123` | 默认管理员密码 |

---

## 🏗️ 技术栈

### 后端
- **框架**: Flask
- **存储**: Telegram Bot API + SQLite
- **CDN**: Cloudflare API
- **语言**: Python 3.8+

### 前端
- **框架**: Nuxt.js 3
- **UI 库**: Nuxt UI (Tailwind CSS)
- **状态管理**: Pinia
- **工具库**: VueUse
- **语言**: TypeScript

---

## 📖 API 文档

完整的交互式 API 文档请访问：`http://your-domain/docs`

### 主要接口

#### 匿名上传

```bash
POST /api/upload
Content-Type: multipart/form-data

file: <图片文件>
```

#### Token 上传

```bash
POST /api/auth/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <图片文件>
```

#### 创建 Token

```bash
POST /api/auth/token/generate
Content-Type: application/json

{
  "upload_limit": 100,
  "expires_days": 30,
  "description": "my client"
}
```

#### 验证 Token

```bash
POST /api/auth/token/verify
Authorization: Bearer <token>
```

#### 获取图片

```bash
GET /image/<encrypted_id>
```

#### 获取统计信息

```bash
GET /api/stats
```

#### 获取最近上传

```bash
GET /api/recent?page=1&limit=12
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "url": "https://your-domain.com/image/xxx",
    "filename": "image.jpg",
    "size": "1.2 MB",
    "upload_time": "2025-01-01 12:00:00"
  }
}
```

---

## 🔧 常见问题

### Q: 图片无法访问？
A: 检查 Telegram Bot 是否有频道管理员权限，确保 `STORAGE_CHAT_ID` 配置正确。

### Q: CDN 不生效？
A:
1. 确认 Cloudflare 缓存规则已正确配置
2. 检查 `CLOUDFLARE_CDN_DOMAIN` 是否正确（不含 https://）
3. 验证 API Token 权限是否足够
4. 查看后端日志确认 CDN 状态

### Q: 如何修改管理员密码？
A: 登录管理后台后，在设置页面修改密码。

### Q: Docker 容器无法启动？
A:
1. 检查 `.env` 文件配置是否正确
2. 确保端口 18793 未被占用
3. 查看容器日志：`docker logs telegram-imagebed`

### Q: 群组上传不工作？
A:
1. 确保 Bot 已添加到群组并有管理员权限
2. 检查 `ENABLE_GROUP_UPLOAD` 是否为 `true`
3. 如果设置了 `GROUP_UPLOAD_ADMIN_ONLY`，确认用户 ID 在 `GROUP_ADMIN_IDS` 中

---

## 📝 更新日志

### 最新更新

#### 多存储支持
- ✅ 支持 Telegram / S3 / 本地 / Rclone 四种存储驱动
- ✅ 管理后台可视化配置存储
- ✅ 支持上传场景路由（游客/Token/群组/管理员）
- ✅ 存储健康状态监控

#### Token 系统
- ✅ 游客可创建上传 Token
- ✅ Token 配额和有效期管理
- ✅ Token 上传记录查询
- ✅ 管理后台 Token 管理

#### API 文档重构
- ✅ 数据驱动的组件化文档页面
- ✅ 多语言代码示例（cURL/JavaScript/Python/PHP）
- ✅ 侧边栏导航与滚动定位
- ✅ 响应式移动端适配

#### 群组上传功能
- ✅ 支持 Telegram 群组/频道直接上传
- ✅ 可配置仅管理员上传
- ✅ 自动回复 CDN 链接
- ✅ 可设置回复消息自动删除

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 📮 联系方式

如有问题，请提交 [Issue](https://github.com/xiyan520/tg-telegram-imagebed/issues)
