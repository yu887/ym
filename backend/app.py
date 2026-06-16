from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from db import get_db_connection, init_db
import os

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'library-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
jwt = JWTManager(app)

def get_user_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def check_reminders():
    """后台定时任务：检查即将到期和逾期的图书记录"""
    now = datetime.now()
    three_days_later = (now + timedelta(days=3)).strftime('%Y-%m-%d')
    today = now.strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 即将到期提醒（到期前3天）
    cursor.execute('''
        SELECT br.*, b.title
        FROM borrow_records br
        JOIN books b ON br.book_id = b.id
        WHERE br.status = 'borrowed'
        AND br.due_date = %s
        AND br.due_soon_reminded = 0
    ''', (three_days_later,))
    for record in cursor.fetchall():
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, content)
            VALUES (%s, 'reminder', '即将到期提醒', %s)
        ''', (
            record['user_id'],
            f'您借阅的《{record["title"]}》将在3天后({record["due_date"]})到期，请及时归还！'
        ))
        cursor.execute('UPDATE borrow_records SET due_soon_reminded = 1 WHERE id = %s', (record['id'],))

    # 2. 逾期标记
    cursor.execute('''
        UPDATE borrow_records SET status = 'overdue'
        WHERE status = 'borrowed' AND due_date < %s
    ''', (today,))

    # 3. 逾期通知
    cursor.execute('''
        SELECT br.*, b.title
        FROM borrow_records br
        JOIN books b ON br.book_id = b.id
        WHERE br.status = 'overdue' AND br.overdue_reminded = 0
    ''')
    for record in cursor.fetchall():
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, content)
            VALUES (%s, 'reminder', '逾期提醒', %s)
        ''', (
            record['user_id'],
            f'您借阅的《{record["title"]}》已逾期（到期日: {record["due_date"]}），请尽快归还！'
        ))
        cursor.execute('UPDATE borrow_records SET overdue_reminded = 1 WHERE id = %s', (record['id'],))

    conn.commit()
    cursor.close()
    conn.close()

# 启动归还提醒后台调度器（每隔60秒检查一次）
scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', seconds=60, id='reminder_check')
scheduler.start()

# ── 健康检查 & 调试 ────────────────────────────────────────────
@app.route('/ping')
def ping():
    """无需数据库的健康检查"""
    import sys
    return jsonify({
        'status': 'ok',
        'python': sys.version,
        'db_type': os.environ.get('DB_TYPE', 'mysql'),
    })

@app.route('/api/health')
def health():
    """带数据库的健康检查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) AS cnt FROM users')
        user_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM books')
        book_count = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()
        return jsonify({
            'status': 'ok',
            'db_type': os.environ.get('DB_TYPE', 'mysql'),
            'users': user_count,
            'books': book_count,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({'message': '用户名或密码错误'}), 401

    user_dict = dict(user)

    # 检查密码: 先尝试哈希验证, 失败则尝试明文比对(兼容旧数据)
    if check_password_hash(user_dict['password'], password):
        pass  # 哈希密码验证通过
    elif user_dict['password'] == password:
        # 旧明文密码, 自动升级为哈希存储
        cursor.execute('UPDATE users SET password = %s WHERE id = %s',
            (generate_password_hash(password), user_dict['id']))
        conn.commit()
    else:
        cursor.close()
        conn.close()
        return jsonify({'message': '用户名或密码错误'}), 401

    cursor.close()
    conn.close()

    # 返回用户信息时排除密码字段
    user_dict.pop('password', None)
    access_token = create_access_token(identity=str(user_dict['id']))
    return jsonify({'token': access_token, 'user': user_dict}), 200

@app.route('/api/books', methods=['GET'])
def get_books():
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = 'SELECT * FROM books WHERE 1=1'
    params = []
    
    if keyword:
        sql += " AND (title LIKE %s OR author LIKE %s OR isbn LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
    
    if category:
        sql += ' AND category = %s'
        params.append(category)
    
    cursor.execute(sql, params)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([dict(book) for book in books]), 200

@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if book:
        return jsonify(dict(book)), 200
    return jsonify({'message': '图书不存在'}), 404

@app.route('/api/borrow-applications', methods=['POST'])
@jwt_required()
def create_borrow_application():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    book_id = data.get('book_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    current_user = cursor.fetchone()
    
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'message': '图书不存在'}), 404
    
    if book['available_quantity'] <= 0:
        return jsonify({'message': '图书库存不足'}), 400

    # 检查用户当前借阅数量是否达到上限
    cursor.execute('SELECT COUNT(*) AS cnt FROM borrow_records WHERE user_id = %s AND status = %s', (user_id, 'borrowed'))
    borrow_count = cursor.fetchone()['cnt']
    MAX_BORROW_LIMIT = 5
    if borrow_count >= MAX_BORROW_LIMIT:
        cursor.close()
        conn.close()
        return jsonify({'message': f'您已达到借阅上限({MAX_BORROW_LIMIT}本)，请先归还图书再借阅'}), 400

    cursor.execute(
        'INSERT INTO borrow_applications (user_id, user_name, book_id, book_title) VALUES (%s, %s, %s, %s)',
        (user_id, current_user['username'], book_id, book['title'])
    )
    conn.commit()
    
    cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
    admin_id = cursor.fetchone()['id']

    cursor.execute(
        'INSERT INTO notifications (user_id, type, title, content) VALUES (%s, "approval", %s, %s)',
        (admin_id, f'借阅申请: {book["title"]}', f'用户 {current_user["username"]} 申请借阅《{book["title"]}》')
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({'message': '申请提交成功'}), 201

@app.route('/api/borrow-applications', methods=['GET'])
@jwt_required()
def get_my_applications():
    """用户查看自己的借阅申请"""
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ba.*, b.title as book_title, b.author as book_author
        FROM borrow_applications ba
        LEFT JOIN books b ON ba.book_id = b.id
        WHERE ba.user_id = %s
        ORDER BY ba.application_date DESC
    ''', (user_id,))
    applications = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(app) for app in applications]), 200

@app.route('/api/borrow-applications/<int:app_id>', methods=['DELETE'])
@jwt_required()
def cancel_application(app_id):
    """用户取消待审批申请 或 管理员删除申请"""
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM borrow_applications WHERE id = %s', (app_id,))
    application = cursor.fetchone()
    if not application:
        cursor.close()
        conn.close()
        return jsonify({'message': '申请不存在'}), 404

    # 管理员可以删除任意申请
    current_user = dict(cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)).fetchone())
    is_admin = current_user.get('role') == 'admin'

    if not is_admin:
        # 普通用户只能取消自己的待审批申请
        if application['user_id'] != user_id:
            cursor.close()
            conn.close()
            return jsonify({'message': '权限不足'}), 403
        if application['status'] != 'pending':
            cursor.close()
            conn.close()
            return jsonify({'message': '只能取消待审批的申请'}), 400

    cursor.execute('DELETE FROM borrow_applications WHERE id = %s', (app_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': '申请已删除'}), 200

@app.route('/api/borrow-records', methods=['GET'])
@jwt_required()
def get_borrow_records():
    user_id = int(get_jwt_identity())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT br.*, b.title, b.author 
        FROM borrow_records br 
        JOIN books b ON br.book_id = b.id 
        WHERE br.user_id = %s 
        ORDER BY br.borrow_date DESC
    ''', (user_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([dict(record) for record in records]), 200

@app.route('/api/borrow-records/<int:record_id>/request-return', methods=['POST'])
@jwt_required()
def request_return(record_id):
    user_id = int(get_jwt_identity())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM borrow_records WHERE id = %s AND user_id = %s', (record_id, user_id))
    record = cursor.fetchone()
    
    if not record:
        cursor.close()
        conn.close()
        return jsonify({'message': '记录不存在'}), 404
    
    if record['status'] != 'borrowed':
        cursor.close()
        conn.close()
        return jsonify({'message': '该记录已归还或已逾期'}), 400
    
    if record['return_requested'] == 1:
        cursor.close()
        conn.close()
        return jsonify({'message': '已申请归还，等待管理员确认'}), 400
    
    cursor.execute('''
        UPDATE borrow_records 
        SET return_requested = 1, return_request_date = CURRENT_TIMESTAMP 
        WHERE id = %s
    ''', (record_id,))
    
    cursor.execute('SELECT * FROM books WHERE id = %s', (record['book_id'],))
    book = cursor.fetchone()
    
    cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
    admin_id = cursor.fetchone()['id']

    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    current_user = cursor.fetchone()
    
    cursor.execute(
        'INSERT INTO notifications (user_id, type, title, content) VALUES (%s, "return", %s, %s)',
        (admin_id, f'归还申请: {book["title"]}', f'用户 {current_user["username"]} 申请归还《{book["title"]}》')
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '归还申请已提交，请等待管理员确认'}), 200

@app.route('/api/admin/borrow-applications', methods=['GET'])
@jwt_required()
def admin_get_applications():
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    status = request.args.get('status', 'pending')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ba.*, u.username, u.name as user_name, b.title, b.author 
        FROM borrow_applications ba 
        LEFT JOIN users u ON ba.user_id = u.id 
        LEFT JOIN books b ON ba.book_id = b.id 
        WHERE ba.status = %s
        ORDER BY ba.application_date DESC
    ''', (status,))
    applications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for app in applications:
        app_dict = dict(app)
        # 优先使用记录中存储的用户名称，避免用户被删除后名称丢失
        if app_dict.get('user_name'):
            app_dict['display_user_name'] = app_dict['user_name']
        elif app_dict.get('username'):
            app_dict['display_user_name'] = app_dict['username']
        else:
            app_dict['display_user_name'] = '未知用户'
        
        # 优先使用记录中存储的图书标题
        if app_dict.get('book_title'):
            app_dict['display_book_title'] = app_dict['book_title']
        elif app_dict.get('title'):
            app_dict['display_book_title'] = app_dict['title']
        else:
            app_dict['display_book_title'] = '未知图书'
        
        result.append(app_dict)
    
    return jsonify(result), 200

@app.route('/api/admin/borrow-applications/<int:app_id>/approve', methods=['POST'])
@jwt_required()
def approve_application(app_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM borrow_applications WHERE id = %s', (app_id,))
    application = cursor.fetchone()
    
    if not application or application['status'] != 'pending':
        return jsonify({'message': '申请不存在或已处理'}), 400
    
    cursor.execute('SELECT * FROM books WHERE id = %s', (application['book_id'],))
    book = cursor.fetchone()
    
    if book['available_quantity'] <= 0:
        return jsonify({'message': '库存不足'}), 400
    
    due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    cursor.execute(
        'INSERT INTO borrow_records (user_id, user_name, book_id, book_title, book_author, due_date) VALUES (%s, %s, %s, %s, %s, %s)',
        (application['user_id'], application['user_name'], application['book_id'], book['title'], book['author'], due_date)
    )
    
    cursor.execute(
        'UPDATE books SET available_quantity = available_quantity - 1 WHERE id = %s',
        (application['book_id'],)
    )
    
    cursor.execute(
        'UPDATE borrow_applications SET status = %s, review_date = CURRENT_TIMESTAMP, review_user_id = %s WHERE id = %s',
        ('approved', user_id, app_id)
    )
    
    cursor.execute(
        'INSERT INTO notifications (user_id, type, title, content) VALUES (%s, "borrow", %s, %s)',
        (application['user_id'], '借阅通知', f'您已借阅《{book["title"]}》，请在三天内归还！到期日: {due_date}')
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '审批通过'}), 200

@app.route('/api/admin/borrow-applications/<int:app_id>/reject', methods=['POST'])
@jwt_required()
def reject_application(app_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    data = request.get_json()
    remark = data.get('remark', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM borrow_applications WHERE id = %s', (app_id,))
    application = cursor.fetchone()
    
    if not application or application['status'] != 'pending':
        return jsonify({'message': '申请不存在或已处理'}), 400
    
    cursor.execute('SELECT * FROM books WHERE id = %s', (application['book_id'],))
    book = cursor.fetchone()
    
    cursor.execute(
        'UPDATE borrow_applications SET status = %s, review_date = CURRENT_TIMESTAMP, review_user_id = %s, remark = %s WHERE id = %s',
        ('rejected', user_id, remark, app_id)
    )
    
    cursor.execute(
        'INSERT INTO notifications (user_id, type, title, content) VALUES (%s, "borrow", %s, %s)',
        (application['user_id'], '借阅申请被拒绝', f'您借阅《{book["title"]}》的申请被拒绝: {remark}')
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '已拒绝申请'}), 200

@app.route('/api/admin/borrow-records', methods=['GET'])
@jwt_required()
def admin_get_borrow_records():
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT br.*, u.username, u.name as user_name, b.title, b.author 
        FROM borrow_records br 
        LEFT JOIN users u ON br.user_id = u.id 
        LEFT JOIN books b ON br.book_id = b.id 
        ORDER BY br.borrow_date DESC
    ''')
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for record in records:
        record_dict = dict(record)
        # 优先使用记录中存储的用户名称
        if record_dict.get('user_name'):
            record_dict['display_user_name'] = record_dict['user_name']
        elif record_dict.get('username'):
            record_dict['display_user_name'] = record_dict['username']
        else:
            record_dict['display_user_name'] = '未知用户'
        
        # 优先使用记录中存储的图书信息
        if record_dict.get('book_title'):
            record_dict['display_book_title'] = record_dict['book_title']
        elif record_dict.get('title'):
            record_dict['display_book_title'] = record_dict['title']
        else:
            record_dict['display_book_title'] = '未知图书'
        
        if record_dict.get('book_author'):
            record_dict['display_book_author'] = record_dict['book_author']
        elif record_dict.get('author'):
            record_dict['display_book_author'] = record_dict['author']
        else:
            record_dict['display_book_author'] = '未知作者'
        
        result.append(record_dict)
    
    return jsonify(result), 200

@app.route('/api/admin/borrow-records/<int:record_id>/confirm-return', methods=['POST'])
@jwt_required()
def confirm_return(record_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM borrow_records WHERE id = %s', (record_id,))
    record = cursor.fetchone()
    
    if not record or record['status'] != 'borrowed':
        return jsonify({'message': '记录不存在或已归还'}), 400
    
    # 检查用户是否已经申请归还
    if record['return_requested'] != 1:
        return jsonify({'message': '用户尚未申请归还，请等待用户申请'}), 400
    
    # 检查管理员是否已经确认
    if record['admin_confirm_returned'] == 1:
        return jsonify({'message': '管理员已确认归还'}), 400
    
    # 管理员确认归还
    cursor.execute('''
        UPDATE borrow_records 
        SET admin_confirm_returned = 1, admin_confirm_date = CURRENT_TIMESTAMP 
        WHERE id = %s
    ''', (record_id,))
    
    # 双方都确认，完成归还
    cursor.execute('''
        UPDATE borrow_records 
        SET status = "returned", return_date = CURRENT_TIMESTAMP 
        WHERE id = %s
    ''', (record_id,))
    
    cursor.execute(
        'UPDATE books SET available_quantity = available_quantity + 1 WHERE id = %s',
        (record['book_id'],)
    )
    
    cursor.execute('SELECT * FROM books WHERE id = %s', (record['book_id'],))
    book = cursor.fetchone()
    
    cursor.execute(
        'INSERT INTO notifications (user_id, type, title, content) VALUES (%s, "return", %s, %s)',
        (record['user_id'], '图书已归还', f'您借阅的《{book["title"]}》已成功归还！')
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '归还成功！双方已确认，图书已归还'}), 200

@app.route('/api/admin/borrow-records/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_borrow_record(record_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM borrow_records WHERE id = %s', (record_id,))
    record = cursor.fetchone()
    if not record:
        cursor.close()
        conn.close()
        return jsonify({'message': '记录不存在'}), 404

    if record['status'] == 'borrowed':
        cursor.close()
        conn.close()
        return jsonify({'message': '不能删除借阅中的记录，请先归还'}), 400

    cursor.execute('DELETE FROM borrow_records WHERE id = %s', (record_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': '借阅记录已删除'}), 200

@app.route('/api/admin/books', methods=['POST'])
@jwt_required()
def create_book():
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO books (isbn, title, author, publisher, publish_date, category, total_quantity, available_quantity, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['isbn'], data['title'], data['author'], data['publisher'],
            data.get('publish_date'), data['category'],
            data['total_quantity'], data['total_quantity'], data.get('description', '')
        ))
        conn.commit()
        book_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'message': '图书添加成功', 'id': book_id}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@app.route('/api/admin/books/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查找所有与该图书相关的借阅记录
    cursor.execute('SELECT * FROM borrow_records WHERE book_id = %s AND status = "borrowed"', (book_id,))
    borrow_records = cursor.fetchall()
    
    # 将这些借阅记录标记为已归还
    for record in borrow_records:
        cursor.execute('''
            UPDATE borrow_records 
            SET status = 'returned', return_date = NOW()
            WHERE id = %s
        ''', (record['id'],))
    
    # 删除图书
    cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '图书删除成功'}), 200

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    ''', (user_id,))
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([dict(notif) for notif in notifications]), 200

@app.route('/api/notifications/<int:notif_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notif_id):
    user_id = int(get_jwt_identity())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s',
        (notif_id, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '已标记为已读'}), 200

@app.route('/api/notifications/<int:notif_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notif_id):
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notifications WHERE id = %s AND user_id = %s', (notif_id, user_id))
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({'message': '通知不存在或权限不足'}), 404
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': '通知已删除'}), 200

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, name, email, phone, role, created_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([dict(user) for user in users]), 200

@app.route('/api/check-overdue', methods=['POST'])
def check_overdue():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE borrow_records 
        SET status = 'overdue' 
        WHERE status = 'borrowed' AND due_date < CURDATE()
    ''')
    
    cursor.execute('''
        SELECT br.*, u.name as user_name, u.email, b.title 
        FROM borrow_records br 
        JOIN users u ON br.user_id = u.id 
        JOIN books b ON br.book_id = b.id 
        WHERE br.status = 'overdue'
    ''')
    
    overdue_records = cursor.fetchall()
    
    for record in overdue_records:
        cursor.execute('''
            SELECT COUNT(*) AS cnt FROM notifications
            WHERE user_id = %s AND type = 'remind' AND content LIKE %s
        ''', (record['user_id'], f'%{record["title"]}%'))
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute('''
                INSERT INTO notifications (user_id, type, title, content)
                VALUES (%s, 'remind', %s, %s)
            ''', (
                record['user_id'],
                '图书到期提醒',
                f'您借阅的《{record["title"]}》已逾期，请尽快归还！'
            ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': '逾期检查完成', 'count': len(overdue_records)}), 200

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    name = data.get('name', username)  # 默认使用用户名作为姓名

    if not username or not password:
        return jsonify({'message': '用户名和密码不能为空'}), 400

    if password != confirm_password:
        return jsonify({'message': '两次输入的密码不一致'}), 400

    if username == password:
        return jsonify({'message': '用户名和密码不能相同'}), 400

    if len(password) < 6:
        return jsonify({'message': '密码长度不能少于6位'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'message': '用户名已存在'}), 400

    hashed_password = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO users (username, password, name, role) VALUES (%s, %s, %s, %s)',
        (username, hashed_password, name, 'user')
    )
    conn.commit()

    cursor.execute('SELECT * FROM users WHERE id = %s', (cursor.lastrowid,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    user_dict = dict(user)
    user_dict.pop('password', None)
    access_token = create_access_token(identity=str(user_dict['id']))
    return jsonify({'token': access_token, 'user': user_dict}), 201

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = int(get_jwt_identity())
    current_user = get_user_info(current_user_id)
    if not current_user or current_user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403
    
    if current_user_id == user_id:
        return jsonify({'message': '不能删除自己'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'message': '用户不存在'}), 404
    
    cursor.execute('SELECT * FROM borrow_records WHERE user_id = %s AND status = "borrowed"', (user_id,))
    borrow_records = cursor.fetchall()
    
    for record in borrow_records:
        cursor.execute('''
            UPDATE borrow_records 
            SET status = 'returned', return_date = NOW()
            WHERE id = %s
        ''', (record['id'],))
        
        cursor.execute('''
            UPDATE books 
            SET available_quantity = available_quantity + 1 
            WHERE id = %s
        ''', (record['book_id'],))
    
    cursor.execute('DELETE FROM notifications WHERE user_id = %s', (user_id,))
    
    cursor.execute('DELETE FROM borrow_applications WHERE user_id = %s', (user_id,))
    
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({'message': '用户删除成功'}), 200

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != "" ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(categories), 200


@app.route('/api/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'message': '旧密码和新密码不能为空'}), 400
    if len(new_password) < 6:
        return jsonify({'message': '新密码长度不能少于6位'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()

    if not check_password_hash(user['password'], old_password) and user['password'] != old_password:
        cursor.close()
        conn.close()
        return jsonify({'message': '旧密码错误'}), 400

    cursor.execute('UPDATE users SET password = %s WHERE id = %s',
        (generate_password_hash(new_password), user_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '密码修改成功'}), 200


@app.route('/api/admin/books/<int:book_id>', methods=['PUT'])
@jwt_required()
def update_book(book_id):
    user_id = int(get_jwt_identity())
    user = get_user_info(user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403

    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        conn.close()
        return jsonify({'message': '图书不存在'}), 404

    # 计算新的可借数量: total_quantity变化量
    new_total = data.get('total_quantity', book['total_quantity'])
    quantity_diff = new_total - book['total_quantity']
    new_available = max(0, book['available_quantity'] + quantity_diff)

    cursor.execute('''
        UPDATE books SET isbn=%s, title=%s, author=%s, publisher=%s, publish_date=%s,
        category=%s, total_quantity=%s, available_quantity=%s, description=%s
        WHERE id=%s
    ''', (
        data.get('isbn', book['isbn']),
        data.get('title', book['title']),
        data.get('author', book['author']),
        data.get('publisher', book['publisher']),
        data.get('publish_date', book['publish_date']),
        data.get('category', book['category']),
        new_total,
        new_available,
        data.get('description', book['description']),
        book_id
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '图书更新成功'}), 200


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user_admin(user_id):
    current_user_id = int(get_jwt_identity())
    current_user = get_user_info(current_user_id)
    if not current_user or current_user['role'] != 'admin':
        return jsonify({'message': '权限不足'}), 403

    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    target_user = cursor.fetchone()
    if not target_user:
        cursor.close()
        conn.close()
        return jsonify({'message': '用户不存在'}), 404

    cursor.execute('''
        UPDATE users SET name=%s, email=%s, phone=%s, role=%s
        WHERE id=%s
    ''', (
        data.get('name', target_user['name']),
        data.get('email', target_user['email']),
        data.get('phone', target_user['phone']),
        data.get('role', target_user['role']),
        user_id
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '用户更新成功'}), 200


# 生产模式：托管前端静态文件
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

@app.route('/')
def serve_index():
    """根路径返回前端首页"""
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if os.path.isfile(index_path):
        return send_file(index_path)
    return jsonify({'message': 'Frontend not built'}), 404


@app.route('/<path:path>')
def serve_static(path):
    """静态文件 + SPA fallback（不拦截 /api/ 路由）"""
    # 尝试直接匹配静态文件（JS/CSS/图片等）
    file_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    # SPA fallback：非静态文件的路径返回 index.html
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if os.path.isfile(index_path) and not path.startswith('api/'):
        return send_file(index_path)
    # API 路径返回 404 JSON
    return jsonify({'message': 'Not Found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)