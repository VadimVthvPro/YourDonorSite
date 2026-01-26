# 🔧 ИСПРАВЛЕНИЕ МЕССЕНДЖЕРА: Пошаговая инструкция

## ШАГ 1: Загрузить файлы на сервер

```bash
cd /Users/VadimVthv/Your_donor

# SQL миграция
scp migrate_chat_messages.sql root@178.172.212.221:/tmp/

# Обновлённый JS
scp website/js/messenger.js root@178.172.212.221:/opt/tvoydonor/website/js/
```

---

## ШАГ 2: Подключиться к серверу

```bash
ssh root@178.172.212.221
```

---

## ШАГ 3: Применить миграцию БД

### Вариант A: Через postgres пользователя (рекомендуется)

```bash
# Переключаемся на postgres
sudo -u postgres psql

# Подключаемся к БД
\c your_donor

# Применяем миграцию
\i /tmp/migrate_chat_messages.sql

# Проверяем результат
\d chat_messages

# Должны увидеть:
# - sender_type (вместо sender_role)
# - message_text (вместо message)
# - message_type (новая колонка)

# Выходим
\q
```

### Вариант B: Если нужен пароль

```bash
# Узнаём пароль от БД из .env файла
cat /opt/tvoydonor/website/backend/.env | grep DATABASE_PASSWORD

# Запоминаем пароль и выполняем:
psql -U donor_user -d your_donor -f /tmp/migrate_chat_messages.sql

# Введите пароль когда попросит
```

---

## ШАГ 4: Обновить версию (cache-busting)

```bash
cd /opt/tvoydonor/website
TIMESTAMP=$(date +%s)
sed -i "s/window.VERSION = .*/window.VERSION = '${TIMESTAMP}';/" js/config.js

echo "✅ Версия обновлена: ${TIMESTAMP}"
```

---

## ШАГ 5: Перезапустить сервисы

```bash
# Проверяем Nginx
nginx -t

# Если ОК, перезагружаем
systemctl reload nginx

# Перезапускаем API
supervisorctl restart tvoydonor-api

echo "✅ Сервисы перезапущены"
```

---

## ШАГ 6: Проверить что миграция применилась

```bash
sudo -u postgres psql -d your_donor -c "\d chat_messages"
```

**Должны увидеть:**
```
 Column        | Type              
---------------+-------------------
 id            | integer          
 conversation_id | integer        
 sender_id     | integer          
 sender_type   | character varying(20)  ← ✅ НОВОЕ
 message_text  | text                   ← ✅ НОВОЕ
 message_type  | character varying(50)  ← ✅ НОВОЕ
 is_read       | boolean          
 created_at    | timestamp        
 metadata      | jsonb                  ← ✅ НОВОЕ
 read_at       | timestamp              ← ✅ НОВОЕ
 edited_at     | timestamp              ← ✅ НОВОЕ
 deleted_at    | timestamp              ← ✅ НОВОЕ
```

---

## ШАГ 7: Выйти с сервера

```bash
exit
```

---

## 🧪 ТЕСТИРОВАНИЕ

1. Откройте сайт: https://tvoydonor.by
2. Очистите кэш: **Ctrl+Shift+R**
3. Залогиньтесь как медцентр
4. Подтвердите донора (отправит клишированное сообщение)
5. Откройте мессенджер
6. ✅ **Клишированное сообщение должно быть СПРАВА**

---

## 🔄 ОТКАТ (если нужно)

```bash
ssh root@178.172.212.221
sudo -u postgres psql -d your_donor

DROP TABLE chat_messages;
ALTER TABLE chat_messages_backup RENAME TO chat_messages;

\q
exit
```

---

## ⚠️ ЕСЛИ ВОЗНИКЛИ ПРОБЛЕМЫ

### Проблема: "password authentication failed"

**Решение:** Используйте `sudo -u postgres psql` (без пароля)

### Проблема: "column sender_type does not exist"

**Решение:** Миграция не применилась, повторите ШАГ 3

### Проблема: Сообщения всё ещё слева

**Решение:** Очистите кэш браузера (**Ctrl+Shift+R**)

---

**Начните с ШАГа 1! 🚀**
