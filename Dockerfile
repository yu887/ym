# ---- 阶段 1: 构建前端 ----
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci && npm cache clean --force
COPY frontend/ ./
RUN npm run build

# ---- 阶段 2: 最终运行时镜像 ----
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源代码
COPY backend/ .

# 从构建阶段复制前端产物到 static 目录（Flask 直接服务）
COPY --from=frontend-builder /app/dist/ ./static/

# 安全：非 root 用户运行
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# dumb-init 作为 PID 1 确保信号正确处理
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "run.py"]

EXPOSE 5000
