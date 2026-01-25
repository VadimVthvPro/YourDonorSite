#!/bin/bash
echo "========================================="
echo "🔧 СОЗДАНИЕ DONATION_HISTORY"
echo "========================================="

echo ""
echo "Подключаемся к серверу..."
echo "Пароль: Vadamahjkl1!"
echo ""

ssh root@178.172.212.221 << 'ENDSSH'

echo "Создаём таблицу donation_history..."

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Создаём таблицу если не существует
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    donation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    donation_type VARCHAR(20) DEFAULT 'blood',
    volume_ml INTEGER DEFAULT 450,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаём индексы
CREATE INDEX IF NOT EXISTS idx_donation_history_donor ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);
CREATE INDEX IF NOT EXISTS idx_donation_history_mc ON donation_history(medical_center_id);

SELECT '✅ Таблица donation_history создана!' as status;

\d donation_history

EOSQL

echo ""
echo "=========================================
✅ ТАБЛИЦА СОЗДАНА!
=========================================
"

ENDSSH
