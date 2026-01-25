#!/bin/bash
# Тестирование API после исправлений
# Использование: ssh root@178.172.212.221 "bash -s" < test_api.sh

set -e

echo "========================================="
echo "🧪 ТЕСТИРОВАНИЕ API"
echo "========================================="

BASE_URL="http://localhost:5001/api"

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=${3:-200}
    
    echo -n "Testing ${name}... "
    
    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (${status_code})${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (got ${status_code}, expected ${expected_status})${NC}"
        echo "Response: ${body}" | head -c 200
        echo ""
        return 1
    fi
}

echo ""
echo "Тестирование базовых API endpoints:"
echo "-------------------------------------"

# Базовые эндпоинты
test_endpoint "Regions" "/regions"
test_endpoint "Districts for region 1" "/regions/1/districts"
test_endpoint "Medcenters" "/medcenters"

echo ""
echo "Тестирование донорских API:"
echo "-------------------------------------"

# Получаем токен из тестовой регистрации или используем существующего
# (в продакшене нужен реальный токен)
TOKEN="test_token_here"

echo ""
echo "Тестирование медцентр API:"
echo "-------------------------------------"

# Медцентры обычно требуют авторизации

echo ""
echo "========================================="
echo "📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ"
echo "========================================="

# Проверка структуры БД
echo ""
echo "Проверка таблиц БД:"
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor -c "\dt" | grep -E "conversations|chat_messages|message_templates|donation_history|admin_users|telegram_link_codes" || echo "⚠️  Некоторые таблицы отсутствуют"

echo ""
echo "Проверка колонок в messages:"
psql -U donor_user -h localhost your_donor -c "\d messages" | grep -E "conversation_id|is_system" || echo "⚠️  Некоторые колонки отсутствуют"

echo ""
echo "Проверка колонок в users:"
psql -U donor_user -h localhost your_donor -c "\d users" | grep -E "password_hash|donated_count|last_response_date" || echo "⚠️  Некоторые колонки отсутствуют"

echo ""
echo "========================================="
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "========================================="
