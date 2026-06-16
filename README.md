
# 图书借阅小程序

一个基于 Python Flask + MySQL + Vue 3 的图书借阅管理系统。

## 功能特性

### 用户功能
- 图书查询（按书名、作者、ISBN搜索，按分类筛选）
- 借阅申请提交、查看、取消
- 借阅记录查看、申请归还
- 通知中心（借阅审批、到期提醒、归还确认，支持删除）

### 管理员功能
- 借阅申请审批（通过/拒绝）
- 借阅记录管理
- 图书管理（添加、删除）
- 用户管理
- 图书归还处理
- 逾期提醒功能

## 技术栈

### 后端
- Python 3.x
- Flask（Web框架）
- Flask-JWT-Extended（身份认证）
- Flask-CORS（跨域支持）
- PyMySQL（MySQL驱动）

### 前端
- Vue 3
- Vue Router（路由）
- Element Plus（UI组件库）
- Axios（HTTP客户端）

### 数据库
- SQLite（开发环境，开箱即用）
- MySQL 5.7+（生产环境，参见 `database/schema.sql`）

## 项目结构

```
图书借阅小程序/
├── backend/              # 后端代码
│   ├── app.py           # Flask主程序
│   ├── requirements.txt # Python依赖
│   └── .env             # 环境变量配置（可选）
├── frontend/            # 前端代码
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── utils/
│   │   │   └── api.js   # 共享Axios实例
│   │   ├── views/       # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Home.vue
│   │   │   └── Admin.vue
│   │   ├── router/      # 路由配置
│   │   │   └── index.js
│   │   ├── App.vue
│   │   └── main.js
│   ├── .env.development # 前端环境变量
│   └── package.json
└── database/            # 数据库
    └── schema.sql       # MySQL数据库表结构（生产环境用）
```

## 快速开始

### 1. 数据库配置

首先确保已安装 MySQL，然后创建数据库并导入表结构：

```bash
# 登录MySQL
mysql -u root -p

# 执行数据库脚本
source e:/ym/图书借阅小程序/database/schema.sql
```

### 2. 后端启动

```bash
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 运行后端服务
python app.py
```

后端服务将在 `http://localhost:5000` 启动

> **安全配置**: 可通过环境变量 `JWT_SECRET_KEY` 设置 JWT 密钥。创建 `backend/.env` 文件：
> ```
> JWT_SECRET_KEY=your-custom-secret-key
> ```

### 3. 前端启动

```bash
cd frontend

# 安装Node.js依赖
npm install

# 启动开发服务器
npm run serve
```

前端服务将在 `http://localhost:8080` 启动

## 测试账号

系统已预置测试账号：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 普通用户 | testuser | 123456 |

## API接口说明

### 认证相关
- `POST /api/login` - 用户登录
- `POST /api/register` - 用户注册
- `PUT /api/change-password` - 修改密码（需登录）

### 图书相关
- `GET /api/books` - 获取图书列表
- `GET /api/books/:id` - 获取图书详情
- `GET /api/categories` - 获取所有分类

### 借阅申请
- `POST /api/borrow-applications` - 提交借阅申请
- `GET /api/borrow-applications` - 用户查看自己的申请列表
- `DELETE /api/borrow-applications/:id` - 取消/删除申请
- `GET /api/admin/borrow-applications` - 管理员获取申请列表
- `POST /api/admin/borrow-applications/:id/approve` - 审批通过
- `POST /api/admin/borrow-applications/:id/reject` - 审批拒绝

### 借阅记录
- `GET /api/borrow-records` - 用户获取借阅记录
- `POST /api/borrow-records/:id/request-return` - 用户申请归还
- `GET /api/admin/borrow-records` - 管理员获取所有借阅记录
- `POST /api/admin/borrow-records/:id/confirm-return` - 管理员确认归还
- `DELETE /api/admin/borrow-records/:id` - 管理员删除记录

### 图书管理
- `POST /api/admin/books` - 添加图书
- `PUT /api/admin/books/:id` - 编辑图书
- `DELETE /api/admin/books/:id` - 删除图书

### 通知
- `GET /api/notifications` - 获取通知列表
- `PUT /api/notifications/:id/read` - 标记通知已读
- `DELETE /api/notifications/:id` - 删除通知

### 用户管理
- `GET /api/admin/users` - 获取用户列表
- `PUT /api/admin/users/:id` - 编辑用户信息
- `DELETE /api/admin/users/:id` - 删除用户

### 其他
- `POST /api/check-overdue` - 检查逾期并发送提醒

## 注意事项

1. 开发环境使用 SQLite，无需额外配置数据库
2. 生产环境请设置 `JWT_SECRET_KEY` 环境变量替换默认密钥
3. 生产环境建议切换到 MySQL，执行 `database/schema.sql` 建表并修改 `backend/app.py` 中的数据库连接
4. 建议设置定时任务调用 `/api/check-overdue` 接口检查逾期图书
5. 密码使用 werkzeug 哈希存储，安全可靠
6. 借阅上限为每人 5 本，可在 `backend/app.py` 中修改 `MAX_BORROW_LIMIT`

