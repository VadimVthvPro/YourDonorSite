"""
Дополнительные функции для работы с пользователями
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

class UserFunctions:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_db_connection(self):
        """Создает соединение с базой данных"""
        return psycopg2.connect(**self.db_config)

    async def update_donation_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление даты последней сдачи крови"""
        await update.callback_query.edit_message_text(
            "📅 Обновление даты последней сдачи крови\n\n"
            "Укажите дату последней сдачи крови в формате ДД.ММ.ГГГГ\n"
            "(или напишите 'никогда', если вы еще не сдавали кровь):"
        )
        return 'UPDATING_DONATION_DATE'

    async def handle_donation_date_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обновления даты сдачи крови"""
        last_donation = update.message.text
        
        if last_donation.lower() == 'никогда':
            last_donation_date = None
        else:
            try:
                last_donation_date = datetime.strptime(last_donation, '%d.%m.%Y').date()
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ\n"
                    "Попробуйте еще раз:"
                )
                return 'UPDATING_DONATION_DATE'
        
        # Обновляем дату в базе данных
        user = update.effective_user
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET last_donation_date = %s 
            WHERE telegram_id = %s
        """, (last_donation_date, user.id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        await update.message.reply_text(
            "✅ Дата последней сдачи крови обновлена!"
        )
        
        # Возвращаемся в меню пользователя
        from bot import BloodDonorBot
        bot_instance = BloodDonorBot()
        await bot_instance.show_user_menu(update, context)
        return 'USER_MENU'

    async def update_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление местоположения"""
        await update.callback_query.edit_message_text(
            "📍 Обновление местоположения\n\n"
            "Укажите ваше новое местоположение (город):"
        )
        return 'UPDATING_LOCATION'

    async def handle_location_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обновления местоположения"""
        location = update.message.text
        
        # Обновляем местоположение в базе данных
        user = update.effective_user
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET location = %s 
            WHERE telegram_id = %s
        """, (location, user.id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Местоположение обновлено на: {location}"
        )
        
        # Возвращаемся в меню пользователя
        from bot import BloodDonorBot
        bot_instance = BloodDonorBot()
        await bot_instance.show_user_menu(update, context)
        return 'USER_MENU'

    async def handle_update_donation_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Введите новую дату последней сдачи крови (ДД.ММ.ГГГГ):")
        return UPDATING_DONATION_DATE

    async def save_updated_donation_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            new_date = update.message.text.strip()
            if new_date.lower() == "никогда":
                last_donation_date = None
            else:
                last_donation_date = datetime.strptime(new_date, "%d.%m.%Y").date()

            user_id = update.effective_user.id
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_donation_date = %s 
                WHERE telegram_id = %s
            """, (last_donation_date, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text("✅ Дата сдачи крови успешно обновлена.")
            await self.show_user_menu(update, context)
            return USER_MENU
        except Exception as e:
            logger.error(f"Ошибка обновления даты сдачи: {e}")
            await update.message.reply_text("❌ Неверный формат или ошибка обновления. Попробуйте снова:")
            return UPDATING_DONATION_DATE

    async def handle_update_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Введите новый город/локацию:")
        return UPDATING_LOCATION

    async def save_updated_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            location = update.message.text.strip()
            user_id = update.effective_user.id
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET location = %s 
                WHERE telegram_id = %s
            """, (location, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text("✅ Местоположение успешно обновлено.")
            await self.show_user_menu(update, context)
            return USER_MENU
        except Exception as e:
            logger.error(f"Ошибка обновления местоположения: {e}")
            await update.message.reply_text("❌ Ошибка обновления. Попробуйте снова:")
            return UPDATING_LOCATION

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
            total_users = cursor.fetchone()['count']

            cursor.execute("""
                SELECT blood_type, COUNT(*) as count 
                FROM users 
                WHERE role = 'user' 
                GROUP BY blood_type 
                ORDER BY blood_type
            """)
            blood_stats = cursor.fetchall()

            cursor.execute("""
                SELECT location, COUNT(*) as count 
                FROM users 
                WHERE role = 'user' 
                GROUP BY location 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_locations = cursor.fetchall()

            text = f"📊 Общая статистика:\n\n"
            text += f"👥 Всего доноров: {total_users}\n\n"
            text += "🩸 По группам крови:\n"
            for row in blood_stats:
                text += f"• {row['blood_type']}: {row['count']}\n"
            text += "\n📍 Топ городов:\n"
            for row in top_locations:
                text += f"• {row['location']}: {row['count']}\n"

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка при выводе статистики: {e}")
            await update.callback_query.edit_message_text("❌ Не удалось загрузить статистику.")

    async def show_my_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает запросы врача"""
        user = update.effective_user
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM donation_requests 
            WHERE doctor_id = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user.id,))
        
        requests = cursor.fetchall()
        
        if requests:
            text = "📋 Ваши последние запросы:\n\n"
            for req in requests:
                text += f"🩸 {req['blood_type']} - {req['location']}\n"
                text += f"📅 {req['request_date'].strftime('%d.%m.%Y')}\n"
                text += f"🕐 {req['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        else:
            text = "📋 У вас пока нет запросов на сдачу крови."
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        
        cursor.close()
        conn.close()

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику по донорам"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем статистику по группам крови
        cursor.execute("""
            SELECT 
                blood_type,
                COUNT(*) as total_donors,
                COUNT(CASE WHEN last_donation_date IS NULL THEN 1 END) as new_donors,
                COUNT(CASE WHEN last_donation_date < CURRENT_DATE - INTERVAL '60 days' THEN 1 END) as available_donors
            FROM users 
            WHERE role = 'user' AND is_registered = TRUE AND blood_type IS NOT NULL
            GROUP BY blood_type
            ORDER BY blood_type
        """)
        
        stats = cursor.fetchall()
        
        if stats:
            text = "📊 Статистика по донорам:\n\n"
            for stat in stats:
                text += f"🩸 {stat['blood_type']}:\n"
                text += f"   Всего доноров: {stat['total_donors']}\n"
                text += f"   Новых доноров: {stat['new_donors']}\n"
                text += f"   Доступных: {stat['available_donors']}\n\n"
        else:
            text = "📊 Пока нет зарегистрированных доноров."
        
        # Общая статистика
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN role = 'doctor' THEN 1 END) as total_doctors,
                COUNT(CASE WHEN role = 'user' THEN 1 END) as total_donors
            FROM users 
            WHERE is_registered = TRUE
        """)
        
        general_stats = cursor.fetchone()
        if general_stats:
            text += f"👥 Общая статистика:\n"
            text += f"   Всего пользователей: {general_stats['total_users']}\n"
            text += f"   Врачей: {general_stats['total_doctors']}\n"
            text += f"   Доноров: {general_stats['total_donors']}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        
        cursor.close()
        conn.close()

    def get_available_donors(self, blood_type: str, location: str = None):
        """Получает список доступных доноров"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if location:
            cursor.execute("""
                SELECT telegram_id, first_name, last_name, location, last_donation_date
                FROM users 
                WHERE blood_type = %s AND role = 'user' AND is_registered = TRUE
                AND (location ILIKE %s OR location ILIKE %s)
                AND (last_donation_date IS NULL OR last_donation_date < CURRENT_DATE - INTERVAL '60 days')
            """, (blood_type, f"%{location}%", location))
        else:
            cursor.execute("""
                SELECT telegram_id, first_name, last_name, location, last_donation_date
                FROM users 
                WHERE blood_type = %s AND role = 'user' AND is_registered = TRUE
                AND (last_donation_date IS NULL OR last_donation_date < CURRENT_DATE - INTERVAL '60 days')
            """, (blood_type,))
        
        donors = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return donors

    def check_donation_eligibility(self, user_id: int) -> dict:
        """Проверяет возможность сдачи крови пользователем"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT last_donation_date, blood_type, location
            FROM users 
            WHERE telegram_id = %s AND role = 'user'
        """, (user_id,))
        
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_data:
            return {'can_donate': False, 'reason': 'Пользователь не найден'}
        
        if not user_data['last_donation_date']:
            return {'can_donate': True, 'days_wait': 0}
        
        days_since = (date.today() - user_data['last_donation_date']).days
        min_interval = 60
        
        if days_since >= min_interval:
            return {'can_donate': True, 'days_wait': 0}
        else:
            return {
                'can_donate': False, 
                'days_wait': min_interval - days_since,
                'last_donation': user_data['last_donation_date']
            } 