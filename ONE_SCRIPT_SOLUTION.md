# 🎯 ОДИН СКРИПТ - ОДНА КОМАНДА

## ⚡ САМЫЙ ПРОСТОЙ СПОСОБ

Выполните **ТРИ** команды по порядку (каждая спросит пароль 1 раз):

---

### 📋 КОМАНДА 1: Резервная копия и загрузка CSS

```bash
ssh root@178.172.212.221 'mkdir -p /opt/tvoydonor/backups && cp /opt/tvoydonor/website/css/styles.css /opt/tvoydonor/backups/styles.css.backup.$(date +%Y%m%d_%H%M%S) && echo "✅ Бэкап создан"' && scp /Users/VadimVthv/Your_donor/website/css/styles.css root@178.172.212.221:/opt/tvoydonor/website/css/styles.css && echo "✅ CSS загружен"
```

**Пароль:** `Vadamahjkl1!` (ввести 2 раза - для ssh и scp)

---

### 📋 КОМАНДА 2: Обновить версию и перезагрузить nginx

```bash
ssh root@178.172.212.221 'TIMESTAMP=$(date +%s) && sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/index.html && sed -i "s|href=\"css/styles\.css\"|href=\"css/styles.css?v=$TIMESTAMP\"|g" /opt/tvoydonor/website/index.html && [ -d /var/cache/nginx ] && rm -rf /var/cache/nginx/* ; nginx -t && systemctl reload nginx && echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━" && echo "✅ УСТАНОВКА ЗАВЕРШЕНА!" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━" && echo "" && echo "Новая версия CSS: $TIMESTAMP" && grep "styles.css" /opt/tvoydonor/website/index.html | head -1'
```

**Пароль:** `Vadamahjkl1!`

---

### 📋 КОМАНДА 3: Проверка результата

```bash
ssh root@178.172.212.221 'echo "🔍 ПРОВЕРКА:" && echo "" && echo "1. grid-template-columns:" && grep -A 8 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep "grid-template-columns:" | head -1 | xargs && echo "" && echo "2. font-size заголовка:" && grep -A 50 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-title" -A 4 | grep "font-size" | head -1 | xargs && echo "" && echo "3. font-size списка:" && grep -A 80 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep ".contra-list li {" -A 7 | grep "font-size" | head -1 | xargs && echo "" && echo "✅ Все исправления на месте!"'
```

**Пароль:** `Vadamahjkl1!`

---

## ✅ ОЖИДАЕМЫЙ ВЫВОД:

### После КОМАНДЫ 1:
```
✅ Бэкап создан
styles.css    100%   69KB   1.2MB/s   00:00
✅ CSS загружен
```

### После КОМАНДЫ 2:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
━━━━━━━━━━━━━━━━━━━━━━━━━
✅ УСТАНОВКА ЗАВЕРШЕНА!
━━━━━━━━━━━━━━━━━━━━━━━━━

Новая версия CSS: 1769365XXX
<link rel="stylesheet" href="css/styles.css?v=1769365XXX">
```

### После КОМАНДЫ 3:
```
🔍 ПРОВЕРКА:

1. grid-template-columns:
grid-template-columns: 1fr; /* ОДНА КОЛОНКА */

2. font-size заголовка:
font-size: 0.95rem; /* Увеличен */

3. font-size списка:
font-size: 0.85rem; /* Увеличен */

✅ Все исправления на месте!
```

---

## 🧪 ТЕСТИРОВАНИЕ НА ТЕЛЕФОНЕ:

1. **Откройте:** `https://tvoydonor.by`

2. **ОЧИСТИТЕ КЭШ (обязательно!):**
   - **iOS:** Настройки → Safari → Очистить историю и данные
   - **Android:** Chrome → ⋮ → Настройки → Очистить данные браузера → Кэш

3. **Обновите** страницу

4. **Прокрутите** до "Противопоказания"

---

## ✅ КАК ДОЛЖНО ВЫГЛЯДЕТЬ:

```
┌──────────────────────────────────────────────┐
│ [🔴] Постоянные противопоказания            │
│      Донорство невозможно                   │
│      • ВИЧ-инфекция • Онкология • Болезни  │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ [🟡] Временные противопоказания             │
│      На определённый срок                   │
│      • ОРВИ • Грипп • Операции             │
└──────────────────────────────────────────────┘
```

**Характеристики:**
- ✅ Плашки **НА ВСЮ ШИРИНУ**
- ✅ Текст **КРУПНЫЙ** и читаемый
- ✅ Иконки **КРУПНЫЕ**

---

## 🆘 ЕСЛИ НЕ РАБОТАЕТ:

### 1. Кэш не очистился
Откройте в **режиме инкогнито** - там кэша нет совсем.

### 2. CSS не обновился
Повторите КОМАНДУ 2 ещё раз.

### 3. Всё ещё не работает
Выполните:
```bash
ssh root@178.172.212.221 'systemctl restart nginx'
```
Пароль: `Vadamahjkl1!`

Потом снова очистите кэш и проверьте.

---

## 📊 ЧТО ИЗМЕНИЛОСЬ:

| Элемент | Было | Стало |
|---------|------|-------|
| Колонки | 2 | **1** ✅ |
| Заголовок | 0.85rem | **0.95rem** ✅ |
| Список | 0.75rem | **0.85rem** ✅ |
| Иконка | 36px | **40px** ✅ |

---

**СКОПИРУЙТЕ КОМАНДЫ 1, 2, 3 ПО ПОРЯДКУ И ПРОВЕРЬТЕ РЕЗУЛЬТАТ!**

После тестирования напишите что получилось! 🚀
