#!/bin/bash
# Docker 构建脚本

set -e

echo "=========================================="
echo "  Telegram 图床 - Docker 构建脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}警告: .env 文件不存在${NC}"
    echo "请先创建 .env 文件并配置必要的环境变量"
    echo "参考 .env.example 文件"
    exit 1
fi

# 检查必要的环境变量
echo -e "${BLUE}[1/5] 检查环境变量...${NC}"
source .env
if [ -z "$BOT_TOKEN" ] || [ -z "$STORAGE_CHAT_ID" ]; then
    echo -e "${RED}错误: BOT_TOKEN 或 STORAGE_CHAT_ID 未设置${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 环境变量检查通过${NC}"
echo ""

# 构建前端
echo -e "${BLUE}[2/5] 构建前端...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
echo "构建前端..."
npm run build
cd ..
echo -e "${GREEN}✓ 前端构建完成${NC}"
echo ""

# 构建 Docker 镜像
echo -e "${BLUE}[3/5] 构建 Docker 镜像...${NC}"
docker build -t telegram-imagebed:latest .
echo -e "${GREEN}✓ Docker 镜像构建完成${NC}"
echo ""

# 停止旧容器
echo -e "${BLUE}[4/5] 停止旧容器...${NC}"
if [ "$(docker ps -q -f name=telegram-imagebed)" ]; then
    docker stop telegram-imagebed
    docker rm telegram-imagebed
    echo -e "${GREEN}✓ 旧容器已停止并删除${NC}"
else
    echo "没有运行中的容器"
fi
echo ""

# 启动新容器
echo -e "${BLUE}[5/5] 启动新容器...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ 容器启动成功${NC}"
echo ""

# 显示容器状态
echo -e "${BLUE}容器状态:${NC}"
docker-compose ps
echo ""

# 显示日志
echo -e "${BLUE}查看日志:${NC}"
echo "  docker-compose logs -f"
echo ""

echo -e "${GREEN}=========================================="
echo "  构建和部署完成！"
echo "==========================================${NC}"
echo ""
echo "访问地址: http://localhost:18793"
echo "管理后台: http://localhost:18793/admin"
echo ""
