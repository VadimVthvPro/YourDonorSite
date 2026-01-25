#!/bin/bash
echo "========================================="
echo "🧪 ТЕСТ API С РЕАЛЬНЫМ ТОКЕНОМ"
echo "========================================="

echo ""
echo "Этот скрипт нужно запустить ПОСЛЕ входа в кабинет донора/медцентра"
echo ""
echo "1. Откройте https://tvoydonor.by"
echo "2. Войдите как ДОНОР или МЕДЦЕНТР"
echo "3. Откройте DevTools (F12) → Console"
echo "4. Выполните:"
echo ""
echo "// Для ДОНОРА:"
echo "fetch(window.API_URL + '/donor/statistics', {"
echo "  headers: {"
echo "    'Authorization': 'Bearer ' + localStorage.getItem('auth_token')"
echo "  }"
echo "}).then(r => r.json()).then(d => console.log('СТАТИСТИКА:', d))"
echo ""
echo "// Для МЕДЦЕНТРА:"
echo "fetch(window.API_URL + '/stats/medcenter', {"
echo "  headers: {"
echo "    'Authorization': 'Bearer ' + localStorage.getItem('auth_token')"
echo "  }"
echo "}).then(r => r.json()).then(d => console.log('СТАТИСТИКА:', d))"
echo ""
echo "5. Скопируйте результат и отправьте мне!"
echo ""
echo "=========================================
АЛЬТЕРНАТИВА: ПРОВЕРКА НАПРЯМУЮ НА СЕРВЕРЕ
=========================================
"

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "Проверяем логи API в реальном времени..."
echo "Откройте кабинет донора/медцентра и перейдите в раздел Статистика"
echo "Нажмите Ctrl+C когда закончите"
echo ""

tail -f /var/log/tvoydonor-api.err.log | grep -i "statistics\|donation_history\|error\|exception"

ENDSSH
