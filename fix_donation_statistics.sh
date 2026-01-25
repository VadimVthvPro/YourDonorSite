#!/bin/bash
echo "========================================="
echo "🔧 ИСПРАВЛЕНИЕ СТАТИСТИКИ ДОНАЦИЙ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Проверяем и создаём таблицу donation_history..."
sudo -u postgres psql -d your_donor << 'EOSQL'

-- Проверяем существование таблицы
SELECT 'Проверка таблицы donation_history:' as info;
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'donation_history'
) as table_exists;

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

SELECT 'Структура таблицы donation_history:' as info;
\d donation_history

-- Проверяем текущие записи
SELECT '
Текущие записи в donation_history:' as info;
SELECT COUNT(*) as total_records FROM donation_history;

-- Проверяем доноров с завершёнными донациями
SELECT '
Доноры с завершёнными donation_responses:' as info;
SELECT 
    u.id, 
    u.full_name, 
    u.total_donations, 
    u.last_donation_date,
    COUNT(dr.id) as completed_responses
FROM users u
LEFT JOIN donation_responses dr ON u.id = dr.user_id AND dr.status = 'completed'
WHERE u.total_donations > 0 OR dr.id IS NOT NULL
GROUP BY u.id, u.full_name, u.total_donations, u.last_donation_date;

EOSQL

echo ""
echo "2️⃣ Загружаем исправленный app.py..."

ENDSSH

# Загружаем app.py
scp /Users/VadimVthv/Your_donor/website/backend/app.py root@178.172.212.221:/opt/tvoydonor/website/backend/app.py

echo ""
echo "3️⃣ Перезапускаем API..."

ssh root@178.172.212.221 << 'ENDSSH'

supervisorctl restart tvoydonor-api
sleep 3
supervisorctl status tvoydonor-api

echo ""
echo "=========================================
✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!
=========================================
"

echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. Откройте кабинет медцентра"
echo "2. Найдите донора с total_donations > 0"
echo "3. Создайте новый запрос крови"
echo "4. Пригласите донора (создайте отклик)"
echo "5. Подтвердите отклик (confirmed)"
echo "6. Завершите донацию (completed)"
echo ""
echo "7. Откройте кабинет донора"
echo "8. Проверьте раздел 'Статистика'"
echo "   → Должна отображаться история донаций!"
echo ""

ENDSSH
