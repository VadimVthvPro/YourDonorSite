#!/bin/bash

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔧 ИСПРАВЛЕНИЕ TELEGRAM-ВЕРИФИКАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Найденная проблема:"
echo "   Фронтенд генерировал новый случайный код вместо использования кода от backend"
echo ""
echo "✅ Исправления:"
echo "   1. Функция принимает 3-й параметр (telegramCode от backend)"
echo "   2. Добавлено пояснение что аккаунт уже создан"
echo "   3. Улучшены тексты кнопок"
echo "   4. Исправлен таймер (10 минут вместо 15)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SERVER="root@178.172.212.221"

# Шаг 1: Загрузка auth.js
echo "📋 Шаг 1/3: Загрузка исправленного auth.js..."
echo ""
scp /Users/VadimVthv/Your_donor/website/js/auth.js $SERVER:/opt/tvoydonor/website/js/auth.js

if [ $? -eq 0 ]; then
    echo "✅ auth.js загружен"
else
    echo "❌ Ошибка загрузки!"
    exit 1
fi

echo ""

# Шаг 2: Обновление версии JS
echo "📋 Шаг 2/3: Обновление версии JS в HTML..."
echo ""

TIMESTAMP=$(date +%s)
echo "Новая версия: $TIMESTAMP"

ssh $SERVER << ENDSSH
# Обновляем версию auth.js в HTML
find /opt/tvoydonor/website/pages -name "auth.html" -type f | while read file; do
    sed -i "s|auth\.js?v=[0-9]*|auth.js?v=$TIMESTAMP|g" "\$file"
    sed -i "s|js/auth\.js\"|js/auth.js?v=$TIMESTAMP\"|g" "\$file"
    echo "✅ Обновлён: \$file"
done

echo ""
echo "Проверка:"
grep "auth.js" /opt/tvoydonor/website/pages/auth.html | head -1
ENDSSH

echo ""

# Шаг 3: Проверка
echo "📋 Шаг 3/3: Проверка изменений..."
echo ""

ssh $SERVER << 'ENDSSH'
echo "Проверяем функцию showTelegramVerificationModal:"
grep -A 5 "function showTelegramVerificationModal" /opt/tvoydonor/website/js/auth.js | head -6
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. Откройте https://tvoydonor.by/pages/auth.html?mode=register&type=donor"
echo ""
echo "2. Заполните форму регистрации и нажмите «Зарегистрироваться»"
echo ""
echo "3. ✅ Ожидаемый результат:"
echo "   • Модальное окно с кодом"
echo "   • Пояснение: 'Ваш аккаунт уже создан и активен!'"
echo "   • Код от backend (проверяется в консоли браузера)"
echo ""
echo "4. Откройте @TvoyDonorZdesBot в Telegram"
echo ""
echo "5. Нажмите START и отправьте код"
echo ""
echo "6. ✅ Бот должен ответить: '✅ Регистрация подтверждена!'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Для отладки откройте консоль браузера (F12) и найдите:"
echo "   [TELEGRAM MODAL] Показ модального окна с кодом от backend: XXXXXX"
echo ""
echo "✅ Скрипт завершён!"
echo ""
