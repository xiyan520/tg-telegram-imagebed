# ==================== 阶段1: 构建前端 ====================
FROM node:20-alpine AS frontend-builder

# 设置工作目录
WORKDIR /frontend

# 复制前端依赖文件
COPY frontend/package*.json ./

# 安装所有依赖（包括开发依赖，构建时需要）
RUN npm ci

# 复制前端源码
COPY frontend/ ./

# 构建前端
RUN npm run generate

# ==================== 阶段2: 构建最终镜像 ====================
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录结构
RUN mkdir -p /app/data

# 复制后端代码（根目录仅 main.py，其余都在 tg_imagebed 包内）
COPY VERSION .
COPY main.py .
COPY tg_imagebed/ ./tg_imagebed/

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /frontend/.output/public /app/frontend/.output/public

# 暴露端口
EXPOSE 18793

# 设置环境变量
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
