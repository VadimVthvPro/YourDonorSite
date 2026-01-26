#!/bin/bash
# 🔧 ИСПРАВЛЕНИЕ ДУБЛИРУЮЩИХСЯ ID И ИСТОРИИ ДОНАЦИЙ

SERVER_IP="178.172.212.221"

echo "════════════════════════════════════════════════════════════════"
echo "🔧 ИСПРАВЛЕНИЕ: Меню медцентра + История донаций"
echo "════════════════════════════════════════════════════════════════"

echo ""
echo "📋 ЧТО БУДЕТ ИСПРАВЛЕНО:"
echo "  1. Дублирующиеся ID в HTML медцентра (stat-requests, stat-donors)"
echo "  2. JavaScript обновление элементов меню"
echo "  3. Улучшенное логирование в истории донаций"
echo ""

read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 ШАГ 1/3: Загрузка файлов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • medcenter-dashboard.html..."
scp website/pages/medcenter-dashboard.html root@$SERVER_IP:/opt/tvoydonor/website/pages/
echo "  • medcenter-dashboard.js..."
scp website/js/medcenter-dashboard.js root@$SERVER_IP:/opt/tvoydonor/website/js/
echo "  • donor-dashboard.js..."
scp website/js/donor-dashboard.js root@$SERVER_IP:/opt/tvoydonor/website/js/
echo "✅ Файлы загружены"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 2/3: Обновление версии и перезагрузка"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh root@$SERVER_IP "
    cd /opt/tvoydonor/website
    TIMESTAMP=\$(date +%s)
    sed -i \"s/window.VERSION = .*/window.VERSION = '\${TIMESTAMP}';/\" js/config.js
    echo \"✅ Версия: \${TIMESTAMP}\"
    
    nginx -t && systemctl reload nginx
    echo \"✅ Nginx перезагружен\"
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ШАГ 3/3: Проверка"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ожидание 2 секунды..."
sleep 2

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. МЕДЦЕНТР → Меню (раздел Статистика):"
echo "   • Обновите страницу (Ctrl+Shift+R / Cmd+Shift+R)"
echo "   • Должно показать:"
echo "     📋 28 ЗАПРОСОВ КРОВИ"
echo "     👥 4 УНИКАЛЬНЫХ ДОНОРА"
echo ""
echo "2. ДОНОР (ID=3) → Мои донации:"
echo "   • Обновите страницу (Ctrl+Shift+R / Cmd+Shift+R)"
echo "   • Откройте консоль браузера (F12)"
echo "   • Перейдите в раздел 'Мои донации'"
echo "   • В консоли должно быть:"
echo "     📋 Рендерим историю донаций, получено записей: 11"
echo "     ✅ История донаций отрендерена, записей: 11"
echo "   • Должно показать 11 записей донаций"
echo ""
echo "3. Если 'Мои донации' всё ещё не работает:"
echo "   • Откройте консоль (F12)"
echo "   • Скопируйте ВСЕ ошибки (красные)"
echo "   • Отправьте мне"
echo ""
