#!/bin/bash
# Проверка эндпоинтов сообщений в app.py на сервере
# Использование: ssh root@178.172.212.221 "bash -s" < check_message_endpoints.sh

set -e

echo "========================================="
echo "🔍 ПРОВЕРКА ЭНДПОИНТОВ СООБЩЕНИЙ"
echo "========================================="

echo ""
echo "1️⃣ Эндпоинты в app.py связанные с messages:"
grep -n "@app.route.*messages" /opt/tvoydonor/website/backend/app.py | head -20

echo ""
echo "2️⃣ Эндпоинты в app.py связанные с conversations:"
grep -n "def.*conversation" /opt/tvoydonor/website/backend/app.py | head -10

echo ""
echo "3️⃣ Проверка наличия функции get_conversations:"
grep -A 10 "def get_conversations" /opt/tvoydonor/website/backend/app.py | head -15

echo ""
echo "4️⃣ Тест эндпоинта напрямую (с токеном):"
# Сначала получим настоящий токен донора
TOKEN=$(psql -U donor_user -h localhost your_donor -t -c "SELECT token FROM user_sessions WHERE user_id=1 ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d '[:space:]')

if [ ! -z "$TOKEN" ]; then
    echo "Токен найден: ${TOKEN:0:20}..."
    echo ""
    echo "Запрос к /api/messages/conversations:"
    curl -s "http://localhost:5001/api/messages/conversations" \
      -H "Authorization: Bearer $TOKEN" | head -200
else
    echo "❌ Токен не найден! Нужно войти на сайт."
fi

echo ""
echo ""
echo "========================================="
echo "✅ ПРОВЕРКА ЗАВЕРШЕНА"
echo "========================================="
