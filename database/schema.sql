-- ============================================================
-- 图书借阅小程序 — MySQL 数据库表结构（完整参考）
-- 注意：程序启动时会自动调用 init_db() 建表和插入种子数据，
--       此文件作为手动建库的参考，也会在 MySQL 容器首次初始化时执行。
-- ============================================================

CREATE DATABASE IF NOT EXISTS library_system
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE library_system;

-- ── 用户表 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 图书表 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100),
    publisher VARCHAR(100),
    publish_date VARCHAR(20),
    category VARCHAR(50),
    total_quantity INT NOT NULL DEFAULT 1,
    available_quantity INT NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_isbn (isbn),
    INDEX idx_title (title),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 借阅申请表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS borrow_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    user_name VARCHAR(50),
    book_id INT NOT NULL,
    book_title VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_date TIMESTAMP NULL,
    review_user_id INT NULL,
    remark VARCHAR(500),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_book_id (book_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 借阅记录表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS borrow_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    user_name VARCHAR(50),
    book_id INT NOT NULL,
    book_title VARCHAR(200),
    book_author VARCHAR(100),
    borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NOT NULL,
    return_date TIMESTAMP NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'borrowed',
    return_requested INT DEFAULT 0,
    return_request_date TIMESTAMP NULL,
    admin_confirm_returned INT DEFAULT 0,
    admin_confirm_date TIMESTAMP NULL,
    reminder_sent INT DEFAULT 0,
    due_soon_reminded INT DEFAULT 0,
    overdue_reminded INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_book_id (book_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 通知表 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    is_read INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 种子数据 ────────────────────────────────────────────────
-- 注意：密码由 app 的 init_db() 使用 werkzeug 哈希加密存储。
--       以下 INSERT 语句在 MySQL 首次初始化时执行（明文密码），
--       但 app 的 login() 会自动将明文密码升级为哈希。

INSERT IGNORE INTO users (username, password, name, role) VALUES
    ('admin', 'admin123', '管理员', 'admin'),
    ('testuser', '123456', '测试用户', 'user');

INSERT IGNORE INTO books (isbn, title, author, publisher, publish_date, category, total_quantity, available_quantity, description) VALUES
    ('978-7-111-54493-7', 'Python编程：从入门到实践', 'Eric Matthes', '人民邮电出版社', '2016-07', '编程', 5, 5, 'Python入门经典'),
    ('978-7-115-42857-7', 'JavaScript高级程序设计', 'Nicholas C. Zakas', '人民邮电出版社', '2017-10', '编程', 3, 3, 'JS权威指南'),
    ('978-7-111-42837-7', '深入理解计算机系统', 'Randal E. Bryant', '机械工业出版社', '2016-01', '计算机', 4, 4, 'CSAPP'),
    ('978-7-5086-6329-1', '三体', '刘慈欣', '重庆出版社', '2008-01', '科幻', 6, 6, '科幻经典'),
    ('978-7-5327-7972-8', '活着', '余华', '上海文艺出版社', '2012-08', '文学', 5, 5, '文学名著'),
    ('978-7-115-36547-8', 'Vue.js设计与实现', '霍春阳', '人民邮电出版社', '2022-01', '编程', 3, 3, 'Vue核心原理'),
    ('978-7-111-60374-6', '算法导论', 'Thomas H. Cormen', '机械工业出版社', '2022-03', '算法', 4, 4, '算法圣经'),
    ('978-7-5442-9116-2', '百年孤独', '加西亚·马尔克斯', '南海出版公司', '2011-06', '文学', 3, 3, '魔幻现实主义');
