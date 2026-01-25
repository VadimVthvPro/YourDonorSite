#!/bin/bash
echo "========================================="
echo "🔧 ПОЛНАЯ ПЕРЕЗАГРУЗКА + ПРОВЕРКА"
echo "========================================="

echo ""
echo "1️⃣ Загружаем последнюю версию app.py..."
scp /Users/VadimVthv/Your_donor/website/backend/app.py root@178.172.212.221:/opt/tvoydonor/website/backend/app.py

echo ""
echo "2️⃣ Подключаемся к серверу..."
echo ""

ssh root@178.172.212.221 << 'ENDSSH'

echo "3️⃣ Проверяем код в app.py на сервере..."
echo ""
echo "Строки 2143-2149 (INSERT в donation_history):"
sed -n '2143,2149p' /opt/tvoydonor/website/backend/app.py

echo ""
echo "4️⃣ Создаём/проверяем таблицу donation_history..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Создаём таблицу
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

CREATE INDEX IF NOT EXISTS idx_donation_history_donor ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);
CREATE INDEX IF NOT EXISTS idx_donation_history_mc ON donation_history(medical_center_id);

SELECT '✅ Таблица donation_history готова' as status;

-- Мигрируем старые донации
INSERT INTO donation_history (donor_id, medical_center_id, donation_date, donation_type, volume_ml, created_at)
SELECT 
    dr.user_id,
    dr.medical_center_id,
    COALESCE(dr.actual_donation_date::date, dr.updated_at::date, CURRENT_DATE),
    'blood',
    450,
    COALESCE(dr.actual_donation_date, dr.updated_at, NOW())
FROM donation_responses dr
WHERE dr.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM donation_history dh
    WHERE dh.donor_id = dr.user_id
    AND dh.medical_center_id = dr.medical_center_id
    AND dh.donation_date = COALESCE(dr.actual_donation_date::date, dr.updated_at::date)
);

SELECT '✅ Миграция завершена' as status;
SELECT COUNT(*) as "Записей в donation_history" FROM donation_history;

-- Показываем данные
SELECT 
    u.id,
    u.full_name,
    u.total_donations,
    COUNT(dh.id) as history_records
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0 OR dh.id IS NOT NULL
GROUP BY u.id, u.full_name, u.total_donations
ORDER BY u.total_donations DESC;

EOSQL

echo ""
echo "5️⃣ Очищаем логи и перезапускаем API..."
echo ""

# Очищаем логи для чистого теста
> /var/log/tvoydonor-api.err.log
> /var/log/tvoydonor-api.out.log

supervisorctl restart tvoydonor-api
sleep 5
supervisorctl status tvoydonor-api

echo ""
echo "6️⃣ Проверяем что API запустился без ошибок..."
echo ""

tail -20 /var/log/tvoydonor-api.out.log

echo ""
echo "7️⃣ Тестируем эндпоинт /api/donor/statistics..."
echo ""

# Попытка запроса (ожидаем 401 без токена, но не 500!)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/donor/statistics)
echo "HTTP код: $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ API работает (401 = нужна авторизация)"
elif [ "$HTTP_CODE" = "500" ]; then
    echo "❌ ОШИБКА 500! Проверяем логи:"
    tail -30 /var/log/tvoydonor-api.err.log
else
    echo "⚠️ Неожиданный код: $HTTP_CODE"
fi

echo ""
echo "=========================================
✅ ПЕРЕЗАГРУЗКА ЗАВЕРШЕНА!
=========================================
"

echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. Откройте https://tvoydonor.by как МЕДЦЕНТР"
echo "2. Найдите донора"
echo "3. Создайте запрос крови"
echo "4. Подтвердите донора (confirmed)"
echo "5. Завершите донацию (completed)"
echo ""
echo "6. Откройте кабинет ДОНОРА"
echo "7. Перейдите в 'Статистика'"
echo "8. Проверьте что появилась история!"
echo ""

ENDSSH
