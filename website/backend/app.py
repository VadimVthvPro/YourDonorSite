#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Твой Донор - Flask API сервер
"""

import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'your_donor'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
    'port': os.getenv('DB_PORT', 5432)
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD', 'doctor2024')

# ============================================
# Утилиты БД
# ============================================

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, args)
        if commit:
            conn.commit()
            if cur.description:
                rv = cur.fetchall()
                return (rv[0] if rv else None) if one else rv
            return cur.rowcount
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        raise e
    finally:
        cur.close()

def generate_token():
    return secrets.token_urlsafe(64)

# ============================================
# Авторизация
# ============================================

def require_auth(user_type=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Требуется авторизация'}), 401
            
            session = query_db(
                """SELECT * FROM user_sessions 
                   WHERE session_token = %s AND is_active = TRUE AND expires_at > NOW()""",
                (token,), one=True
            )
            
            if not session:
                return jsonify({'error': 'Сессия истекла'}), 401
            
            if user_type and session['user_type'] != user_type:
                return jsonify({'error': 'Нет доступа'}), 403
            
            g.session = session
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============================================
# API: Регионы и районы
# ============================================

@app.route('/api/regions', methods=['GET'])
def get_regions():
    regions = query_db("SELECT id, name FROM regions ORDER BY id")
    return jsonify(regions)

@app.route('/api/regions/<int:region_id>/districts', methods=['GET'])
def get_districts(region_id):
    districts = query_db(
        "SELECT id, name FROM districts WHERE region_id = %s ORDER BY name",
        (region_id,)
    )
    return jsonify(districts)

# ============================================
# API: Медцентры
# ============================================

@app.route('/api/medcenters', methods=['GET'])
def get_medcenters():
    district_id = request.args.get('district_id')
    region_id = request.args.get('region_id')
    
    query = """
        SELECT mc.id, mc.name, mc.address, mc.email, mc.is_blood_center,
               mc.district_id, d.name as district_name, r.name as region_name, r.id as region_id
        FROM medical_centers mc
        LEFT JOIN districts d ON mc.district_id = d.id
        LEFT JOIN regions r ON d.region_id = r.id
        WHERE mc.is_active = TRUE
    """
    params = []
    
    if district_id:
        query += " AND mc.district_id = %s"
        params.append(district_id)
    elif region_id:
        query += " AND d.region_id = %s"
        params.append(region_id)
    
    query += " ORDER BY mc.name"
    
    medcenters = query_db(query, tuple(params))
    return jsonify(medcenters)

@app.route('/api/medcenters/<int:mc_id>', methods=['GET'])
def get_medcenter(mc_id):
    mc = query_db(
        """SELECT mc.*, d.name as district_name, r.name as region_name, r.id as region_id
           FROM medical_centers mc
           LEFT JOIN districts d ON mc.district_id = d.id
           LEFT JOIN regions r ON d.region_id = r.id
           WHERE mc.id = %s""",
        (mc_id,), one=True
    )
    if not mc:
        return jsonify({'error': 'Медцентр не найден'}), 404
    return jsonify(mc)

@app.route('/api/medcenters', methods=['POST'])
def register_medcenter():
    """Регистрация нового медцентра"""
    data = request.json
    
    required = ['name', 'district_id', 'email']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    # Проверяем существует ли
    existing = query_db(
        "SELECT id FROM medical_centers WHERE name = %s AND district_id = %s",
        (data['name'], data['district_id']), one=True
    )
    
    if existing:
        return jsonify({'error': 'Медцентр уже зарегистрирован'}), 400
    
    query_db(
        """INSERT INTO medical_centers (name, district_id, address, email, phone, is_blood_center)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            data['name'],
            data['district_id'],
            data.get('address'),
            data['email'],
            data.get('phone'),
            data.get('is_blood_center', False)
        ), commit=True
    )
    
    mc = query_db(
        "SELECT id, name FROM medical_centers WHERE name = %s AND district_id = %s",
        (data['name'], data['district_id']), one=True
    )
    
    # Инициализируем светофор
    blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    for bt in blood_types:
        query_db(
            "INSERT INTO blood_needs (medical_center_id, blood_type, status) VALUES (%s, %s, 'normal')",
            (mc['id'], bt), commit=True
        )
    
    # Создаём сессию
    token = generate_token()
    query_db(
        """INSERT INTO user_sessions (medical_center_id, session_token, user_type, expires_at)
           VALUES (%s, %s, 'medcenter', NOW() + INTERVAL '24 hours')""",
        (mc['id'], token), commit=True
    )
    
    return jsonify({
        'message': 'Медцентр зарегистрирован',
        'token': token,
        'medical_center': mc
    }), 201

# ============================================
# API: Авторизация донора
# ============================================

@app.route('/api/donor/register', methods=['POST'])
def register_donor():
    data = request.json
    
    required = ['full_name', 'birth_year', 'blood_type', 'medical_center_id']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    # Проверяем группу крови
    valid_blood = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if data['blood_type'] not in valid_blood:
        return jsonify({'error': 'Неверная группа крови'}), 400
    
    # Проверяем существует ли
    existing = query_db(
        """SELECT id FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s""",
        (data['full_name'], data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    if existing:
        return jsonify({'error': 'Донор уже зарегистрирован'}), 400
    
    # Получаем район медцентра
    mc = query_db(
        """SELECT mc.district_id, d.region_id
           FROM medical_centers mc
           JOIN districts d ON mc.district_id = d.id
           WHERE mc.id = %s""",
        (data['medical_center_id'],), one=True
    )
    
    if not mc:
        return jsonify({'error': 'Медцентр не найден'}), 404
    
    query_db(
        """INSERT INTO users 
           (full_name, birth_year, blood_type, medical_center_id, 
            region_id, district_id, city, phone, email, telegram_username)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data['full_name'],
            data['birth_year'],
            data['blood_type'],
            data['medical_center_id'],
            mc['region_id'],
            mc['district_id'],
            data.get('city'),
            data.get('phone'),
            data.get('email'),
            data.get('telegram_username')
        ), commit=True
    )
    
    user = query_db(
        """SELECT id, full_name, blood_type FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s""",
        (data['full_name'], data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    token = generate_token()
    query_db(
        """INSERT INTO user_sessions (user_id, session_token, user_type, expires_at)
           VALUES (%s, %s, 'donor', NOW() + INTERVAL '7 days')""",
        (user['id'], token), commit=True
    )
    
    return jsonify({
        'message': 'Регистрация успешна',
        'token': token,
        'user': user
    }), 201

@app.route('/api/donor/login', methods=['POST'])
def login_donor():
    data = request.json
    
    required = ['full_name', 'birth_year', 'medical_center_id']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    user = query_db(
        """SELECT id, full_name, blood_type FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s AND is_active = TRUE""",
        (data['full_name'], data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    if not user:
        return jsonify({'error': 'Донор не найден. Сначала зарегистрируйтесь.'}), 404
    
    token = generate_token()
    query_db(
        """INSERT INTO user_sessions (user_id, session_token, user_type, expires_at)
           VALUES (%s, %s, 'donor', NOW() + INTERVAL '7 days')""",
        (user['id'], token), commit=True
    )
    
    query_db("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],), commit=True)
    
    return jsonify({
        'message': 'Вход выполнен',
        'token': token,
        'user': user
    })

@app.route('/api/donor/profile', methods=['GET'])
@require_auth('donor')
def get_donor_profile():
    user = query_db(
        """SELECT u.*, mc.name as medical_center_name, mc.address as medical_center_address,
                  mc.phone as medical_center_phone, mc.email as medical_center_email,
                  d.name as district_name, r.name as region_name
           FROM users u
           LEFT JOIN medical_centers mc ON u.medical_center_id = mc.id
           LEFT JOIN districts d ON u.district_id = d.id
           LEFT JOIN regions r ON u.region_id = r.id
           WHERE u.id = %s""",
        (g.session['user_id'],), one=True
    )
    
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    return jsonify(user)

@app.route('/api/donor/profile', methods=['PUT'])
@require_auth('donor')
def update_donor_profile():
    data = request.json
    allowed = ['phone', 'email', 'telegram_username', 'city', 'notify_urgent', 'notify_low']
    
    updates = []
    values = []
    for field in allowed:
        if field in data:
            updates.append(f"{field} = %s")
            values.append(data[field])
    
    if updates:
        values.append(g.session['user_id'])
        query_db(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(values), commit=True)
    
    return jsonify({'message': 'Профиль обновлён'})

# ============================================
# API: Авторизация медцентра
# ============================================

@app.route('/api/medcenter/register', methods=['POST'])
def register_medcenter_with_password():
    """Регистрация нового медцентра с паролем"""
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Укажите название медцентра'}), 400
    if not data.get('email'):
        return jsonify({'error': 'Укажите email медцентра'}), 400
    if not data.get('password') or len(data.get('password', '')) < 6:
        return jsonify({'error': 'Пароль должен быть не менее 6 символов'}), 400
    
    # Проверяем существует ли медцентр с таким email
    existing = query_db(
        "SELECT id FROM medical_centers WHERE email = %s",
        (data['email'],), one=True
    )
    
    if existing:
        return jsonify({'error': 'Медцентр с таким email уже зарегистрирован'}), 400
    
    # Создаём медцентр
    try:
        query_db(
            """INSERT INTO medical_centers (name, district_id, address, email, phone, is_blood_center, master_password)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (data['name'], data.get('district_id'), data.get('address'), 
             data['email'], data.get('phone'), data.get('is_blood_center', False), 
             data['password']), commit=True
        )
        
        # Получаем созданный медцентр
        mc = query_db(
            """SELECT mc.id, mc.name, mc.address, mc.email, mc.is_blood_center,
                      d.name as district_name, r.name as region_name
               FROM medical_centers mc
               LEFT JOIN districts d ON mc.district_id = d.id
               LEFT JOIN regions r ON d.region_id = r.id
               WHERE mc.email = %s""",
            (data['email'],), one=True
        )
        
        if not mc:
            return jsonify({'error': 'Ошибка создания медцентра'}), 500
        
        # Инициализируем светофор (все группы крови в норме)
        blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        for bt in blood_types:
            query_db(
                """INSERT INTO blood_needs (medical_center_id, blood_type, status) 
                   VALUES (%s, %s, 'normal') ON CONFLICT DO NOTHING""",
                (mc['id'], bt), commit=True
            )
        
        # Создаём сессию
        token = generate_token()
        query_db(
            """INSERT INTO user_sessions (session_token, user_type, medical_center_id, expires_at)
               VALUES (%s, 'medcenter', %s, NOW() + INTERVAL '30 days')""",
            (token, mc['id']), commit=True
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'medical_center': mc
        })
        
    except Exception as e:
        print(f"Ошибка регистрации медцентра: {e}")
        return jsonify({'error': 'Ошибка регистрации медцентра'}), 500

@app.route('/api/medcenter/login', methods=['POST'])
def login_medcenter():
    data = request.json
    
    if not data.get('medical_center_id') or not data.get('password'):
        return jsonify({'error': 'Укажите медцентр и пароль'}), 400
    
    mc = query_db(
        "SELECT id, name, master_password FROM medical_centers WHERE id = %s AND is_active = TRUE",
        (data['medical_center_id'],), one=True
    )
    
    if not mc:
        return jsonify({'error': 'Медцентр не найден'}), 404
    
    # Проверяем пароль (индивидуальный или мастер)
    if data['password'] != mc.get('master_password', MASTER_PASSWORD) and data['password'] != MASTER_PASSWORD:
        return jsonify({'error': 'Неверный пароль'}), 401
    
    token = generate_token()
    query_db(
        """INSERT INTO user_sessions (medical_center_id, session_token, user_type, expires_at)
           VALUES (%s, %s, 'medcenter', NOW() + INTERVAL '24 hours')""",
        (mc['id'], token), commit=True
    )
    
    return jsonify({
        'message': 'Вход выполнен',
        'token': token,
        'medical_center': {'id': mc['id'], 'name': mc['name']}
    })

@app.route('/api/medcenter/profile', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_profile():
    mc = query_db(
        """SELECT mc.id, mc.name, mc.address, mc.phone, mc.email, mc.is_blood_center,
                  d.name as district_name, r.name as region_name
           FROM medical_centers mc
           LEFT JOIN districts d ON mc.district_id = d.id
           LEFT JOIN regions r ON d.region_id = r.id
           WHERE mc.id = %s""",
        (g.session['medical_center_id'],), one=True
    )
    
    if not mc:
        return jsonify({'error': 'Медцентр не найден'}), 404
    
    return jsonify(mc)

# ============================================
# API: Донорский светофор
# ============================================

@app.route('/api/blood-needs/<int:mc_id>', methods=['GET'])
def get_blood_needs(mc_id):
    needs = query_db(
        """SELECT blood_type, status, last_updated, notes
           FROM blood_needs WHERE medical_center_id = %s ORDER BY blood_type""",
        (mc_id,)
    )
    
    if not needs:
        blood_types = ['A+', 'A-', 'AB+', 'AB-', 'B+', 'B-', 'O+', 'O-']
        needs = [{'blood_type': bt, 'status': 'normal', 'notes': None} for bt in blood_types]
    
    return jsonify(needs)

@app.route('/api/blood-needs/<int:mc_id>', methods=['PUT'])
@require_auth('medcenter')
def update_blood_needs(mc_id):
    if g.session['medical_center_id'] != mc_id:
        return jsonify({'error': 'Нет доступа'}), 403
    
    data = request.json
    blood_type = data.get('blood_type')
    status = data.get('status')
    
    if not blood_type or status not in ['normal', 'low', 'critical']:
        return jsonify({'error': 'Неверные данные'}), 400
    
    # Upsert
    existing = query_db(
        "SELECT id FROM blood_needs WHERE medical_center_id = %s AND blood_type = %s",
        (mc_id, blood_type), one=True
    )
    
    if existing:
        query_db(
            "UPDATE blood_needs SET status = %s, last_updated = NOW() WHERE medical_center_id = %s AND blood_type = %s",
            (status, mc_id, blood_type), commit=True
        )
    else:
        query_db(
            "INSERT INTO blood_needs (medical_center_id, blood_type, status) VALUES (%s, %s, %s)",
            (mc_id, blood_type, status), commit=True
        )
    
    # Уведомления при критическом статусе
    if status == 'critical':
        send_urgent_notifications(mc_id, blood_type)
    
    return jsonify({'message': 'Статус обновлён', 'blood_type': blood_type, 'status': status})

@app.route('/api/blood-needs/public', methods=['GET'])
def get_public_blood_needs():
    """Публичный статус крови для главной страницы"""
    needs = query_db(
        """SELECT mc.id as medical_center_id, mc.name as medical_center_name,
                  bn.blood_type, bn.status, bn.last_updated
           FROM blood_needs bn
           JOIN medical_centers mc ON bn.medical_center_id = mc.id
           WHERE mc.is_blood_center = TRUE AND mc.is_active = TRUE
           ORDER BY mc.name, bn.blood_type"""
    )
    return jsonify(needs)

# ============================================
# API: Запросы на донацию
# ============================================

@app.route('/api/requests', methods=['GET'])
def get_requests():
    mc_id = request.args.get('medical_center_id')
    blood_type = request.args.get('blood_type')
    status = request.args.get('status', 'active')
    district_id = request.args.get('district_id')
    
    query = """
        SELECT dr.*, mc.name as medical_center_name, mc.address as medical_center_address,
               mc.phone as medical_center_phone, d.name as district_name, r.name as region_name
        FROM donation_requests dr
        JOIN medical_centers mc ON dr.medical_center_id = mc.id
        LEFT JOIN districts d ON mc.district_id = d.id
        LEFT JOIN regions r ON d.region_id = r.id
        WHERE 1=1
    """
    params = []
    
    if mc_id:
        query += " AND dr.medical_center_id = %s"
        params.append(mc_id)
    
    if blood_type:
        query += " AND dr.blood_type = %s"
        params.append(blood_type)
    
    if status:
        query += " AND dr.status = %s"
        params.append(status)
    
    if district_id:
        query += " AND (dr.target_district_id = %s OR dr.target_district_id IS NULL)"
        params.append(district_id)
    
    query += " ORDER BY dr.created_at DESC"
    
    reqs = query_db(query, tuple(params))
    return jsonify(reqs)

@app.route('/api/requests', methods=['POST'])
@require_auth('medcenter')
def create_request():
    data = request.json
    
    if not data.get('blood_type'):
        return jsonify({'error': 'Укажите группу крови'}), 400
    
    mc_id = g.session['medical_center_id']
    valid_days = data.get('valid_days', 7)
    
    query_db(
        """INSERT INTO donation_requests 
           (medical_center_id, blood_type, urgency, needed_amount, description, 
            contact_info, target_district_id, valid_until)
           VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() + INTERVAL '%s days')
           RETURNING id""",
        (
            mc_id,
            data['blood_type'],
            data.get('urgency', 'normal'),
            data.get('needed_amount', 1),
            data.get('description'),
            data.get('contact_info'),
            data.get('target_district_id'),
            valid_days
        ), commit=True
    )
    
    new_req = query_db(
        "SELECT * FROM donation_requests WHERE medical_center_id = %s ORDER BY created_at DESC LIMIT 1",
        (mc_id,), one=True
    )
    
    # Уведомления
    if data.get('urgency') in ['urgent', 'critical']:
        send_urgent_notifications(mc_id, data['blood_type'], new_req['id'], data.get('target_district_id'))
    
    return jsonify({'message': 'Запрос создан', 'request': new_req}), 201

@app.route('/api/requests/<int:request_id>', methods=['PUT'])
@require_auth('medcenter')
def update_request(request_id):
    req = query_db("SELECT * FROM donation_requests WHERE id = %s", (request_id,), one=True)
    
    if not req:
        return jsonify({'error': 'Запрос не найден'}), 404
    
    if req['medical_center_id'] != g.session['medical_center_id']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    data = request.json
    allowed = ['status', 'description', 'needed_amount', 'urgency']
    updates = []
    values = []
    
    for field in allowed:
        if field in data:
            updates.append(f"{field} = %s")
            values.append(data[field])
    
    if updates:
        values.append(request_id)
        query_db(f"UPDATE donation_requests SET {', '.join(updates)} WHERE id = %s", tuple(values), commit=True)
    
    return jsonify({'message': 'Запрос обновлён'})

@app.route('/api/requests/<int:request_id>', methods=['DELETE'])
@require_auth('medcenter')
def delete_request(request_id):
    req = query_db("SELECT * FROM donation_requests WHERE id = %s", (request_id,), one=True)
    
    if not req or req['medical_center_id'] != g.session['medical_center_id']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    query_db("DELETE FROM donation_requests WHERE id = %s", (request_id,), commit=True)
    return jsonify({'message': 'Запрос удалён'})

# ============================================
# API: Запросы крови
# ============================================

@app.route('/api/blood-requests', methods=['GET'])
@require_auth('medcenter')
def get_blood_requests():
    """Получить список запросов крови медцентра"""
    mc_id = g.session['medical_center_id']
    status = request.args.get('status', 'all')
    blood_type = request.args.get('blood_type', 'all')
    
    query = """
        SELECT id, blood_type, urgency, status, description,
               created_at, expires_at, fulfilled_at,
               (SELECT COUNT(*) FROM donation_responses dr 
                WHERE dr.request_id = blood_requests.id) as responses_count,
               (SELECT COUNT(*) FROM donation_responses dr 
                WHERE dr.request_id = blood_requests.id AND dr.status = 'approved') as approved_count
        FROM blood_requests
        WHERE medical_center_id = %s
    """
    params = [mc_id]
    
    if status != 'all':
        query += " AND status = %s"
        params.append(status)
    
    if blood_type != 'all':
        query += " AND blood_type = %s"
        params.append(blood_type)
    
    query += " ORDER BY created_at DESC"
    
    requests_list = query_db(query, tuple(params))
    return jsonify(requests_list or [])

@app.route('/api/blood-requests', methods=['POST'])
@require_auth('medcenter')
def create_blood_request():
    """Создать новый запрос крови"""
    mc_id = g.session['medical_center_id']
    data = request.json
    
    required = ['blood_type', 'urgency']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    # Проверяем группу крови
    valid_blood = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if data['blood_type'] not in valid_blood:
        return jsonify({'error': 'Неверная группа крови'}), 400
    
    # Проверяем срочность
    if data['urgency'] not in ['normal', 'urgent', 'critical']:
        return jsonify({'error': 'Неверная срочность'}), 400
    
    # Вычисляем expires_at
    expires_days = data.get('expires_days', 7)
    
    # Создаём запрос
    request_id = query_db(
        """INSERT INTO blood_requests 
           (medical_center_id, blood_type, urgency, status, description, expires_at, created_at)
           VALUES (%s, %s, %s, 'active', %s, NOW() + INTERVAL '%s days', NOW())
           RETURNING id""",
        (mc_id, data['blood_type'], data['urgency'], data.get('description', ''), expires_days),
        commit=True, one=True
    )['id']
    
    # Обновляем светофор если критическая срочность
    if data['urgency'] == 'critical':
        query_db(
            """INSERT INTO blood_needs (medical_center_id, blood_type, status, last_updated)
               VALUES (%s, %s, 'critical', NOW())
               ON CONFLICT (medical_center_id, blood_type)
               DO UPDATE SET status = 'critical', last_updated = NOW()""",
            (mc_id, data['blood_type']), commit=True
        )
        
        # Отправляем уведомления
        mc = query_db("SELECT district_id FROM medical_centers WHERE id = %s", (mc_id,), one=True)
        send_urgent_notifications(mc_id, data['blood_type'], request_id, mc.get('district_id'))
    
    return jsonify({'message': 'Запрос создан', 'request_id': request_id}), 201

@app.route('/api/blood-requests/<int:request_id>', methods=['PUT'])
@require_auth('medcenter')
def update_blood_request(request_id):
    """Обновить статус запроса"""
    mc_id = g.session['medical_center_id']
    data = request.json
    
    # Проверяем принадлежность запроса медцентру
    req = query_db(
        "SELECT id FROM blood_requests WHERE id = %s AND medical_center_id = %s",
        (request_id, mc_id), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден'}), 404
    
    status = data.get('status')
    if status not in ['active', 'fulfilled', 'cancelled']:
        return jsonify({'error': 'Неверный статус'}), 400
    
    # Обновляем
    if status == 'fulfilled':
        query_db(
            "UPDATE blood_requests SET status = %s, fulfilled_at = NOW() WHERE id = %s",
            (status, request_id), commit=True
        )
    else:
        query_db(
            "UPDATE blood_requests SET status = %s WHERE id = %s",
            (status, request_id), commit=True
        )
    
    return jsonify({'message': 'Статус обновлён'})

@app.route('/api/blood-requests/<int:request_id>', methods=['DELETE'])
@require_auth('medcenter')
def delete_blood_request(request_id):
    """Удалить запрос"""
    mc_id = g.session['medical_center_id']
    
    # Проверяем принадлежность
    req = query_db(
        "SELECT id FROM blood_requests WHERE id = %s AND medical_center_id = %s",
        (request_id, mc_id), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден'}), 404
    
    query_db("DELETE FROM blood_requests WHERE id = %s", (request_id,), commit=True)
    return jsonify({'message': 'Запрос удалён'})

# ============================================
# API: Отклики
# ============================================

@app.route('/api/responses', methods=['GET'])
def get_responses():
    request_id = request.args.get('request_id')
    mc_id = request.args.get('medical_center_id')
    user_id = request.args.get('user_id')
    
    query = """
        SELECT dr.*, u.full_name as donor_name, u.blood_type as donor_blood_type,
               u.phone as donor_phone, u.email as donor_email, u.telegram_username,
               req.blood_type as request_blood_type, req.urgency,
               mc.name as medical_center_name
        FROM donation_responses dr
        JOIN users u ON dr.user_id = u.id
        JOIN donation_requests req ON dr.request_id = req.id
        JOIN medical_centers mc ON req.medical_center_id = mc.id
        WHERE 1=1
    """
    params = []
    
    if request_id:
        query += " AND dr.request_id = %s"
        params.append(request_id)
    
    if mc_id:
        query += " AND dr.medical_center_id = %s"
        params.append(mc_id)
    
    if user_id:
        query += " AND dr.user_id = %s"
        params.append(user_id)
    
    query += " ORDER BY dr.created_at DESC"
    
    responses = query_db(query, tuple(params))
    return jsonify(responses)

@app.route('/api/responses', methods=['POST'])
@require_auth('donor')
def create_response():
    data = request.json
    
    if not data.get('request_id'):
        return jsonify({'error': 'Укажите запрос'}), 400
    
    user_id = g.session['user_id']
    
    req = query_db(
        "SELECT * FROM donation_requests WHERE id = %s AND status = 'active'",
        (data['request_id'],), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден или неактивен'}), 404
    
    existing = query_db(
        "SELECT id FROM donation_responses WHERE request_id = %s AND user_id = %s",
        (data['request_id'], user_id), one=True
    )
    
    if existing:
        return jsonify({'error': 'Вы уже откликнулись'}), 400
    
    query_db(
        """INSERT INTO donation_responses 
           (request_id, user_id, medical_center_id, planned_date, planned_time, donor_comment)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            data['request_id'],
            user_id,
            req['medical_center_id'],
            data.get('planned_date'),
            data.get('planned_time'),
            data.get('comment')
        ), commit=True
    )
    
    query_db(
        "UPDATE donation_requests SET responses_count = responses_count + 1 WHERE id = %s",
        (data['request_id'],), commit=True
    )
    
    return jsonify({'message': 'Отклик отправлен'}), 201

@app.route('/api/responses/<int:response_id>', methods=['PUT'])
@require_auth('medcenter')
def update_response(response_id):
    resp = query_db("SELECT * FROM donation_responses WHERE id = %s", (response_id,), one=True)
    
    if not resp:
        return jsonify({'error': 'Отклик не найден'}), 404
    
    if resp['medical_center_id'] != g.session['medical_center_id']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    data = request.json
    new_status = data.get('status')
    
    if new_status not in ['pending', 'confirmed', 'completed', 'cancelled', 'no_show']:
        return jsonify({'error': 'Неверный статус'}), 400
    
    query_db(
        """UPDATE donation_responses 
           SET status = %s, medcenter_comment = %s,
               donation_completed = %s, actual_donation_date = %s
           WHERE id = %s""",
        (
            new_status,
            data.get('comment'),
            new_status == 'completed',
            datetime.now() if new_status == 'completed' else None,
            response_id
        ), commit=True
    )
    
    if new_status == 'completed':
        query_db(
            """UPDATE users SET last_donation_date = CURRENT_DATE, 
                   total_donations = total_donations + 1 WHERE id = %s""",
            (resp['user_id'],), commit=True
        )
    
    return jsonify({'message': 'Статус обновлён'})

# ============================================
# API: Доноры медцентра
# ============================================

@app.route('/api/medcenter/donors', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_donors():
    mc_id = g.session['medical_center_id']
    blood_type = request.args.get('blood_type')
    include_district = request.args.get('include_district', 'true')
    
    # Получаем район медцентра
    mc = query_db(
        "SELECT district_id FROM medical_centers WHERE id = %s",
        (mc_id,), one=True
    )
    
    if include_district == 'true' and mc and mc.get('district_id'):
        # Показываем всех доноров из района
        query = """
            SELECT u.id, u.full_name, u.blood_type, u.phone, u.email, u.telegram_username,
                   u.last_donation_date, u.total_donations, u.is_honorary_donor,
                   mc.name as medical_center_name
            FROM users u
            LEFT JOIN medical_centers mc ON u.medical_center_id = mc.id
            WHERE u.district_id = %s AND u.is_active = TRUE
        """
        params = [mc['district_id']]
    else:
        # Только доноры привязанные к этому медцентру
        query = """
            SELECT id, full_name, blood_type, phone, email, telegram_username,
                   last_donation_date, total_donations, is_honorary_donor
            FROM users WHERE medical_center_id = %s AND is_active = TRUE
        """
        params = [mc_id]
    
    if blood_type:
        query += " AND blood_type = %s"
        params.append(blood_type)
    
    query += " ORDER BY full_name"
    
    donors = query_db(query, tuple(params))
    return jsonify(donors if donors else [])

# ============================================
# API: Сообщения/консультации
# ============================================

@app.route('/api/messages', methods=['GET'])
def get_messages():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Требуется авторизация'}), 401
    
    session = query_db(
        "SELECT * FROM user_sessions WHERE session_token = %s AND is_active = TRUE",
        (token,), one=True
    )
    
    if not session:
        return jsonify({'error': 'Сессия истекла'}), 401
    
    if session['user_type'] == 'donor':
        messages = query_db(
            """SELECT m.*, mc.name as from_medcenter_name
               FROM messages m
               LEFT JOIN medical_centers mc ON m.from_medcenter_id = mc.id
               WHERE m.to_user_id = %s ORDER BY m.created_at DESC""",
            (session['user_id'],)
        )
    else:
        messages = query_db(
            """SELECT m.*, u.full_name as from_user_name
               FROM messages m
               LEFT JOIN users u ON m.from_user_id = u.id
               WHERE m.to_medcenter_id = %s ORDER BY m.created_at DESC""",
            (session['medical_center_id'],)
        )
    
    return jsonify(messages)

@app.route('/api/messages', methods=['POST'])
def send_message():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Требуется авторизация'}), 401
    
    session = query_db(
        "SELECT * FROM user_sessions WHERE session_token = %s AND is_active = TRUE",
        (token,), one=True
    )
    
    if not session:
        return jsonify({'error': 'Сессия истекла'}), 401
    
    data = request.json
    
    if not data.get('message'):
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    if session['user_type'] == 'donor':
        # Донор пишет в медцентр
        user = query_db("SELECT medical_center_id FROM users WHERE id = %s", (session['user_id'],), one=True)
        query_db(
            """INSERT INTO messages (from_user_id, to_medcenter_id, subject, message)
               VALUES (%s, %s, %s, %s)""",
            (session['user_id'], user['medical_center_id'], data.get('subject'), data['message']),
            commit=True
        )
    else:
        # Медцентр пишет донору
        if not data.get('to_user_id'):
            return jsonify({'error': 'Укажите получателя'}), 400
        query_db(
            """INSERT INTO messages (from_medcenter_id, to_user_id, subject, message)
               VALUES (%s, %s, %s, %s)""",
            (session['medical_center_id'], data['to_user_id'], data.get('subject'), data['message']),
            commit=True
        )
    
    return jsonify({'message': 'Сообщение отправлено'}), 201

@app.route('/api/messages/<int:msg_id>/read', methods=['PUT'])
def mark_message_read(msg_id):
    query_db("UPDATE messages SET is_read = TRUE WHERE id = %s", (msg_id,), commit=True)
    return jsonify({'message': 'Прочитано'})

# ============================================
# API: Статистика
# ============================================

@app.route('/api/stats/medcenter', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_stats():
    mc_id = g.session['medical_center_id']
    
    donors_count = query_db(
        "SELECT COUNT(*) as count FROM users WHERE medical_center_id = %s AND is_active = TRUE",
        (mc_id,), one=True
    )
    
    active_requests = query_db(
        "SELECT COUNT(*) as count FROM donation_requests WHERE medical_center_id = %s AND status = 'active'",
        (mc_id,), one=True
    )
    
    pending_responses = query_db(
        "SELECT COUNT(*) as count FROM donation_responses WHERE medical_center_id = %s AND status = 'pending'",
        (mc_id,), one=True
    )
    
    donors_by_blood = query_db(
        """SELECT blood_type, COUNT(*) as count FROM users 
           WHERE medical_center_id = %s AND is_active = TRUE AND blood_type IS NOT NULL
           GROUP BY blood_type""",
        (mc_id,)
    )
    
    return jsonify({
        'total_donors': donors_count['count'],
        'active_requests': active_requests['count'],
        'pending_responses': pending_responses['count'],
        'donors_by_blood_type': {item['blood_type']: item['count'] for item in donors_by_blood}
    })

# ============================================
# Telegram уведомления
# ============================================

def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_urgent_notifications(mc_id, blood_type, request_id=None, target_district_id=None):
    """Отправка срочных уведомлений донорам через Telegram"""
    print(f"[TELEGRAM] Вызов send_urgent_notifications: mc_id={mc_id}, blood_type={blood_type}")
    
    mc = query_db("SELECT name, address, district_id FROM medical_centers WHERE id = %s", (mc_id,), one=True)
    
    if not mc:
        print(f"[TELEGRAM] Медцентр {mc_id} не найден")
        return
    
    # Используем район медцентра, если не указан target_district_id
    if not target_district_id:
        target_district_id = mc.get('district_id')
    
    query = """
        SELECT telegram_id, full_name, id FROM users
        WHERE blood_type = %s AND is_active = TRUE
    """
    params = [blood_type]
    
    # Фильтр: либо привязан к медцентру, либо из того же района
    if target_district_id:
        query += " AND (medical_center_id = %s OR district_id = %s)"
        params.extend([mc_id, target_district_id])
    else:
        query += " AND medical_center_id = %s"
        params.append(mc_id)
    
    donors = query_db(query, tuple(params))
    
    print(f"[TELEGRAM] Найдено доноров с группой {blood_type}: {len(donors) if donors else 0}")
    
    if not donors:
        print(f"[TELEGRAM] Нет подходящих доноров для уведомления")
        return
    
    # Создаём запрос крови в БД, если ещё не создан
    if not request_id:
        request_id = query_db(
            """INSERT INTO blood_requests 
               (medical_center_id, blood_type, status, created_at) 
               VALUES (%s, %s, 'active', NOW()) 
               RETURNING id""",
            (mc_id, blood_type), commit=True, one=True
        )['id']
        print(f"[TELEGRAM] Создан новый запрос крови ID: {request_id}")
    
    message = f"""🚨 <b>Срочно нужна кровь!</b>

🩸 <b>Группа:</b> {blood_type}
🏥 <b>Медцентр:</b> {mc['name']}
📍 <b>Адрес:</b> {mc['address'] or 'не указан'}

Откликнитесь на сайте Твой Донор или свяжитесь с медцентром."""
    
    sent_count = 0
    donors_without_telegram = []
    
    for donor in donors:
        if donor['telegram_id']:
            success = send_telegram_message(donor['telegram_id'], message)
            if success:
                sent_count += 1
                print(f"[TELEGRAM] ✓ Отправлено: {donor['full_name']} (ID: {donor['telegram_id']})")
            else:
                print(f"[TELEGRAM] ✗ Ошибка отправки: {donor['full_name']}")
        else:
            donors_without_telegram.append(donor['full_name'])
    
    print(f"[TELEGRAM] Итого отправлено: {sent_count}/{len(donors)}")
    if donors_without_telegram:
        print(f"[TELEGRAM] Доноры без Telegram: {', '.join(donors_without_telegram[:5])}")
    
    return sent_count

# ============================================
# API: Telegram интеграция
# ============================================

@app.route('/api/donor/telegram/link-code', methods=['GET'])
@require_auth('donor')
def generate_telegram_link_code():
    """Генерация кода для привязки Telegram"""
    donor_id = g.session['user_id']
    
    # Генерируем 6-значный код
    import random
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Сохраняем код в БД (срок действия 10 минут)
    query_db(
        """INSERT INTO telegram_link_codes (user_id, code, expires_at, created_at)
           VALUES (%s, %s, NOW() + INTERVAL '10 minutes', NOW())
           ON CONFLICT (user_id) DO UPDATE 
           SET code = EXCLUDED.code, expires_at = EXCLUDED.expires_at, created_at = EXCLUDED.created_at""",
        (donor_id, code), commit=True
    )
    
    return jsonify({'code': code, 'expires_in': 600})

@app.route('/api/donor/telegram/status', methods=['GET'])
@require_auth('donor')
def get_telegram_status():
    """Проверка статуса привязки Telegram"""
    donor_id = g.session['user_id']
    
    donor = query_db(
        "SELECT telegram_id, telegram_username FROM users WHERE id = %s",
        (donor_id,), one=True
    )
    
    return jsonify({
        'linked': donor['telegram_id'] is not None,
        'telegram_id': donor['telegram_id'],
        'telegram_username': donor['telegram_username']
    })

@app.route('/api/donor/telegram/unlink', methods=['POST'])
@require_auth('donor')
def unlink_telegram():
    """Отвязка Telegram от аккаунта"""
    donor_id = g.session['user_id']
    
    query_db(
        "UPDATE users SET telegram_id = NULL, telegram_username = NULL WHERE id = %s",
        (donor_id,), commit=True
    )
    
    return jsonify({'message': 'Telegram отвязан'})

# ============================================
# Выход
# ============================================

@app.route('/api/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token:
        query_db("UPDATE user_sessions SET is_active = FALSE WHERE session_token = %s", (token,), commit=True)
    return jsonify({'message': 'Выход выполнен'})

# ============================================
# Health check
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    try:
        query_db("SELECT 1", one=True)
        db_status = 'ok'
    except:
        db_status = 'error'
    
    return jsonify({'status': 'ok', 'database': db_status})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("=" * 50)
    print("🩸 Твой Донор - API Server")
    print("=" * 50)
    print(f"Порт: {port}")
    print(f"БД: {DB_CONFIG['database']}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
