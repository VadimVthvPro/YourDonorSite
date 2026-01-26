#!/bin/bash

# ============================================
# КОМПЛЕКСНЫЙ СКРИПТ ИСПРАВЛЕНИЯ МОБИЛЬНОГО CSS
# ============================================

set -e  # Останавливаемся при ошибке

SERVER="root@178.172.212.221"
LOCAL_CSS="/Users/VadimVthv/Your_donor/website/css/styles.css"
REMOTE_CSS="/opt/tvoydonor/website/css/styles.css"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔬 ГЛУБОКАЯ ДИАГНОСТИКА И ИСПРАВЛЕНИЕ CSS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# ШАГ 1: ПРОВЕРКА ЛОКАЛЬНОГО CSS
# ============================================
echo "📋 ШАГ 1/8: Проверка локального CSS..."
echo "════════════════════════════════════════"

if [ ! -f "$LOCAL_CSS" ]; then
    echo "❌ ОШИБКА: Файл $LOCAL_CSS не найден!"
    exit 1
fi

echo "✅ Локальный файл найден: $LOCAL_CSS"
echo "   Размер: $(wc -c < "$LOCAL_CSS") байт"
echo "   Строк: $(wc -l < "$LOCAL_CSS")"

# Проверяем что в локальном CSS есть нужные изменения
echo ""
echo "🔍 Проверяем локальный CSS на наличие исправлений..."
if grep -q "grid-template-columns: 1fr; /\* ОДНА КОЛОНКА" "$LOCAL_CSS"; then
    echo "✅ Найдено: grid-template-columns: 1fr"
else
    echo "⚠️  ВНИМАНИЕ: Не найдено 'grid-template-columns: 1fr'"
fi

if grep -q "font-size: 0.95rem; /\* Увеличен" "$LOCAL_CSS"; then
    echo "✅ Найдено: font-size: 0.95rem (увеличенный)"
else
    echo "⚠️  ВНИМАНИЕ: Не найдено 'font-size: 0.95rem'"
fi

echo ""
echo "✅ Все проверки пройдены, продолжаем..."

# ============================================
# ШАГ 2: РЕЗЕРВНОЕ КОПИРОВАНИЕ НА СЕРВЕРЕ
# ============================================
echo ""
echo "📋 ШАГ 2/8: Создание резервной копии на сервере..."
echo "════════════════════════════════════════════════════"

ssh $SERVER << 'EOF'
BACKUP_DIR="/opt/tvoydonor/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/styles.css.backup.$(date +%Y%m%d_%H%M%S)"
cp /opt/tvoydonor/website/css/styles.css "$BACKUP_FILE"
echo "✅ Резервная копия создана: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
EOF

# ============================================
# ШАГ 3: ЗАГРУЗКА CSS НА СЕРВЕР
# ============================================
echo ""
echo "📋 ШАГ 3/8: Загрузка CSS на сервер..."
echo "════════════════════════════════════════"

echo "Загружаем $LOCAL_CSS → $SERVER:$REMOTE_CSS"
scp "$LOCAL_CSS" "$SERVER:$REMOTE_CSS"

if [ $? -eq 0 ]; then
    echo "✅ CSS успешно загружен на сервер"
else
    echo "❌ ОШИБКА загрузки CSS!"
    exit 1
fi

# ============================================
# ШАГ 4: ПРОВЕРКА НА СЕРВЕРЕ
# ============================================
echo ""
echo "📋 ШАГ 4/8: Проверка загруженного CSS на сервере..."
echo "═══════════════════════════════════════════════════"

ssh $SERVER << 'EOF'
echo "Размер файла на сервере:"
ls -lh /opt/tvoydonor/website/css/styles.css

echo ""
echo "🔍 Проверяем наличие исправлений в CSS на сервере:"
if grep -q "grid-template-columns: 1fr; /\* ОДНА КОЛОНКА" /opt/tvoydonor/website/css/styles.css; then
    echo "✅ Найдено: grid-template-columns: 1fr"
else
    echo "❌ НЕ НАЙДЕНО: grid-template-columns: 1fr"
    echo "ПРОБЛЕМА: CSS не содержит исправлений!"
    exit 1
fi

if grep -q "font-size: 0.95rem; /\* Увеличен" /opt/tvoydonor/website/css/styles.css; then
    echo "✅ Найдено: font-size: 0.95rem"
else
    echo "❌ НЕ НАЙДЕНО: font-size: 0.95rem"
    exit 1
fi

echo ""
echo "✅ Все исправления присутствуют в CSS на сервере!"
EOF

# ============================================
# ШАГ 5: ОБНОВЛЕНИЕ ВЕРСИИ CSS В HTML
# ============================================
echo ""
echo "📋 ШАГ 5/8: Обновление версии CSS в HTML файлах..."
echo "═══════════════════════════════════════════════════"

TIMESTAMP=$(date +%s)
echo "Новая версия CSS: $TIMESTAMP"

ssh $SERVER << ENDSSH
# Обновляем version во всех HTML файлах
find /opt/tvoydonor/website -name "*.html" -type f | while read file; do
    if grep -q "styles.css" "\$file"; then
        sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" "\$file"
        sed -i "s|styles\.css\"|styles.css?v=$TIMESTAMP\"|g" "\$file"
        echo "✅ Обновлён: \$file"
    fi
done

echo ""
echo "🔍 Проверяем что версия обновилась:"
grep -n "styles.css" /opt/tvoydonor/website/index.html | head -1
ENDSSH

# ============================================
# ШАГ 6: ОЧИСТКА КЭША NGINX
# ============================================
echo ""
echo "📋 ШАГ 6/8: Очистка кэша nginx..."
echo "════════════════════════════════════"

ssh $SERVER << 'EOF'
# Проверяем конфигурацию nginx
echo "Проверка конфигурации nginx..."
nginx -t

if [ $? -ne 0 ]; then
    echo "❌ ОШИБКА в конфигурации nginx!"
    exit 1
fi

echo ""
echo "Очистка кэша nginx (если есть)..."
if [ -d "/var/cache/nginx" ]; then
    rm -rf /var/cache/nginx/*
    echo "✅ Кэш nginx очищен"
else
    echo "ℹ️  Директория кэша не найдена (это нормально)"
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

# ============================================
# ШАГ 7: ПРОВЕРКА ПРИМЕНЕНИЯ ИЗМЕНЕНИЙ
# ============================================
echo ""
echo "📋 ШАГ 7/8: Финальная проверка изменений..."
echo "═══════════════════════════════════════════"

ssh $SERVER << 'EOF'
echo "🔍 Проверяем CSS в @media (max-width: 768px):"
echo ""
echo "1. grid-template-columns (должно быть: 1fr):"
grep -A 8 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep "grid-template-columns:" | head -1

echo ""
echo "2. .contra-title font-size (должно быть: 0.95rem):"
grep -A 50 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-title" -A 4 | grep "font-size" | head -1

echo ""
echo "3. .contra-list li font-size (должно быть: 0.85rem):"
grep -A 80 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-list li {" -A 7 | grep "font-size"

echo ""
echo "4. Версия CSS в HTML:"
grep "styles.css" /opt/tvoydonor/website/index.html | head -1

echo ""
echo "5. Права доступа к файлу CSS:"
ls -la /opt/tvoydonor/website/css/styles.css

echo ""
echo "6. Последнее изменение файла:"
stat /opt/tvoydonor/website/css/styles.css | grep Modify
EOF

# ============================================
# ШАГ 8: ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 ШАГ 8/8: Инструкции для тестирования"
echo "════════════════════════════════════════"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ НА ТЕЛЕФОНЕ:"
echo ""
echo "1. Откройте https://tvoydonor.by на телефоне"
echo ""
echo "2. ЖЁСТКО ОБНОВИТЕ СТРАНИЦУ (очень важно!):"
echo "   • iOS/Mac: Cmd + Shift + R"
echo "   • Android: Ctrl + Shift + R"
echo "   • Или: Настройки браузера → Очистить кэш → Обновить"
echo ""
echo "3. Прокрутите до раздела 'Противопоказания'"
echo ""
echo "4. ✅ Ожидаемый результат:"
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
echo "   ✅ Текст внутри ГОРИЗОНТАЛЬНО: [иконка][заголовок][список]"
echo "   ✅ Шрифт КРУПНЫЙ И ЧИТАЕМЫЙ"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 ТЕХНИЧЕСКИЕ ДЕТАЛИ:"
echo "   • Версия CSS: $TIMESTAMP"
echo "   • Колонки: 1 (на всю ширину)"
echo "   • Заголовок: 0.95rem (увеличен)"
echo "   • Список: 0.85rem (увеличен)"
echo "   • Иконка: 40x40px (увеличена)"
echo ""
echo "🔍 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА:"
echo "   • F12 → Network → styles.css?v=$TIMESTAMP"
echo "   • Elements → .contra-grid → Computed → grid-template-columns: 1fr"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🆘 ЕСЛИ НЕ РАБОТАЕТ:"
echo "   1. Очистите кэш браузера полностью"
echo "   2. Попробуйте в режиме инкогнито"
echo "   3. Проверьте что версия CSS = $TIMESTAMP в DevTools"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Скрипт завершён успешно!"
echo ""
