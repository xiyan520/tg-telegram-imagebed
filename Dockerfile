# 使用官方 Python 运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录结构
RUN mkdir -p /app/templates /app/static/js /app/static/css /app/data

# 复制应用代码
COPY main.py .
COPY admin_module.py .
COPY templates/ ./templates/
COPY static/ ./static/

# 设置数据目录权限为最宽松，确保可写
RUN chmod -R 777 /app/data

# 暴露端口
EXPOSE 18793

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:18793/api/info')" || exit 1

# 使用 root 用户运行
CMD ["python", "main.py"]