#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "🔧 ИСПРАВЛЕНИЕ config.js (УБИРАЕМ ПОРТ :5001)"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 ПРОБЛЕМА:"
echo "  ❌ API URL: https://tvoydonor.by:5001/api/regions"
echo "  ✅ Должно быть: https://tvoydonor.by/api/regions"
echo ""
echo "🔧 РЕШЕНИЕ:"
echo "  • Загружаем исправленный config.js"
echo "  • Nginx будет проксировать /api/ → 127.0.0.1:5001"
echo ""
read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

cd /Users/VadimVthv/Your_donor

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Загрузка config.js"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

scp website/js/config.js root@178.172.212.221:/opt/tvoydonor/website/js/

echo "✅ config.js загружен"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Перезагрузка Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh root@178.172.212.221 'systemctl reload nginx'

echo "✅ Nginx перезагружен"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "  1. Откройте: https://tvoydonor.by/pages/auth.html"
echo "  2. Нажмите F12 → Console"
echo "  3. Нажмите Cmd+Shift+R (жёсткое обновление)"
echo ""
echo "✅ ТЕПЕРЬ ДОЛЖНЫ УВИДЕТЬ:"
echo "  🌐 API URL: https://tvoydonor.by/api (production)"
echo "  📍 Загрузка регионов из: https://tvoydonor.by/api/regions"
echo "  📍 Статус ответа: 200 OK"
echo "  📍 Регионов загружено: 7"
echo "  ✅ Регионы успешно загружены"
echo ""
echo "✅ Выбор области должен работать!"
echo ""
