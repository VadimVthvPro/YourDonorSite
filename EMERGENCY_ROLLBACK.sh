#!/bin/bash

# ════════════════════════════════════════════════════════════════
# 🚨 ЭКСТРЕННЫЙ ОТКАТ: УДАЛЕНИЕ АВТОВХОДА
# ════════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════════════════"
echo "🚨 ЭКСТРЕННЫЙ ОТКАТ ИЗМЕНЕНИЙ"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  ЧТО БУДЕТ СДЕЛАНО:"
echo "  1. Откат app.js (убрать автовход)"
echo "  2. Откат auth.js (убрать автовход)"
echo "  3. Откат index.html (убрать auth-storage.js)"
echo "  4. Пересоздание config.js"
echo "  5. Перезагрузка Nginx"
echo ""
echo "✅ САЙТ ВЕРНЁТСЯ К РАБОЧЕМУ СОСТОЯНИЮ (до автовхода)"
echo ""
read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

SERVER="root@178.172.212.221"
PROJECT_DIR="/Users/VadimVthv/Your_donor"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 1/5: Откат app.js"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
cat > /opt/tvoydonor/website/js/app.js << 'APPEOF'
/**
 * Твой Донор - Главный JavaScript файл
 * Интерактивность, анимации и динамический функционал
 */

console.log('==== app.js ЗАГРУЖЕН ====');

// Глобальный URL для API
// Используем API URL из config.js если доступен, иначе fallback
if (!window.API_URL) {
    window.API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:5001/api'
        : `${window.location.protocol}//${window.location.hostname}:5001/api`;
}
const API_URL = window.API_URL;

document.addEventListener('DOMContentLoaded', function() {
    // Проверяем авторизацию и обновляем кнопки
    checkAuthAndUpdateNav();
    
    // Инициализация всех компонентов
    initScrollAnimations();
    initHeader();
    initFAQ();
    initMobileMenu();
    initStatCounters();
    initCentersSelector();
    initSmoothScroll();
});

/**
 * Проверка авторизации и обновление навигации
 */
function checkAuthAndUpdateNav() {
    const authToken = localStorage.getItem('auth_token');
    const userType = localStorage.getItem('user_type');
    const navButtons = document.getElementById('nav-buttons');
    
    if (!navButtons) return;
    
    if (authToken && userType) {
        // Пользователь авторизован
        let dashboardUrl = '';
        let dashboardLabel = '';
        let userName = '';
        
        if (userType === 'donor') {
            dashboardUrl = 'pages/donor-dashboard.html';
            dashboardLabel = 'Личный кабинет';
            const donorData = JSON.parse(localStorage.getItem('donor_user') || '{}');
            userName = donorData.full_name || 'Донор';
        } else if (userType === 'medcenter') {
            dashboardUrl = 'pages/medcenter-dashboard.html';
            dashboardLabel = 'Панель медцентра';
            const mcData = JSON.parse(localStorage.getItem('medcenter_user') || '{}');
            userName = mcData.name || 'Медцентр';
        }
        
        navButtons.innerHTML = `
            <span class="nav-user-name">${userName}</span>
            <a href="${dashboardUrl}" class="btn btn-primary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 18px; height: 18px; margin-right: 6px;">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
                ${dashboardLabel}
            </a>
        `;
    }
}
APPEOF

echo "✅ app.js откачен (убран автовход)"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 2/5: Откат index.html"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
# Удаляем строку с auth-storage.js из index.html
sed -i '/<script src="js\/auth-storage.js"><\/script>/d' /opt/tvoydonor/website/index.html

echo "✅ index.html откачен (убрана ссылка на auth-storage.js)"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 3/5: Откат auth.js (страница входа)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
# Удаляем функцию autoLoginIfSessionExists и восстанавливаем обычный DOMContentLoaded
sed -i '/async function autoLoginIfSessionExists/,/^}/d' /opt/tvoydonor/website/js/auth.js
sed -i 's/document.addEventListener('"'"'DOMContentLoaded'"'"', async function() {/document.addEventListener('"'"'DOMContentLoaded'"'"', function() {/' /opt/tvoydonor/website/js/auth.js
sed -i '/await autoLoginIfSessionExists/d' /opt/tvoydonor/website/js/auth.js
sed -i '/Если мы здесь, значит сессии нет или она невалидна/d' /opt/tvoydonor/website/js/auth.js

echo "✅ auth.js откачен (убран автовход)"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 ШАГ 4/5: Пересоздание config.js"
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

sed -i "s/VERSIONPLACEHOLDER/${TIMESTAMP}/" config.js
echo "✅ config.js пересоздан! Версия: ${TIMESTAMP}"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 5/5: Перезагрузка Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh $SERVER 'bash -s' << 'ENDSSH'
nginx -t && systemctl reload nginx
echo "✅ Nginx перезагружен"
ENDSSH

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ОТКАТ ЗАВЕРШЁН!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 ПРОВЕРКА:"
echo "  1. Откройте: https://tvoydonor.by/"
echo "  2. Нажмите: Cmd+Shift+R (жёсткое обновление)"
echo "  3. Сайт должен выглядеть НОРМАЛЬНО"
echo "  4. Авторизация работает ОБЫЧНЫМ образом (без автовхода)"
echo ""
echo "⚠️  ВАЖНО: Теперь при каждом открытии сайта придётся входить заново"
echo ""
