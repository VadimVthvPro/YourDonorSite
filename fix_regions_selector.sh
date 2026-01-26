#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "🔧 ИСПРАВЛЕНИЕ ВЫБОРА ОБЛАСТИ"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 ЧТО БУДЕТ ПРОВЕРЕНО И ИСПРАВЛЕНО:"
echo "  1. Конфигурация Nginx (location /api/)"
echo "  2. База данных (таблица regions)"
echo "  3. API эндпоинт /api/regions"
echo "  4. Консоль браузера для ошибок"
echo ""
read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

cd /Users/VadimVthv/Your_donor

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 ШАГ 1: ПРОВЕРКА БАЗЫ ДАННЫХ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Выполните на сервере (введите пароль когда попросит):"
echo ""
echo "ssh root@178.172.212.221"
echo ""
echo "Затем выполните:"
echo ""
echo 'sudo -u postgres psql your_donor -c "SELECT COUNT(*) as total_regions FROM regions;"'
echo ""
echo "Если видите 0 регионов - нужно заполнить таблицу!"
echo ""
read -p "Нажмите Enter после проверки..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 ШАГ 2: ПРОВЕРКА NGINX КОНФИГУРАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "На сервере выполните:"
echo ""
echo 'grep -A 5 "location /api/" /etc/nginx/sites-available/tvoydonor'
echo ""
echo "Должно быть:"
echo "  location /api/ {"
echo "    proxy_pass http://127.0.0.1:5001/api/;"
echo "    proxy_set_header Host \$host;"
echo "    ..."
echo "  }"
echo ""
read -p "Нажмите Enter после проверки..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 ШАГ 3: ПРОВЕРКА API ЭНДПОИНТА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "На сервере выполните:"
echo ""
echo 'curl -s http://127.0.0.1:5001/api/regions | python3 -m json.tool | head -20'
echo ""
echo "Должен вернуться JSON с регионами"
echo ""
read -p "Нажмите Enter после проверки..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 ШАГ 4: ПРОВЕРКА В БРАУЗЕРЕ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "1. Откройте https://tvoydonor.by/"
echo "2. Нажмите F12 (открыть консоль)"
echo "3. Перейдите на вкладку Console"
echo "4. Нажмите Cmd+Shift+R (жёсткое обновление)"
echo ""
echo "✅ ДОЛЖНЫ УВИДЕТЬ:"
echo "  📍 Загрузка регионов из: https://tvoydonor.by/api/regions"
echo "  📍 Статус ответа: 200 OK"
echo "  📍 Регионов загружено: 6"
echo "  ✅ Регионы успешно загружены"
echo ""
echo "❌ ЕСЛИ ВИДИТЕ ОШИБКУ:"
echo "  • CORS error - проблема в Nginx"
echo "  • 404 Not Found - проблема в Nginx routing"
echo "  • 500 Internal Server - проблема в app.py или БД"
echo ""

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🔧 ЕСЛИ ТАБЛИЦА regions ПУСТАЯ - ВЫПОЛНИТЕ:"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "На сервере (ssh root@178.172.212.221):"
echo ""
cat << 'SQL'
sudo -u postgres psql your_donor << 'EOF'
-- Заполняем регионы Беларуси
INSERT INTO regions (id, name) VALUES 
  (1, 'Брестская область'),
  (2, 'Витебская область'),
  (3, 'Гомельская область'),
  (4, 'Гродненская область'),
  (5, 'Минская область'),
  (6, 'Могилевская область')
ON CONFLICT (id) DO NOTHING;

-- Проверяем
SELECT * FROM regions ORDER BY id;
EOF
SQL

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "После исправления проблем:"
echo "  1. Перезагрузите Nginx: systemctl reload nginx"
echo "  2. Откройте сайт: https://tvoydonor.by/"
echo "  3. Cmd+Shift+R (жёсткое обновление)"
echo "  4. Попробуйте выбрать область"
echo ""
