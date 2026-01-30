from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_cors import CORS
from datetime import datetime
import json
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'iraqi_chat_secret_key_2024_change_this'
app.config['DATABASE'] = 'iraqi_chat.db'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            bio TEXT,
            age INTEGER,
            profile_pic TEXT DEFAULT 'default.png',
            country TEXT DEFAULT 'Iraq',
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP,
            is_online BOOLEAN DEFAULT 0
        )
    ''')
    
    # جدول الرسائل
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')
    
    # جدول الاتصالات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (contact_id) REFERENCES users (id),
            UNIQUE(user_id, contact_id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# المسارات الأساسية
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', user_id=session['user_id'])

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('profile.html')

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('search.html')

# واجهات API
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # التحقق من وجود المستخدم
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'اسم المستخدم أو الإيميل موجود بالفعل'}), 400
    
    # تسجيل المستخدم الجديد
    hashed_password = generate_password_hash(password)
    cursor.execute('''
        INSERT INTO users (username, email, password, created_at) 
        VALUES (?, ?, ?, ?)
    ''', (username, email, hashed_password, datetime.now()))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        'success': True,
        'message': 'تم التسجيل بنجاح',
        'user': {'id': user_id, 'username': username}
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if user and check_password_hash(user[3], password):
        session['user_id'] = user[0]
        session['username'] = user[1]
        
        # تحديث حالة الاتصال
        cursor.execute('UPDATE users SET is_online = 1, last_seen = ? WHERE id = ?', 
                      (datetime.now(), user[0]))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الدخول بنجاح',
            'user': {'id': user[0], 'username': user[1]}
        })
    
    conn.close()
    return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_online = 0 WHERE id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        
        session.clear()
    
    return jsonify({'success': True, 'message': 'تم تسجيل الخروج'})

@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, email, full_name, bio, age, profile_pic, 
               country, city, is_online, last_seen 
        FROM users WHERE id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'full_name': user[3],
            'bio': user[4],
            'age': user[5],
            'profile_pic': user[6],
            'country': user[7],
            'city': user[8],
            'is_online': bool(user[9]),
            'last_seen': user[10]
        })
    
    return jsonify({'error': 'المستخدم غير موجود'}), 404

@app.route('/api/profile/update', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET full_name = ?, bio = ?, age = ?, country = ?, city = ?
        WHERE id = ?
    ''', (data.get('full_name'), data.get('bio'), data.get('age'),
          data.get('country', 'Iraq'), data.get('city'), session['user_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم تحديث الملف الشخصي'})

@app.route('/api/users/search')
def search_users():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    query = request.args.get('q', '')
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, full_name, bio, profile_pic, is_online 
        FROM users 
        WHERE username LIKE ? OR full_name LIKE ? 
        AND id != ?
        LIMIT 20
    ''', (f'%{query}%', f'%{query}%', session['user_id']))
    
    users = cursor.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({
            'id': user[0],
            'username': user[1],
            'full_name': user[2],
            'bio': user[3],
            'profile_pic': user[4],
            'is_online': bool(user[5])
        })
    
    return jsonify(result)

@app.route('/api/messages/<int:receiver_id>')
def get_messages(receiver_id):
    if 'user_id' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.id, m.sender_id, m.receiver_id, m.message, m.timestamp, m.is_read,
               u1.username as sender_name, u2.username as receiver_name
        FROM messages m
        JOIN users u1 ON m.sender_id = u1.id
        JOIN users u2 ON m.receiver_id = u2.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) 
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.timestamp
    ''', (session['user_id'], receiver_id, receiver_id, session['user_id']))
    
    messages = cursor.fetchall()
    conn.close()
    
    result = []
    for msg in messages:
        result.append({
            'id': msg[0],
            'sender_id': msg[1],
            'receiver_id': msg[2],
            'message': msg[3],
            'timestamp': msg[4],
            'is_read': bool(msg[5]),
            'sender_name': msg[6],
            'receiver_name': msg[7]
        })
    
    return jsonify(result)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        emit('user_online', {'user_id': session['user_id'], 'username': session['username']}, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = session.get('user_id')
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    
    if not all([sender_id, receiver_id, message]):
        return
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # حفظ الرسالة في قاعدة البيانات
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, message) 
        VALUES (?, ?, ?)
    ''', (sender_id, receiver_id, message))
    
    message_id = cursor.lastrowid
    
    # الحصول على تفاصيل الرسالة
    cursor.execute('''
        SELECT m.*, u.username 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.id = ?
    ''', (message_id,))
    
    msg_data = cursor.fetchone()
    conn.commit()
    conn.close()
    
    # إرسال الرسالة إلى المستقبل
    emit('receive_message', {
        'id': msg_data[0],
        'sender_id': msg_data[1],
        'receiver_id': msg_data[2],
        'message': msg_data[3],
        'timestamp': msg_data[4],
        'sender_name': msg_data[7]
    }, room=f"user_{receiver_id}")
    
    # إرسال نسخة إلى المرسل
    emit('message_sent', {
        'id': msg_data[0],
        'sender_id': msg_data[1],
        'receiver_id': msg_data[2],
        'message': msg_data[3],
        'timestamp': msg_data[4],
        'sender_name': msg_data[7]
    }, room=f"user_{sender_id}")

@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_online = 0 WHERE id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        
        emit('user_offline', {'user_id': session['user_id']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
