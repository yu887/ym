"""
图书借阅小程序 — 生产环境启动入口
使用 Waitress WSGI 服务器，性能远优于 Flask 内置开发服务器

支持平台：
  - Docker Compose: DB_TYPE=mysql (默认)
  - Render / 免费平台: DB_TYPE=sqlite (自动检测 PORT 环境变量)
"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# ── 平台自动检测 ────────────────────────────────────────────────
# Render / Railway 等平台会设置 PORT 环境变量，自动切换到 SQLite 模式
IS_CLOUD_PLATFORM = bool(os.environ.get('PORT') or os.environ.get('RENDER'))
if IS_CLOUD_PLATFORM and not os.environ.get('DB_TYPE'):
    os.environ['DB_TYPE'] = 'sqlite'
    print('[!] 检测到云平台环境，自动切换为 SQLite 模式')

# 若未设置 JWT_SECRET_KEY，自动生成随机密钥
if not os.environ.get('JWT_SECRET_KEY'):
    random_key = secrets.token_hex(32)
    os.environ['JWT_SECRET_KEY'] = random_key
    print(f'[!] 已自动生成 JWT_SECRET_KEY: {random_key}')

from app import app
from waitress import serve
from db import wait_for_db, init_db

# 云平台使用 PORT 环境变量，本地默认 5000
PORT = int(os.environ.get('PORT', 5000))

print('=' * 50)
print('  图书借阅小程序 — 生产服务器')
print(f'  监听端口: {PORT}')
print(f'  数据库类型: {os.environ.get("DB_TYPE", "mysql")}')
if os.environ.get('DB_HOST'):
    print(f'  数据库地址: {os.environ["DB_HOST"]}:{os.environ.get("DB_PORT", "3306")}')
print('=' * 50)

# 等待数据库就绪（MySQL 需要等待，SQLite 秒过）
wait_for_db()

# 创建表并插入种子数据（幂等操作，可安全重复调用）
init_db()

print(f'[+] 数据库初始化完成，正在启动服务器 (0.0.0.0:{PORT})...')
serve(app, host='0.0.0.0', port=PORT, threads=4)
