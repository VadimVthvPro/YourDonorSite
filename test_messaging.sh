#!/bin/bash
# Проверка проблемы с сообщениями
# Использование: ssh root@178.172.212.221 "bash -s" < test_messaging.sh

set -e

echo "========================================="
echo "💬 ДИАГНОСТИКА СИСТЕМЫ СООБЩЕНИЙ"
echo "========================================="

export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo ""
echo "1️⃣ Проверка таблиц сообщений:"
psql -U donor_user -h localhost your_donor << 'SQL'
-- Проверяем какие таблицы для сообщений есть
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND (tablename LIKE '%message%' OR tablename LIKE '%conversation%')
ORDER BY tablename;
SQL

echo ""
echo "2️⃣ Структура conversations:"
psql -U donor_user -h localhost your_donor -c "\d conversations"

echo ""
echo "3️⃣ Структура messages:"
psql -U donor_user -h localhost your_donor -c "\d messages"

echo ""
echo "4️⃣ Структура chat_messages:"
psql -U donor_user -h localhost your_donor -c "\d chat_messages" 2>&1 || echo "Таблица chat_messages не существует"

echo ""
echo "5️⃣ Проверка эндпоинтов сообщений:"
echo "Тест 1: /api/messenger/conversations"
curl -s "http://localhost:5001/api/messenger/conversations" \
  -H "Authorization: Bearer FAKE_TOKEN" 2>&1 | head -100

echo ""
echo ""
echo "Тест 2: /api/messages/updates"
curl -s "http://localhost:5001/api/messages/updates?last_id=0" \
  -H "Authorization: Bearer FAKE_TOKEN" 2>&1 | head -100

echo ""
echo ""
echo "========================================="
echo "📋 ОШИБКИ В ЛОГАХ (последние 100 строк):"
echo "========================================="
tail -100 /var/log/tvoydonor-api.err.log | grep -B 3 -A 10 "message\|conversation" -i || echo "Ошибок с сообщениями нет!"

echo ""
echo "========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "========================================="
