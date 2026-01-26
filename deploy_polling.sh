#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "🔄 ДЕПЛОЙ: АВТООБНОВЛЕНИЕ БЕЗ ПЕРЕЗАГРУЗКИ"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 ЧТО БУДЕТ РАЗВЁРНУТО:"
echo "  ✅ data-poller.js - система polling"
echo "  ✅ donor-dashboard.js - обновлённый (+ polling)"
echo "  ✅ medcenter-dashboard.js - обновлённый (+ polling)"
echo "  ✅ donor-dashboard.html - подключение data-poller.js"
echo "  ✅ medcenter-dashboard.html - подключение data-poller.js"
echo ""
echo "🔄 POLLING ИНТЕРВАЛЫ:"
echo "  • Отклики медцентра: каждые 5 сек"
echo "  • Запросы крови: каждые 10 сек"
echo "  • Статистика: каждые 30 сек"
echo ""
echo "⚠️  ВАЖНО:"
echo "  • Это НЕ сломает сайт!"
echo "  • Пауза при редактировании (безопасно)"
echo "  • Умное обновление (без мигания)"
echo ""
read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

cd /Users/VadimVthv/Your_donor

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Загрузка JS файлов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

scp website/js/data-poller.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp website/js/donor-dashboard.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp website/js/medcenter-dashboard.js root@178.172.212.221:/opt/tvoydonor/website/js/

echo "✅ JS файлы загружены"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Обновление HTML (подключение data-poller.js)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Создаём временные файлы с обновлёнными HTML
ssh root@178.172.212.221 '
cd /opt/tvoydonor/website/pages

# Donor dashboard - добавляем data-poller.js ПЕРЕД donor-dashboard.js
if ! grep -q "data-poller.js" donor-dashboard.html; then
    sed -i "/donor-dashboard.js/i\    <script src=\"../js/data-poller.js\"></script>" donor-dashboard.html
    echo "✅ data-poller.js добавлен в donor-dashboard.html"
else
    echo "✓ data-poller.js уже подключён в donor-dashboard.html"
fi

# Medcenter dashboard - добавляем data-poller.js ПЕРЕД medcenter-dashboard.js
if ! grep -q "data-poller.js" medcenter-dashboard.html; then
    sed -i "/medcenter-dashboard.js/i\    <script src=\"../js/data-poller.js\"></script>" medcenter-dashboard.html
    echo "✅ data-poller.js добавлен в medcenter-dashboard.html"
else
    echo "✓ data-poller.js уже подключён в medcenter-dashboard.html"
fi
'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Обновление config.js (cache busting)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh root@178.172.212.221 '
cd /opt/tvoydonor/website/js
TIMESTAMP=$(date +%s)
sed -i "s/window.VERSION = .*/window.VERSION = ${TIMESTAMP};/" config.js
echo "✅ Версия обновлена: ${TIMESTAMP}"
'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Перезагрузка Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh root@178.172.212.221 'systemctl reload nginx'
echo "✅ Nginx перезагружен"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Сохранение в Git"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

git add -A
git commit -m "feat: автообновление данных без перезагрузки (polling)

- Донор: запросы крови каждые 10 сек, статистика каждые 30 сек
- Медцентр: отклики каждые 5 сек, запросы каждые 10 сек, статистика каждые 30 сек
- Умное обновление (сравнение с кэшем)
- Пауза при редактировании
- Toast уведомления о новых данных
- Без мигания интерфейса"

git tag -a v41-polling -m "v41: Автообновление данных (polling)"

echo "✅ Git commit и tag созданы"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ДЕПЛОЙ ЗАВЕРШЁН!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "  1. Откройте https://tvoydonor.by/"
echo "  2. Нажмите Cmd+Shift+R (жёсткое обновление)"
echo "  3. Откройте консоль (F12)"
echo ""
echo "✅ ДОЛЖНЫ УВИДЕТЬ:"
echo "  🔄 Запуск polling: donor-blood-requests (каждые 10 сек)"
echo "  🔄 Запуск polling: donor-statistics (каждые 30 сек)"
echo "  ✅ Автообновление запущено"
echo ""
echo "📱 ТЕСТ 1: ДОНОР + МЕДЦЕНТР"
echo "  1. Откройте донора на телефоне"
echo "  2. Откройте медцентр на компьютере"
echo "  3. Донор откликается на запрос"
echo "  4. Медцентр видит отклик через 5 сек БЕЗ ОБНОВЛЕНИЯ!"
echo ""
echo "📱 ТЕСТ 2: СОЗДАНИЕ ЗАПРОСА"
echo "  1. Медцентр создаёт запрос крови"
echo "  2. Донор видит его через 10 сек БЕЗ ОБНОВЛЕНИЯ!"
echo ""
echo "📱 ТЕСТ 3: ПАУЗА ПРИ РЕДАКТИРОВАНИИ"
echo "  1. Начните печатать в input"
echo "  2. В консоли: \"⏸️ Polling приостановлен (пользователь печатает)\""
echo "  3. Уберите фокус - polling возобновится"
echo ""
echo "🔍 ОТЛАДКА:"
echo "  • window.dataPoller.status() - статус всех polling"
echo "  • window.dataPoller.stopAll() - остановить все"
echo ""
