#!/bin/bash
# ============================================================
# 图书借阅小程序 — 一键生产部署脚本
# 用法: chmod +x deploy.sh && ./deploy.sh
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  图书借阅小程序 — 生产环境部署${NC}"
echo -e "${GREEN}========================================${NC}"

# ---- 1. 检查 Docker 环境 ----
echo -e "\n${YELLOW}[1/5] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker 未安装，正在安装...${NC}"
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker && systemctl start docker
fi

# 优先使用 docker compose (v2)，回退到 docker-compose (v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}docker-compose 未安装，正在安装...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}Docker 环境就绪${NC}"

# ---- 2. 生成安全密钥 ----
echo -e "\n${YELLOW}[2/5] 生成安全配置...${NC}"

if [ ! -f .env ]; then
    echo "MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)" > .env
    echo "DB_USER=library_user" >> .env
    echo "DB_PASSWORD=$(openssl rand -hex 16)" >> .env
    echo "DB_NAME=library_system" >> .env
    echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
    echo -e "${GREEN}已生成随机密码和密钥${NC}"
else
    echo -e "${YELLOW}.env 已存在，跳过生成${NC}"
fi

# ---- 3. 构建镜像 ----
echo -e "\n${YELLOW}[3/5] 构建 Docker 镜像...${NC}"
$DOCKER_COMPOSE build --no-cache
echo -e "${GREEN}镜像构建完成${NC}"

# ---- 4. 启动服务 ----
echo -e "\n${YELLOW}[4/5] 启动服务...${NC}"
$DOCKER_COMPOSE down 2>/dev/null || true
$DOCKER_COMPOSE up -d
echo -e "${GREEN}服务已启动${NC}"

# ---- 5. 等待就绪并验证 ----
echo -e "\n${YELLOW}[5/5] 等待服务就绪...${NC}"
sleep 10
$DOCKER_COMPOSE logs --tail=20 app

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取服务器公网 IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "YOUR_SERVER_IP")

echo -e "\n${GREEN}📌 访问地址:${NC}"
echo -e "   前端页面: http://${SERVER_IP}:5000"
echo -e "   API接口:  http://${SERVER_IP}:5000/api/books"
echo -e "\n${GREEN}📌 测试账号:${NC}"
echo -e "   管理员: admin / admin123"
echo -e "   普通用户: testuser / 123456"
echo -e "\n${GREEN}📌 常用命令:${NC}"
echo -e "   查看日志: $DOCKER_COMPOSE logs -f app"
echo -e "   重启服务: $DOCKER_COMPOSE restart"
echo -e "   停止服务: $DOCKER_COMPOSE down"
echo -e "   数据备份: $DOCKER_COMPOSE exec db mysqldump -u root -p library_system > backup.sql"

# ---- 防火墙提醒 ----
echo -e "\n${YELLOW}⚠️  请确保防火墙已开放 5000 端口:${NC}"
if command -v firewall-cmd &> /dev/null; then
    echo -e "   firewall-cmd --add-port=5000/tcp --permanent && firewall-cmd --reload"
elif command -v ufw &> /dev/null; then
    echo -e "   ufw allow 5000/tcp"
else
    echo -e "   请手动在云服务器安全组中放行 5000 端口（TCP）"
fi
