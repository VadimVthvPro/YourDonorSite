#!/bin/bash
echo "========================================="
echo "🔧 ПОЛНОЕ ИСПРАВЛЕНИЕ СТАТИСТИКИ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Создаём таблицу donation_history..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Создаём таблицу donation_history
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

SELECT '✅ Таблица donation_history создана' as status;

EOSQL

echo ""
echo "2️⃣ Мигрируем завершённые донации..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Мигрируем donation_responses → donation_history
INSERT INTO donation_history (donor_id, medical_center_id, donation_date, donation_type, volume_ml, created_at)
SELECT 
    dr.user_id as donor_id,
    dr.medical_center_id,
    COALESCE(dr.actual_donation_date::date, dr.updated_at::date, CURRENT_DATE) as donation_date,
    'blood' as donation_type,
    450 as volume_ml,
    COALESCE(dr.actual_donation_date, dr.updated_at, NOW()) as created_at
FROM donation_responses dr
WHERE dr.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM donation_history dh
    WHERE dh.donor_id = dr.user_id
    AND dh.medical_center_id = dr.medical_center_id
    AND dh.donation_date = COALESCE(dr.actual_donation_date::date, dr.updated_at::date)
)
ORDER BY dr.id;

SELECT '✅ Миграция завершена' as status;

-- Показываем результат
SELECT 
    COUNT(*) as "Записей в donation_history",
    COUNT(DISTINCT donor_id) as "Уникальных доноров"
FROM donation_history;

EOSQL

echo ""
echo "3️⃣ Проверяем данные..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Доноры с историей
SELECT 
    u.id,
    u.full_name,
    u.total_donations as "Счётчик",
    COUNT(dh.id) as "В истории",
    MAX(dh.donation_date) as "Последняя"
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0 OR dh.id IS NOT NULL
GROUP BY u.id, u.full_name, u.total_donations
ORDER BY u.total_donations DESC;

EOSQL

echo ""
echo "4️⃣ Перезапускаем API..."
echo ""

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
echo "ДОНОР:"
echo "1. Откройте кабинет донора"
echo "2. Перейдите в раздел 'Статистика'"
echo "   → Должна показаться история донаций!"
echo ""
echo "МЕДЦЕНТР:"
echo "1. Откройте кабинет медцентра"
echo "2. Посмотрите главную страницу"
echo "   → Счётчики должны показать данные!"
echo ""

ENDSSH
