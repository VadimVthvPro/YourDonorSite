# Спецификация проекта "Твой Донор"

Краткая техническая спецификация платформы для координации доноров крови с медицинскими учреждениями.

## Основная информация

**Название:** Твой Донор  
**Тип:** Веб-платформа с Telegram интеграцией  
**Назначение:** Связь доноров крови с медицинскими центрами  
**Статус:** Готова к развертыванию  

---

## Архитектура

### Технологический стек

**Backend:**
- Flask 3.0.0 (Python REST API)
- PostgreSQL 12+ (СУБД)
- python-telegram-bot 20.7 (Telegram интеграция)

**Frontend:**
- Чистый JavaScript (ES6+)
- HTML5 + CSS3 (адаптивный дизайн)
- Без фреймворков

**Коммуникация:**
- REST API (JSON)
- Long Polling для мессенджера
- Telegram Bot API для уведомлений

### Структура системы

```
Пользователи (Браузер)
         ↓
    Frontend (HTML/CSS/JS)
         ↓
    Flask API (REST)
         ↓
    PostgreSQL (БД)
         ↑
    Telegram Bot API
         ↑
    Telegram (Мобильное приложение)
```

---

## Функциональные возможности

### Для доноров

1. Регистрация и аутентификация
2. Просмотр запросов крови (с фильтрацией)
3. Донорский светофор (индикация срочности)
4. Отклик на запросы с выбором даты
5. Планирование донации в любое время
6. Личный кабинет с профилем
7. История донаций и статистика
8. Встроенный мессенджер с медцентрами
9. Привязка Telegram для уведомлений

### Для медицинских центров

1. Регистрация через мастер-пароль
2. Создание запросов крови (обычные/срочные)
3. Управление донорским светофором
4. Просмотр и обработка откликов доноров
5. База данных зарегистрированных доноров
6. Встроенный мессенджер с донорами
7. Шаблоны сообщений
8. Массовая рассылка уведомлений
9. Статистика по донациям

### Автоматизация (Telegram бот)

- Уведомления о срочных запросах крови
- Подтверждение регистрации по коду
- Уведомления об одобрении/отклонении заявок
- Напоминания о запланированных донациях
- Новые сообщения от медцентров
- Команды: `/start`, `/help`, `/link`, `/status`, `/myid`

---

## База данных

### Основные таблицы

**users** - доноры
- id, telegram_id, full_name, email, phone
- blood_type, region, password_hash
- last_donation_date, total_donations, litres_donated
- created_at, updated_at

**medical_centers** - медицинские центры
- id, name, address, phone, email, region
- password_hash, telegram_id
- master_password_used, created_at, updated_at

**blood_requests** - запросы крови
- id, medical_center_id, blood_type
- description, needed_donors, urgency_level
- status, created_at, updated_at

**donation_responses** - отклики доноров
- id, request_id, user_id, medical_center_id
- status, response_date, hidden
- created_at, updated_at

**conversations** - диалоги
- id, donor_id, medical_center_id
- status, last_message_at, last_message_preview
- donor_unread_count, medcenter_unread_count
- created_at, updated_at

**messages** - сообщения
- id, conversation_id, sender_id, sender_role
- content, message_type, metadata
- is_read, deleted_at, created_at

**donation_history** - история донаций
- id, donor_id, medical_center_id
- donation_date, blood_type, amount_ml
- created_at

**telegram_verification_codes** - коды подтверждения
- id, user_id, code
- expires_at, is_used, created_at

**message_templates** - шаблоны сообщений
- id, medical_center_id, name, content
- type, variables, created_at, updated_at

---

## API Endpoints

### Аутентификация
- `POST /api/register` - регистрация донора
- `POST /api/login` - вход донора
- `POST /api/medcenter/register` - регистрация медцентра
- `POST /api/medcenter/login` - вход медцентра
- `POST /api/logout` - выход

### Донор
- `GET /api/donor/profile` - профиль донора
- `PUT /api/donor/profile` - обновление профиля
- `GET /api/blood-requests` - список запросов крови
- `POST /api/blood-requests/:id/respond` - откликнуться
- `GET /api/donor/responses` - мои отклики
- `POST /api/donor/schedule-donation` - запланировать донацию
- `GET /api/donor/donations` - история донаций

### Медцентр
- `GET /api/medcenter/profile` - профиль медцентра
- `PUT /api/medcenter/profile` - обновление профиля
- `GET /api/medical-center/blood-requests` - мои запросы
- `POST /api/medical-center/blood-requests` - создать запрос
- `PUT /api/blood-requests/:id` - обновить запрос
- `DELETE /api/blood-requests/:id` - удалить запрос
- `GET /api/medcenter/responses` - отклики на мои запросы
- `PUT /api/responses/:id` - обновить статус отклика
- `GET /api/medcenter/donors` - база доноров
- `GET /api/medcenter/statistics` - статистика

### Мессенджер
- `GET /api/messages/conversations` - список диалогов
- `GET /api/messages/conversations/:id` - один диалог
- `POST /api/messages/conversations` - создать диалог
- `GET /api/messages/conversations/:id/messages` - сообщения
- `POST /api/messages/conversations/:id/messages` - отправить сообщение
- `PUT /api/messages/messages/:id` - редактировать сообщение
- `DELETE /api/messages/messages/:id` - удалить сообщение
- `POST /api/messages/conversations/:id/read` - пометить прочитанным
- `GET /api/messages/updates` - Long Polling для обновлений

### Telegram
- `POST /api/telegram/generate-code` - создать код привязки
- `POST /api/telegram/verify-code` - проверить код
- `GET /api/telegram/status` - статус привязки
- `POST /api/telegram/unlink` - отвязать Telegram

### Шаблоны (для медцентра)
- `GET /api/messages/templates` - список шаблонов
- `POST /api/messages/templates` - создать шаблон
- `PUT /api/messages/templates/:id` - редактировать шаблон
- `DELETE /api/messages/templates/:id` - удалить шаблон
- `POST /api/messages/broadcast` - массовая рассылка

---

## Безопасность

### Аутентификация
- Токены сессий (случайные 32-байтовые строки)
- Хранение в localStorage на клиенте
- Срок действия: 30 дней
- Отдельные токены для доноров и медцентров

### Пароли
- Хеширование: bcrypt
- Минимальная длина: 6 символов
- Хранение только хеша

### База данных
- Параметризованные запросы (защита от SQL injection)
- Подключение через переменные окружения
- Отдельный пользователь БД с ограниченными правами

### API
- CORS настроен только для доверенных источников
- Валидация всех входных данных
- Проверка прав доступа для каждого запроса

### Секретные данные
- Все в .env файле
- .env в .gitignore
- Права доступа к .env: 600

---

## Конфигурация (.env)

Обязательные переменные:

```env
# База данных
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_donor
DB_USER=postgres
DB_PASSWORD=

# Безопасность
SECRET_KEY=
MASTER_PASSWORD=

# Telegram
TELEGRAM_BOT_TOKEN=

# URLs
WEBSITE_URL=
APP_URL=

# Сервер
FLASK_DEBUG=false
PORT=5001
```

Подробности в файле `ENV_SETUP_GUIDE.md`.

---

## Требования к серверу

**Минимальные:**
- CPU: 1 ядро
- RAM: 512 МБ
- Disk: 500 МБ
- OS: Linux/macOS/Windows

**Рекомендуемые:**
- CPU: 2+ ядра
- RAM: 2 ГБ
- Disk: 5 ГБ
- OS: Ubuntu 20.04+ / Debian 10+

**Сеть:**
- Порты: 5001 (API), 8080 (Frontend), 5432 (PostgreSQL)
- Исходящие: api.telegram.org:443
- Входящие: 80, 443 (HTTP/HTTPS)

Подробности в файле `REQUIREMENTS.md`.

---

## Развертывание

### Локальная разработка

```bash
# 1. Установить зависимости
pip install -r website/backend/requirements.txt

# 2. Создать БД
psql -U postgres -d your_donor -f website/backend/create_database.sql

# 3. Настроить .env
cp website/backend/env_example.txt website/backend/.env
# Заполнить значения

# 4. Запустить (3 терминала)
python3 website/backend/app.py
python3 website/backend/telegram_bot.py
python3 -m http.server 8080 --directory website
```

### Продакшен

Требуется:
- Домен с HTTPS (для Telegram WebApp)
- Nginx/Apache как reverse proxy
- systemd для автозапуска
- SSL сертификат (Let's Encrypt)

Подробная инструкция в файле `DEPLOYMENT.md`.

---

## Масштабируемость

**Текущая архитектура:**
- До 1000 одновременных пользователей
- До 10000 доноров
- До 100 медцентров
- До 1000 запросов/месяц

**Для больших нагрузок:**
- Кеширование (Redis)
- Балансировщик нагрузки
- Репликация PostgreSQL
- WebSocket вместо Long Polling
- Очередь задач (Celery)

---

## Документация

**Основные файлы:**
- `README.md` - общее описание и быстрый старт
- `REQUIREMENTS.md` - системные требования
- `INSTALLATION.md` - пошаговая установка
- `DEPLOYMENT.md` - развертывание на продакшен
- `ENV_SETUP_GUIDE.md` - настройка переменных окружения
- `DONATION_PREPARATION_RULES.md` - правила подготовки к донации

**Техническая документация:**
- `website/backend/create_database.sql` - схема БД с комментариями
- `website/backend/migrations/` - все миграции БД
- Комментарии в коде (Python, JavaScript)

---

## Лицензия

Проект создан в образовательных целях. При использовании в реальных медицинских условиях требуется консультация со специалистами здравоохранения.

---

## Контакты

Для вопросов по установке и использованию см. документацию:
- Установка: `INSTALLATION.md`
- Конфигурация: `ENV_SETUP_GUIDE.md`
- Развертывание: `DEPLOYMENT.md`
