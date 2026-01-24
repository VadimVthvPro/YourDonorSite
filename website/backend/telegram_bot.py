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
    'database': os.getenv('DB_NAME', 'your_donor'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
    'port': os.getenv('DB_PORT', 5432)
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:8000')

# Супер-админ для подтверждения медцентров
SUPER_ADMIN_TELEGRAM_ID = os.getenv('SUPER_ADMIN_TELEGRAM_ID', '')
SUPER_ADMIN_USERNAME = os.getenv('SUPER_ADMIN_TELEGRAM_USERNAME', 'vadimvthv')
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret')
API_URL = os.getenv('APP_URL', 'http://localhost:5001')

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
    
    is_super_admin = False
    admin_message = ""
    
    # ============================================
    # Автоматическая регистрация супер-админа
    # ============================================
    if telegram_username and telegram_username.lower() == SUPER_ADMIN_USERNAME.lower():
        is_super_admin = True
        # Сохраняем или обновляем telegram_id админа
        try:
            existing_admin = query_db(
                "SELECT id FROM admin_users WHERE telegram_username = %s",
                (telegram_username.lower(),), one=True
            )
            
            if existing_admin:
                query_db(
                    "UPDATE admin_users SET telegram_id = %s WHERE telegram_username = %s",
                    (telegram_id, telegram_username.lower()), commit=True
                )
                logger.info(f"[ADMIN] Супер-админ @{telegram_username} обновил telegram_id: {telegram_id}")
            else:
                query_db(
                    """INSERT INTO admin_users (telegram_id, telegram_username, role) 
                       VALUES (%s, %s, 'super_admin')
                       ON CONFLICT (telegram_id) DO UPDATE SET telegram_username = %s""",
                    (telegram_id, telegram_username.lower(), telegram_username.lower()), commit=True
                )
                logger.info(f"[ADMIN] Супер-админ @{telegram_username} (ID: {telegram_id}) зарегистрирован в системе")
            
            # Проверяем ожидающие заявки медцентров
            pending_medcenters = query_db(
                "SELECT id, name, email FROM medical_centers WHERE approval_status = 'pending' ORDER BY created_at DESC LIMIT 5"
            )
            
            if pending_medcenters:
                admin_message = f"\n\n🔔 <b>ОЖИДАЮЩИЕ ЗАЯВКИ:</b> {len(pending_medcenters)}\n"
                for mc in pending_medcenters:
                    admin_message += f"• #{mc['id']} {mc['name']}\n"
                admin_message += "\nИспользуйте /pending для управления заявками."
            else:
                admin_message = "\n\n✅ Нет ожидающих заявок медцентров."
                
        except Exception as e:
            logger.error(f"[ADMIN] Ошибка регистрации админа: {e}")
    
    # Проверяем deep link параметр (код из ссылки)
    if context.args and len(context.args) > 0:
        code = context.args[0].strip()
        if code.isdigit() and len(code) == 6:
            # Автоматически проверяем код
            await verify_code(update, context, code)
            return
    
    # Проверяем, привязан ли уже аккаунт
    donor = query_db(
        "SELECT id, full_name, blood_type FROM users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    # Создаём inline-кнопки
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🌐 Запустить платформу",
            web_app=WebAppInfo(url=WEBSITE_URL)
        )],
        [InlineKeyboardButton(
            "❓ Помощь",
            callback_data="help"
        )]
    ])
    
    if donor:
        admin_badge = ""
        if is_super_admin:
            admin_badge = "👑 <b>СУПЕР-АДМИН</b>\n\n"
        
        await update.message.reply_html(
            f"{admin_badge}"
            f"👋 Привет, <b>{donor['full_name']}</b>!\n\n"
            f"Твой аккаунт уже привязан к Твой Донор.\n"
            f"Группа крови: <b>{donor['blood_type'] or 'не указана'}</b>\n\n"
            f"Ты будешь получать уведомления о срочных запросах на донацию."
            f"{admin_message}\n\n"
            f"Нажми кнопку ниже, чтобы запустить платформу!",
            reply_markup=keyboard
        )
    else:
        welcome_text = (
            f"🩸 <b>Добро пожаловать в «Твой Донор»!</b>\n\n"
            f"Я помогу вам стать донором крови и спасать жизни.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 <b>ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ</b>\n\n"
            f"Если вы регистрируетесь на платформе и получили 6-значный код — просто отправьте его мне.\n\n"
            f"Пример: <code>123456</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 <b>ПОЛЬЗОВАТЬСЯ ПЛАТФОРМОЙ</b>\n\n"
            f"Вы можете использовать наш сервис прямо здесь, не выходя из Telegram!\n\n"
            f"Нажмите кнопку «Запустить платформу» ниже.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 <b>ЧТО Я УМЕЮ:</b>\n\n"
            f"• Подтверждать регистрацию\n"
            f"• Уведомлять о срочных запросах крови\n"
            f"• Напоминать о донациях\n"
            f"• Присылать сообщения от медцентров"
        )
        
        await update.message.reply_html(
            welcome_text,
            reply_markup=keyboard
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    await update.message.reply_html(
        "<b>🩸 Твой Донор - Справка</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/link КОД - Привязать аккаунт по коду\n"
        "/status - Проверить статус привязки\n"
        "/myid - Получить Telegram ID\n"
        "/unsubscribe - Отписаться от уведомлений\n"
        "/help - Эта справка\n\n"
        "<b>Как это работает:</b>\n"
        "1. Зарегистрируйтесь на платформе Твой Донор\n"
        "2. В личном кабинете получите код привязки\n"
        "3. Отправьте команду /link КОД\n"
        "4. Получайте уведомления о срочных запросах\n\n"
        f"🌐 Платформа: {WEBSITE_URL}"
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
            f"Зарегистрируйтесь на платформе и укажите свой Telegram ID:\n"
            f"<code>{telegram_id}</code>\n\n"
            f"🌐 {WEBSITE_URL}"
        )

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myid - получить свой Telegram ID"""
    telegram_id = update.effective_user.id
    await update.message.reply_html(
        f"<b>Ваш Telegram ID:</b>\n\n"
        f"<code>{telegram_id}</code>\n\n"
        f"Используйте этот ID для привязки аккаунта на платформе Твой Донор."
    )

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unsubscribe - отписаться от уведомлений"""
    telegram_id = update.effective_user.id
    
    result = query_db(
        "UPDATE users SET notify_urgent = FALSE, notify_low = FALSE WHERE telegram_id = %s",
        (telegram_id,), commit=True
    )
    
    if result > 0:
        await update.message.reply_html(
            "✅ <b>Уведомления отключены</b>\n\n"
            "Вы больше не будете получать уведомления о запросах на донацию.\n\n"
            f"Чтобы включить их снова, измените настройки в профиле на платформе:\n"
            f"🌐 {WEBSITE_URL}"
        )
    else:
        await update.message.reply_html(
            "❌ <b>Аккаунт не найден</b>\n\n"
            "Ваш Telegram не привязан к аккаунту Твой Донор."
        )

async def link_by_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привязка аккаунта по 6-значному коду"""
    telegram_id = update.effective_user.id
    telegram_username = update.effective_user.username
    
    # Проверяем, уже привязан ли
    existing = query_db(
        "SELECT id, full_name FROM users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    if existing:
        await update.message.reply_html(
            f"✅ Ваш аккаунт уже привязан: <b>{existing['full_name']}</b>\n\n"
            "Если хотите привязать другой аккаунт, сначала отвяжите текущий на платформе."
        )
        return
    
    # Проверяем формат кода
    if not context.args or len(context.args) == 0:
        await update.message.reply_html(
            "❌ <b>Неверный формат</b>\n\n"
            "Использование: <code>/link КОД</code>\n\n"
            "Где КОД - 6-значный код из личного кабинета на платформе.\n\n"
            "<b>Как получить код:</b>\n"
            "1. Войдите на сайт в личный кабинет донора\n"
            "2. Откройте раздел \"Настройки\" → \"Telegram\"\n"
            "3. Нажмите \"Получить код привязки\"\n"
            "4. Введите код командой /link КОД"
        )
        return
    
    code = context.args[0].strip()
    
    if not code.isdigit() or len(code) != 6:
        await update.message.reply_html(
            "❌ Код должен содержать 6 цифр.\n"
            "Пример: <code>/link 123456</code>"
        )
        return
    
    # Ищем код в БД
    link_data = query_db(
        """SELECT tlc.user_id, u.full_name, u.blood_type 
           FROM telegram_link_codes tlc
           JOIN users u ON tlc.user_id = u.id
           WHERE tlc.code = %s AND tlc.expires_at > NOW() AND tlc.used_at IS NULL""",
        (code,), one=True
    )
    
    if not link_data:
        await update.message.reply_html(
            "❌ <b>Код не найден или истёк</b>\n\n"
            "Возможные причины:\n"
            "• Код введён неверно\n"
            "• Код уже использован\n"
            "• Прошло более 10 минут с момента генерации\n\n"
            "Получите новый код на платформе в разделе \"Настройки\"."
        )
        return
    
    # Привязываем
    try:
        query_db(
            "UPDATE users SET telegram_id = %s, telegram_username = %s WHERE id = %s",
            (telegram_id, telegram_username, link_data['user_id']), commit=True
        )
        
        query_db(
            "UPDATE telegram_link_codes SET used_at = NOW() WHERE user_id = %s",
            (link_data['user_id'],), commit=True
        )
        
        await update.message.reply_html(
            f"✅ <b>Аккаунт успешно привязан!</b>\n\n"
            f"👤 <b>Имя:</b> {link_data['full_name']}\n"
            f"🩸 <b>Группа крови:</b> {link_data['blood_type']}\n\n"
            f"Теперь вы будете получать уведомления о срочных запросах на донацию крови.\n\n"
            f"🌐 <a href='{WEBSITE_URL}'>Перейти на платформу</a>"
        )
        
        logger.info(f"Telegram привязан: user_id={link_data['user_id']}, telegram_id={telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка привязки Telegram: {e}")
        await update.message.reply_html(
            "❌ Ошибка при привязке аккаунта. Попробуйте ещё раз или обратитесь в поддержку."
        )

# ============================================
# Callback обработчики
# ============================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    if query.data == "help":
        help_text = (
            f"❓ <b>ПОМОЩЬ</b>\n\n"
            f"<b>Как подтвердить регистрацию:</b>\n"
            f"1. Зарегистрируйтесь на платформе tvoydonor.by\n"
            f"2. Скопируйте 6-значный код\n"
            f"3. Отправьте его мне\n\n"
            f"<b>Как пользоваться платформой:</b>\n"
            f"Нажмите кнопку «Запустить платформу» — сервис откроется прямо в Telegram.\n\n"
            f"<b>Какие уведомления я присылаю:</b>\n"
            f"• 🚨 Срочные запросы крови вашей группы\n"
            f"• 📅 Напоминания о записи на донацию\n"
            f"• ✅ Подтверждения от медцентров\n"
            f"• 💬 Сообщения от медцентров\n\n"
            f"<b>Контакты:</b>\n"
            f"Платформа: {WEBSITE_URL}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🌐 Запустить платформу",
                web_app=WebAppInfo(url=WEBSITE_URL)
            )],
            [InlineKeyboardButton(
                "◀️ Назад",
                callback_data="back_to_start"
            )]
        ])
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif query.data == "back_to_start":
        # Возврат к стартовому сообщению
        user = update.effective_user
        telegram_id = user.id
        
        donor = query_db(
            "SELECT id, full_name, blood_type FROM users WHERE telegram_id = %s",
            (telegram_id,), one=True
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🌐 Запустить платформу",
                web_app=WebAppInfo(url=WEBSITE_URL)
            )],
            [InlineKeyboardButton(
                "❓ Помощь",
                callback_data="help"
            )]
        ])
        
        if donor:
            await query.edit_message_text(
                f"👋 Привет, <b>{donor['full_name']}</b>!\n\n"
                f"Твой аккаунт уже привязан к Твой Донор.\n"
                f"Группа крови: <b>{donor['blood_type'] or 'не указана'}</b>\n\n"
                f"Ты будешь получать уведомления о срочных запросах на донацию.\n\n"
                f"Нажми кнопку ниже, чтобы запустить платформу прямо в Telegram!",
                parse_mode='HTML',
                reply_markup=keyboard
            )
        else:
            welcome_text = (
                f"🩸 <b>Добро пожаловать в «Твой Донор»!</b>\n\n"
                f"Я помогу вам стать донором крови и спасать жизни.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📋 <b>ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ</b>\n\n"
                f"Если вы регистрируетесь на платформе и получили 6-значный код — просто отправьте его мне.\n\n"
                f"Пример: <code>123456</code>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🌐 <b>ПОЛЬЗОВАТЬСЯ ПЛАТФОРМОЙ</b>\n\n"
                f"Вы можете использовать наш сервис прямо здесь, не выходя из Telegram!\n\n"
                f"Нажмите кнопку «Запустить платформу» ниже.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 <b>ЧТО Я УМЕЮ:</b>\n\n"
                f"• Подтверждать регистрацию\n"
                f"• Уведомлять о срочных запросах крови\n"
                f"• Напоминать о донациях\n"
                f"• Присылать сообщения от медцентров"
            )
            
            await query.edit_message_text(
                welcome_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
    
    elif query.data == "link_account":
        telegram_id = update.effective_user.id
        await query.edit_message_text(
            f"🔗 <b>Привязка аккаунта</b>\n\n"
            f"1. Войдите в свой аккаунт на платформе Твой Донор\n"
            f"2. Перейдите в Настройки профиля\n"
            f"3. В поле 'Telegram ID' введите:\n\n"
            f"<code>{telegram_id}</code>\n\n"
            f"4. Сохраните изменения\n\n"
            f"После этого вы будете получать уведомления о срочных запросах.\n\n"
            f"🌐 {WEBSITE_URL}",
            parse_mode='HTML'
        )
    
    # ============================================
    # Обработка подтверждения/отклонения медцентров
    # ============================================
    elif query.data.startswith("approve_mc_"):
        await handle_medcenter_approval(query, approve=True)
    
    elif query.data.startswith("reject_mc_"):
        await handle_medcenter_approval(query, approve=False)


async def handle_medcenter_approval(query, approve: bool):
    """Обработка подтверждения или отклонения медцентра"""
    import requests
    
    user_id = query.from_user.id
    user_username = query.from_user.username
    
    # Проверяем, что это супер-админ по username
    is_admin = False
    
    # Проверяем по username
    if user_username and user_username.lower() == SUPER_ADMIN_USERNAME.lower():
        is_admin = True
    
    # Или проверяем в базе данных
    if not is_admin:
        admin_in_db = query_db(
            "SELECT id FROM admin_users WHERE telegram_id = %s AND is_active = TRUE",
            (user_id,), one=True
        )
        if admin_in_db:
            is_admin = True
    
    if not is_admin:
        await query.edit_message_text(
            "❌ <b>Доступ запрещён</b>\n\n"
            "Только супер-администратор может подтверждать медцентры.",
            parse_mode='HTML'
        )
        return
    
    # Извлекаем ID медцентра
    try:
        mc_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка: неверный ID медцентра", parse_mode='HTML')
        return
    
    action = "approve" if approve else "reject"
    action_text = "подтверждён" if approve else "отклонён"
    emoji = "✅" if approve else "❌"
    
    # Вызываем API для подтверждения/отклонения
    try:
        api_url = f"{API_URL}/api/admin/medcenter/{mc_id}/{action}"
        response = requests.post(
            api_url,
            json={"admin_secret": SECRET_KEY},
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            mc_name = result.get('medical_center', {}).get('name', f'#{mc_id}')
            mc_email = result.get('medical_center', {}).get('email', '')
            
            # Обновляем сообщение
            await query.edit_message_text(
                f"{emoji} <b>Медцентр {action_text}!</b>\n\n"
                f"<b>Название:</b> {mc_name}\n"
                f"<b>Email:</b> {mc_email}\n"
                f"<b>ID:</b> #{mc_id}\n\n"
                f"{'Медцентр теперь может войти в систему.' if approve else 'Заявка отклонена. Медцентр не сможет войти в систему.'}",
                parse_mode='HTML'
            )
            
            logger.info(f"[ADMIN] Медцентр #{mc_id} {action_text} пользователем {user_id}")
            
            # Если подтверждён - можно отправить уведомление медцентру на email (опционально)
            
        else:
            error_msg = response.json().get('error', 'Неизвестная ошибка')
            await query.edit_message_text(
                f"❌ <b>Ошибка</b>\n\n{error_msg}",
                parse_mode='HTML'
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[ADMIN] Ошибка API: {e}")
        await query.edit_message_text(
            f"❌ <b>Ошибка соединения с сервером</b>\n\n"
            f"Попробуйте позже или проверьте работу API.\n\n"
            f"Техническая информация: {str(e)[:100]}",
            parse_mode='HTML'
        )

# ============================================
# Обработка обычных сообщений
# ============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная обработка текстовых сообщений"""
    text = update.message.text.strip()
    telegram_id = update.effective_user.id
    
    # Проверяем, что текст содержит ТОЛЬКО цифры
    if text.isdigit():
        # Проверяем длину
        if len(text) == 6:
            # Это 6-значный код - обрабатываем как попытку регистрации
            await verify_code(update, context, text)
        else:
            # Неправильная длина
            await update.message.reply_html(
                f"⚠️ <b>Код должен содержать ровно 6 цифр</b>\n\n"
                f"Вы ввели: <b>{len(text)}</b> {'цифру' if len(text) == 1 else 'цифры' if len(text) < 5 else 'цифр'}\n"
                f"Проверьте код и попробуйте ещё раз.\n\n"
                f"Получить код можно на платформе в личном кабинете."
            )
    else:
        # Это обычный текст - автоответ
        await update.message.reply_html(
            "🤖 <b>Функция автоответа в разработке</b>\n\n"
            "Пока я могу только:\n"
            "• Подтвердить вашу регистрацию (введите 6-значный код с платформы)\n"
            "• Отправлять уведомления о запросах крови\n\n"
            "<b>Доступные команды:</b>\n"
            "/start - Начать работу\n"
            "/help - Справка\n"
            "/status - Статус аккаунта\n\n"
            f"По всем вопросам обращайтесь на сайт:\n"
            f"🌐 {WEBSITE_URL}"
        )

async def verify_code(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """Проверка и привязка по 6-значному коду"""
    telegram_id = update.effective_user.id
    telegram_username = update.effective_user.username
    
    # Проверяем, уже привязан ли
    existing = query_db(
        "SELECT id, full_name FROM users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    if existing:
        await update.message.reply_html(
            f"ℹ️ <b>Ваш аккаунт уже подтверждён</b>\n\n"
            f"Вы привязаны к аккаунту: <b>{existing['full_name']}</b>\n\n"
            f"Если это не вы — обратитесь в поддержку на платформе:\n"
            f"🌐 {WEBSITE_URL}"
        )
        return
    
    # Ищем код в БД
    link_data = query_db(
        """SELECT tlc.user_id, u.full_name, u.blood_type 
           FROM telegram_link_codes tlc
           JOIN users u ON tlc.user_id = u.id
           WHERE tlc.code = %s AND tlc.expires_at > NOW() AND tlc.used_at IS NULL""",
        (code,), one=True
    )
    
    if not link_data:
        await update.message.reply_html(
            "❌ <b>Код неверный или истёк</b>\n\n"
            "Проверьте код на платформе и попробуйте ещё раз.\n"
            "Если код истёк — запросите новый на странице регистрации.\n\n"
            "💡 <b>Совет:</b> Код действует 10 минут с момента генерации."
        )
        return
    
    # Привязываем аккаунт
    try:
        query_db(
            "UPDATE users SET telegram_id = %s, telegram_username = %s WHERE id = %s",
            (telegram_id, telegram_username, link_data['user_id']), commit=True
        )
        
        query_db(
            "UPDATE telegram_link_codes SET used_at = NOW() WHERE user_id = %s",
            (link_data['user_id'],), commit=True
        )
        
        await update.message.reply_html(
            f"✅ <b>Регистрация подтверждена!</b>\n\n"
            f"Ваш аккаунт успешно привязан.\n\n"
            f"👤 <b>Имя:</b> {link_data['full_name']}\n"
            f"🩸 <b>Группа крови:</b> {link_data['blood_type']}\n\n"
            f"Теперь вы будете получать уведомления о:\n"
            f"• Срочных запросах крови вашей группы\n"
            f"• Статусе ваших откликов\n"
            f"• Напоминаниях о донациях\n\n"
            f"Спасибо, что вы с нами! ❤️\n\n"
            f"🌐 <a href='{WEBSITE_URL}/pages/donor-dashboard.html'>Перейти в личный кабинет</a>"
        )
        
        logger.info(f"Telegram привязан (через прямой ввод кода): user_id={link_data['user_id']}, telegram_id={telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка привязки Telegram: {e}")
        await update.message.reply_html(
            "❌ Ошибка при привязке аккаунта. Попробуйте ещё раз или обратитесь в поддержку."
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

def send_urgent_blood_request(blood_type: str, medical_center_name: str, address: str = None, medical_center_id: int = None):
    """
    Отправить срочный запрос донорам с подходящей группой крови ИЗ ТОГО ЖЕ РАЙОНА
    """
    # Получить район медцентра для фильтрации
    district_id = None
    if medical_center_id:
        mc_info = query_db(
            "SELECT district_id FROM medical_centers WHERE id = %s",
            (medical_center_id,), one=True
        )
        if mc_info:
            district_id = mc_info['district_id']
            logger.info(f"[NOTIFICATION] Медцентр ID={medical_center_id}, district_id={district_id}")
    
    # Находим доноров с подходящей группой крови ИЗ ТОГО ЖЕ РАЙОНА
    if district_id:
        donors = query_db(
            """SELECT telegram_id, full_name, district_id FROM users
               WHERE blood_type = %s 
               AND district_id = %s
               AND telegram_id IS NOT NULL
               AND is_active = TRUE
               AND notify_urgent = TRUE""",
            (blood_type, district_id)
        )
        logger.info(f"[NOTIFICATION] Фильтр по району {district_id}: найдено {len(donors) if donors else 0} доноров")
    else:
        # Если район не указан, отправляем всем (старое поведение для совместимости)
        donors = query_db(
            """SELECT telegram_id, full_name FROM users
               WHERE blood_type = %s 
               AND telegram_id IS NOT NULL
               AND is_active = TRUE
               AND notify_urgent = TRUE""",
            (blood_type,)
        )
        logger.warning(f"[NOTIFICATION] Медцентр без района! Отправка всем донорам группы {blood_type}")
    
    if not donors:
        logger.info(f"[NOTIFICATION] Нет доноров для уведомления (группа {blood_type}, район {district_id})")
        return 0
    
    # Логирование списка доноров
    for donor in donors:
        district_info = f", район={donor.get('district_id')}" if 'district_id' in donor else ""
        logger.info(f"[NOTIFICATION]   → {donor.get('full_name', 'N/A')}{district_info}")
    
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
    
    logger.info(f"[NOTIFICATION] ✅ Отправлено {sent_count}/{len(donors)} уведомлений для группы {blood_type}, район {district_id}")
    return sent_count

def send_blood_status_notification(blood_type: str, status: str, medical_center_name: str, medical_center_id: int = None):
    """
    Отправить уведомление об изменении статуса группы крови (светофор)
    status: 'normal', 'needed', 'urgent', 'critical'
    """
    # Получить район медцентра для фильтрации
    district_id = None
    if medical_center_id:
        mc_info = query_db(
            "SELECT district_id FROM medical_centers WHERE id = %s",
            (medical_center_id,), one=True
        )
        if mc_info:
            district_id = mc_info['district_id']
            logger.info(f"[TRAFFIC LIGHT] Медцентр ID={medical_center_id}, district_id={district_id}")
    
    # Находим доноров с подходящей группой крови ИЗ ТОГО ЖЕ РАЙОНА
    if district_id:
        donors = query_db(
            """SELECT telegram_id, full_name, district_id FROM users
               WHERE blood_type = %s 
               AND district_id = %s
               AND telegram_id IS NOT NULL
               AND is_active = TRUE""",
            (blood_type, district_id)
        )
        logger.info(f"[TRAFFIC LIGHT] Фильтр по району {district_id}: найдено {len(donors) if donors else 0} доноров")
    else:
        # Если район не указан, отправляем всем
        donors = query_db(
            """SELECT telegram_id, full_name FROM users
               WHERE blood_type = %s 
               AND telegram_id IS NOT NULL
               AND is_active = TRUE""",
            (blood_type,)
        )
        logger.warning(f"[TRAFFIC LIGHT] Медцентр без района! Отправка всем донорам группы {blood_type}")
    
    if not donors:
        logger.info(f"[TRAFFIC LIGHT] Нет доноров для уведомления (группа {blood_type}, район {district_id})")
        return 0
    
    # Формируем сообщение в зависимости от статуса
    if status == 'critical':
        emoji = "🔴🚨"
        title = "КРИТИЧЕСКИ НУЖНА КРОВЬ!!!"
        desc = "⚡ МАКСИМАЛЬНАЯ СРОЧНОСТЬ! Жизнь человека может зависеть от вашей помощи. Пожалуйста, откликнитесь НЕМЕДЛЕННО!"
    elif status == 'urgent':
        emoji = "🚨"
        title = "СРОЧНО НУЖНА КРОВЬ!"
        desc = "Это срочный запрос! Ваша помощь нужна как можно скорее."
    elif status == 'needed':
        emoji = "⚠️"
        title = "Нужно пополнить запасы крови"
        desc = "Запасы вашей группы крови снижаются. Пожалуйста, запланируйте донацию в ближайшее время."
    else:
        return 0  # Для статуса 'normal' не отправляем уведомления
    
    message = (
        f"{emoji} <b>{title}</b>\n\n"
        f"🩸 <b>Группа крови:</b> {blood_type}\n"
        f"🏥 <b>Медцентр:</b> {medical_center_name}\n\n"
        f"{desc}\n\n"
        f"🌐 <a href='{WEBSITE_URL}'>Перейти на платформу</a>"
    )
    
    # Отправляем уведомления
    sent_count = 0
    for donor in donors:
        if send_notification(donor['telegram_id'], message):
            sent_count += 1
    
    logger.info(f"Отправлено {sent_count}/{len(donors)} уведомлений о статусе {status} для группы {blood_type}")
    return sent_count

def send_message_notification(user_id: int, medcenter_name: str, subject: str, message_text: str):
    """
    Отправить уведомление о новом сообщении от медцентра
    """
    # Получаем telegram_id донора
    donor = query_db(
        "SELECT telegram_id FROM users WHERE id = %s AND telegram_id IS NOT NULL",
        (user_id,), one=True
    )
    
    if not donor or not donor['telegram_id']:
        logger.info(f"У пользователя {user_id} нет привязанного Telegram")
        return False
    
    # Формируем сообщение
    message = (
        f"📩 <b>Новое сообщение от медцентра</b>\n\n"
        f"🏥 <b>От:</b> {medcenter_name}\n"
        f"📝 <b>Тема:</b> {subject}\n\n"
        f"<i>{message_text[:200]}</i>{'...' if len(message_text) > 200 else ''}\n\n"
        f"🌐 <a href='{WEBSITE_URL}/pages/donor-dashboard.html'>Прочитать полностью</a>"
    )
    
    success = send_notification(donor['telegram_id'], message)
    if success:
        logger.info(f"Уведомление о сообщении отправлено пользователю {user_id}")
    return success

def send_blood_request_notification(blood_type: str, urgency: str, medical_center_name: str, address: str = None, medical_center_id: int = None):
    """
    Отправить уведомление о запросе крови любой срочности
    urgency: 'normal', 'urgent', 'critical'
    ⚠️ ВАЖНО: Отправка только донорам ИЗ ТОГО ЖЕ РАЙОНА что и медцентр
    """
    # Получить район медцентра для фильтрации
    district_id = None
    district_name = "неизвестен"
    
    if medical_center_id:
        mc_info = query_db(
            """SELECT mc.district_id, d.name as district_name
               FROM medical_centers mc
               LEFT JOIN districts d ON mc.district_id = d.id
               WHERE mc.id = %s""",
            (medical_center_id,), one=True
        )
        if mc_info:
            district_id = mc_info['district_id']
            district_name = mc_info['district_name'] or "неизвестен"
            logger.info(f"[BLOOD REQUEST] Медцентр ID={medical_center_id}, район='{district_name}' (ID={district_id})")
    
    # Находим доноров с подходящей группой крови ИЗ ТОГО ЖЕ РАЙОНА
    if district_id:
        donors = query_db(
            """SELECT telegram_id, full_name, district_id FROM users
               WHERE blood_type = %s 
               AND district_id = %s
               AND telegram_id IS NOT NULL
               AND is_active = TRUE""",
            (blood_type, district_id)
        )
        logger.info(f"[BLOOD REQUEST] 🔍 Фильтр по району '{district_name}': найдено {len(donors) if donors else 0} доноров группы {blood_type}")
    else:
        # Если район не указан, отправляем всем (старое поведение для совместимости)
        donors = query_db(
            """SELECT telegram_id, full_name FROM users
               WHERE blood_type = %s 
               AND telegram_id IS NOT NULL
               AND is_active = TRUE""",
            (blood_type,)
        )
        logger.warning(f"[BLOOD REQUEST] ⚠️ Медцентр без района! Отправка всем донорам группы {blood_type}: {len(donors) if donors else 0} чел.")
    
    if not donors:
        logger.info(f"[BLOOD REQUEST] ℹ️ Нет доноров для уведомления (группа {blood_type}, район '{district_name}')")
        return 0
    
    # Логирование списка получателей
    logger.info(f"[BLOOD REQUEST] 📋 Список получателей:")
    for donor in donors[:10]:  # Показываем первых 10
        district_info = f", район ID={donor.get('district_id')}" if 'district_id' in donor else ""
        logger.info(f"[BLOOD REQUEST]   → {donor.get('full_name', 'N/A')}{district_info}")
    if len(donors) > 10:
        logger.info(f"[BLOOD REQUEST]   ... и ещё {len(donors) - 10} донор(ов)")
    
    # Формируем сообщение в зависимости от срочности
    if urgency == 'critical' or urgency == 'urgent':
        emoji = "🚨"
        title = "СРОЧНО! Нужна кровь!"
        desc = "Это срочный запрос! Ваша помощь нужна как можно скорее."
    else:
        emoji = "🩸"
        title = "Новый запрос на донацию"
        desc = "Медцентр запрашивает донацию крови. Вы можете записаться в удобное время."
    
    message = (
        f"{emoji} <b>{title}</b>\n\n"
        f"🩸 <b>Группа крови:</b> {blood_type}\n"
        f"🏥 <b>Медцентр:</b> {medical_center_name}\n"
    )
    
    if address:
        message += f"📍 <b>Адрес:</b> {address}\n"
    
    message += (
        f"\n{desc}\n\n"
        f"🌐 <a href='{WEBSITE_URL}/pages/donor-dashboard.html'>Откликнуться на запрос</a>"
    )
    
    # Отправляем уведомления
    sent_count = 0
    for donor in donors:
        if send_notification(donor['telegram_id'], message):
            sent_count += 1
    
    logger.info(f"[BLOOD REQUEST] ✅ Отправлено {sent_count}/{len(donors)} уведомлений ({urgency}) для группы {blood_type}, район '{district_name}'")
    return sent_count

# ============================================
# ============================================
# Команда для супер-админа - ожидающие заявки
# ============================================

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /pending - показать ожидающие заявки медцентров (только для админа)"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем что это админ
    admin = query_db(
        "SELECT id FROM admin_users WHERE telegram_id = %s",
        (telegram_id,), one=True
    )
    
    if not admin:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    # Получаем ожидающие заявки
    pending = query_db(
        """SELECT id, name, email, address, phone, district_id, created_at 
           FROM medical_centers 
           WHERE approval_status = 'pending' 
           ORDER BY created_at ASC"""
    )
    
    if not pending:
        await update.message.reply_text("✅ Нет ожидающих заявок медцентров.")
        return
    
    # Отправляем каждую заявку с кнопками
    await update.message.reply_text(f"📋 <b>Ожидающие заявки: {len(pending)}</b>", parse_mode='HTML')
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    for mc in pending:
        # Получаем название района
        district_name = "Не указан"
        if mc.get('district_id'):
            district = query_db(
                "SELECT name FROM districts WHERE id = %s",
                (mc['district_id'],), one=True
            )
            if district:
                district_name = district['name']
        
        text = (
            f"🏥 <b>{mc['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 Email: {mc['email']}\n"
            f"📍 Адрес: {mc.get('address', 'Не указан')}\n"
            f"📞 Телефон: {mc.get('phone', 'Не указан')}\n"
            f"🗺 Район: {district_name}\n"
            f"📅 Дата заявки: {mc['created_at'].strftime('%d.%m.%Y %H:%M') if mc.get('created_at') else 'Неизвестно'}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_mc_{mc['id']}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_mc_{mc['id']}")
            ]
        ])
        
        await update.message.reply_html(text, reply_markup=keyboard)

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
    application.add_handler(CommandHandler("link", link_by_code))
    application.add_handler(CommandHandler("pending", pending_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("✅ Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
