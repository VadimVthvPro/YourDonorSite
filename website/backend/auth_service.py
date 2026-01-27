"""
============================================
Твой Донор - Auth Service
============================================
JWT + Refresh Token система авторизации
Автоматическое запоминание всех пользователей

@version 2.0.0
@date 2026-01-27
"""

import os
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, make_response

# ============================================
# Конфигурация
# ============================================

# JWT секрет (должен быть в .env)
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Время жизни токенов
ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)  # 30 минут
REFRESH_TOKEN_EXPIRES = timedelta(days=30)     # 30 дней для всех

# Cookie настройки
COOKIE_NAME = 'refresh_token'
COOKIE_PATH = '/'
COOKIE_HTTPONLY = True

# ВАЖНО для cross-origin (Telegram Mini App):
# - Secure=True обязательно при SameSite=None
# - SameSite=None нужен для cross-origin запросов
# Для production (HTTPS) - True, для development (HTTP) - False
IS_PRODUCTION = os.getenv('FLASK_ENV', 'production') != 'development'
COOKIE_SECURE = IS_PRODUCTION  # Secure только для HTTPS

# SameSite настройки:
# - 'None' + Secure: для cross-origin (Telegram Mini App)
# - 'Lax': для same-site навигации
# - 'Strict': максимальная безопасность, но ломает cross-site
COOKIE_SAMESITE = 'None' if IS_PRODUCTION else 'Lax'  # None для cross-origin в production


# ============================================
# Генерация токенов
# ============================================

def generate_access_token(user_id, user_type, extra_claims=None):
    """
    Генерация JWT access token
    
    @param user_id: ID пользователя или медцентра
    @param user_type: 'donor' | 'medcenter'
    @param extra_claims: Дополнительные данные для токена
    @return: JWT строка
    """
    now = datetime.utcnow()
    
    payload = {
        'sub': str(user_id),           # Subject (ID)
        'type': user_type,              # Тип пользователя
        'iat': now,                     # Issued At
        'exp': now + ACCESS_TOKEN_EXPIRES,  # Expiration
        'jti': secrets.token_hex(16)    # JWT ID (уникальный идентификатор)
    }
    
    if extra_claims:
        payload.update(extra_claims)
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token():
    """
    Генерация криптографически стойкого refresh token
    
    @return: Случайная строка 64 символа
    """
    return secrets.token_urlsafe(48)  # 64 символа base64


def hash_token(token):
    """
    Хэширование токена для хранения в БД
    
    @param token: Оригинальный токен
    @return: SHA256 хэш
    """
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================
# Верификация токенов
# ============================================

def verify_access_token(token):
    """
    Проверка и декодирование JWT access token
    
    @param token: JWT строка
    @return: Декодированный payload или None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Токен истёк
    except jwt.InvalidTokenError:
        return None  # Невалидный токен


def verify_refresh_token(token, query_db_func):
    """
    Проверка refresh token в БД
    
    @param token: Refresh token из cookie
    @param query_db_func: Функция для запросов к БД
    @return: Сессия из БД или None
    """
    token_hash = hash_token(token)
    
    session = query_db_func(
        """SELECT * FROM user_sessions 
           WHERE refresh_token_hash = %s 
             AND is_active = TRUE 
             AND expires_at > NOW()""",
        (token_hash,), one=True
    )
    
    return session


# ============================================
# Создание и управление сессиями
# ============================================

def create_session(query_db_func, user_id=None, medical_center_id=None, 
                   user_type='donor', device_info=None, ip_address=None, 
                   platform='web'):
    """
    Создание новой сессии с refresh token
    
    @return: (access_token, refresh_token, session_id)
    """
    # Генерируем токены
    entity_id = user_id if user_type == 'donor' else medical_center_id
    access_token = generate_access_token(entity_id, user_type)
    refresh_token = generate_refresh_token()
    refresh_hash = hash_token(refresh_token)
    
    expires_at = datetime.utcnow() + REFRESH_TOKEN_EXPIRES
    
    # Сохраняем в БД
    query_db_func(
        """INSERT INTO user_sessions 
           (user_id, medical_center_id, refresh_token_hash, user_type, 
            device_info, ip_address, platform, expires_at, last_used_at, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)""",
        (user_id, medical_center_id, refresh_hash, user_type,
         device_info, ip_address, platform, expires_at),
        commit=True
    )
    
    # Получаем ID созданной сессии
    session = query_db_func(
        "SELECT id FROM user_sessions WHERE refresh_token_hash = %s",
        (refresh_hash,), one=True
    )
    
    return access_token, refresh_token, session['id'] if session else None


def rotate_refresh_token(query_db_func, old_token):
    """
    Ротация refresh token (создание нового при каждом использовании)
    
    @param old_token: Текущий refresh token
    @return: (new_access_token, new_refresh_token) или (None, None)
    """
    old_hash = hash_token(old_token)
    
    # Находим сессию
    session = query_db_func(
        """SELECT * FROM user_sessions 
           WHERE refresh_token_hash = %s 
             AND is_active = TRUE 
             AND expires_at > NOW()""",
        (old_hash,), one=True
    )
    
    if not session:
        return None, None
    
    # Генерируем новые токены
    user_type = session['user_type']
    entity_id = session['user_id'] if user_type == 'donor' else session['medical_center_id']
    
    new_access_token = generate_access_token(entity_id, user_type)
    new_refresh_token = generate_refresh_token()
    new_refresh_hash = hash_token(new_refresh_token)
    
    # Обновляем сессию (token rotation)
    new_expires_at = datetime.utcnow() + REFRESH_TOKEN_EXPIRES
    
    query_db_func(
        """UPDATE user_sessions 
           SET refresh_token_hash = %s, 
               expires_at = %s,
               last_used_at = NOW()
           WHERE id = %s""",
        (new_refresh_hash, new_expires_at, session['id']),
        commit=True
    )
    
    return new_access_token, new_refresh_token


def invalidate_session(query_db_func, refresh_token):
    """
    Инвалидация сессии (logout)
    
    @param refresh_token: Refresh token из cookie
    @return: True если успешно
    """
    token_hash = hash_token(refresh_token)
    
    rows = query_db_func(
        "UPDATE user_sessions SET is_active = FALSE WHERE refresh_token_hash = %s",
        (token_hash,), commit=True
    )
    
    return rows > 0 if rows else False


def invalidate_all_sessions(query_db_func, user_id=None, medical_center_id=None):
    """
    Инвалидация всех сессий пользователя (logout-all)
    """
    if user_id:
        query_db_func(
            "UPDATE user_sessions SET is_active = FALSE WHERE user_id = %s",
            (user_id,), commit=True
        )
    elif medical_center_id:
        query_db_func(
            "UPDATE user_sessions SET is_active = FALSE WHERE medical_center_id = %s",
            (medical_center_id,), commit=True
        )


def get_active_sessions(query_db_func, user_id=None, medical_center_id=None):
    """
    Получить список активных сессий пользователя
    """
    if user_id:
        return query_db_func(
            """SELECT id, device_info, ip_address, platform, created_at, last_used_at
               FROM user_sessions 
               WHERE user_id = %s AND is_active = TRUE AND expires_at > NOW()
               ORDER BY last_used_at DESC""",
            (user_id,)
        )
    elif medical_center_id:
        return query_db_func(
            """SELECT id, device_info, ip_address, platform, created_at, last_used_at
               FROM user_sessions 
               WHERE medical_center_id = %s AND is_active = TRUE AND expires_at > NOW()
               ORDER BY last_used_at DESC""",
            (medical_center_id,)
        )
    return []


# ============================================
# Cookie хелперы
# ============================================

def set_refresh_cookie(response, refresh_token):
    """
    Установка HttpOnly cookie с refresh token
    """
    max_age = int(REFRESH_TOKEN_EXPIRES.total_seconds())
    
    response.set_cookie(
        COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH
    )
    
    return response


def clear_refresh_cookie(response):
    """
    Очистка refresh token cookie
    """
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH
    )
    return response


def get_refresh_token_from_request():
    """
    Извлечение refresh token из cookie ИЛИ header
    
    Порядок приоритета:
    1. Header X-Refresh-Token (для Telegram Mini App)
    2. Cookie refresh_token (для веба)
    """
    # 🔥 Сначала проверяем Header (для Telegram)
    header_token = request.headers.get('X-Refresh-Token')
    if header_token:
        print(f"[AUTH] 📱 refresh_token из Header X-Refresh-Token")
        return header_token
    
    # Затем Cookie (для веба)
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        print(f"[AUTH] 🌐 refresh_token из Cookie")
        return cookie_token
    
    # Также проверяем тело запроса (для Telegram refresh)
    if request.is_json:
        body_token = request.json.get('refresh_token')
        if body_token:
            print(f"[AUTH] 📦 refresh_token из тела запроса")
            return body_token
    
    return None


# ============================================
# Декоратор авторизации (НОВЫЙ)
# ============================================

def require_auth_jwt(user_type=None):
    """
    Декоратор для проверки JWT access token
    
    Использование:
        @require_auth_jwt('donor')
        def protected_route():
            user_id = g.user_id
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Получаем токен из заголовка
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Требуется авторизация'}), 401
            
            token = auth_header.replace('Bearer ', '')
            
            # Верифицируем JWT
            payload = verify_access_token(token)
            
            if not payload:
                return jsonify({
                    'error': 'Токен истёк или недействителен',
                    'code': 'TOKEN_EXPIRED'
                }), 401
            
            # Проверяем тип пользователя
            if user_type and payload.get('type') != user_type:
                return jsonify({'error': f'Доступ запрещён. Требуется роль: {user_type}'}), 403
            
            # Сохраняем данные в g
            g.user_id = int(payload['sub'])
            g.user_type = payload['type']
            g.token_payload = payload
            
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================
# Утилиты
# ============================================

def get_client_info():
    """
    Получить информацию о клиенте из запроса
    """
    return {
        'device_info': request.headers.get('User-Agent', 'Unknown')[:255],
        'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
        'platform': 'web'  # Можно определять по User-Agent
    }


def cleanup_expired_sessions(query_db_func):
    """
    Очистка истекших сессий (запускать периодически)
    """
    query_db_func(
        "DELETE FROM user_sessions WHERE expires_at < NOW() OR is_active = FALSE",
        commit=True
    )
