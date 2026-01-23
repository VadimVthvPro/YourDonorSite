#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Твой Донор - Flask API сервер
"""

import os
import secrets
import time
import json
from datetime import datetime, timedelta, date
from functools import wraps

from flask import Flask, request, jsonify, g, send_file
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from dotenv import load_dotenv

# Импорт функции уведомлений из telegram_bot
try:
    from telegram_bot import send_notification, send_urgent_blood_request
except ImportError:
    # Если telegram_bot недоступен, создаём заглушку
    def send_notification(telegram_id, message):
        print(f"[TELEGRAM] Уведомление для {telegram_id}: {message}")
        return False
    
    def send_urgent_blood_request(blood_type, medical_center_name, address=None):
        print(f"[TELEGRAM] Срочный запрос: {blood_type}, {medical_center_name}")
        return 0

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# URL приложения для ссылок
APP_URL = os.getenv('APP_URL', 'http://localhost:8080')

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

def create_donation_approval_message(donor_name, donation_date, donation_time, medical_center, donor_blood_type):
    """
    Создаёт клишированное сообщение для одобрения донора.
    
    Args:
        donor_name: Имя донора
        donation_date: Дата донации (строка "2026-02-15" или объект date)
        donation_time: Время донации ("10:00")
        medical_center: dict с полями {name, address, phone}
        donor_blood_type: Группа крови донора
    
    Returns:
        str: Отформатированное сообщение
    """
    
    # Форматирование даты
    if isinstance(donation_date, str):
        try:
            date_obj = datetime.strptime(donation_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d %B %Y')
            # Русские названия месяцев
            months_ru = {
                'January': 'января', 'February': 'февраля', 'March': 'марта',
                'April': 'апреля', 'May': 'мая', 'June': 'июня',
                'July': 'июля', 'August': 'августа', 'September': 'сентября',
                'October': 'октября', 'November': 'ноября', 'December': 'декабря'
            }
            for en, ru in months_ru.items():
                formatted_date = formatted_date.replace(en, ru)
        except:
            formatted_date = donation_date
    elif isinstance(donation_date, date):
        formatted_date = donation_date.strftime('%d.%m.%Y')
    else:
        formatted_date = str(donation_date)
    
    message = f"""✅ **ВАША ЗАЯВКА ОДОБРЕНА!**

Здравствуйте, {donor_name}!

Мы рады сообщить, что ваша заявка на донацию крови одобрена.

📅 **Дата и время:** {formatted_date} в {donation_time}

🏥 **Медицинский центр:**
{medical_center['name']}
📍 {medical_center['address']}
📞 {medical_center['phone']}

🩸 **Группа крови:** {donor_blood_type}

---

📋 **ПОДГОТОВКА К ДОНАЦИИ**

**За 48 часов до сдачи:**
• Исключите алкогольные напитки
• Избегайте жирной, жареной, острой и копчёной пищи
• Исключите молочные продукты, яйца, масло
• Не принимайте лекарства (кроме жизненно необходимых)

**За 24 часа до сдачи:**
• Хорошо выспитесь (не менее 8 часов)
• Пейте больше жидкости (вода, чай, соки, морсы)
• Откажитесь от острой и жирной пищи

**В день сдачи:**
• Обязательно позавтракайте за 2-3 часа до визита
• Разрешены: сладкий чай, вода, сухое печенье, каша на воде, хлеб, варенье
• Не курите за 1 час до сдачи крови
• Возьмите с собой паспорт
• Наденьте удобную одежду

---

❌ **ПРОТИВОПОКАЗАНИЯ**

При наличии сообщите врачу:
• Повышенная температура, простуда, ОРВИ
• Приём антибиотиков в последние 2 недели
• Недавние операции или удаление зубов (менее 10 дней)
• Татуировки или пирсинг менее 1 года назад
• Вакцинация менее 10 дней назад

---

💚 **ПОСЛЕ ДОНАЦИИ**

• Посидите спокойно 10-15 минут
• Пейте больше жидкости в течение 2 часов
• Не снимайте повязку 3-4 часа
• Избегайте физических нагрузок в течение суток

---

💬 **Есть вопросы?** Напишите нам в этом чате.
📅 **Не можете прийти?** Обязательно сообщите заранее.

**Спасибо за вашу готовность помочь!** 🩸
Ваша донация может спасти до 3 жизней."""

    return message

# ============================================
# Авторизация
# ============================================

def require_auth(user_type=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                app.logger.warning(f"❌ Нет токена для {f.__name__}, путь: {request.path}")
                return jsonify({'error': 'Требуется авторизация'}), 401
            
            session = query_db(
                """SELECT * FROM user_sessions 
                   WHERE session_token = %s AND is_active = TRUE AND expires_at > NOW()""",
                (token,), one=True
            )
            
            if not session:
                app.logger.warning(f"❌ Сессия не найдена или истекла для {f.__name__}, token={token[:10]}..., путь: {request.path}")
                return jsonify({'error': 'Сессия истекла. Войдите заново.'}), 401
            
            if user_type and session['user_type'] != user_type:
                app.logger.warning(f"❌ 403 FORBIDDEN: {f.__name__} требует '{user_type}', но user_type='{session['user_type']}', user_id={session.get('user_id')}, путь: {request.path}")
                return jsonify({'error': f'Доступ запрещён. Требуется роль: {user_type}'}), 403
            
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
    print(f"[DONOR REGISTER] Получены данные: {data}")
    print(f"[DONOR REGISTER] Тип данных: {type(data)}")
    
    if not data:
        print("[DONOR REGISTER] Пустой запрос!")
        return jsonify({'error': 'Данные не получены'}), 400
    
    required = ['full_name', 'birth_year', 'blood_type', 'medical_center_id', 'password', 'phone']
    missing_fields = []
    for field in required:
        if not data.get(field):
            missing_fields.append(field)
            print(f"[DONOR REGISTER] Отсутствует поле: {field}, значение: {data.get(field)}")
    
    if missing_fields:
        error_msg = f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'
        print(f"[DONOR REGISTER] {error_msg}")
        return jsonify({'error': error_msg}), 400
    
    # Проверяем группу крови
    valid_blood = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if data['blood_type'] not in valid_blood:
        return jsonify({'error': 'Неверная группа крови'}), 400
    
    # Очищаем ФИО от лишних пробелов
    full_name = data['full_name'].strip()
    
    # Проверяем существует ли
    existing = query_db(
        """SELECT id FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s""",
        (full_name, data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    if existing:
        print(f"[DONOR REGISTER] Донор уже существует: ID {existing['id']}")
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
    
    # Хешируем пароль
    import hashlib
    password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
    
    query_db(
        """INSERT INTO users 
           (full_name, birth_year, blood_type, medical_center_id, 
            region_id, district_id, city, phone, email, telegram_username, password_hash)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            full_name,
            data['birth_year'],
            data['blood_type'],
            data['medical_center_id'],
            mc['region_id'],
            mc['district_id'],
            data.get('city'),
            data.get('phone'),
            data.get('email'),
            data.get('telegram_username'),
            password_hash
        ), commit=True
    )
    
    user = query_db(
        """SELECT id, full_name, blood_type FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s""",
        (data['full_name'], data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    # Генерируем код для привязки Telegram
    import random
    import string
    code = ''.join(random.choices(string.digits, k=6))
    
    query_db(
        """INSERT INTO telegram_link_codes (user_id, code, expires_at)
           VALUES (%s, %s, NOW() + INTERVAL '10 minutes')""",
        (user['id'], code), commit=True
    )
    
    print(f"[DONOR REGISTER] Создан код привязки Telegram: {code} для user_id={user['id']}")
    
    # Создаём временную сессию (без полного доступа до верификации Telegram)
    token = generate_token()
    query_db(
        """INSERT INTO user_sessions (user_id, session_token, user_type, expires_at)
           VALUES (%s, %s, 'donor', NOW() + INTERVAL '7 days')""",
        (user['id'], token), commit=True
    )
    
    return jsonify({
        'message': 'Регистрация успешна! Привяжите Telegram бота @TvoyDonorZdesBot',
        'token': token,
        'user': user,
        'telegram_verification_required': True,
        'telegram_code': code,
        'telegram_bot_username': 'TvoyDonorZdesBot',
        'telegram_bot_url': 'https://t.me/TvoyDonorZdesBot'
    }), 201

@app.route('/api/donor/login', methods=['POST'])
def login_donor():
    data = request.json
    
    required = ['full_name', 'birth_year', 'medical_center_id', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    # Очищаем ФИО от лишних пробелов
    full_name = data['full_name'].strip()
    
    user = query_db(
        """SELECT id, full_name, blood_type, password_hash FROM users 
           WHERE full_name = %s AND birth_year = %s AND medical_center_id = %s AND is_active = TRUE""",
        (full_name, data['birth_year'], data['medical_center_id']),
        one=True
    )
    
    if not user:
        return jsonify({'error': 'Донор не найден. Сначала зарегистрируйтесь.'}), 404
    
    # Проверка пароля
    if user.get('password_hash'):
        import hashlib
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        if user['password_hash'] != password_hash:
            return jsonify({'error': 'Неверный пароль'}), 401
    else:
        # Если пароль не установлен, сохраняем его
        import hashlib
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        query_db("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user['id']), commit=True)
    
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
        'user': {'id': user['id'], 'full_name': user['full_name'], 'blood_type': user['blood_type']}
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

@app.route('/api/donor/statistics', methods=['GET'])
@require_auth('donor')
def get_donor_statistics():
    from datetime import date, timedelta
    
    user_id = g.session['user_id']
    
    # Получаем данные донора
    user = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    # Основная статистика
    total_donations = user.get('total_donations', 0) or 0
    total_volume_ml = user.get('total_volume_ml', 0) or 0
    last_donation_date = user.get('last_donation_date')
    
    # Рассчитываем дни до следующей донации
    days_until_next = None
    next_donation_date = None
    can_donate = True
    
    if last_donation_date:
        if isinstance(last_donation_date, str):
            from datetime import datetime as dt
            last_donation_date = dt.strptime(last_donation_date, '%Y-%m-%d').date()
        
        days_since = (date.today() - last_donation_date).days
        days_until_next = max(0, 60 - days_since)
        next_donation_date = last_donation_date + timedelta(days=60)
        can_donate = days_since >= 60
    
    # Определяем уровень донора
    level_data = get_donor_level(total_donations)
    
    # Получаем достижения
    achievements = get_donor_achievements(user_id, user, total_donations)
    
    # Получаем историю донаций
    donations_history = query_db(
        """SELECT dh.*, mc.name as medical_center_name
           FROM donation_history dh
           LEFT JOIN medical_centers mc ON dh.medical_center_id = mc.id
           WHERE dh.donor_id = %s
           ORDER BY dh.donation_date DESC
           LIMIT 20""",
        (user_id,)
    )
    
    # Подготовка данных для графика (донации по месяцам)
    donations_by_month = query_db(
        """SELECT 
               TO_CHAR(donation_date, 'YYYY-MM') as month,
               COUNT(*) as count
           FROM donation_history
           WHERE donor_id = %s
           GROUP BY TO_CHAR(donation_date, 'YYYY-MM')
           ORDER BY month ASC""",
        (user_id,)
    )
    
    # Подсчёт донаций за текущий календарный год
    current_year = date.today().year
    donations_this_year = query_db(
        """SELECT COUNT(*) as count
           FROM donation_history
           WHERE donor_id = %s
           AND EXTRACT(YEAR FROM donation_date) = %s""",
        (user_id, current_year), one=True
    )
    donations_this_year_count = donations_this_year['count'] if donations_this_year else 0
    
    # Максимум донаций в год (цельная кровь: 60 дней между донациями = ~6 раз)
    max_donations_per_year = 6
    year_progress_percent = min(100, (donations_this_year_count / max_donations_per_year) * 100)
    
    # Рассчитываем "спасённые жизни"
    lives_saved_estimate = total_donations * 3
    
    # Дата первой донации
    donor_since = None
    if donations_history:
        first_donation = query_db(
            """SELECT MIN(donation_date) as first_date
               FROM donation_history
               WHERE donor_id = %s""",
            (user_id,), one=True
        )
        donor_since = first_donation['first_date'] if first_donation else None
    
    return jsonify({
        'total_donations': total_donations,
        'total_volume_ml': total_volume_ml,
        'last_donation_date': last_donation_date.isoformat() if last_donation_date else None,
        'next_donation_date': next_donation_date.isoformat() if next_donation_date else None,
        'days_until_next': days_until_next,
        'can_donate': can_donate,
        'level': level_data,
        'achievements': achievements,
        'donations_by_month': donations_by_month,
        'donations_history': donations_history,
        'blood_type': user.get('blood_type'),
        'lives_saved_estimate': lives_saved_estimate,
        'donor_since': donor_since.isoformat() if donor_since else None,
        'donations_this_year': donations_this_year_count,
        'max_donations_per_year': max_donations_per_year,
        'year_progress_percent': year_progress_percent,
        'current_year': current_year
    })

def get_donor_level(donations):
    """Определяет уровень донора на основе количества донаций"""
    levels = [
        {'level': 1, 'name': 'Новичок', 'min': 0, 'max': 0, 'icon': 'drop_small', 'color': '#9e9e9e'},
        {'level': 2, 'name': 'Донор', 'min': 1, 'max': 2, 'icon': 'drop', 'color': '#ef9a9a'},
        {'level': 3, 'name': 'Активный донор', 'min': 3, 'max': 5, 'icon': 'drop_plus', 'color': '#e53935'},
        {'level': 4, 'name': 'Опытный донор', 'min': 6, 'max': 10, 'icon': 'drop_star', 'color': '#b71c1c'},
        {'level': 5, 'name': 'Почётный донор', 'min': 11, 'max': 20, 'icon': 'drop_crown', 'color': '#ffa726'},
        {'level': 6, 'name': 'Герой', 'min': 21, 'max': 40, 'icon': 'drop_laurel', 'color': '#78909c'},
        {'level': 7, 'name': 'Легенда', 'min': 41, 'max': 999, 'icon': 'drop_halo', 'color': '#d32f2f'},
    ]
    
    current_level = levels[0]
    for level in levels:
        if level['min'] <= donations <= level['max']:
            current_level = level
            break
        elif donations > level['max']:
            current_level = level
    
    # Находим следующий уровень
    next_level = None
    for level in levels:
        if level['level'] == current_level['level'] + 1:
            next_level = level
            break
    
    donations_in_level = donations - current_level['min']
    donations_to_next = next_level['min'] - donations if next_level else 0
    
    return {
        'current': current_level['level'],
        'name': current_level['name'],
        'icon': current_level['icon'],
        'color': current_level['color'],
        'donations_in_level': donations_in_level,
        'donations_to_next': donations_to_next,
        'next_level_name': next_level['name'] if next_level else None
    }

def get_donor_achievements(user_id, user, total_donations):
    """Определяет полученные и доступные достижения"""
    achievements = []
    
    # Получаем историю донаций для проверки условий
    donations = query_db(
        """SELECT donation_date, blood_type
           FROM donation_history
           WHERE donor_id = %s
           ORDER BY donation_date ASC""",
        (user_id,)
    )
    
    # Количественные достижения
    qty_achievements = [
        {'id': 'first_drop', 'name': 'Первая капля', 'icon': '🩸', 'condition': 1},
        {'id': 'five', 'name': 'Пятёрочка', 'icon': '🩸🩸', 'condition': 5},
        {'id': 'ten', 'name': 'Десятка', 'icon': '🩸🩸🩸', 'condition': 10},
        {'id': 'twenty', 'name': 'Двадцатка', 'icon': '🏆', 'condition': 20},
        {'id': 'fifty', 'name': 'Полтинник', 'icon': '💎', 'condition': 50},
    ]
    
    for ach in qty_achievements:
        unlocked = total_donations >= ach['condition']
        date_unlocked = None
        if unlocked and len(donations) >= ach['condition']:
            date_unlocked = donations[ach['condition'] - 1]['donation_date']
        
        achievements.append({
            'id': ach['id'],
            'name': ach['name'],
            'icon': ach['icon'],
            'unlocked': unlocked,
            'date': date_unlocked.isoformat() if date_unlocked else None,
            'progress': f"{min(total_donations, ach['condition'])}/{ach['condition']}"
        })
    
    # Сезонные достижения
    winter_donation = any(d['donation_date'].month in [12, 1, 2] for d in donations if d['donation_date'])
    achievements.append({
        'id': 'winter_hero',
        'name': 'Зимний герой',
        'icon': '❄️',
        'unlocked': winter_donation,
        'date': None,
        'progress': '1/1' if winter_donation else '0/1'
    })
    
    summer_donation = any(d['donation_date'].month in [6, 7, 8] for d in donations if d['donation_date'])
    achievements.append({
        'id': 'summer_savior',
        'name': 'Летний спаситель',
        'icon': '🌞',
        'unlocked': summer_donation,
        'date': None,
        'progress': '1/1' if summer_donation else '0/1'
    })
    
    # Редкая кровь
    rare_blood = user.get('blood_type') in ['AB-', 'B-']
    if rare_blood:
        achievements.append({
            'id': 'rare_blood',
            'name': 'Редкая кровь',
            'icon': '💎',
            'unlocked': True,
            'date': None,
            'progress': '1/1'
        })
    
    return achievements

@app.route('/api/donor/profile', methods=['PUT'])
@require_auth('donor')
def update_donor_profile():
    data = request.json
    allowed = ['phone', 'email', 'telegram_username', 'city', 'notify_urgent', 'notify_low', 
               'blood_type', 'last_donation_date', 'medical_center_id']
    
    updates = []
    values = []
    
    # Если меняется медцентр, нужно обновить регион и район
    if 'medical_center_id' in data:
        mc = query_db(
            """SELECT mc.district_id, d.region_id
               FROM medical_centers mc
               JOIN districts d ON mc.district_id = d.id
               WHERE mc.id = %s""",
            (data['medical_center_id'],), one=True
        )
        if mc:
            updates.append("district_id = %s")
            values.append(mc['district_id'])
            updates.append("region_id = %s")
            values.append(mc['region_id'])

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

@app.route('/api/medcenter/profile', methods=['PUT'])
@require_auth('medcenter')
def update_medcenter_profile():
    """Обновить профиль медцентра"""
    mc_id = g.session['medical_center_id']
    data = request.json
    
    # Разрешённые поля для обновления
    allowed_fields = ['name', 'address', 'phone', 'email']
    updates = []
    params = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])
    
    if not updates:
        return jsonify({'error': 'Нет данных для обновления'}), 400
    
    updates.append("updated_at = NOW()")
    params.append(mc_id)
    
    query_db(
        f"UPDATE medical_centers SET {', '.join(updates)} WHERE id = %s",
        tuple(params), commit=True
    )
    
    return jsonify({'message': 'Профиль обновлён'})

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
    
    # Всегда возвращаем все 8 групп крови
    all_blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    needs_dict = {n['blood_type']: n for n in (needs or [])}
    
    # Заполняем отсутствующие группы крови статусом 'normal'
    result = []
    for bt in all_blood_types:
        if bt in needs_dict:
            result.append(needs_dict[bt])
        else:
            result.append({
                'blood_type': bt, 
                'status': 'normal', 
                'last_updated': None,
                'notes': None
            })
    
    return jsonify(result)

@app.route('/api/blood-needs/<int:mc_id>', methods=['PUT'])
@require_auth('medcenter')
def update_blood_needs(mc_id):
    app.logger.info(f"✅ update_blood_needs вызван для mc_id={mc_id}, session_mc_id={g.session.get('medical_center_id')}")
    if g.session['medical_center_id'] != mc_id:
        app.logger.warning(f"❌ Нет доступа: mc_id={mc_id} != session_mc_id={g.session['medical_center_id']}")
        return jsonify({'error': 'Нет доступа'}), 403
    
    data = request.json
    blood_type = data.get('blood_type')
    status = data.get('status')
    
    # Стандартизированные статусы: normal, needed, urgent
    if not blood_type or status not in ['normal', 'needed', 'urgent']:
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
    
    # Логика уведомлений при изменении статуса
    mc = query_db("SELECT name, address FROM medical_centers WHERE id = %s", (mc_id,), one=True)
    
    if status == 'urgent':
        # 1. Проверяем, есть ли активный запрос крови
        active_request = query_db(
            """SELECT id FROM blood_requests 
               WHERE medical_center_id = %s AND blood_type = %s AND status = 'active' AND expires_at > NOW()""",
            (mc_id, blood_type), one=True
        )
        
        request_id = None
        if not active_request:
            # 2. Если нет, создаём автоматический запрос
            request_id = query_db(
                """INSERT INTO blood_requests 
                   (medical_center_id, blood_type, urgency, status, description, expires_at, created_at)
                   VALUES (%s, %s, 'urgent', 'active', 'Автоматический запрос из светофора', NOW() + INTERVAL '2 days', NOW())
                   RETURNING id""",
                (mc_id, blood_type), commit=True, one=True
            )['id']
            print(f"[AUTO-REQUEST] Создан запрос ID {request_id} для {blood_type}")
        else:
            request_id = active_request['id']
            # Обновляем срочность существующего запроса
            query_db(
                "UPDATE blood_requests SET urgency = 'urgent' WHERE id = %s",
                (request_id,), commit=True
            )
        
        # 3. Отправляем срочные уведомления через send_blood_status_notification
        if mc:
            try:
                from telegram_bot import send_blood_status_notification
                send_blood_status_notification(blood_type, 'urgent', mc['name'])
            except Exception as e:
                logger.error(f"Ошибка отправки Telegram уведомления: {e}")
    
    elif status == 'needed':
        # Отправляем уведомления о том, что нужно пополнить
        if mc:
            try:
                from telegram_bot import send_blood_status_notification
                send_blood_status_notification(blood_type, 'needed', mc['name'])
            except Exception as e:
                logger.error(f"Ошибка отправки Telegram уведомления: {e}")
    
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
        FROM blood_requests dr
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
        """INSERT INTO blood_requests 
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
        "SELECT * FROM blood_requests WHERE medical_center_id = %s ORDER BY created_at DESC LIMIT 1",
        (mc_id,), one=True
    )
    
    # Уведомления
    if data.get('urgency') in ['urgent', 'critical']:
        send_urgent_notifications(mc_id, data['blood_type'], new_req['id'], data.get('target_district_id'))
    
    return jsonify({'message': 'Запрос создан', 'request': new_req}), 201

@app.route('/api/requests/<int:request_id>', methods=['PUT'])
@require_auth('medcenter')
def update_request(request_id):
    req = query_db("SELECT * FROM blood_requests WHERE id = %s", (request_id,), one=True)
    
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
        query_db(f"UPDATE blood_requests SET {', '.join(updates)} WHERE id = %s", tuple(values), commit=True)
    
    return jsonify({'message': 'Запрос обновлён'})

@app.route('/api/requests/<int:request_id>', methods=['DELETE'])
@require_auth('medcenter')
def delete_request(request_id):
    req = query_db("SELECT * FROM blood_requests WHERE id = %s", (request_id,), one=True)
    
    if not req or req['medical_center_id'] != g.session['medical_center_id']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    query_db("DELETE FROM blood_requests WHERE id = %s", (request_id,), commit=True)
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
    if data['urgency'] not in ['normal', 'needed', 'urgent', 'critical']:
        return jsonify({'error': 'Неверная срочность'}), 400
    
    # Вычисляем expires_at
    expires_days = data.get('expires_days', 7)
    needed_donors = data.get('needed_donors')  # None если без ограничения
    auto_close = data.get('auto_close', False)
    
    # Создаём запрос
    request_id = query_db(
        """INSERT INTO blood_requests 
           (medical_center_id, blood_type, urgency, status, description, expires_at, created_at,
            needed_donors, current_donors, auto_close)
           VALUES (%s, %s, %s, 'active', %s, NOW() + INTERVAL '%s days', NOW(), %s, 0, %s)
           RETURNING id""",
        (mc_id, data['blood_type'], data['urgency'], data.get('description', ''), 
         expires_days, needed_donors, auto_close),
        commit=True, one=True
    )['id']
    
    # Обновляем светофор если критическая срочность
    if data['urgency'] in ['urgent', 'critical']:
        status_to_set = 'urgent' # Унификация
        query_db(
            """INSERT INTO blood_needs (medical_center_id, blood_type, status, last_updated)
               VALUES (%s, %s, %s, NOW())
               ON CONFLICT (medical_center_id, blood_type)
               DO UPDATE SET status = %s, last_updated = NOW()""",
            (mc_id, data['blood_type'], status_to_set, status_to_set), commit=True
        )
    
    # Отправляем уведомления для ВСЕХ запросов (не только urgent)
    mc = query_db("SELECT name, address FROM medical_centers WHERE id = %s", (mc_id,), one=True)
    if mc:
        try:
            from telegram_bot import send_blood_request_notification
            send_blood_request_notification(data['blood_type'], data['urgency'], mc['name'], mc.get('address'))
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram уведомления о запросе: {e}")
    
    return jsonify({'message': 'Запрос создан', 'request_id': request_id}), 201

@app.route('/api/blood-requests/<int:request_id>', methods=['GET'])
@require_auth('medcenter')
def get_blood_request(request_id):
    """Получить один запрос крови для редактирования"""
    mc_id = g.session['medical_center_id']
    
    # Проверяем принадлежность запроса медцентру
    req = query_db(
        """SELECT br.*, 
                  (SELECT COUNT(*) FROM donation_responses WHERE request_id = br.id) as responses_count
           FROM blood_requests br
           WHERE br.id = %s AND br.medical_center_id = %s""",
        (request_id, mc_id), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден'}), 404
    
    return jsonify({
        'id': req['id'],
        'blood_type': req['blood_type'],
        'urgency': req['urgency'],
        'description': req['description'],
        'expires_at': req['expires_at'].isoformat() if req.get('expires_at') else None,
        'status': req['status'],
        'created_at': req['created_at'].isoformat() if req.get('created_at') else None,
        'needed_donors': req.get('needed_donors'),
        'current_donors': req.get('current_donors', 0),
        'auto_close': req.get('auto_close', False),
        'responses_count': req.get('responses_count', 0)
    })

@app.route('/api/blood-requests/<int:request_id>', methods=['PUT'])
@require_auth('medcenter')
def update_blood_request(request_id):
    """Обновить запрос крови"""
    mc_id = g.session['medical_center_id']
    data = request.json
    
    # Проверяем принадлежность запроса медцентру
    req = query_db(
        "SELECT id FROM blood_requests WHERE id = %s AND medical_center_id = %s",
        (request_id, mc_id), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден'}), 404
    
    # Обновление статуса (для изменения статуса запроса)
    if 'status' in data:
        status = data['status']
        if status not in ['active', 'fulfilled', 'cancelled']:
            return jsonify({'error': 'Неверный статус'}), 400
        
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
    
    # Обновление полей запроса (при редактировании)
    updates = []
    params = []
    
    if 'blood_type' in data:
        valid_blood = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        if data['blood_type'] not in valid_blood:
            return jsonify({'error': 'Неверная группа крови'}), 400
        updates.append("blood_type = %s")
        params.append(data['blood_type'])
    
    if 'urgency' in data:
        if data['urgency'] not in ['normal', 'needed', 'urgent', 'critical']:
            return jsonify({'error': 'Неверная срочность'}), 400
        updates.append("urgency = %s")
        params.append(data['urgency'])
    
    if 'description' in data:
        updates.append("description = %s")
        params.append(data['description'])
    
    if 'expires_at' in data:
        updates.append("expires_at = %s")
        params.append(data['expires_at'])
    
    if 'needed_donors' in data:
        updates.append("needed_donors = %s")
        params.append(data['needed_donors'])
    
    if 'auto_close' in data:
        updates.append("auto_close = %s")
        params.append(data['auto_close'])
    
    if not updates:
        return jsonify({'error': 'Нет данных для обновления'}), 400
    
    params.append(request_id)
    query_db(
        f"UPDATE blood_requests SET {', '.join(updates)} WHERE id = %s",
        tuple(params), commit=True
    )
    
    return jsonify({'message': 'Запрос обновлён'})

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
    show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'
    
    query = """
        SELECT dr.*, 
               u.full_name as donor_name, 
               u.blood_type as donor_blood_type,
               u.phone as donor_phone, 
               u.email as donor_email, 
               u.telegram_username,
               u.total_donations as donor_total_donations,
               u.last_donation_date as donor_last_donation_date,
               u.total_volume_ml as donor_total_volume_ml,
               req.blood_type as request_blood_type, 
               req.urgency,
               mc.name as medical_center_name
        FROM donation_responses dr
        JOIN users u ON dr.user_id = u.id
        JOIN blood_requests req ON dr.request_id = req.id
        JOIN medical_centers mc ON req.medical_center_id = mc.id
        WHERE 1=1
    """
    params = []
    
    # Фильтр скрытых откликов
    if not show_hidden:
        query += " AND dr.hidden = FALSE"
    
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
        "SELECT * FROM blood_requests WHERE id = %s AND status = 'active'",
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
        "UPDATE blood_requests SET responses_count = responses_count + 1 WHERE id = %s",
        (data['request_id'],), commit=True
    )
    
    return jsonify({'message': 'Отклик отправлен'}), 201

@app.route('/api/medical-center/donations', methods=['POST'])
@require_auth('medcenter')
def record_donation():
    """Записать успешную донацию"""
    from datetime import date
    
    mc_id = g.session['medical_center_id']
    data = request.json
    
    required = ['donor_id', 'blood_type']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    donor_id = data['donor_id']
    blood_type = data['blood_type']
    volume_ml = data.get('volume_ml', 450)
    
    # Правильная обработка даты донации
    donation_date_str = data.get('donation_date')
    if donation_date_str and donation_date_str != 'CURRENT_DATE':
        donation_date = donation_date_str
    else:
        donation_date = date.today()
    
    notes = data.get('notes', '')
    response_id = data.get('response_id')
    
    # Проверяем группу крови
    valid_blood = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if blood_type not in valid_blood:
        return jsonify({'error': 'Неверная группа крови'}), 400
    
    # Записываем донацию в историю
    query_db(
        """INSERT INTO donation_history 
           (donor_id, medical_center_id, donation_date, blood_type, volume_ml, status, notes, response_id)
           VALUES (%s, %s, %s, %s, %s, 'completed', %s, %s)""",
        (donor_id, mc_id, donation_date, blood_type, volume_ml, notes, response_id),
        commit=True
    )
    
    # Обновляем статистику донора в таблице users
    query_db(
        """UPDATE users SET 
           total_donations = COALESCE(total_donations, 0) + 1,
           last_donation_date = %s,
           total_volume_ml = COALESCE(total_volume_ml, 0) + %s
           WHERE id = %s""",
        (donation_date, volume_ml, donor_id),
        commit=True
    )
    
    # Если есть response_id, обновляем статус отклика
    if response_id:
        query_db(
            "UPDATE donation_responses SET status = 'completed' WHERE id = %s",
            (response_id,),
            commit=True
        )
    
    return jsonify({'message': 'Донация записана', 'donor_id': donor_id}), 201

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
    
    if new_status not in ['pending', 'confirmed', 'completed', 'cancelled', 'no_show', 'rejected']:
        return jsonify({'error': 'Неверный статус'}), 400
    
    # ВАЛИДАЦИЯ ПРИ ПОДТВЕРЖДЕНИИ
    if new_status == 'confirmed':
        # Получаем данные донора
        donor = query_db(
            "SELECT * FROM users WHERE id = %s",
            (resp['user_id'],), one=True
        )
        
        if not donor:
            return jsonify({'error': 'Донор не найден'}), 404
        
        # Получаем данные запроса
        blood_request = query_db(
            "SELECT * FROM blood_requests WHERE id = %s",
            (resp['request_id'],), one=True
        )
        
        if not blood_request:
            return jsonify({'error': 'Запрос не найден'}), 404
        
        # ПРОВЕРКА 1: Группа крови совпадает
        if donor['blood_type'] != blood_request['blood_type']:
            return jsonify({
                'error': f"Группа крови донора ({donor['blood_type']}) не совпадает с запросом ({blood_request['blood_type']})"
            }), 400
        
        # ПРОВЕРКА 2: Прошло 60 дней с последней донации
        if donor.get('last_donation_date'):
            from datetime import date, timedelta
            last_date = donor['last_donation_date']
            if isinstance(last_date, str):
                from datetime import datetime as dt
                last_date = dt.strptime(last_date, '%Y-%m-%d').date()
            
            days_since = (date.today() - last_date).days
            if days_since < 60:
                return jsonify({
                    'error': f'С последней донации прошло только {days_since} дней (минимум 60 дней)'
                }), 400
    
    # Обновляем статус
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
    
    # При завершении обновляем статистику донора
    if new_status == 'completed':
        query_db(
            """UPDATE users SET 
               last_donation_date = CURRENT_DATE, 
               total_donations = COALESCE(total_donations, 0) + 1,
               total_volume_ml = COALESCE(total_volume_ml, 0) + 450
               WHERE id = %s""",
            (resp['user_id'],), commit=True
        )
    
    # ПРИ ПОДТВЕРЖДЕНИИ: создать диалог и отправить уведомление
    if new_status == 'confirmed':
        # Получаем данные донора и медцентра для создания диалога
        donor = query_db(
            "SELECT * FROM users WHERE id = %s",
            (resp['user_id'],), one=True
        )
        
        medical_center = query_db(
            "SELECT * FROM medical_centers WHERE id = %s",
            (resp['medical_center_id'],), one=True
        )
        
        if donor and medical_center:
            # Создаём или получаем существующий диалог
            conversation = query_db(
                """SELECT * FROM conversations 
                   WHERE donor_id = %s AND medical_center_id = %s""",
                (resp['user_id'], resp['medical_center_id']), one=True
            )
            
            if not conversation:
                app.logger.info(f"Создание нового диалога: donor_id={resp['user_id']}, medical_center_id={resp['medical_center_id']}")
                query_db(
                    """INSERT INTO conversations 
                       (donor_id, medical_center_id, status, created_at, updated_at)
                       VALUES (%s, %s, 'active', NOW(), NOW())""",
                    (resp['user_id'], resp['medical_center_id']), commit=True
                )
                conversation = query_db(
                    """SELECT * FROM conversations 
                       WHERE donor_id = %s AND medical_center_id = %s""",
                    (resp['user_id'], resp['medical_center_id']), one=True
                )
                app.logger.info(f"✅ Диалог создан: conversation_id={conversation['id']}")
            
            # Отправляем приглашение на донацию
            blood_request = query_db(
                "SELECT * FROM blood_requests WHERE id = %s",
                (resp['request_id'],), one=True
            )
            
            donation_date = data.get('donation_date', 'будет уточнена')
            donation_time = data.get('donation_time', 'будет уточнено')
            
            # Создаём сообщение используя шаблон
            message_text = create_donation_approval_message(
                donor_name=donor['full_name'],
                donation_date=donation_date,
                donation_time=donation_time,
                medical_center=medical_center,
                donor_blood_type=donor['blood_type']
            )
            
            # Сохраняем сообщение
            app.logger.info(f"Отправка сообщения: conversation_id={conversation['id']}, type=invitation")
            query_db(
                """INSERT INTO messages 
                   (conversation_id, sender_role, message_type, content, metadata, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())""",
                (
                    conversation['id'],
                    'medical_center',
                    'invitation',
                    message_text,
                    json.dumps({
                        'donation_date': str(donation_date),
                        'donation_time': str(donation_time),
                        'medical_center_id': medical_center['id'],
                        'blood_type': donor['blood_type']
                    })
                ),
                commit=True
            )
            app.logger.info(f"✅ Сообщение отправлено донору {donor['id']}")
            
            # Отправляем в Telegram
            donor_telegram = query_db(
                """SELECT telegram_id FROM users WHERE id = %s AND telegram_id IS NOT NULL""",
                (donor['id'],), one=True
            )
            
            if donor_telegram and donor_telegram.get('telegram_id'):
                try:
                    telegram_text = f"""✅ Ваша заявка на донацию одобрена!

📅 {donation_date}, {donation_time}
🏥 {medical_center['name']}
📍 {medical_center['address']}

⚠️ Важно: За 48 часов исключите алкоголь и жирную пищу.

📋 Полные правила подготовки на сайте
💬 {APP_URL}/pages/donor-dashboard.html"""
                    
                    send_telegram_message(donor_telegram['telegram_id'], telegram_text)
                    app.logger.info(f"✅ Telegram отправлен донору {donor['id']}")
                except Exception as e:
                    app.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
        
        # АВТОЗАКРЫТИЕ: проверяем, достигнут ли лимит
        blood_request = query_db(
            "SELECT * FROM blood_requests WHERE id = %s",
            (resp['request_id'],), one=True
        )
        
        if blood_request and blood_request.get('auto_close') and blood_request.get('needed_donors'):
            # Считаем подтверждённых доноров
            confirmed_count = query_db(
                """SELECT COUNT(*) as count FROM donation_responses 
                   WHERE request_id = %s AND status = 'confirmed'""",
                (resp['request_id'],), one=True
            )['count']
            
            if confirmed_count >= blood_request['needed_donors']:
                # Закрываем запрос
                query_db(
                    """UPDATE blood_requests 
                       SET status = 'closed' 
                       WHERE id = %s""",
                    (resp['request_id'],), commit=True
                )
                app.logger.info(f"Запрос {resp['request_id']} автоматически закрыт (лимит достигнут)")
    
    # АВТООТКРЫТИЕ: при отмене подтверждения
    if resp['status'] == 'confirmed' and new_status in ['pending', 'cancelled', 'rejected']:
        blood_request = query_db(
            "SELECT * FROM blood_requests WHERE id = %s",
            (resp['request_id'],), one=True
        )
        
        if blood_request and blood_request['status'] == 'closed':
            # Считаем подтверждённых доноров
            confirmed_count = query_db(
                """SELECT COUNT(*) as count FROM donation_responses 
                   WHERE request_id = %s AND status = 'confirmed'""",
                (resp['request_id'],), one=True
            )['count']
            
            # Если было закрытие из-за лимита и теперь доноров меньше
            if blood_request.get('needed_donors') and confirmed_count < blood_request['needed_donors']:
                # Открываем запрос обратно
                query_db(
                    """UPDATE blood_requests 
                       SET status = 'active' 
                       WHERE id = %s""",
                    (resp['request_id'],), commit=True
                )
                app.logger.info(f"Запрос {resp['request_id']} автоматически открыт")
    
    return jsonify({'message': 'Статус обновлён', 'status': new_status})

@app.route('/api/medical-center/responses/cleanup', methods=['POST'])
@require_auth('medcenter')
def cleanup_outdated_responses():
    """Очистка устаревших откликов на закрытые/отменённые запросы"""
    medical_center_id = g.session['medical_center_id']
    
    # Удаляем отклики со статусом pending или cancelled на неактивные запросы
    result = query_db("""
        DELETE FROM donation_responses 
        WHERE id IN (
            SELECT dr.id 
            FROM donation_responses dr
            JOIN blood_requests br ON dr.request_id = br.id
            WHERE br.medical_center_id = %s
            AND dr.status IN ('pending', 'cancelled', 'rejected')
            AND br.status IN ('closed', 'cancelled', 'expired')
        )
    """, (medical_center_id,), commit=True)
    
    return jsonify({
        'message': f'Удалено {result} устаревших откликов',
        'deleted_count': result
    }), 200

@app.route('/api/responses/<int:response_id>/hide', methods=['PUT'])
@require_auth('medcenter')
def hide_response(response_id):
    """Скрыть отклик (не удаляя из БД)"""
    # Проверяем существование и доступ
    resp = query_db(
        """SELECT dr.*, br.medical_center_id 
           FROM donation_responses dr
           JOIN blood_requests br ON dr.request_id = br.id
           WHERE dr.id = %s""",
        (response_id,), one=True
    )
    
    if not resp:
        return jsonify({'error': 'Отклик не найден'}), 404
    
    if resp['medical_center_id'] != g.session['medical_center_id']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    # Скрываем
    query_db(
        "UPDATE donation_responses SET hidden = TRUE WHERE id = %s",
        (response_id,), commit=True
    )
    
    return jsonify({'message': 'Отклик скрыт'}), 200

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
        
        to_user_id = data['to_user_id']
        subject = data.get('subject', 'Новое сообщение')
        message = data['message']
        
        query_db(
            """INSERT INTO messages (from_medcenter_id, to_user_id, subject, message)
               VALUES (%s, %s, %s, %s)""",
            (session['medical_center_id'], to_user_id, subject, message),
            commit=True
        )
        
        # Отправляем Telegram уведомление донору
        try:
            from telegram_bot import send_message_notification
            medcenter = query_db(
                "SELECT name FROM medical_centers WHERE id = %s",
                (session['medical_center_id'],), one=True
            )
            send_message_notification(to_user_id, medcenter['name'], subject, message)
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram уведомления о сообщении: {e}")
    
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
        "SELECT COUNT(*) as count FROM blood_requests WHERE medical_center_id = %s AND status = 'active'",
        (mc_id,), one=True
    )
    
    pending_responses = query_db(
        "SELECT COUNT(*) as count FROM donation_responses WHERE medical_center_id = %s AND status = 'pending'",
        (mc_id,), one=True
    )
    
    # Донации за текущий месяц
    from datetime import datetime, timedelta
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_donations = query_db(
        """SELECT COUNT(*) as count FROM donation_history 
           WHERE medical_center_id = %s AND donation_date >= %s""",
        (mc_id, start_of_month), one=True
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
        'month_donations': month_donations['count'],
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

@app.route('/api/donor/telegram/save-code', methods=['POST'])
@require_auth('donor')
def save_telegram_code():
    """Сохранение кода верификации (после регистрации)"""
    donor_id = g.session['user_id']
    data = request.json
    
    if not data or not data.get('code'):
        return jsonify({'error': 'Код не указан'}), 400
    
    code = data['code']
    
    # Сохраняем код в БД (срок действия 15 минут)
    query_db(
        """INSERT INTO telegram_link_codes (user_id, code, expires_at, created_at)
           VALUES (%s, %s, NOW() + INTERVAL '15 minutes', NOW())
           ON CONFLICT (user_id) DO UPDATE 
           SET code = EXCLUDED.code, expires_at = EXCLUDED.expires_at, created_at = EXCLUDED.created_at""",
        (donor_id, code), commit=True
    )
    
    print(f"[TELEGRAM] Код {code} сохранён для user_id={donor_id}")
    
    return jsonify({'success': True, 'code': code, 'expires_in': 900})

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
# API: Запросы крови для доноров
# ============================================

@app.route('/api/donor/blood-requests', methods=['GET'])
@require_auth('donor')
def get_donor_blood_requests():
    """Получить список запросов крови для донора"""
    user_id = g.session['user_id']
    
    # Получаем данные донора
    donor = query_db("""
        SELECT district_id, blood_type, medical_center_id 
        FROM users 
        WHERE id = %s
    """, (user_id,), one=True)
    
    if not donor:
        return jsonify({'error': 'Донор не найден'}), 404
    
    # Получаем активные запросы крови:
    # 1) От медцентра, к которому привязан донор
    # 2) От медцентров в том же районе
    # 3) С подходящей группой крови
    query = """
        SELECT 
            br.id,
            br.blood_type,
            br.urgency,
            br.description,
            br.status,
            br.created_at,
            br.expires_at,
            mc.name as medical_center_name,
            mc.address as medical_center_address,
            mc.phone as medical_center_phone,
            mc.email as medical_center_email,
            dr.id as response_id,
            dr.status as response_status,
            dr.donor_comment as response_message,
            dr.created_at as responded_at
        FROM blood_requests br
        JOIN medical_centers mc ON br.medical_center_id = mc.id
        LEFT JOIN donation_responses dr ON dr.request_id = br.id AND dr.user_id = %s
        WHERE 
            br.status = 'active' 
            AND br.expires_at > NOW()
            AND br.blood_type = %s
            AND (
                br.medical_center_id = %s 
                OR mc.district_id = %s
            )
        ORDER BY 
            CASE br.urgency 
                WHEN 'critical' THEN 1
                WHEN 'urgent' THEN 2
                ELSE 3
            END,
            br.created_at DESC
    """
    
    requests = query_db(query, (
        user_id, 
        donor['blood_type'],
        donor['medical_center_id'],
        donor['district_id']
    ))
    
    return jsonify(requests or [])

@app.route('/api/donor/blood-requests/<int:request_id>/respond', methods=['POST'])
@require_auth('donor')
def respond_to_blood_request(request_id):
    """Откликнуться на запрос крови"""
    user_id = g.session['user_id']
    data = request.json
    
    # ЖЁСТКАЯ ПРОВЕРКА: Прошло ли 60 дней с последней донации
    donor = query_db(
        "SELECT last_donation_date FROM users WHERE id = %s",
        (user_id,), one=True
    )
    
    if donor and donor['last_donation_date']:
        from datetime import date, timedelta
        last_date = donor['last_donation_date']
        if isinstance(last_date, str):
            from datetime import datetime as dt
            last_date = dt.strptime(last_date, '%Y-%m-%d').date()
        
        days_since = (date.today() - last_date).days
        
        if days_since < 60:
            return jsonify({
                'error': f'Нельзя откликнуться! С последней донации прошло только {days_since} дней. Минимум 60 дней между донациями.',
                'days_since': days_since,
                'days_remaining': 60 - days_since
            }), 403  # 403 Forbidden
    
    # Проверяем, существует ли запрос
    req = query_db(
        "SELECT id, medical_center_id, blood_type, urgency FROM blood_requests WHERE id = %s AND status = 'active'",
        (request_id,), one=True
    )
    
    if not req:
        return jsonify({'error': 'Запрос не найден или неактивен'}), 404
    
    # Проверяем, не откликался ли уже донор
    existing = query_db(
        "SELECT id FROM donation_responses WHERE request_id = %s AND user_id = %s",
        (request_id, user_id), one=True
    )
    
    if existing:
        return jsonify({'error': 'Вы уже откликнулись на этот запрос'}), 400
    
    # Создаём отклик
    response_id = query_db(
        """INSERT INTO donation_responses 
           (request_id, user_id, medical_center_id, status, donor_comment)
           VALUES (%s, %s, %s, 'pending', %s)
           RETURNING id""",
        (request_id, user_id, req['medical_center_id'], data.get('message', '')),
        commit=True, one=True
    )['id']
    
    # Получаем информацию для ответа
    donor = query_db("""
        SELECT full_name FROM users WHERE id = %s
    """, (user_id,), one=True)
    
    return jsonify({
        'message': 'Ваш отклик отправлен. Медицинский центр свяжется с вами.',
        'response_id': response_id
    }), 201

@app.route('/api/donor/blood-requests/<int:request_id>/respond', methods=['DELETE'])
@require_auth('donor')
def cancel_blood_request_response(request_id):
    """Отменить отклик на запрос крови"""
    user_id = g.session['user_id']
    
    # Проверяем существование отклика
    response = query_db(
        "SELECT id FROM donation_responses WHERE request_id = %s AND user_id = %s",
        (request_id, user_id), one=True
    )
    
    if not response:
        return jsonify({'error': 'Отклик не найден'}), 404
    
    # Удаляем отклик
    query_db(
        "DELETE FROM donation_responses WHERE id = %s",
        (response['id'],), commit=True
    )
    
    return jsonify({'message': 'Отклик отменён'})


@app.route('/api/medcenter/responses/<int:response_id>/approve', methods=['POST'])
@require_auth('medcenter')
def approve_donor_response(response_id):
    """Одобрить донора на донацию (создаёт диалог и отправляет уведомление)"""
    medical_center_id = g.session['medical_center_id']
    data = request.json
    
    # Получаем отклик
    response_data = query_db(
        """SELECT dr.*, u.full_name, u.blood_type, u.phone, 
                  br.blood_type as requested_blood_type,
                  mc.name as medical_center_name, mc.address, mc.phone as mc_phone
           FROM donation_responses dr
           JOIN users u ON dr.user_id = u.id
           JOIN blood_requests br ON dr.request_id = br.id
           JOIN medical_centers mc ON dr.medical_center_id = mc.id
           WHERE dr.id = %s AND dr.medical_center_id = %s""",
        (response_id, medical_center_id), one=True
    )
    
    if not response_data:
        return jsonify({'error': 'Отклик не найден'}), 404
    
    if response_data['status'] == 'approved':
        return jsonify({'error': 'Донор уже одобрен'}), 400
    
    # Получаем дату и время из запроса
    donation_date = data.get('donation_date')  # ISO формат: 2026-02-15
    donation_time = data.get('donation_time', '10:00')  # Формат: HH:MM
    
    if not donation_date:
        return jsonify({'error': 'Не указана дата донации'}), 400
    
    # Обновляем статус отклика
    query_db(
        """UPDATE donation_responses 
           SET status = 'approved', 
               approved_at = NOW(),
               donation_date = %s,
               donation_time = %s
           WHERE id = %s""",
        (donation_date, donation_time, response_id), commit=True
    )
    
    # Создаём или получаем диалог
    conversation = get_or_create_conversation(
        response_data['user_id'], 
        medical_center_id, 
        query_db
    )
    
    # Формируем сообщение-уведомление
    from datetime import datetime
    date_obj = datetime.fromisoformat(donation_date)
    formatted_date = date_obj.strftime('%d %B %Y')  # 15 февраля 2026
    
    # Загружаем правила подготовки из файла проекта
    preparation_rules = """
📋 ПОДГОТОВКА К ДОНАЦИИ

За 48 часов до сдачи:
• Исключите алкогольные напитки
• Избегайте жирной, жареной, острой и копчёной пищи
• Не принимайте лекарства (кроме жизненно необходимых)

За 24 часа до сдачи:
• Хорошо выспитесь (не менее 8 часов)
• Пейте больше жидкости (вода, чай, сок)

В день сдачи:
• Лёгкий завтрак за 2-3 часа до визита (каша на воде, сухое печенье, сладкий чай)
• Не курите за 1 час до сдачи
• Возьмите с собой паспорт

❌ ПРОТИВОПОКАЗАНИЯ (при наличии — сообщите врачу):
• Повышенная температура, простуда
• Приём антибиотиков в последние 2 недели
• Недавние операции или удаление зубов
• Татуировки или пирсинг менее 1 года назад
    """.strip()
    
    notification_content = f"""✅ ВАША ЗАЯВКА ОДОБРЕНА!

📅 Дата и время: {formatted_date}, {donation_time}

🏥 Медицинский центр:
{response_data['medical_center_name']}
📍 {response_data['address']}
📞 {response_data['mc_phone']}

🩸 Группа крови: {response_data['blood_type']}

{preparation_rules}

💬 Есть вопросы? Напишите нам в этом чате.
📅 Не можете прийти? Сообщите заранее.
    """
    
    # Сохраняем уведомление в БД
    query_db(
        """INSERT INTO messages 
           (conversation_id, sender_id, sender_role, content, message_type, metadata, created_at)
           VALUES (%s, NULL, 'system', %s, 'notification', %s, NOW())""",
        (conversation['id'], notification_content, {
            'type': 'approval',
            'response_id': response_id,
            'donation_date': donation_date,
            'donation_time': donation_time,
            'medical_center_id': medical_center_id
        }),
        commit=True
    )
    
    app.logger.info(f"✅ Донор {response_data['user_id']} одобрен, уведомление отправлено")
    
    # TODO: Отправка в Telegram
    try:
        # Получаем telegram_id донора
        donor_tg = query_db(
            """SELECT telegram_id FROM telegram_link_codes 
               WHERE user_id = %s AND linked = TRUE 
               ORDER BY created_at DESC LIMIT 1""",
            (response_data['user_id'],), one=True
        )
        
        if donor_tg and donor_tg['telegram_id']:
            telegram_message = f"""✅ Ваша заявка на донацию одобрена!

📅 {formatted_date}, {donation_time}
🏥 {response_data['medical_center_name']}
📍 {response_data['address']}

⚠️ Важно: За 48 часов исключите алкоголь и жирную пищу.

📋 Полные правила подготовки на сайте"""
            
            send_notification(donor_tg['telegram_id'], telegram_message)
            app.logger.info(f"📲 Telegram уведомление отправлено донору {response_data['user_id']}")
    except Exception as e:
        app.logger.error(f"Ошибка отправки Telegram: {e}")
    
    return jsonify({
        'message': 'Донор одобрен',
        'conversation_id': conversation['id'],
        'notification_sent': True
    }), 200


@app.route('/api/medcenter/responses/<int:response_id>/reject', methods=['POST'])
@require_auth('medcenter')
def reject_donor_response(response_id):
    """Отклонить донора (создаёт диалог и отправляет уведомление)"""
    medical_center_id = g.session['medical_center_id']
    data = request.json
    
    # Получаем отклик
    response_data = query_db(
        """SELECT dr.*, u.full_name, mc.name as medical_center_name
           FROM donation_responses dr
           JOIN users u ON dr.user_id = u.id
           JOIN medical_centers mc ON dr.medical_center_id = mc.id
           WHERE dr.id = %s AND dr.medical_center_id = %s""",
        (response_id, medical_center_id), one=True
    )
    
    if not response_data:
        return jsonify({'error': 'Отклик не найден'}), 404
    
    if response_data['status'] == 'rejected':
        return jsonify({'error': 'Донор уже отклонён'}), 400
    
    reason = data.get('reason', 'Не указана')
    
    # Обновляем статус
    query_db(
        """UPDATE donation_responses 
           SET status = 'rejected', rejection_reason = %s 
           WHERE id = %s""",
        (reason, response_id), commit=True
    )
    
    # Создаём или получаем диалог
    conversation = get_or_create_conversation(
        response_data['user_id'], 
        medical_center_id, 
        query_db
    )
    
    # Формируем сообщение
    notification_content = f"""❌ ЗАЯВКА ОТКЛОНЕНА

К сожалению, ваша заявка на донацию отклонена.

Причина: {reason}

Вы можете откликнуться на другие запросы крови или связаться с нами для уточнения.
    """
    
    # Сохраняем уведомление
    query_db(
        """INSERT INTO messages 
           (conversation_id, sender_id, sender_role, content, message_type, metadata, created_at)
           VALUES (%s, NULL, 'system', %s, 'notification', %s, NOW())""",
        (conversation['id'], notification_content, {
            'type': 'rejection',
            'response_id': response_id,
            'reason': reason
        }),
        commit=True
    )
    
    app.logger.info(f"❌ Донор {response_data['user_id']} отклонён")
    
    # TODO: Отправка в Telegram
    try:
        donor_tg = query_db(
            """SELECT telegram_id FROM telegram_link_codes 
               WHERE user_id = %s AND linked = TRUE 
               ORDER BY created_at DESC LIMIT 1""",
            (response_data['user_id'],), one=True
        )
        
        if donor_tg and donor_tg['telegram_id']:
            telegram_message = f"""❌ Ваша заявка на донацию отклонена.

Причина: {reason}

Вы можете откликнуться на другие запросы."""
            
            send_notification(donor_tg['telegram_id'], telegram_message)
    except Exception as e:
        app.logger.error(f"Ошибка отправки Telegram: {e}")
    
    return jsonify({
        'message': 'Донор отклонён',
        'conversation_id': conversation['id']
    }), 200


# ============================================
# API: Сообщения для доноров
# ============================================

@app.route('/api/donor/schedule-donation', methods=['POST'])
@require_auth('donor')
def schedule_donation():
    """Записаться на плановую донацию"""
    user_id = g.session['user_id']
    data = request.json
    
    medical_center_id = data.get('medical_center_id')
    if not medical_center_id:
        return jsonify({'error': 'Не указан медицинский центр'}), 400
    
    # Получаем информацию о доноре
    donor = query_db(
        """SELECT * FROM users WHERE id = %s""",
        (user_id,), one=True
    )
    
    if not donor:
        return jsonify({'error': 'Донор не найден'}), 404
    
    # Проверяем, прошло ли 60 дней с последней донации
    if donor.get('last_donation_date'):
        from datetime import date, timedelta
        last_date = donor['last_donation_date']
        if isinstance(last_date, str):
            from datetime import datetime as dt
            last_date = dt.strptime(last_date, '%Y-%m-%d').date()
        
        days_since = (date.today() - last_date).days
        if days_since < 60:
            return jsonify({
                'error': f'С последней донации прошло только {days_since} дней. Вы сможете сдать кровь через {60 - days_since} дней.'
            }), 400
    
    # Получаем информацию о медцентре
    mc = query_db(
        """SELECT * FROM medical_centers WHERE id = %s""",
        (medical_center_id,), one=True
    )
    
    if not mc:
        return jsonify({'error': 'Медицинский центр не найден'}), 404
    
    # Ищем активный запрос крови для этой группы в этом медцентре
    blood_request = query_db(
        """SELECT * FROM blood_requests 
           WHERE medical_center_id = %s 
           AND blood_type = %s 
           AND status = 'active'
           ORDER BY created_at DESC
           LIMIT 1""",
        (medical_center_id, donor['blood_type']), one=True
    )
    
    # Если запроса нет - создаём автоматически для плановой донации
    if not blood_request:
        query_db(
            """INSERT INTO blood_requests 
               (medical_center_id, blood_type, urgency, status, description, needed_donors, auto_close)
               VALUES (%s, %s, 'planned', 'active', 'Плановая донация', NULL, false)""",
            (medical_center_id, donor['blood_type']),
            commit=True
        )
        blood_request = query_db(
            """SELECT * FROM blood_requests 
               WHERE medical_center_id = %s 
               AND blood_type = %s 
               AND status = 'active'
               ORDER BY created_at DESC
               LIMIT 1""",
            (medical_center_id, donor['blood_type']), one=True
        )
    
    # Создаём отклик донора со статусом 'pending'
    query_db(
        """INSERT INTO donation_responses 
           (request_id, user_id, medical_center_id, status, donor_comment, created_at)
           VALUES (%s, %s, %s, 'pending', %s, NOW())""",
        (
            blood_request['id'],
            user_id,
            medical_center_id,
            f"Плановая донация. Предпочтительная дата: {data.get('planned_date', 'любая')}. {data.get('comment', '')}"
        ),
        commit=True
    )
    
    # Получаем ID созданного отклика
    response_record = query_db(
        """SELECT * FROM donation_responses 
           WHERE request_id = %s AND user_id = %s
           ORDER BY created_at DESC LIMIT 1""",
        (blood_request['id'], user_id), one=True
    )
    
    # Создаём или получаем диалог
    conversation = query_db(
        """SELECT * FROM conversations 
           WHERE donor_id = %s AND medical_center_id = %s""",
        (user_id, medical_center_id), one=True
    )
    
    if not conversation:
        app.logger.info(f"Создание нового диалога: donor_id={user_id}, medical_center_id={medical_center_id}")
        query_db(
            """INSERT INTO conversations 
               (donor_id, medical_center_id, status, created_at, updated_at)
               VALUES (%s, %s, 'active', NOW(), NOW())""",
            (user_id, medical_center_id), commit=True
        )
        conversation = query_db(
            """SELECT * FROM conversations 
               WHERE donor_id = %s AND medical_center_id = %s""",
            (user_id, medical_center_id), one=True
        )
        app.logger.info(f"✅ Диалог создан: conversation_id={conversation['id']}")
    
    # Формируем сообщение для медцентра
    planned_date = data.get('planned_date')
    comment = data.get('comment')
    
    message_text = f"""📋 Заявка на плановую донацию

ФИО: {donor['full_name']}
Группа крови: {donor['blood_type']}
Телефон: {donor['phone'] or 'не указан'}
Email: {donor['email'] or 'не указан'}
Предпочтительная дата: {planned_date if planned_date else 'любая'}

{f'Комментарий донора: {comment}' if comment else ''}

Донор готов сдать кровь. Пожалуйста, подтвердите заявку и согласуйте время визита."""
    
    # Отправляем сообщение в диалог
    query_db(
        """INSERT INTO messages 
           (conversation_id, sender_role, message_type, content, metadata, created_at)
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        (
            conversation['id'],
            'donor',
            'text',
            message_text,
            json.dumps({
                'planned_date': planned_date,
                'response_id': response_record['id']
            })
        ),
        commit=True
    )
    
    return jsonify({
        'message': 'Заявка отправлена',
        'medical_center_name': mc['name'],
        'response_id': response_record['id']
    }), 201

@app.route('/api/donor/messages/<int:message_id>/read', methods=['POST'])
@require_auth('donor')
def mark_donor_message_read(message_id):
    """Отметить сообщение как прочитанное"""
    user_id = g.session['user_id']
    
    # Проверяем принадлежность сообщения
    msg = query_db(
        "SELECT id FROM messages WHERE id = %s AND to_user_id = %s",
        (message_id, user_id), one=True
    )
    
    if not msg:
        return jsonify({'error': 'Сообщение не найдено'}), 404
    
    query_db(
        "UPDATE messages SET is_read = TRUE WHERE id = %s",
        (message_id,), commit=True
    )
    
    return jsonify({'message': 'Сообщение прочитано'})

@app.route('/api/donor/messages/unread-count', methods=['GET'])
@require_auth('donor')
def get_donor_unread_count():
    """Получить количество непрочитанных сообщений"""
    user_id = g.session['user_id']
    
    result = query_db(
        "SELECT COUNT(*) as count FROM messages WHERE to_user_id = %s AND is_read = FALSE",
        (user_id,), one=True
    )
    
    return jsonify({'unread': result['count'] if result else 0})

# ============================================
# API: Система переписки (ЧАТЫ)
# ============================================

# --- ЭНДПОИНТЫ ДЛЯ МЕДЦЕНТРА ---

@app.route('/api/medcenter/chats', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_chats():
    """Получить список чатов (донорыс которыми есть переписка)"""
    mc_id = g.session['medical_center_id']
    
    # Получаем список доноров с количеством непрочитанных сообщений
    chats = query_db("""
        SELECT DISTINCT
            u.id as donor_id,
            u.full_name as donor_name,
            u.blood_type,
            u.phone as donor_phone,
            u.email as donor_email,
            (SELECT COUNT(*) 
             FROM chat_messages 
             WHERE donor_id = u.id 
               AND medcenter_id = %s 
               AND sender_type = 'donor' 
               AND is_read = FALSE
            ) as unread_count,
            (SELECT message 
             FROM chat_messages 
             WHERE donor_id = u.id AND medcenter_id = %s 
             ORDER BY created_at DESC 
             LIMIT 1
            ) as last_message,
            (SELECT created_at 
             FROM chat_messages 
             WHERE donor_id = u.id AND medcenter_id = %s 
             ORDER BY created_at DESC 
             LIMIT 1
            ) as last_message_time
        FROM users u
        INNER JOIN chat_messages cm ON u.id = cm.donor_id
        WHERE cm.medcenter_id = %s AND u.medical_center_id = %s
        ORDER BY last_message_time DESC
    """, (mc_id, mc_id, mc_id, mc_id, mc_id))
    
    return jsonify(chats or [])

@app.route('/api/medcenter/chats/<int:donor_id>', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_chat_history(donor_id):
    """Получить историю переписки с конкретным донором"""
    mc_id = g.session['medical_center_id']
    
    # Проверяем, что донор привязан к этому медцентру
    donor = query_db(
        "SELECT id, full_name FROM users WHERE id = %s AND medical_center_id = %s",
        (donor_id, mc_id), one=True
    )
    
    if not donor:
        return jsonify({'error': 'Донор не найден или не привязан к вашему медцентру'}), 404
    
    # Получаем последние 100 сообщений
    messages = query_db("""
        SELECT 
            id,
            sender_type,
            message,
            is_read,
            created_at
        FROM chat_messages
        WHERE donor_id = %s AND medcenter_id = %s
        ORDER BY created_at ASC
        LIMIT 100
    """, (donor_id, mc_id))
    
    # Отмечаем все сообщения от донора как прочитанные
    query_db("""
        UPDATE chat_messages 
        SET is_read = TRUE 
        WHERE donor_id = %s 
          AND medcenter_id = %s 
          AND sender_type = 'donor' 
          AND is_read = FALSE
    """, (donor_id, mc_id), commit=True)
    
    return jsonify({
        'donor': donor,
        'messages': messages or []
    })

@app.route('/api/medcenter/chats/<int:donor_id>/send', methods=['POST'])
@require_auth('medcenter')
def send_medcenter_chat_message(donor_id):
    """Отправить сообщение донору"""
    mc_id = g.session['medical_center_id']
    data = request.json
    
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    # Проверяем, что донор привязан к этому медцентру
    donor = query_db(
        "SELECT id, full_name, telegram_id FROM users WHERE id = %s AND medical_center_id = %s",
        (donor_id, mc_id), one=True
    )
    
    if not donor:
        return jsonify({'error': 'Донор не найден'}), 404
    
    # Сохраняем сообщение
    message_id = query_db("""
        INSERT INTO chat_messages (donor_id, medcenter_id, sender_type, message, created_at)
        VALUES (%s, %s, 'medcenter', %s, NOW())
        RETURNING id
    """, (donor_id, mc_id, message_text), commit=True, one=True)['id']
    
    # Отправляем уведомление в Telegram (если привязан)
    if donor['telegram_id']:
        try:
            from telegram_bot import send_chat_message_notification
            mc_name = query_db("SELECT name FROM medical_centers WHERE id = %s", (mc_id,), one=True)['name']
            send_chat_message_notification(
                donor['telegram_id'],
                mc_name,
                message_text[:100]  # Первые 100 символов
            )
        except Exception as e:
            app.logger.error(f"Ошибка отправки Telegram уведомления: {e}")
    
    return jsonify({
        'message_id': message_id,
        'status': 'sent'
    }), 201

# --- ЭНДПОИНТЫ ДЛЯ ДОНОРА ---

@app.route('/api/donor/chats', methods=['GET'])
@require_auth('donor')
def get_donor_chats():
    """Получить список чатов (медцентры с которыми есть переписка)"""
    donor_id = g.session['user_id']
    
    # Получаем список медцентров с количеством непрочитанных сообщений
    chats = query_db("""
        SELECT DISTINCT
            mc.id as medcenter_id,
            mc.name as medcenter_name,
            mc.address,
            mc.phone as medcenter_phone,
            mc.email as medcenter_email,
            (SELECT COUNT(*) 
             FROM chat_messages 
             WHERE medcenter_id = mc.id 
               AND donor_id = %s 
               AND sender_type = 'medcenter' 
               AND is_read = FALSE
            ) as unread_count,
            (SELECT message 
             FROM chat_messages 
             WHERE medcenter_id = mc.id AND donor_id = %s 
             ORDER BY created_at DESC 
             LIMIT 1
            ) as last_message,
            (SELECT created_at 
             FROM chat_messages 
             WHERE medcenter_id = mc.id AND donor_id = %s 
             ORDER BY created_at DESC 
             LIMIT 1
            ) as last_message_time
        FROM medical_centers mc
        INNER JOIN chat_messages cm ON mc.id = cm.medcenter_id
        WHERE cm.donor_id = %s
        ORDER BY last_message_time DESC
    """, (donor_id, donor_id, donor_id, donor_id))
    
    return jsonify(chats or [])

@app.route('/api/donor/chats/<int:medcenter_id>', methods=['GET'])
@require_auth('donor')
def get_donor_chat_history(medcenter_id):
    """Получить историю переписки с конкретным медцентром"""
    donor_id = g.session['user_id']
    
    # Проверяем, что медцентр существует
    medcenter = query_db(
        "SELECT id, name, address, phone FROM medical_centers WHERE id = %s",
        (medcenter_id,), one=True
    )
    
    if not medcenter:
        return jsonify({'error': 'Медцентр не найден'}), 404
    
    # Получаем последние 100 сообщений
    messages = query_db("""
        SELECT 
            id,
            sender_type,
            message,
            is_read,
            created_at
        FROM chat_messages
        WHERE donor_id = %s AND medcenter_id = %s
        ORDER BY created_at ASC
        LIMIT 100
    """, (donor_id, medcenter_id))
    
    # Отмечаем все сообщения от медцентра как прочитанные
    query_db("""
        UPDATE chat_messages 
        SET is_read = TRUE 
        WHERE donor_id = %s 
          AND medcenter_id = %s 
          AND sender_type = 'medcenter' 
          AND is_read = FALSE
    """, (donor_id, medcenter_id), commit=True)
    
    return jsonify({
        'medcenter': medcenter,
        'messages': messages or []
    })

@app.route('/api/donor/chats/<int:medcenter_id>/send', methods=['POST'])
@require_auth('donor')
def send_donor_chat_message(medcenter_id):
    """Отправить сообщение медцентру"""
    donor_id = g.session['user_id']
    data = request.json
    
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    # Проверяем, что медцентр существует
    medcenter = query_db(
        "SELECT id, name FROM medical_centers WHERE id = %s",
        (medcenter_id,), one=True
    )
    
    if not medcenter:
        return jsonify({'error': 'Медцентр не найден'}), 404
    
    # Сохраняем сообщение
    message_id = query_db("""
        INSERT INTO chat_messages (donor_id, medcenter_id, sender_type, message, created_at)
        VALUES (%s, %s, 'donor', %s, NOW())
        RETURNING id
    """, (donor_id, medcenter_id, message_text), commit=True, one=True)['id']
    
    app.logger.info(f"✅ Сообщение отправлено: донор {donor_id} → медцентр {medcenter_id}")
    
    return jsonify({
        'message_id': message_id,
        'status': 'sent'
    }), 201

# --- ОБЩИЕ ЭНДПОИНТЫ ---

@app.route('/api/chats/unread-count', methods=['GET'])
@require_auth()
def get_unread_count():
    """Получить количество непрочитанных сообщений"""
    session = g.session
    user_type = session['user_type']
    
    if user_type == 'donor':
        donor_id = session['user_id']
        result = query_db("""
            SELECT COUNT(*) as count 
            FROM chat_messages 
            WHERE donor_id = %s 
              AND sender_type = 'medcenter' 
              AND is_read = FALSE
        """, (donor_id,), one=True)
    elif user_type == 'medcenter':
        mc_id = session['medical_center_id']
        result = query_db("""
            SELECT COUNT(*) as count 
            FROM chat_messages 
            WHERE medcenter_id = %s 
              AND sender_type = 'donor' 
              AND is_read = FALSE
        """, (mc_id,), one=True)
    else:
        return jsonify({'unread': 0})
    
    return jsonify({'unread': result['count'] if result else 0})

# ============================================
# API: Медцентры (для доноров)
# ============================================

@app.route('/api/medical-centers', methods=['GET'])
def get_medical_centers_with_needs():
    """Получить список медцентров с данными о потребности в крови"""
    district_id = request.args.get('district_id', type=int)
    
    # Базовый запрос
    query = """
        SELECT 
            mc.id,
            mc.name,
            mc.address,
            mc.phone,
            mc.email,
            mc.district_id,
            d.name as district_name,
            r.name as region_name
        FROM medical_centers mc
        LEFT JOIN districts d ON mc.district_id = d.id
        LEFT JOIN regions r ON d.region_id = r.id
        WHERE mc.is_active = TRUE
    """
    
    params = []
    if district_id:
        query += " AND mc.district_id = %s"
        params.append(district_id)
    
    query += " ORDER BY mc.name"
    
    centers = query_db(query, tuple(params) if params else ())
    
    # Для каждого медцентра получаем данные о потребности в крови
    for center in centers:
        blood_needs = query_db(
            """SELECT blood_type, status, last_updated 
               FROM blood_needs 
               WHERE medical_center_id = %s
               ORDER BY blood_type""",
            (center['id'],)
        )
        center['blood_needs'] = blood_needs or []
    
    return jsonify(centers or [])

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

# ============================================
# API: Учёт донаций медцентром
# ============================================

# ============================================
# API: Статистика для медцентров
# ============================================

@app.route('/api/medical-center/statistics', methods=['GET'])
@require_auth('medcenter')
def get_medical_center_statistics():
    """Получить статистику медцентра за период"""
    from datetime import datetime, timedelta, date
    
    medical_center_id = g.session['medical_center_id']
    
    # Получаем параметры периода
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    period = request.args.get('period', 'month')  # today, week, month, quarter, year, all
    
    # Определяем даты периода
    today = date.today()
    
    if from_date and to_date:
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    elif period == 'today':
        start_date = today
        end_date = today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
        end_date = today
    elif period == 'year':
        start_date = today - timedelta(days=365)
        end_date = today
    else:  # all
        start_date = date(2020, 1, 1)
        end_date = today
    
    # Предыдущий период (для сравнения)
    period_length = (end_date - start_date).days + 1
    prev_start_date = start_date - timedelta(days=period_length)
    prev_end_date = start_date - timedelta(days=1)
    
    # ========== ЗАПРОСЫ КРОВИ ==========
    blood_requests_stats = query_db("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
            SUM(CASE WHEN urgency = 'normal' THEN 1 ELSE 0 END) as normal_urgency,
            SUM(CASE WHEN urgency = 'needed' THEN 1 ELSE 0 END) as needed_urgency,
            SUM(CASE WHEN urgency = 'urgent' THEN 1 ELSE 0 END) as urgent_urgency,
            SUM(CASE WHEN urgency = 'critical' THEN 1 ELSE 0 END) as critical_urgency
        FROM blood_requests
        WHERE medical_center_id = %s
        AND created_at::date BETWEEN %s AND %s
    """, (medical_center_id, start_date, end_date), one=True)
    
    # Статистика предыдущего периода
    prev_requests_count = query_db("""
        SELECT COUNT(*) as total FROM blood_requests
        WHERE medical_center_id = %s
        AND created_at::date BETWEEN %s AND %s
    """, (medical_center_id, prev_start_date, prev_end_date), one=True)['total'] or 0
    
    # Статистика по группам крови
    requests_by_blood_type = query_db("""
        SELECT blood_type, COUNT(*) as count
        FROM blood_requests
        WHERE medical_center_id = %s
        AND created_at::date BETWEEN %s AND %s
        GROUP BY blood_type
        ORDER BY count DESC
    """, (medical_center_id, start_date, end_date))
    
    # ========== ДОНОРЫ И ОТКЛИКИ ==========
    responses_stats = query_db("""
        SELECT 
            COUNT(DISTINCT dr.user_id) as unique_donors,
            COUNT(*) as total_responses,
            SUM(CASE WHEN dr.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
            SUM(CASE WHEN dr.status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN dr.status = 'cancelled' OR dr.status = 'rejected' THEN 1 ELSE 0 END) as declined
        FROM donation_responses dr
        JOIN blood_requests br ON dr.request_id = br.id
        WHERE br.medical_center_id = %s
        AND dr.created_at::date BETWEEN %s AND %s
    """, (medical_center_id, start_date, end_date), one=True)
    
    prev_responses_count = query_db("""
        SELECT COUNT(*) as total FROM donation_responses dr
        JOIN blood_requests br ON dr.request_id = br.id
        WHERE br.medical_center_id = %s
        AND dr.created_at::date BETWEEN %s AND %s
    """, (medical_center_id, prev_start_date, prev_end_date), one=True)['total'] or 0
    
    # ========== ДОНАЦИИ ==========
    donations_stats = query_db("""
        SELECT 
            COUNT(*) as total_donations,
            COALESCE(SUM(volume_ml), 0) as total_volume_ml
        FROM donation_history dh
        JOIN users u ON dh.donor_id = u.id
        WHERE dh.medical_center_id = %s
        AND dh.donation_date BETWEEN %s AND %s
    """, (medical_center_id, start_date, end_date), one=True)
    
    prev_donations_count = query_db("""
        SELECT COUNT(*) as total FROM donation_history
        WHERE medical_center_id = %s
        AND donation_date BETWEEN %s AND %s
    """, (medical_center_id, prev_start_date, prev_end_date), one=True)['total'] or 0
    
    # Донации по группам крови
    donations_by_blood_type = query_db("""
        SELECT 
            u.blood_type,
            COUNT(*) as count,
            COALESCE(SUM(dh.volume_ml), 0) as total_volume
        FROM donation_history dh
        JOIN users u ON dh.donor_id = u.id
        WHERE dh.medical_center_id = %s
        AND dh.donation_date BETWEEN %s AND %s
        GROUP BY u.blood_type
        ORDER BY count DESC
    """, (medical_center_id, start_date, end_date))
    
    # Рассчитываем проценты изменений
    def calc_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
    
    requests_change = calc_change(blood_requests_stats['total'] or 0, prev_requests_count)
    responses_change = calc_change(responses_stats['total_responses'] or 0, prev_responses_count)
    donations_change = calc_change(donations_stats['total_donations'] or 0, prev_donations_count)
    
    # Формируем ответ
    stats = {
        'period': {
            'from': start_date.isoformat(),
            'to': end_date.isoformat(),
            'period_type': period
        },
        'blood_requests': {
            'total': blood_requests_stats['total'] or 0,
            'active': blood_requests_stats['active'] or 0,
            'closed': blood_requests_stats['closed'] or 0,
            'cancelled': blood_requests_stats['cancelled'] or 0,
            'expired': blood_requests_stats['expired'] or 0,
            'by_urgency': {
                'normal': blood_requests_stats['normal_urgency'] or 0,
                'needed': blood_requests_stats['needed_urgency'] or 0,
                'urgent': blood_requests_stats['urgent_urgency'] or 0,
                'critical': blood_requests_stats['critical_urgency'] or 0
            },
            'by_blood_type': [dict(r) for r in requests_by_blood_type],
            'change_percent': requests_change
        },
        'responses': {
            'unique_donors': responses_stats['unique_donors'] or 0,
            'total_responses': responses_stats['total_responses'] or 0,
            'confirmed': responses_stats['confirmed'] or 0,
            'pending': responses_stats['pending'] or 0,
            'declined': responses_stats['declined'] or 0,
            'conversion_rate': round((responses_stats['confirmed'] or 0) / (responses_stats['total_responses'] or 1) * 100, 1),
            'change_percent': responses_change
        },
        'donations': {
            'total': donations_stats['total_donations'] or 0,
            'total_volume_ml': donations_stats['total_volume_ml'] or 0,
            'total_volume_liters': round((donations_stats['total_volume_ml'] or 0) / 1000, 2),
            'by_blood_type': [dict(r) for r in donations_by_blood_type],
            'change_percent': donations_change
        }
    }
    
    return jsonify(stats), 200

@app.route('/api/medical-center/statistics/export', methods=['GET'])
@require_auth('medcenter')
def export_statistics():
    """Экспорт статистики в TXT"""
    from datetime import datetime
    import io
    from flask import Response
    
    # Получаем статистику
    stats_response = get_medical_center_statistics()
    stats = stats_response[0].get_json()
    
    # Получаем название медцентра
    mc = query_db(
        "SELECT name FROM medical_centers WHERE id = %s",
        (g.session['medical_center_id'],), one=True
    )
    mc_name = mc['name'] if mc else 'Медицинский центр'
    
    # Формируем текстовый отчёт
    output = io.StringIO()
    
    output.write("=" * 60 + "\n")
    output.write("        СТАТИСТИКА МЕДИЦИНСКОГО ЦЕНТРА\n")
    output.write("=" * 60 + "\n\n")
    output.write(f"Центр: {mc_name}\n")
    output.write(f"Период: {stats['period']['from']} — {stats['period']['to']}\n")
    output.write(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
    
    output.write("-" * 60 + "\n")
    output.write("                    ЗАПРОСЫ КРОВИ\n")
    output.write("-" * 60 + "\n\n")
    
    req = stats['blood_requests']
    output.write(f"Всего запросов:                    {req['total']}\n")
    output.write(f"  - Активных:                       {req['active']}\n")
    output.write(f"  - Завершённых:                    {req['closed']}\n")
    output.write(f"  - Отменённых:                     {req['cancelled']}\n")
    output.write(f"  - Истёкших:                       {req['expired']}\n\n")
    
    output.write("По срочности:\n")
    output.write(f"  - Обычных:                        {req['by_urgency']['normal']}\n")
    output.write(f"  - Нужно пополнить:                {req['by_urgency']['needed']}\n")
    output.write(f"  - Срочных:                        {req['by_urgency']['urgent']}\n")
    output.write(f"  - Критичных:                      {req['by_urgency']['critical']}\n\n")
    
    if req['by_blood_type']:
        output.write("По группам крови:\n")
        for bt in req['by_blood_type']:
            output.write(f"  - {bt['blood_type']:5s}                          {bt['count']}\n")
    output.write("\n")
    
    output.write("-" * 60 + "\n")
    output.write("                  ДОНОРЫ И ОТКЛИКИ\n")
    output.write("-" * 60 + "\n\n")
    
    resp = stats['responses']
    output.write(f"Уникальных доноров:                {resp['unique_donors']}\n")
    output.write(f"Всего откликов:                    {resp['total_responses']}\n")
    output.write(f"  - Одобрено:                       {resp['confirmed']}\n")
    output.write(f"  - Ожидают решения:                {resp['pending']}\n")
    output.write(f"  - Отклонено:                      {resp['declined']}\n\n")
    output.write(f"Конверсия откликов:                {resp['conversion_rate']}%\n\n")
    
    output.write("-" * 60 + "\n")
    output.write("                      ДОНАЦИИ\n")
    output.write("-" * 60 + "\n\n")
    
    don = stats['donations']
    output.write(f"Всего донаций:                     {don['total']}\n")
    output.write(f"Общий объём:                       {don['total_volume_liters']} л\n\n")
    
    if don['by_blood_type']:
        output.write("По группам крови:\n")
        for bt in don['by_blood_type']:
            volume_l = round(bt['total_volume'] / 1000, 2)
            output.write(f"  - {bt['blood_type']:5s}    {bt['count']:3d} донаций   ({volume_l:6.2f} л)\n")
    output.write("\n")
    
    output.write("-" * 60 + "\n")
    output.write("              СРАВНЕНИЕ С ПРОШЛЫМ ПЕРИОДОМ\n")
    output.write("-" * 60 + "\n\n")
    
    output.write(f"Запросов:                          {req['change_percent']:+.1f}%\n")
    output.write(f"Откликов:                          {resp['change_percent']:+.1f}%\n")
    output.write(f"Донаций:                           {don['change_percent']:+.1f}%\n\n")
    
    output.write("=" * 60 + "\n")
    output.write("        Конец отчёта. Спасибо за вашу работу!\n")
    output.write("=" * 60 + "\n")
    
    # Формируем имя файла (транслитерация для избежания проблем с кодировкой)
    from urllib.parse import quote
    period_str = f"{stats['period']['from']}_{stats['period']['to']}"
    filename_safe = f"statistics_medcenter_{g.session['medical_center_id']}_{period_str}.txt"
    filename_display = f"statistics_{mc_name.replace(' ', '_')}_{period_str}.txt"
    
    return Response(
        output.getvalue(),
        mimetype='text/plain; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename_safe}"; filename*=UTF-8\'\'{quote(filename_display)}'
        }
    )

# ============================================
# API: СИСТЕМА СООБЩЕНИЙ (Мессенджер)
# ============================================

# Импорт функций из messaging_api
from messaging_api import (
    get_or_create_conversation,
    format_conversation,
    format_message,
    get_avatar_initials
)

# Диалоги
@app.route('/api/messages/conversations', methods=['GET'])
@require_auth()
def get_conversations():
    """Список диалогов пользователя"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    app.logger.info(f"📥 Запрос диалогов: user_type={user_type}, user_id={user_id}, medical_center_id={medical_center_id}")
    
    status = request.args.get('status', 'active')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    if user_type == 'donor':
        conversations = query_db(
            """SELECT c.*, 
                      c.donor_unread_count as unread_count,
                      mc.id as partner_id,
                      mc.name as partner_name,
                      mc.address,
                      mc.phone
               FROM conversations c
               JOIN medical_centers mc ON c.medical_center_id = mc.id
               WHERE c.donor_id = %s AND c.status = %s
               ORDER BY c.last_message_at DESC NULLS LAST
               LIMIT %s OFFSET %s""",
            (user_id, status, limit, offset)
        )
        
        result = []
        for conv in conversations:
            partner_info = {
                'id': conv['partner_id'],
                'name': conv['partner_name'],
                'type': 'medical_center',
                'address': conv.get('address'),
                'phone': conv.get('phone')
            }
            result.append(format_conversation(conv, partner_info, conv['unread_count'], query_db))
        
        return jsonify({'conversations': result, 'total': len(result)})
    
    elif user_type == 'medcenter':
        app.logger.info(f"🔍 Ищем диалоги для медцентра {medical_center_id}")
        conversations = query_db(
            """SELECT c.*, 
                      c.medcenter_unread_count as unread_count,
                      u.id as partner_id,
                      u.full_name as partner_name,
                      u.blood_type,
                      u.donation_count
               FROM conversations c
               JOIN users u ON c.donor_id = u.id
               WHERE c.medical_center_id = %s AND c.status = %s
               ORDER BY c.last_message_at DESC NULLS LAST
               LIMIT %s OFFSET %s""",
            (medical_center_id, status, limit, offset)
        )
        
        app.logger.info(f"📊 Найдено диалогов: {len(conversations) if conversations else 0}")
        
        result = []
        for conv in conversations:
            partner_info = {
                'id': conv['partner_id'],
                'full_name': conv['partner_name'],
                'type': 'donor',
                'blood_type': conv.get('blood_type'),
                'donation_count': conv.get('donation_count', 0)
            }
            result.append(format_conversation(conv, partner_info, conv['unread_count'], query_db))
        
        app.logger.info(f"✅ Возвращаем {len(result)} диалогов медцентру")
        return jsonify({'conversations': result, 'total': len(result)})
    
    return jsonify({'error': 'Неизвестный тип пользователя'}), 400


@app.route('/api/messages/conversations/<int:conversation_id>', methods=['GET'])
@require_auth()
def get_conversation(conversation_id):
    """Получить один диалог"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            """SELECT c.*, 
                      mc.id as partner_id,
                      mc.name as partner_name,
                      mc.address,
                      mc.phone
               FROM conversations c
               JOIN medical_centers mc ON c.medical_center_id = mc.id
               WHERE c.id = %s AND c.donor_id = %s""",
            (conversation_id, user_id), one=True
        )
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        partner_info = {
            'id': conversation['partner_id'],
            'name': conversation['partner_name'],
            'type': 'medical_center',
            'address': conversation.get('address'),
            'phone': conversation.get('phone')
        }
        unread_count = conversation.get('donor_unread_count', 0)
    
    elif user_type == 'medcenter':
        conversation = query_db(
            """SELECT c.*, 
                      u.id as partner_id,
                      u.full_name as partner_name,
                      u.blood_type,
                      u.donation_count,
                      u.phone,
                      u.email
               FROM conversations c
               JOIN users u ON c.donor_id = u.id
               WHERE c.id = %s AND c.medical_center_id = %s""",
            (conversation_id, medical_center_id), one=True
        )
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        partner_info = {
            'id': conversation['partner_id'],
            'full_name': conversation['partner_name'],
            'type': 'donor',
            'blood_type': conversation.get('blood_type'),
            'donation_count': conversation.get('donation_count', 0),
            'phone': conversation.get('phone'),
            'email': conversation.get('email')
        }
        unread_count = conversation.get('medcenter_unread_count', 0)
    
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    return jsonify(format_conversation(conversation, partner_info, unread_count, query_db))


@app.route('/api/messages/conversations', methods=['POST'])
@require_auth()
def create_conversation():
    """Создать новый диалог"""
    data = request.json
    recipient_id = data.get('recipient_id')
    
    if not recipient_id:
        return jsonify({'error': 'Не указан получатель'}), 400
    
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = get_or_create_conversation(user_id, recipient_id, query_db)
    elif user_type == 'medcenter':
        conversation = get_or_create_conversation(recipient_id, medical_center_id, query_db)
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    return jsonify({'conversation_id': conversation['id'], 'message': 'Диалог создан'}), 201


@app.route('/api/messages/conversations/<int:conversation_id>/archive', methods=['PUT'])
@require_auth()
def archive_conversation(conversation_id):
    """Архивировать диалог"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
            (conversation_id, user_id), one=True
        )
    elif user_type == 'medcenter':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
            (conversation_id, medical_center_id), one=True
        )
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    if not conversation:
        return jsonify({'error': 'Диалог не найден'}), 404
    
    query_db(
        "UPDATE conversations SET status = 'archived', updated_at = NOW() WHERE id = %s",
        (conversation_id,), commit=True
    )
    
    return jsonify({'message': 'Диалог архивирован'})


@app.route('/api/messages/conversations/<int:conversation_id>/unarchive', methods=['PUT'])
@require_auth()
def unarchive_conversation(conversation_id):
    """Восстановить диалог"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
            (conversation_id, user_id), one=True
        )
    elif user_type == 'medcenter':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
            (conversation_id, medical_center_id), one=True
        )
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    if not conversation:
        return jsonify({'error': 'Диалог не найден'}), 404
    
    query_db(
        "UPDATE conversations SET status = 'active', updated_at = NOW() WHERE id = %s",
        (conversation_id,), commit=True
    )
    
    return jsonify({'message': 'Диалог восстановлен'})


# Сообщения
@app.route('/api/messages/conversations/<int:conversation_id>/messages', methods=['GET'])
@require_auth()
def get_conversation_messages(conversation_id):
    """Получить сообщения в диалоге"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
            (conversation_id, user_id), one=True
        )
    elif user_type == 'medcenter':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
            (conversation_id, medical_center_id), one=True
        )
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    if not conversation:
        return jsonify({'error': 'Диалог не найден'}), 404
    
    limit = min(int(request.args.get('limit', 50)), 100)
    before_id = request.args.get('before_id')
    
    if before_id:
        messages = query_db(
            """SELECT * FROM messages 
               WHERE conversation_id = %s 
                 AND deleted_at IS NULL 
                 AND id < %s
               ORDER BY created_at DESC 
               LIMIT %s""",
            (conversation_id, before_id, limit)
        )
    else:
        messages = query_db(
            """SELECT * FROM messages 
               WHERE conversation_id = %s 
                 AND deleted_at IS NULL
               ORDER BY created_at DESC 
               LIMIT %s""",
            (conversation_id, limit)
        )
    
    result = [format_message(msg) for msg in messages]
    result.reverse()
    
    return jsonify({'messages': result, 'count': len(result)})


@app.route('/api/messages/conversations/<int:conversation_id>/messages', methods=['POST'])
@require_auth()
def send_conversation_message(conversation_id):
    """Отправить сообщение"""
    data = request.json
    content = data.get('content', '').strip()
    message_type = data.get('type', 'text')
    metadata = data.get('metadata')
    
    if not content:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            "SELECT * FROM conversations WHERE id = %s AND donor_id = %s",
            (conversation_id, user_id), one=True
        )
        sender_id = user_id
        sender_role = 'donor'
    elif user_type == 'medcenter':
        conversation = query_db(
            "SELECT * FROM conversations WHERE id = %s AND medical_center_id = %s",
            (conversation_id, medical_center_id), one=True
        )
        sender_id = None
        sender_role = 'medical_center'
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    if not conversation:
        return jsonify({'error': 'Диалог не найден'}), 404
    
    query_db(
        """INSERT INTO messages 
           (conversation_id, sender_id, sender_role, content, message_type, metadata, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
        (conversation_id, sender_id, sender_role, content, message_type, 
         metadata if metadata else None),
        commit=True
    )
    
    message = query_db(
        """SELECT * FROM messages 
           WHERE conversation_id = %s 
           ORDER BY created_at DESC 
           LIMIT 1""",
        (conversation_id,), one=True
    )
    
    app.logger.info(f"✅ Сообщение отправлено: {sender_role} -> conversation {conversation_id}")
    
    # Отправка в Telegram если сообщение от медцентра донору
    if sender_role == 'medical_center':
        # Получаем telegram_id донора
        donor = query_db(
            """SELECT u.telegram_id, u.full_name 
               FROM users u
               JOIN conversations c ON u.id = c.donor_id
               WHERE c.id = %s AND u.telegram_id IS NOT NULL""",
            (conversation_id,), one=True
        )
        
        if donor and donor.get('telegram_id'):
            try:
                # Получаем название медцентра
                mc = query_db(
                    """SELECT mc.name 
                       FROM medical_centers mc
                       JOIN conversations c ON mc.id = c.medical_center_id
                       WHERE c.id = %s""",
                    (conversation_id,), one=True
                )
                
                mc_name = mc['name'] if mc else 'Медицинский центр'
                
                # Формируем сообщение для Telegram
                telegram_text = f"""💬 Новое сообщение от {mc_name}

{content}

📱 Ответить: {APP_URL}/pages/donor-dashboard.html#messages"""
                
                send_telegram_message(donor['telegram_id'], telegram_text)
                app.logger.info(f"📱 Telegram отправлен донору {donor['full_name']}")
            except Exception as e:
                app.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
    
    return jsonify(format_message(message)), 201


@app.route('/api/messages/messages/<int:message_id>', methods=['PUT'])
@require_auth()
def edit_message(message_id):
    """Редактировать сообщение"""
    data = request.json
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    user_type = g.session.get('user_type')
    
    message = query_db(
        "SELECT * FROM messages WHERE id = %s AND deleted_at IS NULL",
        (message_id,), one=True
    )
    
    if not message:
        return jsonify({'error': 'Сообщение не найдено'}), 404
    
    if message['message_type'] != 'text':
        return jsonify({'error': 'Можно редактировать только обычные сообщения'}), 403
    
    if user_type == 'donor' and message['sender_role'] != 'donor':
        return jsonify({'error': 'Вы не можете редактировать это сообщение'}), 403
    
    if user_type == 'medcenter' and message['sender_role'] != 'medical_center':
        return jsonify({'error': 'Вы не можете редактировать это сообщение'}), 403
    
    query_db(
        """UPDATE messages 
           SET content = %s, edited_at = NOW() 
           WHERE id = %s""",
        (new_content, message_id), commit=True
    )
    
    updated_message = query_db(
        "SELECT * FROM messages WHERE id = %s",
        (message_id,), one=True
    )
    
    return jsonify(format_message(updated_message))


@app.route('/api/messages/messages/<int:message_id>', methods=['DELETE'])
@require_auth()
def delete_message(message_id):
    """Удалить сообщение"""
    user_type = g.session.get('user_type')
    
    message = query_db(
        "SELECT * FROM messages WHERE id = %s AND deleted_at IS NULL",
        (message_id,), one=True
    )
    
    if not message:
        return jsonify({'error': 'Сообщение не найдено'}), 404
    
    if message['message_type'] != 'text':
        return jsonify({'error': 'Можно удалять только обычные сообщения'}), 403
    
    if user_type == 'donor' and message['sender_role'] != 'donor':
        return jsonify({'error': 'Вы не можете удалить это сообщение'}), 403
    
    if user_type == 'medcenter' and message['sender_role'] != 'medical_center':
        return jsonify({'error': 'Вы не можете удалить это сообщение'}), 403
    
    query_db(
        "UPDATE messages SET deleted_at = NOW() WHERE id = %s",
        (message_id,), commit=True
    )
    
    return jsonify({'message': 'Сообщение удалено'})


@app.route('/api/messages/conversations/<int:conversation_id>/read', methods=['POST'])
@require_auth()
def mark_conversation_read(conversation_id):
    """Отметить все сообщения как прочитанные"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    if user_type == 'donor':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
            (conversation_id, user_id), one=True
        )
        query_db(
            """UPDATE messages 
               SET is_read = TRUE, read_at = NOW() 
               WHERE conversation_id = %s 
                 AND is_read = FALSE 
                 AND sender_role IN ('medical_center', 'system')""",
            (conversation_id,), commit=True
        )
    elif user_type == 'medcenter':
        conversation = query_db(
            "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
            (conversation_id, medical_center_id), one=True
        )
        query_db(
            """UPDATE messages 
               SET is_read = TRUE, read_at = NOW() 
               WHERE conversation_id = %s 
                 AND is_read = FALSE 
                 AND sender_role = 'donor'""",
            (conversation_id,), commit=True
        )
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    if not conversation:
        return jsonify({'error': 'Диалог не найден'}), 404
    
    return jsonify({'message': 'Сообщения отмечены как прочитанные'})


@app.route('/api/messages/updates', methods=['GET'])
@require_auth()
def get_message_updates():
    """Long polling для новых сообщений"""
    user_type = g.session.get('user_type')
    user_id = g.session.get('user_id')
    medical_center_id = g.session.get('medical_center_id')
    
    last_id = request.args.get('last_id', type=int, default=0)
    
    if user_type == 'donor':
        messages = query_db(
            """SELECT m.* 
               FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.donor_id = %s 
                 AND m.id > %s
                 AND m.deleted_at IS NULL
               ORDER BY m.created_at ASC
               LIMIT 50""",
            (user_id, last_id)
        )
        
        unread_counts = query_db(
            """SELECT id, donor_unread_count as unread_count
               FROM conversations
               WHERE donor_id = %s AND donor_unread_count > 0""",
            (user_id,)
        )
    
    elif user_type == 'medcenter':
        messages = query_db(
            """SELECT m.* 
               FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.medical_center_id = %s 
                 AND m.id > %s
                 AND m.deleted_at IS NULL
               ORDER BY m.created_at ASC
               LIMIT 50""",
            (medical_center_id, last_id)
        )
        
        unread_counts = query_db(
            """SELECT id, medcenter_unread_count as unread_count
               FROM conversations
               WHERE medical_center_id = %s AND medcenter_unread_count > 0""",
            (medical_center_id,)
        )
    
    else:
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    formatted_messages = [format_message(msg) for msg in messages]
    
    return jsonify({
        'messages': formatted_messages,
        'unread_counts': {str(row['id']): row['unread_count'] for row in unread_counts},
        'timestamp': datetime.now().isoformat()
    })


# Шаблоны сообщений
@app.route('/api/messages/templates', methods=['GET'])
@require_auth('medcenter')
def get_message_templates():
    """Получить шаблоны сообщений"""
    medical_center_id = g.session.get('medical_center_id')
    
    # Получаем предустановленные + свои шаблоны
    templates = query_db(
        """SELECT * FROM message_templates 
           WHERE is_predefined = TRUE 
              OR medical_center_id = %s
           ORDER BY is_predefined DESC, name ASC""",
        (medical_center_id,)
    )
    
    result = [{
        'id': t['id'],
        'name': t['name'],
        'content': t['content'],
        'variables': t.get('variables', []),
        'is_predefined': t.get('is_predefined', False)
    } for t in templates]
    
    return jsonify({'templates': result})


@app.route('/api/messages/templates', methods=['POST'])
@require_auth('medcenter')
def create_message_template():
    """Создать свой шаблон"""
    data = request.json
    name = data.get('name', '').strip()
    content = data.get('content', '').strip()
    
    if not name or not content:
        return jsonify({'error': 'Название и содержимое обязательны'}), 400
    
    medical_center_id = g.session.get('medical_center_id')
    
    query_db(
        """INSERT INTO message_templates (medical_center_id, name, content, created_at)
           VALUES (%s, %s, %s, NOW())""",
        (medical_center_id, name, content), commit=True
    )
    
    template = query_db(
        """SELECT * FROM message_templates 
           WHERE medical_center_id = %s 
           ORDER BY created_at DESC 
           LIMIT 1""",
        (medical_center_id,), one=True
    )
    
    return jsonify({
        'id': template['id'],
        'name': template['name'],
        'content': template['content'],
        'message': 'Шаблон создан'
    }), 201


# ============================================
# Запуск сервера
# ============================================

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
