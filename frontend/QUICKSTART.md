# 快速开始指南

## 🚀 5 分钟快速启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
# NUXT_PUBLIC_API_BASE=http://localhost:18793
```

### 3. 启动开发服务器

```bash
# 终端 1: 启动后端
cd ..
python main.py

# 终端 2: 启动前端
cd frontend
npm run dev
```

### 4. 访问应用

打开浏览器访问: http://localhost:3000

## 📝 默认账号

管理后台登录：
- 用户名: `admin`
- 密码: `admin123`

⚠️ **重要**: 首次登录后请立即修改密码！

## 🎯 主要功能

### 首页 (/)
- 拖拽上传图片
- 批量上传
- 获取多种格式链接

### 图片画廊 (/gallery)
- 浏览所有图片
- 搜索和筛选

### API 文档 (/docs)
- 查看 API 使用说明
- 在线测试上传

### 管理后台 (/admin)
- 查看统计数据
- 管理图片
- 系统配置

## 🔧 常用命令

```bash
# 开发
npm run dev

# 构建
npm run build

# 预览构建
npm run preview

# 生成静态站点
npm run generate
```

## 📚 下一步

- 阅读 [README.md](./README.md) 了解详细信息
- 查看 [NUXT_MIGRATION.md](../NUXT_MIGRATION.md) 了解迁移指南
- 参考 [DEPLOYMENT.md](../DEPLOYMENT.md) 进行生产部署

## ❓ 遇到问题？

1. 确保 Node.js >= 18
2. 确保后端 API 正常运行
3. 检查 `.env` 配置是否正确
4. 查看浏览器控制台错误信息

祝您使用愉快！🎉
