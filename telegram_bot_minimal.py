#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Твой Донор - Telegram бот (минимальная версия)
Только для верификации и уведомлений
"""

import os
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загрузка переменных окружения
load_dotenv(dotenv_path='website/backend/.env')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация БД
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'your_donor'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
    'port': os.getenv('DB_PORT', 5432)
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# ============================================
# Работа с базой данных
# ============================================

def get_db_connection():
    """Создать подключение к БД"""
    return psycopg2.connect(**DB_CONFIG)

def query_db(query, args=(), one=False, commit=False):
    """Выполнить SQL запрос"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, args)
        
        if commit:
            conn.commit()
            return None
        
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
        if conn and commit:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

# ============================================
# Команды бота
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    user = update.effective_user
    telegram_id = user.id
    
    logger.info(f"Пользователь {telegram_id} ({user.first_name}) запустил бота")
    
    # Проверяем, привязан ли пользователь
    donor = query_db(
        "SELECT id, full_name FROM users WHERE telegram_id = %s AND is_active = TRUE",
        (telegram_id,), one=True
    )
    
    if donor:
        await update.message.reply_text(
            f"👋 Привет, {donor['full_name']}!\n\n"
            f"Ты уже привязан к системе \"Твой Донор\".\n"
            f"Я буду присылать тебе срочные уведомления о запросах крови.\n\n"
            f"📌 Управление профилем: http://localhost:8000/pages/donor-dashboard.html"
        )
    else:
        await update.message.reply_text(
            "👋 Привет! Я бот системы \"Твой Донор\".\n\n"
            "Для привязки аккаунта:\n"
            "1️⃣ Зарегистрируйся на сайте: http://localhost:8000\n"
            "2️⃣ В профиле нажми \"Получить код для привязки\"\n"
            "3️⃣ Отправь мне команду: /link КОД\n\n"
            "После привязки я буду присылать тебе срочные уведомления о запросах крови."
        )

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /link КОД - привязка аккаунта"""
    telegram_id = update.effective_user.id
    telegram_username = update.effective_user.username or ''
    
    # Проверяем, уже привязан ли
    existing = query_db(
        "SELECT id FROM users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    if existing:
        await update.message.reply_text("❌ Ты уже привязан к аккаунту!")
        return
    
    # Получаем код из аргументов
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Используй команду так: /link КОД\n\n"
            "Получить код можно в профиле на сайте."
        )
        return
    
    code = context.args[0].strip()
    
    # Проверяем код в БД
    link_data = query_db(
        """SELECT user_id, expires_at 
           FROM telegram_link_codes 
           WHERE code = %s AND used = FALSE""",
        (code,), one=True
    )
    
    if not link_data:
        await update.message.reply_text("❌ Неверный код или он уже использован.")
        return
    
    # Проверяем срок действия
    if datetime.now() > link_data['expires_at']:
        await update.message.reply_text("❌ Код истёк. Получи новый код на сайте.")
        return
    
    user_id = link_data['user_id']
    
    # Обновляем пользователя
    try:
        query_db(
            """UPDATE users 
               SET telegram_id = %s, telegram_username = %s 
               WHERE id = %s""",
            (telegram_id, telegram_username, user_id), commit=True
        )
        
        # Помечаем код как использованный
        query_db(
            "UPDATE telegram_link_codes SET used = TRUE WHERE code = %s",
            (code,), commit=True
        )
        
        # Получаем имя пользователя
        user = query_db("SELECT full_name FROM users WHERE id = %s", (user_id,), one=True)
        
        await update.message.reply_text(
            f"✅ Отлично, {user['full_name']}!\n\n"
            f"Твой Telegram привязан к аккаунту.\n"
            f"Теперь ты будешь получать срочные уведомления о запросах крови.\n\n"
            f"📌 Управление профилем: http://localhost:8000/pages/donor-dashboard.html"
        )
        
        logger.info(f"Пользователь {user_id} привязал Telegram {telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка привязки: {e}")
        await update.message.reply_text("❌ Ошибка привязки. Попробуй позже.")

# ============================================
# Функция уведомлений (вызывается из app.py)
# ============================================

def send_notification(telegram_id, message):
    """
    Отправить уведомление пользователю
    Эта функция вызывается из Flask API
    """
    # TODO: Реализовать через bot.send_message
    logger.info(f"Уведомление для {telegram_id}: {message}")
    return True

def send_urgent_blood_request(blood_type, medical_center_name, address=None):
    """
    Отправить срочное уведомление о запросе крови всем донорам с нужной группой
    Возвращает количество отправленных уведомлений
    """
    try:
        # Получаем всех доноров с нужной группой крови и привязанным Telegram
        donors = query_db(
            """SELECT telegram_id, full_name 
               FROM users 
               WHERE blood_type = %s 
               AND telegram_id IS NOT NULL 
               AND notify_urgent = TRUE
               AND is_active = TRUE""",
            (blood_type,)
        )
        
        if not donors:
            logger.info(f"Нет доноров с группой {blood_type} для уведомления")
            return 0
        
        message = (
            f"🔴 СРОЧНЫЙ ЗАПРОС КРОВИ!\n\n"
            f"Группа крови: {blood_type}\n"
            f"Медцентр: {medical_center_name}\n"
        )
        
        if address:
            message += f"Адрес: {address}\n"
        
        message += f"\n🌐 Подробнее на сайте: http://localhost:8000/pages/donor-dashboard.html"
        
        # TODO: Отправить сообщения через bot
        # Пока просто логируем
        for donor in donors:
            logger.info(f"Уведомление донору {donor['telegram_id']}: {message}")
        
        return len(donors)
        
    except Exception as e:
        logger.error(f"Ошибка отправки срочных уведомлений: {e}")
        return 0

# ============================================
# Запуск бота
# ============================================

def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return
    
    logger.info("🚀 Запуск бота...")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link))
    
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info("Доступные команды:")
    logger.info("  /start - Приветствие")
    logger.info("  /link КОД - Привязка Telegram к аккаунту")
    
    # Запускаем polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
