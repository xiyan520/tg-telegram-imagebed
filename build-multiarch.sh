#!/bin/bash
# 多架构构建和推送脚本

set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# 配置
IMAGE_NAME="lost4/tg-telegram-imagebed"
TAG="latest"
PLATFORMS="linux/amd64,linux/arm64"
BUILDER_NAME="multiarch-builder"

echo "========================================="
echo "多架构镜像构建脚本"
echo "========================================="
echo "镜像名称: ${IMAGE_NAME}:${TAG}"
echo "目标平台: ${PLATFORMS}"
echo ""

# 检查并创建 buildx 构建器
if ! docker buildx inspect ${BUILDER_NAME} &> /dev/null; then
    echo "创建新的 buildx 构建器..."
    docker buildx create --name ${BUILDER_NAME} --driver docker-container --use
else
    echo "使用已有的 buildx 构建器..."
    docker buildx use ${BUILDER_NAME}
fi

echo ""
echo "开始构建多架构镜像..."
echo ""

# 构建并推送多架构镜像
docker buildx build \
  --platform ${PLATFORMS} \
  -t ${IMAGE_NAME}:${TAG} \
  --push \
  --file Dockerfile \
  .

echo ""
echo "========================================="
echo "构建完成"
echo "========================================="
echo "镜像已推送到 Docker Hub"
echo ""
echo "拉取命令:"
echo "  docker pull ${IMAGE_NAME}:${TAG}"
echo ""
echo "运行命令:"
echo "  docker run -d -p 18793:18793 -v ./data:/app/data ${IMAGE_NAME}:${TAG}"
echo ""
