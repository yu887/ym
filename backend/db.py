"""
图书借阅小程序 — 数据库模块
支持 MySQL（生产环境）和 SQLite（本地开发），通过 DB_TYPE 环境变量切换。

MySQL:  DB_TYPE=mysql (默认) — 需要设置 DB_HOST/DB_USER/DB_PASSWORD/DB_NAME
SQLite: DB_TYPE=sqlite — 使用 library.db 文件，零配置
"""
import os
import time
import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_TYPE = os.environ.get('DB_TYPE', 'mysql')

# ── SQLite 支持：将 PyMySQL 的 %s 占位符自动转换为 SQLite 的 ? ────────
class _SQLiteCursorWrapper:
    """包装 sqlite3.Cursor，自动将 SQL 中的 %s 替换为 ?"""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        sql = sql.replace('%s', '?')
        if params is not None:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def executemany(self, sql, params):
        sql = sql.replace('%s', '?')
        return self._cursor.executemany(sql, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        # sqlite3.Row -> dict
        return {k: row[k] for k in row.keys()}

    def fetchall(self):
        return [{k: row[k] for k in row.keys()} for row in self._cursor.fetchall()]

    def close(self):
        return self._cursor.close()

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _SQLiteConnectionWrapper:
    """包装 sqlite3.Connection，返回包装后的游标"""
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

    def cursor(self):
        return _SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


# ── MySQL 支持 ────────────────────────────────────────────────────────
if DB_TYPE == 'mysql':
    import pymysql
    import pymysql.cursors

    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'library_system'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }

    def get_db_connection():
        return pymysql.connect(**DB_CONFIG)

    def wait_for_db(max_retries=30, delay=2):
        for attempt in range(1, max_retries + 1):
            try:
                conn = pymysql.connect(
                    host=DB_CONFIG['host'], port=DB_CONFIG['port'],
                    user=DB_CONFIG['user'], password=DB_CONFIG['password'],
                    database=DB_CONFIG['database'], charset=DB_CONFIG['charset'],
                    cursorclass=DB_CONFIG['cursorclass'],
                )
                conn.ping()
                conn.close()
                print(f'[DB] MySQL 已就绪（第 {attempt} 次尝试）')
                return
            except pymysql.err.OperationalError as e:
                print(f'[DB] 第 {attempt}/{max_retries} 次尝试：MySQL 尚未就绪（{e}）')
                if attempt == max_retries:
                    raise RuntimeError('MySQL 在限定时间内未能就绪') from e
                time.sleep(delay)

else:
    # SQLite 模式
    DB_PATH = os.environ.get('DB_PATH', 'library.db')

    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return _SQLiteConnectionWrapper(DB_PATH)

    def wait_for_db(max_retries=1, delay=0):
        print('[DB] SQLite 模式，无需等待数据库就绪')


def init_db():
    """创建数据库表（如果不存在），并插入种子数据。幂等操作，可安全重复调用。"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'mysql':
        # ── MySQL DDL ────────────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(50),
                email VARCHAR(100),
                phone VARCHAR(20),
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INT AUTO_INCREMENT PRIMARY KEY,
                isbn VARCHAR(20) NOT NULL UNIQUE,
                title VARCHAR(200) NOT NULL,
                author VARCHAR(100),
                publisher VARCHAR(100),
                publish_date VARCHAR(20),
                category VARCHAR(50),
                total_quantity INT DEFAULT 1,
                available_quantity INT DEFAULT 1,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS borrow_applications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, user_name VARCHAR(50),
                book_id INT NOT NULL, book_title VARCHAR(200),
                status VARCHAR(20) DEFAULT 'pending',
                application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                review_date TIMESTAMP NULL, review_user_id INT NULL,
                remark VARCHAR(500),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS borrow_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, user_name VARCHAR(50),
                book_id INT NOT NULL, book_title VARCHAR(200),
                book_author VARCHAR(100),
                borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date DATE NOT NULL, return_date TIMESTAMP NULL,
                status VARCHAR(20) DEFAULT 'borrowed',
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
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, type VARCHAR(20) NOT NULL,
                title VARCHAR(200) NOT NULL, content TEXT,
                is_read INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        # 兼容旧数据迁移
        cursor.execute("SHOW COLUMNS FROM borrow_applications")
        ba_columns = {row['Field'] for row in cursor.fetchall()}
        if 'user_name' not in ba_columns:
            cursor.execute('ALTER TABLE borrow_applications ADD COLUMN user_name VARCHAR(50)')
        if 'book_title' not in ba_columns:
            cursor.execute('ALTER TABLE borrow_applications ADD COLUMN book_title VARCHAR(200)')

        cursor.execute("SHOW COLUMNS FROM borrow_records")
        br_columns = {row['Field'] for row in cursor.fetchall()}
        for col_def in [
            ('user_name', 'VARCHAR(50)'),
            ('book_title', 'VARCHAR(200)'),
            ('book_author', 'VARCHAR(100)'),
            ('return_requested', 'INT DEFAULT 0'),
            ('return_request_date', 'TIMESTAMP NULL'),
            ('admin_confirm_returned', 'INT DEFAULT 0'),
            ('admin_confirm_date', 'TIMESTAMP NULL'),
            ('reminder_sent', 'INT DEFAULT 0'),
            ('due_soon_reminded', 'INT DEFAULT 0'),
            ('overdue_reminded', 'INT DEFAULT 0'),
        ]:
            if col_def[0] not in br_columns:
                cursor.execute(f'ALTER TABLE borrow_records ADD COLUMN {col_def[0]} {col_def[1]}')
    else:
        # ── SQLite DDL ───────────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
                name TEXT, email TEXT, phone TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT, title TEXT NOT NULL, author TEXT,
                publisher TEXT, publish_date TEXT, category TEXT,
                total_quantity INTEGER DEFAULT 1,
                available_quantity INTEGER DEFAULT 1,
                description TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS borrow_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, user_name TEXT,
                book_id INTEGER, book_title TEXT,
                status TEXT DEFAULT 'pending',
                application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                review_date TIMESTAMP, review_user_id INTEGER,
                remark TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, user_name TEXT,
                book_id INTEGER, book_title TEXT, book_author TEXT,
                borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TEXT, return_date TIMESTAMP,
                status TEXT DEFAULT 'borrowed',
                return_requested INTEGER DEFAULT 0,
                return_request_date TIMESTAMP,
                admin_confirm_returned INTEGER DEFAULT 0,
                admin_confirm_date TIMESTAMP,
                reminder_sent INTEGER DEFAULT 0,
                due_soon_reminded INTEGER DEFAULT 0,
                overdue_reminded INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, type TEXT, title TEXT,
                content TEXT, is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

    # ── 种子数据（MySQL 和 SQLite 共用，占位符由 cursor wrapper 自动转换）──
    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE username = 'admin'")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, name, role) VALUES (%s, %s, %s, %s)",
            ('admin', generate_password_hash('admin123'), '管理员', 'admin'))

    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE username = 'testuser'")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, name, role) VALUES (%s, %s, %s, %s)",
            ('testuser', generate_password_hash('123456'), '测试用户', 'user'))

    cursor.execute("SELECT COUNT(*) AS cnt FROM books")
    if cursor.fetchone()['cnt'] == 0:
        books = [
            ('978-7-111-54493-7', 'Python编程：从入门到实践', 'Eric Matthes',
             '人民邮电出版社', '2016-07', '编程', 5, 5, 'Python入门经典'),
            ('978-7-115-42857-7', 'JavaScript高级程序设计', 'Nicholas C. Zakas',
             '人民邮电出版社', '2017-10', '编程', 3, 3, 'JS权威指南'),
            ('978-7-111-42837-7', '深入理解计算机系统', 'Randal E. Bryant',
             '机械工业出版社', '2016-01', '计算机', 4, 4, 'CSAPP'),
            ('978-7-5086-6329-1', '三体', '刘慈欣',
             '重庆出版社', '2008-01', '科幻', 6, 6, '科幻经典'),
            ('978-7-5327-7972-8', '活着', '余华',
             '上海文艺出版社', '2012-08', '文学', 5, 5, '文学名著'),
            ('978-7-115-36547-8', 'Vue.js设计与实现', '霍春阳',
             '人民邮电出版社', '2022-01', '编程', 3, 3, 'Vue核心原理'),
            ('978-7-111-60374-6', '算法导论', 'Thomas H. Cormen',
             '机械工业出版社', '2022-03', '算法', 4, 4, '算法圣经'),
            ('978-7-5442-9116-2', '百年孤独', '加西亚·马尔克斯',
             '南海出版公司', '2011-06', '文学', 3, 3, '魔幻现实主义'),
        ]
        cursor.executemany('''
            INSERT INTO books
                (isbn, title, author, publisher, publish_date, category,
                 total_quantity, available_quantity, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', books)

    conn.commit()
    cursor.close()
    conn.close()
    print(f'[DB] 数据库表初始化完成（{DB_TYPE}）')
