#更新
支持群组上传图片，新加变量组
`
# 群组上传功能配置
ENABLE_GROUP_UPLOAD=true              # 是否启用群组上传（默认启用）
GROUP_UPLOAD_ADMIN_ONLY=false         # 是否仅管理员可上传（默认否）
GROUP_ADMIN_IDS=123456789,987654321   # 管理员ID列表（逗号分隔）
GROUP_UPLOAD_REPLY=true               # 是否自动回复CDN链接（默认是）
GROUP_UPLOAD_DELETE_DELAY=0           # 回复消息删除延迟（秒），0表示不删除
`
# Telegram Cloudflare ImageBed 设置教程

## 前端界面

![Frontend](https://img.jivon.de/image/QWdBQ0FnVUFBeGtE49e5a6c9)

## 后台界面

![Backend](https://img.jivon.de/image/QWdBQ0FnVUFBeGtE806e79f6)

---

## 设置 Cloudflare

### 1. 创建 API 令牌

![Create Token](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEcb3b08ba)

将生成的 API Token 填入到 `CLOUDFLARE_API_TOKEN` 环境变量中。

### 2. 处理区域信息

点击域名后方的区域 ID，复制后填入到 `CLOUDFLARE_ZONE_ID` 环境变量中。

### 3. 设置缓存规则 (Cache Rules)

请按照下图添加缓存规则：

![Cache Rules 1](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEabb0804d)

![Cache Rules 2](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEedf6e136)

![Cache Rules 3](https://img.jivon.de/image/QWdBQ0FnVUFBeGtE66c411c0)

### 4. 页面规则 (Page Rules)

按照下图添加 Page Rule:

![Page Rule](https://img.jivon.de/image/QWdBQ0FnVUFBeGtEdb6d09a5)

> 至此 Cloudflare 配置完成

---

## 获取 Telegram Bot 的 `BOT_TOKEN` 和 `CHAT_ID`

### 1. 创建新的 Telegram 机器人

* 在 Telegram 中与 [@BotFather](https://t.me/BotFather) 进行对话，发送 `/newbot`
* 按照提示填写机器人名称和用户名
* 创建成功后会收到 `BOT_TOKEN`

![BotFather Token](https://github.com/user-attachments/assets/04f01289-205c-43e0-ba03-d9ab3465e349)

### 2. 将机器人设置为频道管理员

* 新建一个频道 (Channel)
* 进入频道设置，将创建的 Bot 添加为管理员

![Add Admin 1](https://github.com/user-attachments/assets/cedea4c7-8b31-42e0-98a1-8a72ff69528f)

![Add Admin 2](https://github.com/user-attachments/assets/16393802-17eb-4ae4-a758-f0fdb7aaebc4)

### 3. 获取 Chat ID

* 通过 [@VersaToolsBot](https://t.me/VersaToolsBot) 获取频道 ID
* 或者通过 [@GetTheirIDBot](https://t.me/GetTheirIDBot) 获取

![Chat ID](https://github.com/user-attachments/assets/59fe8b20-c969-4d13-8e46-e58c0e8b9e79)

---

## Cloudflare Pages 环境变量配置

> 注：修改环境变量后，**需要重新部署**
>
> ## Docker 部署教程

### 1. 下载 `.env` 环境文件

```bash
wget https://raw.githubusercontent.com/xiyan520/tg-telegram-imagebed/44b8296c5c5b02a4875437c1dafa0a589f2981a2/.env
```

### 2. 修改 `.env` 内容，填入你的 Token、Chat ID、Cloudflare 配置

---

### 3. 使用 `docker-compose` 部署（推荐）

创建 `docker-compose.yml` 文件，内容如下：

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

---

### 4. 启动容器

```bash
docker-compose up -d
```

> 首次运行会自动拉取镜像并启动服务。你可以通过浏览器访问：`http://<你的服务器IP>:18793`


| 环境变量                   | 示例值                 | 说明                                                   |
| ---------------------- | ------------------- | ---------------------------------------------------- |
| `BOT_TOKEN`            | `123468:AAxxxGKrn5` | 从 [@BotFather](https://t.me/BotFather) 获取的 Bot Token |
| `STORAGE_CHAT_ID`      | `-1234567`          | 频道 ID，确保 Bot 是频道/群组的管理员                              |
| `CLOUDFLARE_API_TOKEN` | `cf-xxx`            | Cloudflare 创建的 API Token                             |
| `CLOUDFLARE_ZONE_ID`   | `zoneid-xxx`        | 域名区域 ID                                              |
