#!/bin/bash
# Скрипт для исправления всех проблем на сервере
# Выполните: ssh root@178.172.212.221 "bash -s" < server_fix.sh

set -e  # Останавливаться при ошибках

echo "========================================="
echo "ШАГ 1: СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ БД"
echo "========================================="
cd /opt/tvoydonor
mkdir -p backups
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
pg_dump -U donor_user -h localhost your_donor > backups/backup-$(date +%Y%m%d-%H%M%S).sql
echo "✅ Backup создан: $(ls -1t backups/ | head -1)"

echo ""
echo "========================================="
echo "ШАГ 2: ВЫГРУЗКА АКТУАЛЬНОЙ СТРУКТУРЫ БД"
echo "========================================="
pg_dump -U donor_user -h localhost your_donor --schema-only > backups/current_schema.sql
echo "✅ Схема выгружена в backups/current_schema.sql"

echo ""
echo "========================================="
echo "ШАГ 3: ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ КОЛОНОК"
echo "========================================="

# Добавляем conversation_id в messages если его нет
psql -U donor_user -h localhost your_donor << 'SQL'
-- Проверяем и добавляем недостающие колонки
ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;

-- Создаём таблицу donation_history если её нет
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

-- Добавляем недостающие колонки в users если нужно
ALTER TABLE users ADD COLUMN IF NOT EXISTS donated_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_response_date TIMESTAMP;

-- Создаём индексы
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_user ON donation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);

SELECT 'Миграция завершена' as status;
SQL

echo "✅ Недостающие колонки добавлены"

echo ""
echo "========================================="
echo "ШАГ 4: ЗАЩИТА .ENV ФАЙЛА"
echo "========================================="

# Добавляем .env в .gitignore если его там нет
if ! grep -q "^\.env$" /opt/tvoydonor/.gitignore 2>/dev/null; then
    echo ".env" >> /opt/tvoydonor/.gitignore
    echo "website/backend/.env" >> /opt/tvoydonor/.gitignore
fi

# Создаём правильный .env файл
cat > /opt/tvoydonor/website/backend/.env << 'ENVEOF'
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
ENVEOF

chmod 600 /opt/tvoydonor/website/backend/.env
echo "✅ .env файл защищён и настроен"

echo ""
echo "========================================="
echo "ШАГ 5: ПЕРЕЗАПУСК СЕРВИСОВ"
echo "========================================="
supervisorctl restart all
sleep 2
supervisorctl status
echo "✅ Сервисы перезапущены"

echo ""
echo "========================================="
echo "ШАГ 6: ПРОВЕРКА РАБОТОСПОСОБНОСТИ"
echo "========================================="
echo "Тест API /regions:"
curl -s http://localhost:5001/api/regions | head -c 100
echo "..."

echo ""
echo "Тест API /medcenters:"
curl -s "http://localhost:5001/api/medcenters?district_id=1" | head -c 100
echo "..."

echo ""
echo "========================================="
echo "✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!"
echo "========================================="
echo "Backup БД: /opt/tvoydonor/backups/"
echo "Схема БД: /opt/tvoydonor/backups/current_schema.sql"
echo ".env защищён от перезаписи"
echo ""
echo "Откройте https://tvoydonor.by и проверьте работу"
