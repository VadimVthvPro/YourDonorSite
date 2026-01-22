#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Твой Донор - Telegram бот для уведомлений
Бот для привязки аккаунтов и получения срочных уведомлений о донациях
"""

import os
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Попробуем импортировать python-telegram-bot
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot не установлен. Установите: pip install python-telegram-bot")

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация БД
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'donorbay'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', 5432)
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:8000')

# ============================================
# Работа с базой данных
# ============================================

def get_db_connection():
    """Создать подключение к БД"""
    return psycopg2.connect(**DB_CONFIG)

def query_db(query, args=(), one=False, commit=False):
    """Выполнить SQL запрос"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, args)
        if commit:
            conn.commit()
            return cur.rowcount
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка БД: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

# ============================================
# Команды бота
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и привязка аккаунта"""
    user = update.effective_user
    telegram_id = user.id
    telegram_username = user.username
    
    # Проверяем, привязан ли уже аккаунт
    donor = query_db(
        "SELECT id, full_name, blood_type FROM users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    if donor:
        await update.message.reply_html(
            f"👋 Привет, <b>{donor['full_name']}</b>!\n\n"
            f"Твой аккаунт уже привязан к Твой Донор.\n"
            f"Группа крови: <b>{donor['blood_type'] or 'не указана'}</b>\n\n"
            f"Ты будешь получать уведомления о срочных запросах на донацию.\n\n"
            f"🌐 <a href='{WEBSITE_URL}'>Перейти на сайт</a>"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🌐 Зарегистрироваться на сайте", url=f"{WEBSITE_URL}/pages/auth.html")],
            [InlineKeyboardButton("🔗 Привязать существующий аккаунт", callback_data="link_account")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_html(
            f"👋 Привет, <b>{user.first_name}</b>!\n\n"
            f"Я бот платформы <b>Твой Донор</b> 🩸\n\n"
            f"Через меня ты будешь получать уведомления о срочных запросах на донацию крови.\n\n"
            f"Чтобы начать:\n"
            f"1️⃣ Зарегистрируйся на сайте\n"
            f"2️⃣ Укажи свой Telegram в профиле\n"
            f"3️⃣ Получай важные уведомления!\n\n"
            f"Твой Telegram ID: <code>{telegram_id}</code>\n"
            f"(Используй его для привязки на сайте)",
            reply_markup=reply_markup
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    await update.message.reply_html(
        "<b>🩸 Твой Донор - Справка</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/status - Проверить статус привязки\n"
        "/myid - Получить Telegram ID\n"
        "/unsubscribe - Отписаться от уведомлений\n"
        "/help - Эта справка\n\n"
        "<b>Как это работает:</b>\n"
        "1. Зарегистрируйтесь на сайте Твой Донор\n"
        "2. Укажите свой Telegram ID в профиле\n"
        "3. Получайте уведомления о срочных запросах\n\n"
        f"🌐 Сайт: {WEBSITE_URL}"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус привязки"""
    telegram_id = update.effective_user.id
    
    donor = query_db(
        """SELECT u.id, u.full_name, u.blood_type, u.last_donation_date,
                  u.total_donations, u.notify_urgent, u.notify_low,
                  mc.name as medical_center_name
           FROM users u
           LEFT JOIN medical_centers mc ON u.medical_center_id = mc.id
           WHERE u.telegram_id = %s""",
        (telegram_id,), one=True
    )
    
    if donor:
        # Форматируем дату последней донации
        last_donation = donor['last_donation_date']
        if last_donation:
            last_donation_str = last_donation.strftime('%d.%m.%Y')
        else:
            last_donation_str = 'не было'
        
        # Статус уведомлений
        notif_status = []
        if donor['notify_urgent']:
            notif_status.append('срочные')
        if donor['notify_low']:
            notif_status.append('низкий уровень')
        notif_str = ', '.join(notif_status) if notif_status else 'отключены'
        
        await update.message.reply_html(
            f"<b>📊 Статус аккаунта</b>\n\n"
            f"👤 <b>Имя:</b> {donor['full_name']}\n"
            f"🩸 <b>Группа крови:</b> {donor['blood_type'] or 'не указана'}\n"
            f"🏥 <b>Медцентр:</b> {donor['medical_center_name'] or 'не указан'}\n\n"
            f"📅 <b>Последняя донация:</b> {last_donation_str}\n"
            f"💉 <b>Всего донаций:</b> {donor['total_donations']}\n\n"
            f"🔔 <b>Уведомления:</b> {notif_str}\n\n"
            f"✅ Аккаунт привязан"
        )
    else:
        await update.message.reply_html(
            "❌ <b>Аккаунт не привязан</b>\n\n"
            f"Зарегистрируйтесь на сайте и укажите свой Telegram ID:\n"
            f"<code>{telegram_id}</code>\n\n"
            f"🌐 {WEBSITE_URL}"
        )

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myid - получить свой Telegram ID"""
    telegram_id = update.effective_user.id
    await update.message.reply_html(
        f"<b>Ваш Telegram ID:</b>\n\n"
        f"<code>{telegram_id}</code>\n\n"
        f"Используйте этот ID для привязки аккаунта на сайте Твой Донор."
    )

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unsubscribe - отписаться от уведомлений"""
    telegram_id = update.effective_user.id
    
    result = query_db(
        "UPDATE users SET notify_urgent = FALSE, notify_low = FALSE, notify_all = FALSE WHERE telegram_id = %s",
        (telegram_id,), commit=True
    )
    
    if result > 0:
        await update.message.reply_html(
            "✅ <b>Уведомления отключены</b>\n\n"
            "Вы больше не будете получать уведомления о запросах на донацию.\n\n"
            f"Чтобы включить их снова, измените настройки в профиле на сайте:\n"
            f"🌐 {WEBSITE_URL}"
        )
    else:
        await update.message.reply_html(
            "❌ <b>Аккаунт не найден</b>\n\n"
            "Ваш Telegram не привязан к аккаунту Твой Донор."
        )

# ============================================
# Callback обработчики
# ============================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "link_account":
        telegram_id = update.effective_user.id
        await query.edit_message_text(
            f"🔗 <b>Привязка аккаунта</b>\n\n"
            f"1. Войдите в свой аккаунт на сайте Твой Донор\n"
            f"2. Перейдите в Настройки профиля\n"
            f"3. В поле 'Telegram ID' введите:\n\n"
            f"<code>{telegram_id}</code>\n\n"
            f"4. Сохраните изменения\n\n"
            f"После этого вы будете получать уведомления о срочных запросах.\n\n"
            f"🌐 {WEBSITE_URL}",
            parse_mode='HTML'
        )

# ============================================
# Обработка обычных сообщений
# ============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    await update.message.reply_html(
        "Я бот для уведомлений Твой Донор 🩸\n\n"
        "Используй команду /help для получения справки."
    )

# ============================================
# Функция отправки уведомлений (для вызова из Flask)
# ============================================

async def send_notification_async(telegram_id: int, message: str, app: Application):
    """Асинхронная отправка уведомления"""
    try:
        await app.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='HTML'
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления {telegram_id}: {e}")
        return False

def send_notification(telegram_id: int, message: str):
    """Синхронная отправка уведомления (для использования из Flask)"""
    import requests
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': telegram_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            logger.info(f"Уведомление отправлено: {telegram_id}")
            return True
        else:
            logger.error(f"Ошибка Telegram API: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        return False

def send_urgent_blood_request(blood_type: str, medical_center_name: str, address: str = None):
    """
    Отправить срочный запрос всем донорам с подходящей группой крови
    """
    # Находим доноров с подходящей группой крови
    donors = query_db(
        """SELECT telegram_id FROM users
           WHERE blood_type = %s 
           AND telegram_id IS NOT NULL
           AND is_active = TRUE
           AND (notify_urgent = TRUE OR notify_all = TRUE)""",
        (blood_type,)
    )
    
    if not donors:
        logger.info(f"Нет доноров для уведомления (группа {blood_type})")
        return 0
    
    # Формируем сообщение
    message = (
        f"🚨 <b>СРОЧНО! Нужна кровь!</b>\n\n"
        f"🩸 <b>Группа крови:</b> {blood_type}\n"
        f"🏥 <b>Медцентр:</b> {medical_center_name}\n"
    )
    
    if address:
        message += f"📍 <b>Адрес:</b> {address}\n"
    
    message += (
        f"\n⏰ <b>Это срочный запрос!</b>\n\n"
        f"Если вы можете помочь, перейдите на сайт для подробностей.\n\n"
        f"🌐 {WEBSITE_URL}"
    )
    
    # Отправляем уведомления
    sent_count = 0
    for donor in donors:
        if send_notification(donor['telegram_id'], message):
            sent_count += 1
    
    logger.info(f"Отправлено {sent_count}/{len(donors)} уведомлений для группы {blood_type}")
    return sent_count

# ============================================
# Запуск бота
# ============================================

def main():
    """Запуск Telegram бота"""
    if not TELEGRAM_AVAILABLE:
        print("❌ Telegram бот не может быть запущен.")
        print("Установите: pip install python-telegram-bot")
        return
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        print("Укажите токен в файле .env")
        return
    
    print("=" * 50)
    print("🤖 Твой Донор Telegram Bot")
    print("=" * 50)
    
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("✅ Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
