import os
import logging
import hashlib
import math
from datetime import datetime, timedelta, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, \
    ConversationHandler
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHOOSING_ROLE, ENTERING_PASSWORD, ENTERING_BLOOD_TYPE, ENTERING_LOCATION, \
    ENTERING_LAST_DONATION, USER_MENU, DOCTOR_MENU, ENTERING_DONATION_REQUEST, \
    ENTERING_REQUEST_LOCATION, ENTERING_REQUEST_ADDRESS, ENTERING_REQUEST_HOSPITAL, \
    ENTERING_REQUEST_CONTACT, ENTERING_REQUEST_DATE, UPDATE_LOCATION, UPDATE_DONATION_DATE, \
    UPDATE_BLOOD_TYPE, MC_AUTH_MENU, MC_REGISTER_NAME, MC_REGISTER_ADDRESS, \
    MC_REGISTER_CITY, MC_REGISTER_LOGIN, MC_REGISTER_PASSWORD, MC_LOGIN_LOGIN, \
    MC_LOGIN_PASSWORD, MC_MENU, MANAGE_BLOOD_NEEDS, DONOR_CERT_UPLOAD, \
    DONOR_SEARCH_MC, MC_EDIT_INFO, MC_EDIT_INPUT = range(30)

# Мастер-пароль для врачей
MASTER_PASSWORD = "doctor2024"


class BloodDonorBot:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'blood_donor_bot'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.application = None
        self.init_database()

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Вычисляет расстояние между двумя точками (в км) по формуле гаверсинуса
        """
        if not lat1 or not lon1 or not lat2 or not lon2:
            return None

        R = 6371  # Радиус Земли в км

        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(d_lon / 2) * math.sin(d_lon / 2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        d = R * c
        return d

    def get_db_connection(self):
        """Создает соединение с базой данных"""
        return psycopg2.connect(**self.db_config)

    def init_database(self):
        """Инициализирует базу данных"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Создание таблицы пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'doctor')),
                    blood_type VARCHAR(10),
                    location VARCHAR(255),
                    last_donation_date DATE,
                    is_registered BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Обновление таблицы users (новые колонки)
            alter_commands = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude FLOAT",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude FLOAT",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_certificate_file_id VARCHAR(255)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_certificate_date DATE",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_center_id INTEGER REFERENCES medical_centers(id)"
            ]
            for cmd in alter_commands:
                try:
                    cursor.execute(cmd)
                except psycopg2.errors.DuplicateColumn:
                    conn.rollback()
                except Exception as e:
                    logger.warning(f"Alter table warning: {e}")
                    conn.rollback()
                else:
                    conn.commit()

            # Обновление таблицы donation_requests (новые колонки)
            alter_requests_commands = [
                "ALTER TABLE donation_requests ADD COLUMN IF NOT EXISTS medical_center_id INTEGER REFERENCES medical_centers(id)",
                "ALTER TABLE donation_requests ADD COLUMN IF NOT EXISTS hospital_name VARCHAR(255)",
                "ALTER TABLE donation_requests ADD COLUMN IF NOT EXISTS contact_info TEXT"
            ]
            for cmd in alter_requests_commands:
                try:
                    cursor.execute(cmd)
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Alter table donation_requests warning: {e}")
                    conn.rollback()

            # Создание таблицы медицинских центров
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_centers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    address VARCHAR(255) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    latitude FLOAT,
                    longitude FLOAT,
                    login VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    contact_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создание таблицы потребностей крови
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blood_needs (
                    id SERIAL PRIMARY KEY,
                    medical_center_id INTEGER REFERENCES medical_centers(id),
                    blood_type VARCHAR(10) NOT NULL,
                    status VARCHAR(20) DEFAULT 'ok',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(medical_center_id, blood_type)
                )
            """)

            # Таблица откликов доноров
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donation_responses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    medical_center_id INTEGER REFERENCES medical_centers(id),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Старая таблица запросов (оставляем для совместимости или истории)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donation_requests (
                    id SERIAL PRIMARY KEY,
                    doctor_id BIGINT NOT NULL,
                    medical_center_id INTEGER REFERENCES medical_centers(id),
                    blood_type VARCHAR(10) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    address VARCHAR(255) NOT NULL,
                    hospital_name VARCHAR(255),
                    contact_info TEXT,
                    request_date DATE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doctor_id) REFERENCES users(telegram_id)
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начальная команда бота"""
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Проверяем, зарегистрирован ли пользователь
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (user.id,))
            existing_user = cursor.fetchone()

            if existing_user and existing_user['is_registered']:
                if existing_user['role'] == 'doctor':
                    await self.show_doctor_menu(update, context)
                    return DOCTOR_MENU
                else:
                    await self.show_user_menu(update, context)
                    return USER_MENU
            else:
                keyboard = [
                    [InlineKeyboardButton("👤 Я донор", callback_data="role_user")],
                    [InlineKeyboardButton("👨‍⚕️ Я врач", callback_data="role_doctor")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"👋 Привет, {user.first_name}! Добро пожаловать в BloodDonorBot!\n\n"
                    "Этот бот поможет связать доноров крови с медицинскими учреждениями.\n\n"
                    "Выберите вашу роль:",
                    reply_markup=reply_markup
                )

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка в start: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

        return CHOOSING_ROLE

    async def choose_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора роли"""
        query = update.callback_query
        await query.answer()

        logger.info(f"Пользователь {update.effective_user.id} выбрал роль: {query.data}")

        if query.data == "role_user":
            # Проверяем, зарегистрирован ли уже пользователь (независимо от текущей роли в БД)
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # Ищем пользователя по ID, проверяем флаг регистрации и наличие данных донора
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE telegram_id = %s 
                    AND is_registered = TRUE 
                    AND blood_type IS NOT NULL 
                    AND location IS NOT NULL
                """, (update.effective_user.id,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # Если пользователь существует и данные донора заполнены, обновляем роль и пускаем
                    cursor.execute("UPDATE users SET role = 'user' WHERE telegram_id = %s", (update.effective_user.id,))
                    conn.commit()
                    
                    cursor.close()
                    conn.close()
                    
                    context.user_data['role'] = 'user'
                    await query.edit_message_text("👋 С возвращением в режим донора!")
                    await self.show_user_menu(update, context)
                    return USER_MENU
                
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка проверки регистрации: {e}")

            context.user_data['role'] = 'user'
            # Сразу переходим к выбору группы крови через инлайн кнопки
            keyboard = [
                [InlineKeyboardButton("🩸 A+", callback_data="blood_A+"),
                 InlineKeyboardButton("🩸 A-", callback_data="blood_A-")],
                [InlineKeyboardButton("🩸 B+", callback_data="blood_B+"),
                 InlineKeyboardButton("🩸 B-", callback_data="blood_B-")],
                [InlineKeyboardButton("🩸 AB+", callback_data="blood_AB+"),
                 InlineKeyboardButton("🩸 AB-", callback_data="blood_AB-")],
                [InlineKeyboardButton("🩸 O+", callback_data="blood_O+"),
                 InlineKeyboardButton("🩸 O-", callback_data="blood_O-")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👤 Отлично! Вы выбрали роль донора.\n\n"
                "🩸 Выберите вашу группу крови:",
                reply_markup=reply_markup
            )
            return ENTERING_BLOOD_TYPE
        elif query.data == "role_doctor":
            # Проверяем, был ли пользователь уже врачом
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # Проверяем, был ли пользователь когда-либо зарегистрирован как врач
                # Здесь мы предполагаем, что если is_registered=TRUE и он был врачом раньше, 
                # или просто уже прошел проверку пароля ранее
                # Но для безопасности лучше всегда спрашивать пароль при первом входе в сессию
                # Однако, если пользователь просто переключается туда-сюда, можно упростить
                
                # В данном случае, следуя логике "если инфа есть - сразу вход",
                # проверим, есть ли запись. Но для врача пароль все же важен.
                # Если вы хотите пропускать пароль и для врача при повторном входе:
                
                cursor.execute("SELECT * FROM users WHERE telegram_id = %s AND role = 'doctor' AND is_registered = TRUE", 
                             (update.effective_user.id,))
                existing_doctor = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if existing_doctor:
                    context.user_data['role'] = 'doctor'
                    await query.edit_message_text("👨‍⚕️ С возвращением в режим врача!")
                    await self.show_doctor_menu(update, context)
                    return DOCTOR_MENU
                    
            except Exception as e:
                logger.error(f"Ошибка проверки врача: {e}")

            context.user_data['role'] = 'doctor'
            await query.edit_message_text(
                "👨‍⚕️ Вы выбрали роль врача.\n\n"
                "Для доступа к функциям врача введите мастер-пароль:"
            )
            return ENTERING_PASSWORD

    async def handle_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода пароля"""
        password = update.message.text
        logger.info(f"Пользователь {update.effective_user.id} ввел пароль")

        if context.user_data['role'] == 'doctor':
            if password == MASTER_PASSWORD:
                await self.show_mc_auth_menu(update, context)
                return MC_AUTH_MENU
            else:
                await update.message.reply_text(
                    "❌ Неверный мастер-пароль. Попробуйте еще раз:"
                )
                return ENTERING_PASSWORD
        else:
            # Для обычных пользователей сохраняем пароль
            context.user_data['password'] = password
            await update.message.reply_text(
                "✅ Пароль сохранен!\n\n"
                "Теперь укажите вашу группу крови (например: A+, B-, AB+, O-):"
            )
            return ENTERING_BLOOD_TYPE

    async def show_mc_auth_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню выбора входа/регистрации медцентра"""
        keyboard = [
            [InlineKeyboardButton("🏥 Войти в медцентр", callback_data="login_mc")],
            [InlineKeyboardButton("📝 Зарегистрировать новый центр", callback_data="register_mc")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_role")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "Добро пожаловать в систему управления донорством.\nВыберите действие:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup)

    async def handle_mc_auth_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора в меню авторизации МЦ"""
        query = update.callback_query
        await query.answer()
        choice = query.data

        if choice == "login_mc":
            await query.edit_message_text("🔑 Введите логин вашего медицинского центра:")
            return MC_LOGIN_LOGIN
        elif choice == "register_mc":
            await query.edit_message_text("🏥 Введите название вашего медицинского центра:")
            return MC_REGISTER_NAME
        elif choice == "back_to_role":
            await self.show_role_choice(update, context)
            return CHOOSING_ROLE
        return MC_AUTH_MENU

    # --- REGISTRATION FLOW ---
    async def process_mc_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['reg_mc_name'] = update.message.text
        await update.message.reply_text("📍 Введите адрес медицинского центра:")
        return MC_REGISTER_ADDRESS

    async def process_mc_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['reg_mc_address'] = update.message.text
        await update.message.reply_text(
            "📍 Отправьте геолокацию центра (скрепка -> Геопозиция).\n"
            "Это позволит донорам находить вас на карте.\n"
            "Если не можете, просто напишите название города:"
        )
        return MC_REGISTER_CITY
    
    async def process_mc_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        latitude = None
        longitude = None
        city = None

        if update.message.location:
            loc = update.message.location
            latitude = loc.latitude
            longitude = loc.longitude
            city = f"Координаты {latitude:.4f}, {longitude:.4f}" # Temporary city name if coords
            # Ideally we would reverse geocode here to get city name
            context.user_data['reg_mc_latitude'] = latitude
            context.user_data['reg_mc_longitude'] = longitude
        else:
            city = update.message.text
            context.user_data['reg_mc_latitude'] = None
            context.user_data['reg_mc_longitude'] = None

        context.user_data['reg_mc_city'] = city
        await update.message.reply_text("👤 Придумайте логин для входа:")
        return MC_REGISTER_LOGIN

    async def process_mc_reg_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        login = update.message.text
        # Check uniqueness
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM medical_centers WHERE login = %s", (login,))
        exists = cursor.fetchone()
        cursor.close()
        conn.close()

        if exists:
            await update.message.reply_text("❌ Такой логин уже занят. Придумайте другой:")
            return MC_REGISTER_LOGIN

        context.user_data['reg_mc_login'] = login
        await update.message.reply_text("🔒 Придумайте пароль:")
        return MC_REGISTER_PASSWORD

    async def process_mc_reg_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        data = context.user_data
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO medical_centers (name, address, city, latitude, longitude, login, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (data['reg_mc_name'], data['reg_mc_address'], data['reg_mc_city'], 
                  data.get('reg_mc_latitude'), data.get('reg_mc_longitude'),
                  data['reg_mc_login'], password_hash))
            
            mc_id = cursor.fetchone()[0]
            
            # Ensure user is registered as doctor and linked to MC
            user = update.effective_user
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, role, is_registered, medical_center_id)
                VALUES (%s, %s, %s, %s, 'doctor', TRUE, %s)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET role = 'doctor', is_registered = TRUE, medical_center_id = EXCLUDED.medical_center_id
            """, (user.id, user.username, user.first_name, user.last_name, mc_id))
            
            conn.commit()
            cursor.close()
            conn.close()

            context.user_data['mc_id'] = mc_id
            # Load info for session
            context.user_data['mc_info'] = {
                'id': mc_id, 'name': data['reg_mc_name'], 'address': data['reg_mc_address'],
                'city': data['reg_mc_city']
            }
            await update.message.reply_text("✅ Медицинский центр успешно зарегистрирован!")
            await self.show_doctor_menu(update, context) 
            return MC_MENU
        except Exception as e:
            logger.error(f"Registration error: {e}")
            await update.message.reply_text("❌ Ошибка регистрации. Попробуйте снова /start")
            return ConversationHandler.END

    # --- LOGIN FLOW ---
    async def process_mc_login_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['login_mc_login'] = update.message.text
        await update.message.reply_text("🔒 Введите пароль:")
        return MC_LOGIN_PASSWORD

    async def process_mc_login_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        login = context.user_data.get('login_mc_login')
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM medical_centers WHERE login = %s AND password_hash = %s", 
                       (login, password_hash))
        mc = cursor.fetchone()
        cursor.close()
        
        if mc:
            context.user_data['mc_id'] = mc['id']
            context.user_data['mc_info'] = mc
            
            # Update user role to doctor and link to MC
            conn = self.get_db_connection()
            cursor = conn.cursor()
            user = update.effective_user
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, role, is_registered, medical_center_id)
                VALUES (%s, %s, %s, %s, 'doctor', TRUE, %s)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET role = 'doctor', is_registered = TRUE, medical_center_id = EXCLUDED.medical_center_id
            """, (user.id, user.username, user.first_name, user.last_name, mc['id']))
            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text(f"✅ Вход выполнен: {mc['name']}")
            await self.show_doctor_menu(update, context)
            return MC_MENU
        else:
            conn.close()
            await update.message.reply_text("❌ Неверный логин или пароль. Попробуйте снова логин:")
            return MC_LOGIN_LOGIN

    async def register_doctor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Регистрация врача"""
        user = update.effective_user
        logger.info(f"Регистрация врача: {user.id}")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, role, is_registered)
                VALUES (%s, %s, %s, %s, 'doctor', TRUE)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET role = 'doctor', is_registered = TRUE
            """, (user.id, user.username, user.first_name, user.last_name))

            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text("✅ Вы успешно зарегистрированы как врач!")
            await self.show_doctor_menu(update, context)
        except Exception as e:
            logger.error(f"Ошибка регистрации врача: {e}")
            await update.message.reply_text("Произошла ошибка при регистрации.")

    async def handle_blood_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы крови через инлайн кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith('blood_'):
            blood_type = query.data.replace('blood_', '')
            context.user_data['blood_type'] = blood_type
            
            await query.edit_message_text(
                f"✅ Группа крови {blood_type} выбрана!\n\n"
                "📍 Теперь укажите ваше местоположение (город):"
            )
            return ENTERING_LOCATION
        
        # Для обратной совместимости - если кто-то введет текстом
        blood_type = update.message.text.upper() if update.message else ""
        valid_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

        if blood_type not in valid_types:
            await update.message.reply_text(
                "❌ Неверный формат группы крови. Используйте кнопки выше для выбора."
            )
            return ENTERING_BLOOD_TYPE

        context.user_data['blood_type'] = blood_type
        await update.message.reply_text(
            "✅ Группа крови сохранена!\n\n"
            "📍 Теперь укажите ваше местоположение.\n"
            "Отправьте геопозицию (скрепка -> Геопозиция) или напишите название города:"
        )
        return ENTERING_LOCATION

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода местоположения"""
        if update.message.location:
            location = update.message.location
            context.user_data['latitude'] = location.latitude
            context.user_data['longitude'] = location.longitude
            context.user_data['location'] = f"Координаты: {location.latitude:.4f}, {location.longitude:.4f}"
            await update.message.reply_text("✅ Геопозиция получена!")
        else:
            location_text = update.message.text
            context.user_data['location'] = location_text
            context.user_data['latitude'] = None
            context.user_data['longitude'] = None

        await update.message.reply_text(
            "✅ Местоположение сохранено!\n\n"
            "Укажите дату последней сдачи крови в формате ДД.ММ.ГГГГ\n"
            "(или напишите 'никогда', если вы еще не сдавали кровь):"
        )
        return ENTERING_LAST_DONATION

    async def handle_last_donation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода даты последней сдачи крови"""
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
                return ENTERING_LAST_DONATION

        # Регистрируем пользователя
        user = update.effective_user
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, role, 
                                 blood_type, location, latitude, longitude, last_donation_date, is_registered)
                VALUES (%s, %s, %s, %s, 'user', %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET blood_type = EXCLUDED.blood_type, 
                             location = EXCLUDED.location, 
                             latitude = EXCLUDED.latitude,
                             longitude = EXCLUDED.longitude,
                             last_donation_date = EXCLUDED.last_donation_date,
                             is_registered = TRUE
            """, (user.id, user.username, user.first_name, user.last_name,
                  context.user_data.get('blood_type'), 
                  context.user_data.get('location'),
                  context.user_data.get('latitude'),
                  context.user_data.get('longitude'),
                  last_donation_date))

            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text(
                "🎉 Регистрация завершена! Вы успешно зарегистрированы как донор крови.\n\n"
                "Теперь вы будете получать уведомления о необходимости сдачи крови в вашем регионе."
            )
            await self.show_user_menu(update, context)
            return USER_MENU
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")
            await update.message.reply_text("Произошла ошибка при регистрации.")

    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню пользователя"""
        keyboard = [
            [InlineKeyboardButton("🔔 Входящие запросы", callback_data="relevant_requests")],
            [InlineKeyboardButton("💉 Хочу сдать кровь", callback_data="want_to_donate")],
            [InlineKeyboardButton("📄 Мед. справка", callback_data="my_certs")],
            [InlineKeyboardButton("📊 Моя информация", callback_data="user_info")],
            [InlineKeyboardButton("🩸 Мои донации", callback_data="my_donations")],
            [InlineKeyboardButton("🩸 Изменить группу крови", callback_data="update_blood_type")],
            [InlineKeyboardButton("📅 Обновить дату сдачи", callback_data="update_donation")],
            [InlineKeyboardButton("📍 Изменить местоположение", callback_data="update_location")],
            [InlineKeyboardButton("🔄 Сменить роль", callback_data="switch_role")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                "👤 Меню донора\n\nВыберите действие:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "👤 Меню донора\n\nВыберите действие:",
                reply_markup=reply_markup
            )

    async def show_doctor_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню врача"""
        mc_name = "Неизвестный МЦ"
        
        # Try to get from context
        if context.user_data.get('mc_info'):
            mc_name = context.user_data['mc_info'].get('name', mc_name)
        else:
            # Try to restore from DB if logged in as doctor
            user_id = update.effective_user.id
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check if user is linked to an MC (via login or registration)
            # We need to store this link. For now, let's assume we check user role and try to find last MC?
            # Or better, rely on `mc_id` in `context.user_data` which should be set on login.
            # If it's missing (restart), we might need to re-login or infer from `users` table if we added `medical_center_id` there.
            
            # Let's use the new column we added to `users` table
            cursor.execute("""
                SELECT mc.id, mc.name, mc.address, mc.city, mc.contact_info 
                FROM users u
                JOIN medical_centers mc ON u.medical_center_id = mc.id
                WHERE u.telegram_id = %s
            """, (user_id,))
            
            mc = cursor.fetchone()
            if mc:
                context.user_data['mc_id'] = mc['id']
                context.user_data['mc_info'] = mc
                mc_name = mc['name']
            
            cursor.close()
            conn.close()

        keyboard = [
            [InlineKeyboardButton("🚦 Донорский светофор", callback_data="traffic_light")],
            [InlineKeyboardButton("👥 Отклики доноров", callback_data="donor_responses")],
            [InlineKeyboardButton("✏️ Редактировать МЦ", callback_data="edit_mc_info")],
            [InlineKeyboardButton("🩸 Создать запрос (дата)", callback_data="create_request")],
            [InlineKeyboardButton("📋 Мои запросы", callback_data="my_requests")],
            [InlineKeyboardButton("📊 Статистика", callback_data="statistics")],
            [InlineKeyboardButton("🔄 Сменить роль", callback_data="switch_role")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"👨‍⚕️ Меню врача\n🏥 Центр: {mc_name}\n\nВыберите действие:"

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup
            )

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий в меню"""
        query = update.callback_query
        await query.answer()

        logger.info(f"Пользователь {update.effective_user.id} нажал: {query.data}")

        if query.data == "user_info":
            await self.show_user_info(update, context)
            return USER_MENU
        elif query.data == "relevant_requests":
            await self.show_relevant_requests(update, context)
            return USER_MENU
        elif query.data == "user_traffic_light":
            await self.show_user_traffic_light(update, context)
            return USER_MENU
        elif query.data.startswith("rel_req_page_"):
            page = int(query.data.split("_")[-1])
            await self.show_relevant_requests(update, context, page=page)
            return USER_MENU
        elif query.data.startswith("my_req_page_"):
            page = int(query.data.split("_")[-1])
            await self.show_my_requests(update, context, page=page)
            return DOCTOR_MENU
        elif query.data.startswith("cancel_app_"):
            await self.handle_user_app_action(update, context)
            return USER_MENU
        elif query.data == "edit_mc_info":
            return await self.show_edit_mc_menu(update, context)
        elif query.data == "want_to_donate":
            await self.start_donation_search(update, context)
            return DONOR_SEARCH_MC
        elif query.data == "my_certs":
            await self.show_cert_menu(update, context)
            return DONOR_CERT_UPLOAD
        elif query.data == "my_donations":
            await self.show_my_donations(update, context)
            return USER_MENU
        elif query.data == "update_blood_type":
            keyboard = [
                [InlineKeyboardButton("🩸 A+", callback_data="blood_A+"),
                 InlineKeyboardButton("🩸 A-", callback_data="blood_A-")],
                [InlineKeyboardButton("🩸 B+", callback_data="blood_B+"),
                 InlineKeyboardButton("🩸 B-", callback_data="blood_B-")],
                [InlineKeyboardButton("🩸 AB+", callback_data="blood_AB+"),
                 InlineKeyboardButton("🩸 AB-", callback_data="blood_AB-")],
                [InlineKeyboardButton("🩸 O+", callback_data="blood_O+"),
                 InlineKeyboardButton("🩸 O-", callback_data="blood_O-")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🩸 Выберите новую группу крови:",
                reply_markup=reply_markup
            )
            return UPDATE_BLOOD_TYPE
        elif query.data == "update_donation":
            await query.edit_message_text(
                "📅 Обновление даты последней сдачи крови\n\n"
                "Введите дату последней сдачи крови в формате ДД.ММ.ГГГГ\n"
                "(или напишите 'никогда', если вы еще не сдавали кровь):"
            )
            return UPDATE_DONATION_DATE
        elif query.data == "update_location":
            await query.edit_message_text(
                "📍 Обновление местоположения\n\n"
                "Отправьте новую геопозицию (скрепка -> Геопозиция) или введите название города:"
            )
            return UPDATE_LOCATION
        elif query.data == "switch_role":
            # Возвращаемся к выбору роли
            keyboard = [
                [InlineKeyboardButton("👤 Я донор", callback_data="role_user")],
                [InlineKeyboardButton("👨‍⚕️ Я врач", callback_data="role_doctor")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👋 Выберите вашу роль:",
                reply_markup=reply_markup
            )
            return CHOOSING_ROLE
        elif query.data == "traffic_light":
             await self.show_traffic_light(update, context)
             return MANAGE_BLOOD_NEEDS
        elif query.data == "create_request":
            logger.info("Создание запроса крови")
            await self.create_donation_request(update, context)
            return ENTERING_DONATION_REQUEST
        elif query.data == "my_requests":
            await self.show_my_requests(update, context)
            return DOCTOR_MENU
        elif query.data == "donor_responses":
            await self.show_donor_responses_v2(update, context)
            return MC_MENU
        elif query.data.startswith("view_donor_") or query.data.startswith("confirm_donation_") or query.data.startswith("reject_donation_"):
             await self.handle_donor_response_action(update, context)
             return MC_MENU
        elif query.data == "statistics":
            await self.show_statistics(update, context)
            return DOCTOR_MENU
        elif query.data == "switch_role":
            # Возвращаемся к выбору роли
            keyboard = [
                [InlineKeyboardButton("👤 Я донор", callback_data="role_user")],
                [InlineKeyboardButton("👨‍⚕️ Я врач", callback_data="role_doctor")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👋 Выберите вашу роль:",
                reply_markup=reply_markup
            )
            return CHOOSING_ROLE
        elif query.data == "help":
            await self.show_help(update, context)
            if self.is_doctor(update.effective_user.id):
                return DOCTOR_MENU
            else:
                return USER_MENU
        elif query.data.startswith("respond_"):
            # Обработка отклика донора
            await self.handle_donor_response(update, context)
            # После отклика показываем меню донора
            await self.show_user_menu(update, context)
            return USER_MENU
        elif query.data == "back_to_menu":
            user = update.effective_user
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT role FROM users WHERE telegram_id = %s", (user.id,))
                user_data = cursor.fetchone()
                cursor.close()
                conn.close()

                if user_data and user_data['role'] == 'doctor':
                    await self.show_doctor_menu(update, context)
                    return DOCTOR_MENU
                else:
                    await self.show_user_menu(update, context)
                    return USER_MENU
            except Exception as e:
                logger.error(f"Ошибка при возврате в меню: {e}")
                return CHOOSING_ROLE

    # --- TRAFFIC LIGHT (DOCTOR) ---
    async def show_traffic_light(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mc_id = context.user_data.get('mc_id')
        
        # Recovery mechanism if mc_id is missing
        if not mc_id:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, name FROM medical_centers WHERE doctor_id = %s", (update.effective_user.id,))
            mc = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if mc:
                context.user_data['mc_id'] = mc['id']
                context.user_data['mc_info'] = mc
                mc_id = mc['id']
            else:
                if update.callback_query:
                    await update.callback_query.answer("Ошибка: МЦ не выбран")
                return MC_MENU

        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT blood_type, status FROM blood_needs WHERE medical_center_id = %s", (mc_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Default statuses if not found
        status_map = {row['blood_type']: row['status'] for row in rows}
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        # Status emojis
        emojis = {'ok': '🟢', 'need': '🟡', 'urgent': '🔴'}
        
        keyboard = []
        row = []
        for bt in blood_types:
            status = status_map.get(bt, 'ok')
            btn_text = f"{bt} {emojis[status]}"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"tl_toggle_{bt}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = "🚦 **Донорский светофор**\n\nНажимайте на группу крови, чтобы изменить статус:\n🟢 Достаточно\n🟡 Нужно пополнить\n🔴 Срочно (Агрессивный поиск)"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_traffic_light_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "back_to_menu":
            await self.show_doctor_menu(update, context)
            return MC_MENU
            
        if data.startswith("tl_toggle_"):
            blood_type = data.replace("tl_toggle_", "")
            mc_id = context.user_data.get('mc_id')
            
            if not mc_id:
                # Recovery attempt
                conn = self.get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT id, name FROM medical_centers WHERE doctor_id = %s", (update.effective_user.id,))
                mc = cursor.fetchone()
                cursor.close()
                conn.close()
                if mc:
                    context.user_data['mc_id'] = mc['id']
                    context.user_data['mc_info'] = mc
                    mc_id = mc['id']
                else:
                     await query.edit_message_text("❌ Ошибка сессии. Пожалуйста, перезайдите в меню МЦ.")
                     return DOCTOR_MENU
            
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get current
            cursor.execute("SELECT status FROM blood_needs WHERE medical_center_id = %s AND blood_type = %s", 
                           (mc_id, blood_type))
            row = cursor.fetchone()
            
            current = row['status'] if row else 'ok'
            # Cycle: ok -> need -> urgent -> ok
            next_status = {'ok': 'need', 'need': 'urgent', 'urgent': 'ok'}[current]
            
            # Upsert
            cursor.execute("""
                INSERT INTO blood_needs (medical_center_id, blood_type, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (medical_center_id, blood_type) 
                DO UPDATE SET status = %s
            """, (mc_id, blood_type, next_status, next_status))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if next_status == 'urgent':
                await self.broadcast_need(mc_id, blood_type)

            # Refresh view
            await self.show_traffic_light(update, context)
            return MANAGE_BLOOD_NEEDS
        return MANAGE_BLOOD_NEEDS

    # --- DONOR CERTIFICATES ---
    async def show_cert_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check expiration
        was_expired = self.check_cert_expiration(user_id)
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT medical_certificate_date FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        cert_date = user.get('medical_certificate_date')
        msg = "📄 **Медицинская справка**\n\n"
        
        if was_expired:
             msg += "⚠️ **Ваша предыдущая справка истекла и была удалена.**\nПожалуйста, загрузите новую.\n\n"
        
        if cert_date:
            days_passed = (date.today() - cert_date).days
            validity = 180 # 6 months
            msg += f"✅ Справка активна (загружена {cert_date.strftime('%d.%m.%Y')})\n"
            msg += f"Действительна еще {validity - days_passed} дней."
        else:
            msg += "❌ Справка не загружена.\nЗагрузите фото справки, чтобы врачи могли видеть ваш статус."
            
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg + "\n\nОтправьте фото справки в этот чат для загрузки.", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg + "\n\nОтправьте фото справки в этот чат для загрузки.", reply_markup=reply_markup, parse_mode='Markdown')

    async def process_cert_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.photo:
             await update.message.reply_text("Пожалуйста, отправьте фото.")
             return DONOR_CERT_UPLOAD

        photo = update.message.photo[-1]
        file_id = photo.file_id
        user_id = update.effective_user.id
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET medical_certificate_file_id = %s, medical_certificate_date = CURRENT_DATE
            WHERE telegram_id = %s
        """, (file_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        await update.message.reply_text("✅ Справка успешно загружена/обновлена!")
        await self.show_user_menu(update, context)
        return USER_MENU

    async def handle_cert_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "back_to_menu":
             await self.show_user_menu(update, context)
             return USER_MENU
        return DONOR_CERT_UPLOAD

    def check_cert_expiration(self, user_id):
        """Проверяет и удаляет просроченную справку"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT medical_certificate_date FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user and user['medical_certificate_date']:
            cert_date = user['medical_certificate_date']
            days_passed = (date.today() - cert_date).days
            validity = 180 # 6 months
            
            if days_passed >= validity:
                cursor.execute("""
                    UPDATE users 
                    SET medical_certificate_file_id = NULL, medical_certificate_date = NULL 
                    WHERE telegram_id = %s
                """, (user_id,))
                conn.commit()
                cursor.close()
                conn.close()
                return True # Expired and deleted
                
        cursor.close()
        conn.close()
        return False # Valid or not present

    # --- DONOR SEARCH ---
    async def start_donation_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT blood_type, city, latitude, longitude FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['blood_type']:
            if update.callback_query:
                await update.callback_query.answer("Сначала укажите группу крови!")
            return USER_MENU

        # Find MCs with need
        cursor.execute("""
            SELECT mc.id, mc.name, mc.address, mc.city, bn.status, mc.latitude, mc.longitude
            FROM blood_needs bn
            JOIN medical_centers mc ON bn.medical_center_id = mc.id
            WHERE bn.blood_type = %s AND bn.status IN ('need', 'urgent')
        """, (user['blood_type'],))
        mcs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not mcs:
            if update.callback_query:
                await update.callback_query.edit_message_text("😔 К сожалению, сейчас нет запросов на вашу группу крови.")
            return USER_MENU
            
        # Calculate distances and sort
        user_lat = user['latitude']
        user_lon = user['longitude']
        
        valid_mcs = []
        for mc in mcs:
            dist = self.calculate_distance(user_lat, user_lon, mc['latitude'], mc['longitude'])
            mc['distance'] = dist
            # Filter by radius (e.g., 50km) if user has coords AND mc has coords
            if user_lat and mc['latitude']:
                 if dist <= 50: # 50km radius
                     valid_mcs.append(mc)
            else:
                # If no coords, show all matching by city or just show all?
                # Let's show all but maybe mark them
                valid_mcs.append(mc)

        # Sort by distance (None last)
        valid_mcs.sort(key=lambda x: x['distance'] if x['distance'] is not None else 9999)
        
        if not valid_mcs:
             if update.callback_query:
                 keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
                 await update.callback_query.edit_message_text("😔 В радиусе 50км нет запросов на вашу группу крови.", reply_markup=InlineKeyboardMarkup(keyboard))
             return USER_MENU

        msg = f"🔎 Найдены центры, нуждающиеся в {user['blood_type']}:\n\n"
        keyboard = []
        
        for mc in valid_mcs[:10]: # Show top 10
            icon = "🔴" if mc['status'] == 'urgent' else "🟡"
            dist_str = f"{mc['distance']:.1f}км" if mc['distance'] is not None else mc['city']
            btn_text = f"{icon} {mc['name']} ({dist_str})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_mc_{mc['id']}")])
            
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
        return DONOR_SEARCH_MC
        
    async def handle_donation_search_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "back_to_menu":
            await self.show_user_menu(update, context)
            return USER_MENU
            
        if data == "want_to_donate":
             await self.start_donation_search(update, context)
             return DONOR_SEARCH_MC

        if data.startswith("view_mc_"):
            mc_id = int(data.replace("view_mc_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM medical_centers WHERE id = %s", (mc_id,))
            mc = cursor.fetchone()
            cursor.close()
            conn.close()
            
            msg = f"🏥 **{mc['name']}**\n"
            msg += f"📍 {mc['address']}\n"
            msg += f"🏙 {mc['city']}\n"
            msg += f"📞 {mc['contact_info'] or 'Нет контактов'}\n\n"
            msg += "Вы готовы сдать кровь в этом центре?"
            
            keyboard = [
                [InlineKeyboardButton("✅ Согласен на донацию", callback_data=f"agree_donate_{mc_id}")],
                [InlineKeyboardButton("🔙 К списку", callback_data="want_to_donate")] 
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
            return DONOR_SEARCH_MC

        if data.startswith("agree_donate_"):
            # Check cert expiration first
            self.check_cert_expiration(update.effective_user.id)
            
            # Check last donation date (60 days rule)
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT last_donation_date FROM users WHERE telegram_id = %s", (update.effective_user.id,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data and user_data['last_donation_date']:
                days_since = (datetime.now().date() - user_data['last_donation_date']).days
                if days_since < 60:
                    days_left = 60 - days_since
                    await update.callback_query.answer(f"⛔ Вы сможете сдать кровь только через {days_left} дн.", show_alert=True)
                    return DONOR_SEARCH_MC

            mc_id = int(data.replace("agree_donate_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO donation_responses (user_id, medical_center_id, status)
                VALUES (%s, %s, 'pending')
            """, (update.effective_user.id, mc_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            await update.callback_query.edit_message_text("✅ Спасибо! Ваша заявка отправлена врачу. Ждите подтверждения.")
            await self.show_user_menu(update, context)
            return USER_MENU
        
        return DONOR_SEARCH_MC

    async def show_donor_responses_v2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает отклики доноров (New Implementation)"""
        mc_id = context.user_data.get('mc_id')
        if not mc_id:
            if update.callback_query:
                await update.callback_query.answer("Ошибка: МЦ не выбран")
            return MC_MENU

        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT dr.id, dr.created_at, u.telegram_id, u.first_name, u.last_name, u.username, 
                   u.blood_type, u.medical_certificate_file_id, u.medical_certificate_date
            FROM donation_responses dr
            JOIN users u ON dr.user_id = u.telegram_id
            WHERE dr.medical_center_id = %s AND dr.status = 'pending'
            ORDER BY dr.created_at DESC
        """, (mc_id,))
        
        responses = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not responses:
            msg = "👥 Пока нет новых откликов доноров."
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]])
                )
            return MC_MENU
            
        keyboard = []
        for r in responses:
            name = f"{r['first_name']} {r['last_name'] or ''} ({r['blood_type']})"
            keyboard.append([InlineKeyboardButton(name, callback_data=f"view_donor_{r['id']}")])
            
        keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")])
        
        await update.callback_query.edit_message_text(
            f"👥 Найдено {len(responses)} откликов. Выберите донора для просмотра:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MC_MENU 

    async def handle_donor_response_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "back_to_menu":
            await self.show_doctor_menu(update, context)
            return MC_MENU

        if data.startswith("view_donor_"):
            resp_id = int(data.replace("view_donor_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT dr.id, u.first_name, u.last_name, u.username, u.blood_type,
                       u.medical_certificate_file_id, u.medical_certificate_date, u.last_donation_date
                FROM donation_responses dr
                JOIN users u ON dr.user_id = u.telegram_id
                WHERE dr.id = %s
            """, (resp_id,))
            donor = cursor.fetchone()
            cursor.close()
            conn.close()
            
            msg = f"👤 **Донор:** {donor['first_name']} {donor['last_name'] or ''}\n"
            msg += f"🩸 Группа: {donor['blood_type']}\n"
            # msg += f"📞 Тел: {donor.get('phone_number') or 'Не указан'}\n" # Phone number removed for now
            msg += f"📅 Посл. сдача: {donor['last_donation_date'] or 'Нет данных'}\n\n"
            
            if donor['medical_certificate_file_id']:
                msg += "✅ **Мед. справка загружена**\n"
                msg += f"Дата: {donor['medical_certificate_date']}\n"
            else:
                msg += "❌ Справка не загружена\n"
                
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить (Сдал)", callback_data=f"confirm_donation_{resp_id}")],
                [InlineKeyboardButton("⛔ Отклонить (Не пришел)", callback_data=f"reject_donation_{resp_id}")],
                [InlineKeyboardButton("🔙 К списку", callback_data="donor_responses")]
            ]
            
            # Check if message text is different before editing, to avoid "Message is not modified" error
            # Or just use a new message. Editing is better.
            # Since we don't have the previous message text easily, we rely on the fact that the user clicked a button
            # which usually warrants an update.
            
            try:
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            except Exception as e:
                # If message not modified, maybe just answer
                pass
            
            if donor['medical_certificate_file_id']:
                try:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=donor['medical_certificate_file_id'], caption="Справка донора")
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")
            
            return MC_MENU

        if data.startswith("confirm_donation_"):
            resp_id = int(data.replace("confirm_donation_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update response status
            cursor.execute("UPDATE donation_responses SET status = 'completed' WHERE id = %s RETURNING user_id", (resp_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                # Update user last donation date
                cursor.execute("UPDATE users SET last_donation_date = CURRENT_DATE WHERE telegram_id = %s", (user_id,))
                conn.commit()
            
            cursor.close()
            conn.close()
            
            await update.callback_query.edit_message_text("✅ Донация подтверждена! Таймер донора обновлен.")
            
            # Notify user
            try:
                if row:
                    await context.bot.send_message(user_id, "🎉 Спасибо за донацию! Ваша дата последней сдачи крови обновлена.")
            except:
                pass
                
            await self.show_donor_responses_v2(update, context)
            return MC_MENU

        if data.startswith("reject_donation_"):
            resp_id = int(data.replace("reject_donation_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update response status
            cursor.execute("UPDATE donation_responses SET status = 'rejected' WHERE id = %s RETURNING user_id", (resp_id,))
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            await update.callback_query.edit_message_text("⛔ Заявка отклонена.")
            
            # Notify user
            try:
                if row:
                     user_id = row[0]
                     await context.bot.send_message(user_id, "😔 Врач отметил, что донация не состоялась.")
            except:
                pass

            await self.show_donor_responses_v2(update, context)
            return MC_MENU

        return MC_MENU

    def is_doctor(self, user_id):
        """Проверяет, является ли пользователь врачом"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT role FROM users WHERE telegram_id = %s", (user_id,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            return user_data and user_data['role'] == 'doctor'
        except:
            return False

    async def show_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о пользователе"""
        user = update.effective_user
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (user.id,))
            user_data = cursor.fetchone()

            if user_data:
                last_donation = user_data['last_donation_date']
                if last_donation:
                    days_since = (datetime.now().date() - last_donation).days
                    can_donate = days_since >= 60
                    status = "✅ Можете сдавать кровь" if can_donate else f"⏳ Подождите еще {60 - days_since} дней"
                else:
                    status = "✅ Можете сдавать кровь"

                info_text = f"""
📊 Ваша информация:

🩸 Группа крови: {user_data['blood_type']}
📍 Местоположение: {user_data['location']}
📅 Последняя сдача: {last_donation.strftime('%d.%m.%Y') if last_donation else 'Не сдавали'}
🔄 Статус: {status}
                """
            else:
                info_text = "❌ Информация не найдена"

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(info_text, reply_markup=reply_markup)

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка показа информации пользователя: {e}")

    async def show_my_donations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает донации пользователя (New Implementation)"""
        user = update.effective_user
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Fetch from donation_responses linked to medical_centers
            cursor.execute("""
                SELECT dr.id, dr.status, dr.created_at, mc.name, mc.address, mc.city, mc.contact_info
                FROM donation_responses dr
                JOIN medical_centers mc ON dr.medical_center_id = mc.id
                WHERE dr.user_id = %s
                ORDER BY dr.created_at DESC
                LIMIT 10
            """, (user.id,))

            donations = cursor.fetchall()
            cursor.close()
            conn.close()

            if donations:
                text = "🩸 **Мои заявки на донацию**:\n\n"
                keyboard = []
                
                for i, d in enumerate(donations, 1):
                    status_map = {
                        'pending': '⏳ Ожидает подтверждения',
                        'approved': '✅ Одобрено',
                        'completed': '🩸 Сдано',
                        'cancelled': '❌ Отменено',
                        'rejected': '⛔ Отклонено'
                    }
                    status = status_map.get(d['status'], d['status'])
                    
                    text += f"{i}. 🏥 **{d['name']}**\n"
                    text += f"   📍 {d['city']}, {d['address']}\n"
                    text += f"   📅 {d['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
                    text += f"   Статус: {status}\n\n"
                    
                    # Add cancel button if pending
                    if d['status'] == 'pending':
                        keyboard.append([InlineKeyboardButton(f"❌ Отменить заявку в {d['name']}", callback_data=f"cancel_app_{d['id']}")])

                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                text = "У вас пока нет заявок на донацию."
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Ошибка показа донаций пользователя: {e}")
            await update.callback_query.edit_message_text("Произошла ошибка при загрузке донаций.")

    async def handle_user_app_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data.startswith("cancel_app_"):
            app_id = int(data.replace("cancel_app_", ""))
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if still pending
            cursor.execute("SELECT status FROM donation_responses WHERE id = %s AND user_id = %s", (app_id, update.effective_user.id))
            row = cursor.fetchone()
            
            if row and row[0] == 'pending':
                cursor.execute("UPDATE donation_responses SET status = 'cancelled' WHERE id = %s", (app_id,))
                conn.commit()
                await query.answer("Заявка отменена")
            else:
                await query.answer("Невозможно отменить (уже обработана)")
                
            cursor.close()
            conn.close()
            
            await self.show_my_donations(update, context)
            return USER_MENU
            
        return USER_MENU

    async def update_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновляет местоположение пользователя"""
        user = update.effective_user
        
        latitude = None
        longitude = None
        new_location = None

        if update.message.location:
            loc = update.message.location
            latitude = loc.latitude
            longitude = loc.longitude
            new_location = f"Координаты: {latitude:.4f}, {longitude:.4f}"
        else:
            new_location = update.message.text
            
        logger.info(f"Обновление местоположения для пользователя {user.id}: {new_location}")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            if latitude and longitude:
                cursor.execute("""
                    UPDATE users
                    SET location = %s, latitude = %s, longitude = %s
                    WHERE telegram_id = %s
                """, (new_location, latitude, longitude, user.id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET location = %s, latitude = NULL, longitude = NULL
                    WHERE telegram_id = %s
                """, (new_location, user.id))

            conn.commit()
            cursor.close()
            conn.close()

            await update.message.reply_text("✅ Местоположение успешно обновлено!")
            await self.show_user_menu(update, context)
            return USER_MENU
        except Exception as e:
            logger.error(f"Ошибка обновления местоположения: {e}")
            await update.message.reply_text("Произошла ошибка при обновлении местоположения.")
            return USER_MENU

    async def update_donation_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновляет дату последней сдачи крови"""
        last_donation = update.message.text
        user = update.effective_user

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
                return UPDATE_DONATION_DATE

        logger.info(f"Обновление даты сдачи для пользователя {user.id}: {last_donation_date}")

        try:
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

            await update.message.reply_text("✅ Дата последней сдачи крови успешно обновлена!")
            await self.show_user_menu(update, context)
            return USER_MENU
        except Exception as e:
            logger.error(f"Ошибка обновления даты сдачи: {e}")
            await update.message.reply_text("Произошла ошибка при обновлении даты сдачи.")
            return USER_MENU

    async def show_user_traffic_light(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает пользователю 'Светофор донора' (потребности МЦ поблизости)"""
        user = update.effective_user
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get user location
            cursor.execute("SELECT city, latitude, longitude, blood_type FROM users WHERE telegram_id = %s", (user.id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                await update.callback_query.edit_message_text("Ошибка: данные пользователя не найдены.")
                cursor.close()
                conn.close()
                return USER_MENU

            # Fetch all needs
            cursor.execute("""
                SELECT bn.blood_type, bn.status, mc.name, mc.city, mc.latitude, mc.longitude 
                FROM blood_needs bn
                JOIN medical_centers mc ON bn.medical_center_id = mc.id
                WHERE bn.status IN ('need', 'urgent')
            """)
            needs = cursor.fetchall()
            cursor.close()
            conn.close()
            
            relevant_needs = []
            user_lat = user_data['latitude']
            user_lon = user_data['longitude']
            
            for need in needs:
                # Filter by radius (50km) or city
                is_nearby = False
                dist_str = ""
                
                if user_lat and need['latitude']:
                    dist = self.calculate_distance(user_lat, user_lon, need['latitude'], need['longitude'])
                    if dist <= 50:
                        is_nearby = True
                        dist_str = f" (~{dist:.1f} км)"
                elif user_data['city'] and need['city'] and user_data['city'].lower() in need['city'].lower():
                    is_nearby = True
                
                if is_nearby:
                    need['dist_str'] = dist_str
                    relevant_needs.append(need)
            
            if not relevant_needs:
                text = "🚦 В вашем регионе сейчас нет острой потребности в крови.\nСпасибо, что остаетесь с нами!"
            else:
                text = "🚦 **Донорский светофор (ваш регион)**\n\n"
                for n in relevant_needs:
                    icon = "🔴" if n['status'] == 'urgent' else "🟡"
                    text += f"{icon} **{n['blood_type']}**: {n['name']}{n['dist_str']}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return USER_MENU

        except Exception as e:
            logger.error(f"Error showing user traffic light: {e}")
            await update.callback_query.edit_message_text("Ошибка загрузки светофора.")
            return USER_MENU

    async def create_donation_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание запроса на сдачу крови"""
        logger.info("Начинаем создание запроса крови")
        keyboard = [
            [InlineKeyboardButton("A+", callback_data="request_A+"),
             InlineKeyboardButton("A-", callback_data="request_A-")],
            [InlineKeyboardButton("B+", callback_data="request_B+"),
             InlineKeyboardButton("B-", callback_data="request_B-")],
            [InlineKeyboardButton("AB+", callback_data="request_AB+"),
             InlineKeyboardButton("AB-", callback_data="request_AB-")],
            [InlineKeyboardButton("O+", callback_data="request_O+"),
             InlineKeyboardButton("O-", callback_data="request_O-")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = "🩸 Создание запроса на сдачу крови\n\nВыберите нужную группу крови:"
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup)
        return ENTERING_DONATION_REQUEST

    async def handle_blood_type_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы крови для запроса"""
        query = update.callback_query
        await query.answer()
        
        logger.info(f"Получен callback_data: {query.data}")
        
        if query.data == "back_to_menu":
            await self.show_doctor_menu(update, context)
            return DOCTOR_MENU
            
        if query.data.startswith('request_'):
            blood_type = query.data.replace('request_', '')
            context.user_data['request_blood_type'] = blood_type
            logger.info(f"Выбрана группа крови для запроса: {blood_type}")
            
            # Pre-fill info from MC if available
            mc = context.user_data.get('mc_info')
            if mc:
                context.user_data['request_location'] = mc.get('city')
                context.user_data['request_hospital'] = mc.get('name')
                context.user_data['request_address'] = mc.get('address')
                context.user_data['request_contact'] = mc.get('contact_info')
                
                await query.edit_message_text(
                    f"🩸 Группа крови: {blood_type}\n"
                    f"🏥 Центр: {mc.get('name')}\n"
                    f"📍 Адрес: {mc.get('address')}\n\n"
                    "📅 Введите дату, когда нужна кровь (в формате ДД.ММ.ГГГГ):\n"
                    "(Дата должна быть не раньше сегодняшней)"
                )
                return ENTERING_REQUEST_DATE
            
            await query.edit_message_text(
                f"✅ Выбрана группа крови: {blood_type}\n\n"
                "📍 Введите город, где нужна кровь:"
            )
            return ENTERING_REQUEST_LOCATION
            
        return ENTERING_DONATION_REQUEST

    async def handle_request_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода города для запроса"""
        location = update.message.text
        context.user_data['request_location'] = location

        logger.info(f"Указан город для запроса: {location}")

        await update.message.reply_text(
            "✅ Город указан!\n\n"
            "Теперь введите полный адрес медицинского учреждения:"
        )
        return ENTERING_REQUEST_ADDRESS

    async def handle_request_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода адреса учреждения"""
        address = update.message.text
        context.user_data['request_address'] = address

        logger.info(f"Указан адрес учреждения: {address}")

        await update.message.reply_text(
            "✅ Адрес учреждения сохранен!\n\n"
            "🏥 Теперь укажите название медицинского центра/больницы:"
        )
        return ENTERING_REQUEST_HOSPITAL

    async def handle_request_hospital(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода названия медицинского центра"""
        hospital_name = update.message.text
        context.user_data['request_hospital'] = hospital_name

        logger.info(f"Указано название медицинского центра: {hospital_name}")

        await update.message.reply_text(
            "✅ Название медицинского центра сохранено!\n\n"
            "📞 Укажите контактную информацию для доноров\n"
            "(телефон, email, ФИО ответственного):"
        )
        return ENTERING_REQUEST_CONTACT

    async def handle_request_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода контактной информации"""
        contact_info = update.message.text
        context.user_data['request_contact'] = contact_info

        logger.info(f"Указана контактная информация: {contact_info}")

        await update.message.reply_text(
            "✅ Контактная информация сохранена!\n\n"
            "📅 Укажите дату, когда нужна кровь (ДД.ММ.ГГГГ):"
        )
        return ENTERING_REQUEST_DATE

    async def handle_request_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода даты для запроса"""
        try:
            request_date = datetime.strptime(update.message.text, '%d.%m.%Y').date()
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ\n"
                "Попробуйте еще раз:"
            )
            return ENTERING_REQUEST_DATE

        # Сохраняем запрос в базу данных
        user = update.effective_user
        logger.info(
            f"Сохранение запроса в БД: врач {user.id}, группа {context.user_data['request_blood_type']}, "
            f"город {context.user_data['request_location']}, адрес {context.user_data['request_address']}, "
            f"медцентр {context.user_data['request_hospital']}, контакты {context.user_data['request_contact']}, "
            f"дата {request_date}")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO donation_requests (doctor_id, blood_type, location, address, hospital_name, contact_info, request_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user.id, context.user_data['request_blood_type'],
                  context.user_data['request_location'], context.user_data['request_address'],
                  context.user_data['request_hospital'], context.user_data['request_contact'], request_date))

            # Получаем ID созданного запроса
            request_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"✅ Запрос успешно сохранен в БД с ID {request_id}")

            # Отправляем уведомления всем подходящим донорам
            await self.notify_donors(
                context.user_data['request_blood_type'],
                context.user_data['request_location'],
                context.user_data['request_address'],
                context.user_data['request_hospital'],
                context.user_data['request_contact'],
                request_date,
                request_id
            )

            await update.message.reply_text(
                f"✅ Запрос создан!\n\n"
                f"🩸 Группа крови: {context.user_data['request_blood_type']}\n"
                f"📍 Город: {context.user_data['request_location']}\n"
                f"🏥 Медцентр: {context.user_data['request_hospital']}\n"
                f"📍 Адрес: {context.user_data['request_address']}\n"
                f"📞 Контакты: {context.user_data['request_contact']}\n"
                f"📅 Дата: {request_date.strftime('%d.%m.%Y')}\n\n"
                f"Уведомления отправлены всем подходящим донорам."
            )

            await self.show_doctor_menu(update, context)
            return DOCTOR_MENU
        except Exception as e:
            logger.error(f"Ошибка сохранения запроса в БД: {e}")
            await update.message.reply_text("Произошла ошибка при создании запроса. Попробуйте позже.")
            return DOCTOR_MENU

    async def process_update_blood_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обновления группы крови"""
        query = update.callback_query
        await query.answer()

        if query.data == "back_to_menu":
            await self.show_user_menu(update, context)
            return USER_MENU

        if query.data.startswith('blood_'):
            blood_type = query.data.replace('blood_', '')
            user = update.effective_user
            
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE users 
                    SET blood_type = %s 
                    WHERE telegram_id = %s
                """, (blood_type, user.id))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                await query.edit_message_text(f"✅ Группа крови успешно обновлена на {blood_type}!")
                await self.show_user_menu(update, context)
                return USER_MENU
            except Exception as e:
                logger.error(f"Ошибка обновления группы крови: {e}")
                await query.edit_message_text("Произошла ошибка при обновлении группы крови.")
                return USER_MENU
        
        return UPDATE_BLOOD_TYPE

    async def show_relevant_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает входящие (релевантные) запросы для донора"""
        user = update.effective_user
        items_per_page = 5
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get user info for filters
            cursor.execute("SELECT blood_type, city, latitude, longitude FROM users WHERE telegram_id = %s", (user.id,))
            donor_info = cursor.fetchone()
            
            if not donor_info or not donor_info['blood_type']:
                await update.callback_query.edit_message_text("❌ Сначала заполните информацию о себе (группа крови).")
                cursor.close()
                conn.close()
                return USER_MENU

            # Fetch active requests matching blood type
            # We fetch more than needed to filter by radius in python if needed, 
            # or we can try to filter by city in SQL. 
            # Let's fetch all matching blood type and future date, then filter/paginate.
            
            cursor.execute("""
                SELECT dr.id, dr.blood_type, dr.location, dr.address, dr.hospital_name, 
                       dr.contact_info, dr.request_date, mc.latitude, mc.longitude
                FROM donation_requests dr
                LEFT JOIN medical_centers mc ON dr.medical_center_id = mc.id
                WHERE dr.blood_type = %s 
                AND dr.request_date >= CURRENT_DATE
                ORDER BY dr.request_date ASC
            """, (donor_info['blood_type'],))
            
            all_requests = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Filter by radius if coordinates exist
            filtered_requests = []
            donor_lat = donor_info['latitude']
            donor_lon = donor_info['longitude']
            
            for req in all_requests:
                # Distance check (50km)
                if donor_lat and req['latitude']:
                     dist = self.calculate_distance(donor_lat, donor_lon, req['latitude'], req['longitude'])
                     if dist <= 50:
                         req['distance'] = dist
                         filtered_requests.append(req)
                elif donor_info['city'] and req['location'] and donor_info['city'].lower() in req['location'].lower():
                     # Fallback to city match
                     req['distance'] = None
                     filtered_requests.append(req)
                elif not donor_info['city'] and not donor_lat:
                     # No location info from donor? Show all matching blood type? 
                     # Or maybe ask to set location. Let's show all for now but mark as "Distance unknown"
                     req['distance'] = None
                     filtered_requests.append(req)

            # Pagination
            total_items = len(filtered_requests)
            start_index = page * items_per_page
            end_index = start_index + items_per_page
            current_page_items = filtered_requests[start_index:end_index]
            
            if not current_page_items:
                if page == 0:
                    text = "📭 Сейчас нет активных запросов для вашей группы крови поблизости."
                    keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
                    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    return USER_MENU
                else:
                    # Should not happen if logic is correct, but safe fallback
                    await self.show_relevant_requests(update, context, page=0)
                    return USER_MENU

            text = f"🔔 **Входящие запросы** (Стр. {page + 1})\n\n"
            
            keyboard = []
            
            for req in current_page_items:
                dist_str = f" (~{req['distance']:.1f} км)" if req.get('distance') is not None else ""
                text += f"🩸 **{req['blood_type']}** | 🏥 {req['hospital_name']}\n"
                text += f"📍 {req['location']}, {req['address']}{dist_str}\n"
                text += f"📅 {req['request_date'].strftime('%d.%m.%Y')}\n"
                text += f"📞 {req['contact_info']}\n\n"
                
                # Button to respond to specific request
                keyboard.append([InlineKeyboardButton(f"✅ Откликнуться: {req['hospital_name']}", callback_data=f"respond_{req['id']}")])

            # Nav buttons
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"rel_req_page_{page-1}"))
            if end_index < total_items:
                nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"rel_req_page_{page+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
                
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
            
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return USER_MENU

        except Exception as e:
            logger.error(f"Ошибка при показе релевантных запросов: {e}")
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            await update.callback_query.edit_message_text("Произошла ошибка при загрузке запросов.", reply_markup=InlineKeyboardMarkup(keyboard))
            return USER_MENU

    async def show_my_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает запросы врача с пагинацией"""
        user = update.effective_user
        items_per_page = 5
        offset = page * items_per_page
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Count total
            cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE doctor_id = %s", (user.id,))
            total_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT dr.id, dr.doctor_id, dr.blood_type, dr.location, 
                       COALESCE(dr.hospital_name, 'Не указано') as hospital_name,
                       COALESCE(dr.address, 'Адрес не указан') as address,
                       COALESCE(dr.contact_info, 'Не указано') as contact_info,
                       dr.request_date, dr.description, dr.created_at,
                       COUNT(resp.id) as response_count
                FROM donation_requests dr
                LEFT JOIN donor_responses resp ON dr.id = resp.request_id
                WHERE dr.doctor_id = %s 
                GROUP BY dr.id, dr.doctor_id, dr.blood_type, dr.location, 
                         dr.hospital_name, dr.address, dr.contact_info,
                         dr.request_date, dr.description, dr.created_at
                ORDER BY dr.created_at DESC 
                LIMIT %s OFFSET %s
            """, (user.id, items_per_page, offset))

            requests = cursor.fetchall()
            cursor.close()
            conn.close()

            if requests:
                text = f"📋 **Ваши запросы** (Стр. {page + 1})\n\n"
                for i, req in enumerate(requests, 1):
                    response_text = f"📊 Откликов: {req['response_count']}"
                    
                    text += f"{i}. 🩸 {req['blood_type']} | 📍 {req['location']} | {response_text}\n"
                    text += f"🏥 {req['hospital_name']}\n"
                    text += f"📍 {req['address']}\n"
                    text += f"📞 {req['contact_info']}\n"
                    text += f"📅 {req['request_date'].strftime('%d.%m.%Y')} | 🕒 {req['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
                
                keyboard = []
                nav_row = []
                if page > 0:
                    nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"my_req_page_{page-1}"))
                if (offset + items_per_page) < total_count:
                    nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"my_req_page_{page+1}"))
                
                if nav_row:
                    keyboard.append(nav_row)
                
                keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                text = "У вас пока нет созданных запросов."
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        except Exception as e:
            logger.error(f"Ошибка показа запросов врача: {e}")
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            await update.callback_query.edit_message_text("Произошла ошибка при загрузке запросов.", reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_donor_responses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает отклики доноров на запросы врача"""
        user = update.effective_user
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT dr.blood_type, dr.hospital_name, dr.location, dr.request_date,
                       u.first_name, u.last_name, u.username, u.blood_type as donor_blood_type,
                       u.location as donor_location, resp.responded_at, dr.id as request_id
                FROM donor_responses resp
                JOIN donation_requests dr ON resp.request_id = dr.id
                JOIN users u ON resp.donor_id = u.telegram_id
                WHERE dr.doctor_id = %s
                ORDER BY resp.responded_at DESC
                LIMIT 20
            """, (user.id,))

            responses = cursor.fetchall()

            if responses:
                text = "👥 Отклики доноров на ваши запросы:\n\n"
                
                # Группируем по запросам
                requests_dict = {}
                for resp in responses:
                    req_id = resp['request_id']
                    if req_id not in requests_dict:
                        requests_dict[req_id] = {
                            'info': resp,
                            'donors': []
                        }
                    requests_dict[req_id]['donors'].append(resp)
                
                for i, (req_id, req_data) in enumerate(requests_dict.items(), 1):
                    req_info = req_data['info']
                    donors = req_data['donors']
                    
                    text += f"{i}. 🩸 {req_info['blood_type']} | 📅 {req_info['request_date'].strftime('%d.%m.%Y')}\n"
                    text += f"🏥 {req_info['hospital_name']} | 📍 {req_info['location']}\n"
                    text += f"👥 Откликнулось доноров: {len(donors)}\n\n"
                    
                    for j, donor in enumerate(donors, 1):
                        donor_name = donor['first_name']
                        if donor['last_name']:
                            donor_name += f" {donor['last_name']}"
                        
                        username = f"@{donor['username']}" if donor['username'] else "нет username"
                        
                        text += f"  {j}. {donor_name} ({username})\n"
                        text += f"     🩸 {donor['donor_blood_type']} | 📍 {donor['donor_location']}\n"
                        text += f"     🕒 {donor['responded_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
                    
                    if i >= 5:  # Показываем максимум 5 запросов
                        text += "...\n"
                        break
                        
            else:
                text = "Пока нет откликов на ваши запросы.\n\nКогда доноры начнут откликаться, информация появится здесь."

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка показа откликов доноров: {e}")
            await update.callback_query.edit_message_text("Произошла ошибка при загрузке откликов.")

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику для врача"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Общее количество доноров
            cursor.execute("SELECT COUNT(*) AS total_donors FROM users WHERE role = 'user' AND is_registered = TRUE")
            total_donors = cursor.fetchone()['total_donors']

            # Количество доноров по группам крови
            cursor.execute("""
                SELECT blood_type, COUNT(*) AS count 
                FROM users 
                WHERE role = 'user' AND is_registered = TRUE
                GROUP BY blood_type
                ORDER BY blood_type
            """)
            blood_type_stats = cursor.fetchall()

            # Количество доноров, которые могут сдавать кровь
            cursor.execute("""
                SELECT COUNT(*) AS can_donate_count
                FROM users
                WHERE role = 'user' 
                  AND is_registered = TRUE
                  AND (last_donation_date IS NULL OR last_donation_date <= %s)
            """, (datetime.now().date() - timedelta(days=60),))
            can_donate_count = cursor.fetchone()['can_donate_count']

            # Формируем текст статистики
            stats_text = f"📊 Статистика системы:\n\n"
            stats_text += f"👥 Всего доноров: {total_donors}\n"
            stats_text += f"🩸 Доноры, готовые сдать кровь: {can_donate_count}\n\n"
            stats_text += "📈 Распределение по группам крови:\n"

            for stat in blood_type_stats:
                stats_text += f"• {stat['blood_type']}: {stat['count']} чел.\n"

            stats_text += "\n📋 Последние 5 запросов крови:\n"

            # Последние 5 запросов с количеством откликов
            cursor.execute("""
                SELECT dr.blood_type, dr.location, 
                       COALESCE(dr.hospital_name, 'Не указано') as hospital_name,
                       COALESCE(dr.address, 'Адрес не указан') as address, 
                       dr.request_date,
                       COUNT(resp.id) as response_count
                FROM donation_requests dr
                LEFT JOIN donor_responses resp ON dr.id = resp.request_id
                GROUP BY dr.id, dr.blood_type, dr.location, dr.hospital_name, dr.address, dr.request_date, dr.created_at
                ORDER BY dr.created_at DESC 
                LIMIT 5
            """)
            recent_requests = cursor.fetchall()

            if recent_requests:
                for i, req in enumerate(recent_requests, 1):
                    stats_text += (f"\n{i}. 🩸 {req['blood_type']} | 📍 {req['location']} | 📊 {req['response_count']} откл.\n"
                                   f"🏥 {req['hospital_name']}\n"
                                   f"📍 {req['address']}\n"
                                   f"📅 {req['request_date'].strftime('%d.%m.%Y')}")
            else:
                stats_text += "\nПока нет запросов крови."

            # Добавляем общую статистику по откликам
            cursor.execute("""
                SELECT COUNT(*) as total_responses
                FROM donor_responses
            """)
            total_responses_result = cursor.fetchone()
            total_responses = total_responses_result['total_responses'] if total_responses_result else 0

            stats_text += f"\n\n📊 Общая статистика откликов: {total_responses}"

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(stats_text, reply_markup=reply_markup)

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка показа статистики: {e}")
            await update.callback_query.edit_message_text("Произошла ошибка при загрузке статистики.")

    async def notify_donors(self, blood_type: str, location: str, address: str, hospital_name: str, contact_info: str, request_date, request_id: int):
        """Отправляет уведомления донорам"""
        logger.info(f"Отправка уведомлений донорам группы {blood_type} в {location} ({hospital_name})")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Находим всех подходящих доноров
            cursor.execute("""
                SELECT telegram_id, first_name, last_donation_date, location 
                FROM users 
                WHERE blood_type = %s AND role = 'user' AND is_registered = TRUE
            """, (blood_type,))

            donors = cursor.fetchall()
            logger.info(f"Найдено {len(donors)} доноров группы {blood_type}")

            sent_count = 0
            for donor in donors:
                # Проверяем, может ли донор сдавать кровь
                can_donate = True
                if donor['last_donation_date']:
                    days_since = (datetime.now().date() - donor['last_donation_date']).days
                    can_donate = days_since >= 60

                if can_donate:
                    message = f"""
🆘 СРОЧНО НУЖНА КРОВЬ!

🩸 Группа крови: {blood_type}
📍 Город: {location}
🏥 Медицинский центр: {hospital_name}
📍 Адрес: {address}
📅 Дата: {request_date.strftime('%d.%m.%Y')}
📞 Контакты: {contact_info}

Если вы готовы сдать кровь, нажмите кнопку ниже, чтобы откликнуться.
                    """
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ Я готов сдать!", callback_data=f"respond_{request_id}")],
                        [InlineKeyboardButton("❌ Не могу", callback_data="ignore_request")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await self.application.bot.send_message(
                            chat_id=donor['telegram_id'],
                            text=message,
                            reply_markup=reply_markup
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Не удалось отправить сообщение донору {donor['telegram_id']}: {e}")
                        logger.error(f"Ошибка отправки уведомления донору {donor['telegram_id']}: {e}")

            logger.info(f"Отправлено {sent_count} уведомлений из {len(donors)} возможных доноров")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {e}")

    async def handle_donor_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка отклика донора на запрос крови"""
        query = update.callback_query
        await query.answer()
        
        # Извлекаем ID запроса из callback_data
        request_id = int(query.data.replace("respond_", ""))
        donor_id = update.effective_user.id
        
        logger.info(f"Донор {donor_id} откликается на запрос {request_id}")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Fetch request info (date) and donor info (last donation) to check 60-day rule
            cursor.execute("SELECT request_date FROM donation_requests WHERE id = %s", (request_id,))
            req = cursor.fetchone()
            if not req:
                 await query.edit_message_text("❌ Запрос не найден.")
                 cursor.close()
                 conn.close()
                 return
            request_date = req['request_date']

            cursor.execute("SELECT last_donation_date FROM users WHERE telegram_id = %s", (donor_id,))
            donor_data = cursor.fetchone()
            
            if donor_data and donor_data['last_donation_date']:
                min_allowed_date = donor_data['last_donation_date'] + timedelta(days=60)
                if request_date < min_allowed_date:
                     days_left = (min_allowed_date - request_date).days
                     await query.answer(f"⛔ Дата запроса слишком ранняя! Вам нужно ждать до {min_allowed_date.strftime('%d.%m.%Y')}.", show_alert=True)
                     cursor.close()
                     conn.close()
                     return

            # Проверяем, не откликался ли донор уже на этот запрос
            cursor.execute("""
                SELECT id FROM donor_responses 
                WHERE request_id = %s AND donor_id = %s
            """, (request_id, donor_id))
            
            if cursor.fetchone():
                await query.edit_message_text(
                    "ℹ️ Вы уже откликались на этот запрос.\n\n"
                    "Спасибо за вашу готовность помочь! ❤️"
                )
                cursor.close()
                conn.close()
                return
            
            # Сохраняем отклик в базу данных
            cursor.execute("""
                INSERT INTO donor_responses (request_id, donor_id, response_type)
                VALUES (%s, %s, 'interested')
            """, (request_id, donor_id))
            
            # Получаем информацию о запросе и доноре
            cursor.execute("""
                SELECT dr.doctor_id, dr.blood_type, dr.hospital_name, dr.location, dr.request_date,
                       dr.address, dr.contact_info,
                       u.first_name, u.last_name, u.username
                FROM donation_requests dr
                JOIN users u ON dr.doctor_id = u.telegram_id
                WHERE dr.id = %s
            """, (request_id,))
            
            request_info = cursor.fetchone()
            
            # Получаем информацию о доноре
            cursor.execute("""
                SELECT first_name, last_name, username, blood_type, location
                FROM users WHERE telegram_id = %s
            """, (donor_id,))
            
            donor_info = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Убираем кнопку отклика и показываем подтверждение
            await query.edit_message_text(
                query.message.text + "\n\n✅ ВЫ ОТКЛИКНУЛИСЬ НА ЭТОТ ЗАПРОС!"
            )

            # Отправляем подробную информацию о предстоящей донации
            donation_info = f"""
🎯 ЗАПЛАНИРОВАННАЯ ДОНАЦИЯ

🩸 Группа крови: {request_info['blood_type']}
📅 Дата: {request_info['request_date'].strftime('%d.%m.%Y')}

🏥 Медицинский центр: {request_info['hospital_name'] or 'Не указано'}
📍 Адрес: {request_info['address'] or 'Не указан'}

📞 Контактная информация:
{request_info['contact_info'] or 'Не указано'}

❗ ВАЖНО:
• Не забудьте покушать за 2-3 часа до сдачи
• Выспитесь накануне
• Возьмите с собой документы
• Приходите вовремя

Удачи! Ваш вклад спасет жизни! ❤️
            """

            # Отправляем и закрепляем сообщение
            pinned_msg = await self.application.bot.send_message(
                chat_id=donor_id,
                text=donation_info
            )
            
            try:
                await self.application.bot.pin_chat_message(
                    chat_id=donor_id,
                    message_id=pinned_msg.message_id,
                    disable_notification=True
                )
                logger.info(f"Сообщение о донации закреплено для донора {donor_id}")
            except Exception as pin_error:
                logger.error(f"Не удалось закрепить сообщение: {pin_error}")
                # В личных чатах закрепление может не работать, это нормально
            
            # Уведомляем врача о новом отклике
            if request_info and donor_info:
                await self.notify_doctor_about_response(
                    request_info['doctor_id'], 
                    request_info, 
                    donor_info,
                    request_id
                )
            
            logger.info(f"✅ Отклик донора {donor_id} на запрос {request_id} успешно сохранен")
            
        except Exception as e:
            logger.error(f"Ошибка обработки отклика донора: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при обработке отклика. Попробуйте позже."
            )

    async def notify_doctor_about_response(self, doctor_id: int, request_info, donor_info, request_id: int):
        """Уведомляет врача о новом отклике донора"""
        try:
            # Подсчитываем общее количество откликов на этот запрос
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM donor_responses WHERE request_id = %s
            """, (request_id,))
            total_responses = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            donor_name = donor_info['first_name']
            if donor_info['last_name']:
                donor_name += f" {donor_info['last_name']}"
            
            donor_username = f"@{donor_info['username']}" if donor_info['username'] else "нет username"
            
            message = f"""
🎉 НОВЫЙ ОТКЛИК ДОНОРА!

👤 Донор: {donor_name} ({donor_username})
🩸 Группа крови: {donor_info['blood_type']}
📍 Местоположение донора: {donor_info['location']}

📋 Ваш запрос:
🩸 Группа крови: {request_info['blood_type']}
🏥 {request_info['hospital_name']}
📍 {request_info['location']}
📅 {request_info['request_date'].strftime('%d.%m.%Y')}

📊 Всего откликов на этот запрос: {total_responses}

Свяжитесь с донором для координации сдачи крови.
            """
            
            await self.application.bot.send_message(
                chat_id=doctor_id,
                text=message
            )
            
            logger.info(f"Уведомление о новом отклике отправлено врачу {doctor_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления врачу: {e}")

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает справку"""
        help_text = """
❓ Справка по BloodDonorBot

👤 Для доноров:
• Регистрируйтесь с указанием группы крови и местоположения
• Получайте уведомления о необходимости сдачи крови
• Обновляйте информацию о последней сдаче крови

👨‍⚕️ Для врачей:
• Создавайте запросы на сдачу крови
• Указывайте нужную группу крови, город и адрес учреждения
• Просматривайте статистику по системе

📋 Правила сдачи крови:
• Минимальный интервал между сдачами: 60 дней
• Следуйте рекомендациям врачей
• Поддерживайте здоровый образ жизни

🔙 Для возврата в меню нажмите кнопку "Назад"
        """

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup)

    # --- EDIT MC INFO ---
    async def show_edit_mc_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mc_id = context.user_data.get('mc_id')
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT name, address, city, contact_info FROM medical_centers WHERE id = %s", (mc_id,))
        mc = cursor.fetchone()
        cursor.close()
        conn.close()
        
        msg = f"🏥 **Редактирование Медицинского Центра**\n\n"
        msg += f"Название: {mc['name']}\n"
        msg += f"Адрес: {mc['address']}\n"
        msg += f"Город: {mc['city']}\n"
        msg += f"Контакты: {mc['contact_info'] or 'Не указано'}\n\n"
        msg += "Выберите, что хотите изменить (пока только контакты и адрес):"
        
        keyboard = [
             [InlineKeyboardButton("📝 Изменить адрес", callback_data="edit_mc_address")],
             [InlineKeyboardButton("📞 Изменить контакты", callback_data="edit_mc_contact")],
             [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MC_EDIT_INFO

    async def handle_edit_mc_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "back_to_menu":
            await self.show_doctor_menu(update, context)
            return MC_MENU
            
        if data == "edit_mc_address":
            await query.edit_message_text("📍 Введите новый адрес медицинского центра:")
            context.user_data['edit_mc_field'] = 'address'
            return MC_EDIT_INPUT
            
        if data == "edit_mc_contact":
            await query.edit_message_text("📞 Введите новую контактную информацию (телефон, время работы):")
            context.user_data['edit_mc_field'] = 'contact_info'
            return MC_EDIT_INPUT
            
        return MC_EDIT_INFO

    async def process_mc_edit_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_value = update.message.text
        field = context.user_data.get('edit_mc_field')
        mc_id = context.user_data.get('mc_id')
        
        if field and mc_id:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            query = f"UPDATE medical_centers SET {field} = %s WHERE id = %s"
            cursor.execute(query, (new_value, mc_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            await update.message.reply_text("✅ Информация обновлена!")
            # Update session info
            if 'mc_info' in context.user_data:
                context.user_data['mc_info'][field] = new_value
            
            await self.show_edit_mc_menu(update, context)
            return MC_EDIT_INFO
            
        await update.message.reply_text("❌ Ошибка обновления.")
        return MC_MENU

    async def broadcast_need(self, mc_id, blood_type):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get MC info
            cursor.execute("SELECT name, city FROM medical_centers WHERE id = %s", (mc_id,))
            mc = cursor.fetchone()
            
            # Find users
            cursor.execute("""
                SELECT telegram_id, first_name 
                FROM users 
                WHERE role = 'user' 
                AND blood_type = %s 
                AND (city = %s OR location ILIKE %s)
                AND (last_donation_date IS NULL OR last_donation_date < CURRENT_DATE - INTERVAL '60 days')
            """, (blood_type, mc['city'], f"%{mc['city']}%"))
            
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            
            count = 0
            for user in users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=f"🚨 **СРОЧНО НУЖНА КРОВЬ!**\n\n"
                             f"Центр: {mc['name']} ({mc['city']})\n"
                             f"Группа: {blood_type}\n\n"
                             f"Пожалуйста, если вы можете сдать кровь, откликнитесь через меню 'Хочу сдать кровь'!",
                        parse_mode='Markdown'
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {user['telegram_id']}: {e}")
            
            logger.info(f"Broadcast sent to {count} donors")
            return count
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return 0

    def run(self):
        """Запуск бота"""
        # Создаем приложение
        token = os.getenv('TELEGRAM_TOKEN')
        if not token:
            logger.error("Токен Telegram не найден! Убедитесь, что он указан в .env файле.")
            return

        self.application = Application.builder().token(token).build()

        # Создаем ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                CHOOSING_ROLE: [CallbackQueryHandler(self.choose_role)],
                ENTERING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_password)],
                ENTERING_BLOOD_TYPE: [
                    CallbackQueryHandler(self.handle_blood_type),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_blood_type)
                ],
                ENTERING_LOCATION: [
                    MessageHandler(filters.LOCATION, self.handle_location),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_location)
                ],
                ENTERING_LAST_DONATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_last_donation)],
                ENTERING_DONATION_REQUEST: [CallbackQueryHandler(self.handle_blood_type_request)],
                ENTERING_REQUEST_LOCATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_request_location)],
                ENTERING_REQUEST_ADDRESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_request_address)],
                ENTERING_REQUEST_HOSPITAL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_request_hospital)],
                ENTERING_REQUEST_CONTACT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_request_contact)],
                ENTERING_REQUEST_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_request_date)],
                USER_MENU: [CallbackQueryHandler(self.handle_menu_callback)],
                DOCTOR_MENU: [CallbackQueryHandler(self.handle_menu_callback)],
                MC_MENU: [CallbackQueryHandler(self.handle_menu_callback)],
                MC_AUTH_MENU: [CallbackQueryHandler(self.handle_mc_auth_choice)],
                MC_REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_name)],
                MC_REGISTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_address)],
                MC_REGISTER_CITY: [
                    MessageHandler(filters.LOCATION, self.process_mc_city),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_city)
                ],
                MC_REGISTER_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_reg_login)],
                MC_REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_reg_password)],
                MC_LOGIN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_login_input)],
                MC_LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_login_password)],
                MC_EDIT_INFO: [CallbackQueryHandler(self.handle_edit_mc_choice)],
                MC_EDIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_mc_edit_input)],
                MANAGE_BLOOD_NEEDS: [CallbackQueryHandler(self.handle_traffic_light_action)],
                DONOR_SEARCH_MC: [CallbackQueryHandler(self.handle_donation_search_action)],
                DONOR_CERT_UPLOAD: [
                     CallbackQueryHandler(self.handle_cert_menu_callback),
                     MessageHandler(filters.PHOTO, self.process_cert_upload)
                ],
                UPDATE_LOCATION: [
                    MessageHandler(filters.LOCATION, self.update_location),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_location)
                ],
                UPDATE_DONATION_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_donation_date)],
                UPDATE_BLOOD_TYPE: [CallbackQueryHandler(self.process_update_blood_type)]
            },
            fallbacks=[CommandHandler('start', self.start)]
        )

        self.application.add_handler(conv_handler)

        logger.info("Бот запущен")
        # Запускаем бота
        self.application.run_polling()


if __name__ == '__main__':
    bot = BloodDonorBot()
    bot.run()