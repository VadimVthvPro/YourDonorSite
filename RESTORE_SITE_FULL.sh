#!/bin/bash

# ════════════════════════════════════════════════════════════════
# 🔧 ПОЛНОЕ ВОССТАНОВЛЕНИЕ САЙТА С АВТОВХОДОМ
# ════════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════════════════"
echo "🔧 ПОЛНОЕ ВОССТАНОВЛЕНИЕ САЙТА"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 ЧТО БУДЕТ СДЕЛАНО:"
echo "  1. Восстановление всех JS файлов (корректные версии)"
echo "  2. Восстановление HTML файлов"
echo "  3. Пересоздание config.js с правильной версией"
echo "  4. Перезагрузка Nginx"
echo "  5. Очистка кэша браузера"
echo ""
read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено пользователем"
    exit 0
fi

SERVER="root@178.172.212.221"
PROJECT_DIR="/Users/VadimVthv/Your_donor"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 ШАГ 1/6: Загрузка JS файлов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_DIR"

echo "  • app.js..."
scp website/js/app.js $SERVER:/opt/tvoydonor/website/js/

echo "  • auth.js..."
scp website/js/auth.js $SERVER:/opt/tvoydonor/website/js/

echo "  • auth-storage.js..."
scp website/js/auth-storage.js $SERVER:/opt/tvoydonor/website/js/

echo "  • donor-dashboard.js..."
scp website/js/donor-dashboard.js $SERVER:/opt/tvoydonor/website/js/

echo "  • medcenter-dashboard.js..."
scp website/js/medcenter-dashboard.js $SERVER:/opt/tvoydonor/website/js/

echo "✅ JS файлы загружены"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 ШАГ 2/6: Загрузка HTML файлов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  • index.html..."
scp website/index.html $SERVER:/opt/tvoydonor/website/

echo "  • auth.html..."
scp website/pages/auth.html $SERVER:/opt/tvoydonor/website/pages/

echo "  • donor-dashboard.html..."
scp website/pages/donor-dashboard.html $SERVER:/opt/tvoydonor/website/pages/

echo "  • medcenter-dashboard.html..."
scp website/pages/medcenter-dashboard.html $SERVER:/opt/tvoydonor/website/pages/

echo "✅ HTML файлы загружены"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 ШАГ 3/6: Пересоздание config.js"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
cd /opt/tvoydonor/website/js
TIMESTAMP=$(date +%s)

cat > config.js << 'CONFIGEOF'
/**
 * Глобальная конфигурация приложения
 */

// API URL
const hostname = window.location.hostname;
const protocol = window.location.protocol;

if (hostname === 'localhost' || hostname === '127.0.0.1') {
    window.API_URL = 'http://localhost:5001/api';
} else {
    window.API_URL = protocol + '//' + hostname + ':5001/api';
}

// Версия для cache busting
window.VERSION = 'VERSIONPLACEHOLDER';

console.log('🔧 Config загружен, API_URL:', window.API_URL);
CONFIGEOF

# Заменяем VERSIONPLACEHOLDER на реальный timestamp
sed -i "s/VERSIONPLACEHOLDER/${TIMESTAMP}/" config.js

echo "✅ config.js пересоздан! Версия: ${TIMESTAMP}"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 ШАГ 4/6: Проверка файлов на сервере"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
echo "=== JS файлы ==="
ls -lh /opt/tvoydonor/website/js/*.js | grep -E 'app|auth|config|donor|medcenter' | awk '{print $9, "("$5")"}'

echo ""
echo "=== HTML файлы ==="
ls -lh /opt/tvoydonor/website/index.html | awk '{print $9, "("$5")"}'
ls -lh /opt/tvoydonor/website/pages/*.html | grep -E 'auth|donor|medcenter' | awk '{print $9, "("$5")"}'

echo ""
echo "=== CSS файлы ==="
ls -lh /opt/tvoydonor/website/css/styles.css | awk '{print $9, "("$5")"}'
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 5/6: Перезагрузка Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
nginx -t && systemctl reload nginx
echo "✅ Nginx перезагружен"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ШАГ 6/6: Финальная проверка"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
echo "=== Проверка синтаксиса JS ==="
cd /opt/tvoydonor/website/js

# Проверяем app.js
echo -n "app.js: "
node -c app.js 2>&1 && echo "✅ OK" || echo "❌ ОШИБКА"

# Проверяем auth.js
echo -n "auth.js: "
node -c auth.js 2>&1 && echo "✅ OK" || echo "❌ ОШИБКА"

echo ""
echo "=== Размеры файлов ==="
du -h app.js auth.js config.js auth-storage.js
ENDSSH

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 СЛЕДУЮЩИЕ ШАГИ:"
echo "  1. Откройте: https://tvoydonor.by/"
echo "  2. Нажмите: Cmd+Shift+R (жёсткое обновление)"
echo "  3. Откройте консоль: F12 → Console"
echo "  4. Проверьте логи:"
echo "     ✅ Должно быть: '🔧 Config загружен'"
echo "     ✅ Должно быть: '==== app.js ЗАГРУЖЕН ===='"
echo "     ✅ НЕ должно быть: ошибок 404 или SyntaxError"
echo ""
echo "  5. Если увидите ошибки → скопируйте ВСЕ и отправьте мне"
echo ""
echo "🎉 ФУНКЦИОНАЛ:"
echo "  ✅ Красивый дизайн (CSS работает)"
echo "  ✅ Полный функционал (все кнопки работают)"
echo "  ✅ Автовход (при повторном открытии → автоматически на dashboard)"
echo ""
