#!/bin/bash
# 图书借阅系统 — 一键公网部署脚本
# 启动后端(端口3000) + Serveo公网隧道

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  图书借阅系统 — 公网部署"
echo "========================================"

# 1. 启动后端
echo "[1/2] 启动 Flask 后端 (端口 3000)..."
cd "$SCRIPT_DIR/backend"
DB_TYPE=sqlite python -c "
from db import init_db
from app import app
init_db()
app.run(debug=False, host='0.0.0.0', port=3000)
" &
BACKEND_PID=$!
sleep 3

# 验证后端
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/books | grep -q 200; then
    echo "  后端启动成功 (PID: $BACKEND_PID)"
else
    echo "  后端启动失败!"
    exit 1
fi

# 2. 启动 Serveo 隧道
echo "[2/2] 启动 Serveo 公网隧道..."
echo "========================================"
echo ""
echo "  公网地址即将显示在下方:"
echo ""
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:localhost:3000 serveo.net

# 隧道断开后清理
echo ""
echo "隧道已断开，正在停止后端..."
kill $BACKEND_PID 2>/dev/null
echo "已停止。"
