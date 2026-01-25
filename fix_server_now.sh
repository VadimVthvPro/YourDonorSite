#!/bin/bash
# ПОЛНОЕ ИСПРАВЛЕНИЕ ВСЕХ ОШИБОК НА СЕРВЕРЕ
# Выполните: ssh root@178.172.212.221 (пароль: Vadamahjkl1!)
# Затем скопируйте и вставьте этот скрипт

set -e

export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔍 ШАГ 1: ДИАГНОСТИКА ПРОБЛЕМ"
echo "========================================="

echo ""
echo "📊 Статус сервисов:"
supervisorctl status

echo ""
echo "📋 Последние ошибки Flask API:"
tail -50 /var/log/tvoydonor-api.err.log | grep -A 5 "Error\|Traceback" || echo "Нет ошибок в логах"

echo ""
echo "🗄️ Проверка существующих таблиц:"
psql -U donor_user -h localhost your_donor -c "\dt" -t | awk '{print $1}' | sort

echo ""
echo "========================================="
echo "🛠️ ШАГ 2: СОЗДАНИЕ BACKUP"
echo "========================================="

cd /opt/tvoydonor
mkdir -p backups
timestamp=$(date +%Y%m%d-%H%M%S)
pg_dump -U donor_user -h localhost your_donor > backups/before-fix-${timestamp}.sql
echo "✅ Backup создан: backups/before-fix-${timestamp}.sql"

echo ""
echo "========================================="
echo "🔧 ШАГ 3: ИСПРАВЛЕНИЕ СТРУКТУРЫ БД"
echo "========================================="

# Создаём все недостающие таблицы и колонки
psql -U donor_user -h localhost your_donor << 'SQL'

-- ============================================
-- 1. ТАБЛИЦА CONVERSATIONS (ДИАЛОГИ)
-- ============================================
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

-- ============================================
-- 2. ОБНОВЛЕНИЕ ТАБЛИЦЫ MESSAGES
-- ============================================
ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id INTEGER;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;

-- Добавляем внешний ключ только если его нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'messages_conversation_id_fkey'
    ) THEN
        ALTER TABLE messages 
        ADD CONSTRAINT messages_conversation_id_fkey 
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_msg_conversation ON messages(conversation_id);

-- ============================================
-- 3. ТАБЛИЦА CHAT_MESSAGES
-- ============================================
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

-- ============================================
-- 4. ТАБЛИЦА MESSAGE_TEMPLATES
-- ============================================
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

-- ============================================
-- 5. ТАБЛИЦА DONATION_HISTORY
-- ============================================
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

-- ============================================
-- 6. ПРОВЕРКА И ВЫВОД РЕЗУЛЬТАТА
-- ============================================
SELECT 'Все таблицы созданы успешно!' as status;

-- Проверяем созданные таблицы
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('conversations', 'chat_messages', 'message_templates', 'donation_history')
ORDER BY table_name;

SQL

echo "✅ Структура БД обновлена"

echo ""
echo "========================================="
echo "🔄 ШАГ 4: ПЕРЕЗАПУСК СЕРВИСОВ"
echo "========================================="

supervisorctl stop all
sleep 2
supervisorctl start all
sleep 3

echo ""
echo "📊 Статус после перезапуска:"
supervisorctl status

echo ""
echo "========================================="
echo "🧪 ШАГ 5: ТЕСТИРОВАНИЕ API"
echo "========================================="

echo ""
echo "Тест 1: /api/regions"
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:5001/api/regions | head -50

echo ""
echo "Тест 2: /api/medcenters"
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:5001/api/medcenters | head -50

echo ""
echo "Тест 3: /api/donor/blood-requests (требует токен)"
# Этот запрос может вернуть 401 без токена, но не должен быть 500
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:5001/api/donor/blood-requests | head -50

echo ""
echo "========================================="
echo "🔍 ШАГ 6: ПРОВЕРКА ЛОГОВ ПОСЛЕ ТЕСТА"
echo "========================================="

echo ""
echo "Последние 20 строк лога Flask:"
tail -20 /var/log/tvoydonor-api.err.log

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo ""
echo "📁 Backup сохранён в: /opt/tvoydonor/backups/"
echo "🌐 Откройте https://tvoydonor.by и проверьте работу"
echo ""
echo "Если ещё есть ошибки 500, выполните:"
echo "  tail -100 /var/log/tvoydonor-api.err.log"
echo ""
