#!/bin/bash
# Прямая проверка эндпоинта updateResponseStatus
# Использование: ssh root@178.172.212.221 "bash -s" < test_response_update.sh

set -e

echo "========================================="
echo "🧪 ТЕСТИРОВАНИЕ updateResponseStatus"
echo "========================================="

echo ""
echo "1️⃣ Проверяем существующие отклики:"
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor << 'SQL'
SELECT id, request_id, user_id, status, hidden 
FROM donation_responses 
ORDER BY id DESC 
LIMIT 5;
SQL

echo ""
echo "2️⃣ Тестируем API напрямую (если есть отклики):"
RESPONSE_ID=$(psql -U donor_user -h localhost your_donor -t -c "SELECT id FROM donation_responses LIMIT 1;")

if [ ! -z "$RESPONSE_ID" ]; then
    RESPONSE_ID=$(echo $RESPONSE_ID | tr -d '[:space:]')
    echo "Найден отклик ID: $RESPONSE_ID"
    echo ""
    echo "Пытаемся обновить статус на 'confirmed'..."
    
    curl -v -X PUT "http://localhost:5001/api/responses/$RESPONSE_ID" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer FAKE_TOKEN_FOR_TEST" \
      -d '{"status": "confirmed"}' 2>&1 | grep -A 30 "< HTTP"
else
    echo "❌ Нет откликов для теста!"
    echo ""
    echo "Создадим тестовый запрос и отклик:"
    
    # Создаём тестовый запрос
    psql -U donor_user -h localhost your_donor << 'SQL'
    INSERT INTO blood_requests (medical_center_id, blood_type, urgency, status, description)
    VALUES (2, 'A+', 'normal', 'active', 'Тестовый запрос для проверки')
    RETURNING id;
SQL
    
    # Создаём тестовый отклик
    psql -U donor_user -h localhost your_donor << 'SQL'
    INSERT INTO donation_responses (request_id, user_id, medical_center_id, status)
    VALUES (
        (SELECT id FROM blood_requests ORDER BY id DESC LIMIT 1),
        1,
        2,
        'pending'
    )
    RETURNING id;
SQL
    
    echo ""
    echo "Тестовые данные созданы! Попробуйте ещё раз."
fi

echo ""
echo "========================================="
echo "📋 ПОСЛЕДНИЕ ОШИБКИ ИЗ ЛОГОВ:"
echo "========================================="
tail -50 /var/log/tvoydonor-api.err.log | grep -B 5 -A 10 "Exception\|Error\|does not exist" || echo "Ошибок нет!"

echo ""
echo "========================================="
echo "✅ ТЕСТ ЗАВЕРШЁН"
echo "========================================="
