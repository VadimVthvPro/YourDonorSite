# 🔧 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ ВСЕХ ПРОБЛЕМ

## ✅ ЧТО СДЕЛАНО

1. ✅ Обновлён `create_database.sql` со всеми недостающими колонками
2. ✅ Создан `.gitignore` для защиты `.env` от загрузки в Git
3. ✅ Создан `server_fix.sh` - скрипт для исправления БД на сервере
4. ✅ Создан `deploy_to_server.sh` - скрипт для безопасного развёртывания
5. ✅ Очищены `env_example.txt` от реальных паролей

---

## 🚀 БЫСТРОЕ РЕШЕНИЕ (СНАЧАЛА ВЫПОЛНИТЕ ЭТО)

### Вариант 1: Автоматическое исправление БД

На **ВАШЕМ Mac** выполните:

```bash
cd /Users/VadimVthv/Your_donor
ssh root@178.172.212.221 "bash -s" < server_fix.sh
```

Скрипт автоматически:
- ✅ Создаст backup БД
- ✅ Добавит все недостающие колонки
- ✅ Защитит .env файл
- ✅ Перезапустит сервисы
- ✅ Проверит работоспособность

### Вариант 2: Ручное исправление БД

Если автоматический скрипт не работает, выполните на **СЕРВЕРЕ**:

```bash
ssh root@178.172.212.221
```

Затем выполните команды по очереди:

```bash
# 1. Backup БД
cd /opt/tvoydonor
mkdir -p backups
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
pg_dump -U donor_user -h localhost your_donor > backups/backup-$(date +%Y%m%d-%H%M%S).sql

# 2. Добавление недостающих таблиц и колонок
psql -U donor_user -h localhost your_donor << 'SQL'

-- Таблица диалогов (нужна для messages.conversation_id)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    subject VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, medical_center_id)
);

CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_mc ON conversations(medical_center_id);

-- Добавляем колонки в messages
ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_msg_conversation ON messages(conversation_id);

-- Таблица chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER,
    sender_role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_conv ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_sender ON chat_messages(sender_id);

-- Таблица шаблонов сообщений
CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_mc ON message_templates(medical_center_id);

-- Таблица истории донаций
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    donation_date DATE NOT NULL,
    blood_center_id INTEGER REFERENCES medical_centers(id),
    donation_type VARCHAR(50),
    volume_ml INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donation_history_user ON donation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);

SELECT 'Миграция завершена успешно!' as status;
SQL

# 3. Защита .env файла
if ! grep -q "^\.env$" /opt/tvoydonor/.gitignore 2>/dev/null; then
    echo ".env" >> /opt/tvoydonor/.gitignore
    echo "website/backend/.env" >> /opt/tvoydonor/.gitignore
fi

# 4. Перезапуск сервисов
supervisorctl restart all
sleep 2
supervisorctl status

# 5. Проверка API
curl -s http://localhost:5001/api/regions | head -c 200
```

---

## 📤 ЗАГРУЗКА ОБНОВЛЕНИЙ НА СЕРВЕР (В БУДУЩЕМ)

Когда вы изменили код локально и хотите загрузить на сервер:

### Способ 1: Автоматический (РЕКОМЕНДУЕТСЯ)

```bash
cd /Users/VadimVthv/Your_donor
./deploy_to_server.sh
```

Скрипт автоматически:
- 📦 Создаст backup текущей версии на сервере
- 💾 Сохранит .env файл
- 📤 Загрузит новые файлы
- 🔐 Восстановит .env файл
- ♻️  Перезапустит сервисы
- ✅ Проверит работоспособность

### Способ 2: Ручной

```bash
cd /Users/VadimVthv/Your_donor

# 1. Архивируем без лишнего
tar --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='backups' \
    --exclude='.git' \
    -czf /tmp/deploy.tar.gz website/

# 2. Загружаем на сервер
scp /tmp/deploy.tar.gz root@178.172.212.221:/tmp/

# 3. На сервере распаковываем
ssh root@178.172.212.221
cd /opt/tvoydonor
cp website/backend/.env /tmp/.env.backup  # ВАЖНО: сохранить .env!
tar -xzf /tmp/deploy.tar.gz
cp /tmp/.env.backup website/backend/.env  # Восстанавливаем .env
supervisorctl restart all
```

---

## 🔐 НАСТРОЙКА .ENV НА СЕРВЕРЕ

Если .env слетел, создайте его заново:

```bash
ssh root@178.172.212.221
cat > /opt/tvoydonor/website/backend/.env << 'EOF'
# ============================================
# БАЗА ДАННЫХ PostgreSQL
# ============================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_donor
DB_USER=donor_user
DB_PASSWORD=u1oFnZALhyfpbtir08nH

# ============================================
# БЕЗОПАСНОСТЬ
# ============================================
SECRET_KEY=bbaa349e397590f4fb8d5dc41d36f523166f0ca6f09ab40ec3e94a58e4506810
MASTER_PASSWORD=doctor2024

# ============================================
# TELEGRAM BOT
# ============================================
TELEGRAM_BOT_TOKEN=8212814214:AAG29mEQN2EWS1wFvKbDqC8nr6SgN3_VeZ8

# ============================================
# СУПЕР АДМИНИСТРАТОР
# ============================================
SUPER_ADMIN_TELEGRAM_USERNAME=vadimvthv

# ============================================
# URLs и ДОМЕНЫ
# ============================================
WEBSITE_URL=https://tvoydonor.by
APP_URL=https://tvoydonor.by

# ============================================
# СЕРВЕР
# ============================================
FLASK_DEBUG=false
PORT=5001
EOF

chmod 600 /opt/tvoydonor/website/backend/.env
supervisorctl restart all
```

---

## 🧪 ПРОВЕРКА РАБОТОСПОСОБНОСТИ

### На сервере:

```bash
# Проверка API
curl http://localhost:5001/api/regions

# Проверка через домен
curl https://tvoydonor.by/api/regions

# Проверка БД
PGPASSWORD='u1oFnZALhyfpbtir08nH' psql -U donor_user -h localhost your_donor -c "\dt"

# Статус сервисов
supervisorctl status

# Логи Flask
tail -30 /var/log/tvoydonor-api.err.log

# Логи Telegram bot
tail -30 /var/log/tvoydonor-bot.err.log
```

### В браузере:

1. Откройте https://tvoydonor.by
2. Зарегистрируйте донора
3. Войдите в дашборд
4. Проверьте все функции:
   - ✅ Загрузка профиля
   - ✅ Запросы крови
   - ✅ Мессенджер
   - ✅ Статистика
   - ✅ Запись на донацию

---

## 📋 ЧЕКЛИСТ

- [ ] Выполнил `server_fix.sh` ИЛИ ручную миграцию БД
- [ ] .env файл на сервере корректный и защищён
- [ ] Все сервисы в статусе RUNNING
- [ ] API отвечает через curl
- [ ] Сайт открывается в браузере
- [ ] Регистрация донора работает
- [ ] Дашборд загружается без ошибок 500
- [ ] Telegram бот отвечает

---

## 🆘 ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК

### Восстановление из backup:

```bash
ssh root@178.172.212.221
cd /opt/tvoydonor/backups

# Посмотреть доступные backup'ы
ls -lht

# Восстановить БД (замените имя файла!)
PGPASSWORD='u1oFnZALhyfpbtir08nH' psql -U donor_user -h localhost your_donor < backup-20260125-120000.sql
```

### Полный перезапуск:

```bash
supervisorctl stop all
pkill -f "python.*app.py"
pkill -f "python.*telegram_bot.py"
supervisorctl start all
supervisorctl status
```

---

## 📞 КОНТАКТЫ

Пароли для доступа:
- **Сервер SSH**: Vadamahjkl1!
- **БД на сервере**: u1oFnZALhyfpbtir08nH
- **БД локальная (старая)**: yourdonorishere

IP сервера: **178.172.212.221**
Домен: **tvoydonor.by**
