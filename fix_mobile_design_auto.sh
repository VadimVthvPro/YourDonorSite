#!/bin/bash

# ============================================
# АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ МОБИЛЬНОГО ДИЗАЙНА
# Один скрипт для полного решения проблемы
# ============================================

set -e  # Останавливаемся при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVER="root@178.172.212.221"
LOCAL_CSS="/Users/VadimVthv/Your_donor/website/css/styles.css"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}  🎨 АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ МОБИЛЬНОГО ДИЗАЙНА${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Этот скрипт:"
echo "  1. Создаст резервную копию на сервере"
echo "  2. Загрузит исправленный CSS"
echo "  3. Обновит версию CSS в HTML"
echo "  4. Перезагрузит nginx"
echo "  5. Проверит результат"
echo ""

# ============================================
# ПРОВЕРКА ЛОКАЛЬНОГО CSS
# ============================================
echo -e "${YELLOW}━━━ ШАГ 1/5: Проверка локального CSS ━━━${NC}"
echo ""

if [ ! -f "$LOCAL_CSS" ]; then
    echo -e "${RED}❌ ОШИБКА: Файл $LOCAL_CSS не найден!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Локальный файл найден${NC}"
echo "   Размер: $(wc -c < "$LOCAL_CSS") байт"
echo "   Строк: $(wc -l < "$LOCAL_CSS")"

# Проверяем наличие исправлений
if grep -q "grid-template-columns: 1fr; /\* ОДНА КОЛОНКА" "$LOCAL_CSS"; then
    echo -e "${GREEN}✅ Найдено: grid-template-columns: 1fr${NC}"
else
    echo -e "${RED}❌ ОШИБКА: CSS не содержит исправлений!${NC}"
    exit 1
fi

if grep -q "font-size: 0.95rem; /\* Увеличен" "$LOCAL_CSS"; then
    echo -e "${GREEN}✅ Найдено: font-size: 0.95rem${NC}"
else
    echo -e "${RED}❌ ОШИБКА: CSS не содержит увеличенных шрифтов!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Локальный CSS готов к загрузке${NC}"
echo ""

# ============================================
# РЕЗЕРВНАЯ КОПИЯ + ЗАГРУЗКА
# ============================================
echo -e "${YELLOW}━━━ ШАГ 2/5: Резервная копия и загрузка CSS ━━━${NC}"
echo ""

ssh $SERVER bash << 'EOF'
# Создаём директорию для бэкапов
mkdir -p /opt/tvoydonor/backups

# Создаём резервную копию
BACKUP_FILE="/opt/tvoydonor/backups/styles.css.backup.$(date +%Y%m%d_%H%M%S)"
cp /opt/tvoydonor/website/css/styles.css "$BACKUP_FILE"
echo "✅ Резервная копия создана: $BACKUP_FILE"
EOF

echo ""
echo "Загружаем CSS на сервер..."
scp "$LOCAL_CSS" "$SERVER:/opt/tvoydonor/website/css/styles.css"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CSS успешно загружен на сервер${NC}"
else
    echo -e "${RED}❌ ОШИБКА загрузки CSS!${NC}"
    exit 1
fi

echo ""

# ============================================
# ПРОВЕРКА НА СЕРВЕРЕ
# ============================================
echo -e "${YELLOW}━━━ ШАГ 3/5: Проверка загруженного CSS ━━━${NC}"
echo ""

ssh $SERVER bash << 'EOF'
echo "Размер файла на сервере:"
ls -lh /opt/tvoydonor/website/css/styles.css

echo ""
echo "🔍 Проверяем наличие исправлений:"

if grep -q "grid-template-columns: 1fr; /\* ОДНА КОЛОНКА" /opt/tvoydonor/website/css/styles.css; then
    echo "✅ Найдено: grid-template-columns: 1fr"
else
    echo "❌ НЕ НАЙДЕНО: grid-template-columns: 1fr"
    exit 1
fi

if grep -q "font-size: 0.95rem; /\* Увеличен" /opt/tvoydonor/website/css/styles.css; then
    echo "✅ Найдено: font-size: 0.95rem"
else
    echo "❌ НЕ НАЙДЕНО: font-size: 0.95rem"
    exit 1
fi

echo ""
echo "✅ Все исправления присутствуют!"
EOF

echo ""

# ============================================
# ОБНОВЛЕНИЕ ВЕРСИИ CSS
# ============================================
echo -e "${YELLOW}━━━ ШАГ 4/5: Обновление версии CSS ━━━${NC}"
echo ""

TIMESTAMP=$(date +%s)
echo "Новая версия CSS: $TIMESTAMP"
echo ""

ssh $SERVER bash << ENDSSH
# Обновляем версию во всех HTML файлах
find /opt/tvoydonor/website -name "*.html" -type f | while read file; do
    if grep -q "styles.css" "\$file"; then
        # Заменяем существующую версию
        sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" "\$file"
        # Добавляем версию если её нет
        sed -i "s|href=\"css/styles\.css\"|href=\"css/styles.css?v=$TIMESTAMP\"|g" "\$file"
        sed -i "s|href='css/styles\.css'|href='css/styles.css?v=$TIMESTAMP'|g" "\$file"
        echo "✅ Обновлён: \$file"
    fi
done

echo ""
echo "🔍 Проверяем версию в index.html:"
grep "styles.css" /opt/tvoydonor/website/index.html | head -1

echo ""
echo "✅ Версия CSS обновлена на всех страницах"
ENDSSH

echo ""

# ============================================
# ПЕРЕЗАГРУЗКА NGINX
# ============================================
echo -e "${YELLOW}━━━ ШАГ 5/5: Перезагрузка nginx ━━━${NC}"
echo ""

ssh $SERVER bash << 'EOF'
# Проверяем конфигурацию
echo "Проверка конфигурации nginx..."
nginx -t

if [ $? -ne 0 ]; then
    echo "❌ ОШИБКА в конфигурации nginx!"
    exit 1
fi

echo ""
echo "Очистка кэша nginx..."
if [ -d "/var/cache/nginx" ]; then
    rm -rf /var/cache/nginx/*
    echo "✅ Кэш nginx очищен"
fi

echo ""
echo "Перезагрузка nginx..."
systemctl reload nginx

if [ $? -eq 0 ]; then
    echo "✅ Nginx успешно перезагружен"
else
    echo "❌ ОШИБКА перезагрузки nginx!"
    exit 1
fi
EOF

echo ""

# ============================================
# ФИНАЛЬНАЯ ПРОВЕРКА
# ============================================
echo -e "${YELLOW}━━━ ФИНАЛЬНАЯ ПРОВЕРКА ━━━${NC}"
echo ""

ssh $SERVER bash << 'EOF'
echo "1️⃣  grid-template-columns:"
grep -A 8 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep "grid-template-columns:" | head -1 | xargs

echo ""
echo "2️⃣  .contra-title font-size:"
grep -A 50 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-title" -A 4 | grep "font-size" | head -1 | xargs

echo ""
echo "3️⃣  .contra-list li font-size:"
grep -A 80 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-list li {" -A 7 | grep "font-size" | head -1 | xargs

echo ""
echo "4️⃣  Версия CSS в HTML:"
grep "styles.css" /opt/tvoydonor/website/index.html | head -1 | xargs

echo ""
echo "5️⃣  Последнее изменение CSS:"
stat /opt/tvoydonor/website/css/styles.css | grep Modify
EOF

echo ""

# ============================================
# ИТОГИ
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📱 ТЕСТИРОВАНИЕ НА ТЕЛЕФОНЕ:${NC}"
echo ""
echo "1. Откройте https://tvoydonor.by на телефоне"
echo ""
echo "2. ЖЁСТКО ОБНОВИТЕ СТРАНИЦУ (очень важно!):"
echo "   • iOS/Mac: Cmd + Shift + R"
echo "   • Android: Ctrl + Shift + R"
echo "   • Или: Настройки → Очистить кэш браузера"
echo ""
echo "3. Прокрутите до раздела 'Противопоказания'"
echo ""
echo -e "${GREEN}4. ✅ Ожидаемый результат:${NC}"
echo "   ┌────────────────────────────────────────────────┐"
echo "   │ [🔴] Постоянные противопоказания              │"
echo "   │      Донорство невозможно                     │"
echo "   │      • ВИЧ-инфекция • Онкология • Болезни... │"
echo "   ├────────────────────────────────────────────────┤"
echo "   │ [🟡] Временные противопоказания               │"
echo "   │      На определённый срок                     │"
echo "   │      • ОРВИ • Грипп • Удаление зуба...        │"
echo "   └────────────────────────────────────────────────┘"
echo ""
echo "   ✅ Каждая плашка НА ВСЮ ШИРИНУ экрана"
echo "   ✅ Текст внутри ГОРИЗОНТАЛЬНО"
echo "   ✅ Шрифт КРУПНЫЙ И ЧИТАЕМЫЙ"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📊 ТЕХНИЧЕСКИЕ ДЕТАЛИ:${NC}"
echo "   • Версия CSS: $TIMESTAMP"
echo "   • Колонки: 1 (на всю ширину)"
echo "   • Заголовок: 0.95rem (↑12%)"
echo "   • Список: 0.85rem (↑13%)"
echo "   • Иконка: 40x40px (↑11%)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}🆘 ЕСЛИ НЕ РАБОТАЕТ:${NC}"
echo "   1. Очистите кэш браузера ПОЛНОСТЬЮ"
echo "   2. Попробуйте в режиме инкогнито"
echo "   3. Проверьте версию CSS = $TIMESTAMP в DevTools"
echo "   4. Напишите мне, если проблема сохраняется"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Скрипт выполнен успешно!${NC}"
echo -e "${BLUE}📱 Проверьте результат на телефоне и напишите что получилось!${NC}"
echo ""
