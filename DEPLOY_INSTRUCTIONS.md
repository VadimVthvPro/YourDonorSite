# 🎯 ФИНАЛЬНАЯ ИНСТРУКЦИЯ ПО РАЗВЁРТЫВАНИЮ

## ✅ ЧТО БЫЛО ИСПРАВЛЕНО

1. ✅ **create_database.sql обновлён** - теперь использует `blood_requests` как основную таблицу
2. ✅ **Создан скрипт переименования таблицы** - `fix_blood_requests_table.sh`
3. ✅ **Создан безопасный скрипт развёртывания** - `deploy_safe.sh` (СОХРАНЯЕТ .env!)
4. ✅ **Добавлены все недостающие колонки** - `source`, `donor_count`, `expires_at`, `deleted_at`, `donor_id`, `medical_center_id`

---

## 🚀 ДВА СПОСОБА РАЗВЁРТЫВАНИЯ

### 🎯 СПОСОБ 1: АВТОМАТИЧЕСКОЕ РАЗВЁРТЫВАНИЕ (РЕКОМЕНДУЕТСЯ)

**На вашем Mac выполните:**

```bash
cd /Users/VadimVthv/Your_donor
./deploy_safe.sh
```

**Что делает скрипт:**
- ✅ Создаёт backup текущей версии на сервере
- ✅ **СОХРАНЯЕТ .env перед обновлением**
- ✅ Загружает только изменённые файлы (без .env!)
- ✅ **ВОССТАНАВЛИВАЕТ .env после обновления**
- ✅ Переименовывает `donation_requests` → `blood_requests`
- ✅ Создаёт VIEW `donation_requests` для совместимости
- ✅ Обновляет Python зависимости
- ✅ Перезапускает сервисы
- ✅ Тестирует API

**Введите пароль SSH**: `Vadamahjkl1!`

---

### 🔧 СПОСОБ 2: РУЧНОЕ РАЗВЁРТЫВАНИЕ (ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК)

#### Шаг 1: Исправить таблицу на сервере

```bash
cd /Users/VadimVthv/Your_donor
ssh root@178.172.212.221 "bash -s" < fix_blood_requests_table.sh
```

Пароль: `Vadamahjkl1!`

#### Шаг 2: Загрузить обновлённые файлы

**На вашем Mac:**

```bash
cd /Users/VadimVthv/Your_donor

# Архивируем БЕЗ .env
tar --exclude='.env' --exclude='website/backend/.env' \
    -czf /tmp/update.tar.gz \
    website/backend/create_database.sql \
    website/backend/app.py

# Загружаем
scp /tmp/update.tar.gz root@178.172.212.221:/tmp/
```

#### Шаг 3: На сервере

```bash
ssh root@178.172.212.221
cd /opt/tvoydonor

# ВАЖНО: Сохраняем .env
cp website/backend/.env /tmp/.env.backup

# Распаковываем
tar -xzf /tmp/update.tar.gz

# ВАЖНО: Восстанавливаем .env
cp /tmp/.env.backup website/backend/.env

# Перезапуск
supervisorctl restart all
```

---

## 🔑 СОДЕРЖИМОЕ .ENV (НА ВСЯКИЙ СЛУЧАЙ)

Если .env всё-таки слетит, создайте его заново на сервере:

```bash
ssh root@178.172.212.221
cat > /opt/tvoydonor/website/backend/.env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_donor
DB_USER=donor_user
DB_PASSWORD=u1oFnZALhyfpbtir08nH
SECRET_KEY=bbaa349e397590f4fb8d5dc41d36f523166f0ca6f09ab40ec3e94a58e4506810
MASTER_PASSWORD=doctor2024
TELEGRAM_BOT_TOKEN=8212814214:AAG29mEQN2EWS1wFvKbDqC8nr6SgN3_VeZ8
SUPER_ADMIN_TELEGRAM_USERNAME=vadimvthv
WEBSITE_URL=https://tvoydonor.by
APP_URL=https://tvoydonor.by
FLASK_DEBUG=false
PORT=5001
EOF

chmod 600 /opt/tvoydonor/website/backend/.env
supervisorctl restart all
```

---

## ✅ ПОСЛЕ РАЗВЁРТЫВАНИЯ

1. **Откройте** https://tvoydonor.by
2. **Обновите страницу** (Ctrl+R или Cmd+R)
3. **Проверьте:**
   - ✅ Дашборд медцентра (вход: polotskcgb@gmail.com / doctor2024)
   - ✅ Светофор работает (можно менять статусы группы крови)
   - ✅ Запросы крови загружаются
   - ✅ Отклики загружаются
   - ✅ Дашборд донора
   - ✅ Статистика загружается
   - ✅ Мессенджер работает

---

## 🆘 ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК

### Восстановление из backup:

```bash
ssh root@178.172.212.221
cd /opt/tvoydonor/backups

# Посмотреть доступные backup'ы
ls -lht | head -10

# Восстановить (замените имя файла!)
tar -xzf before-deploy-YYYYMMDD-HHMMSS.tar.gz -C /opt/tvoydonor/

# Восстановить .env
cp /tmp/.env.backup.YYYYMMDD-HHMMSS /opt/tvoydonor/website/backend/.env

# Перезапуск
supervisorctl restart all
```

### Проверка логов:

```bash
ssh root@178.172.212.221

# Логи Flask
tail -50 /var/log/tvoydonor-api.err.log

# Логи Telegram bot
tail -50 /var/log/tvoydonor-bot.err.log

# Статус сервисов
supervisorctl status
```

---

## 📋 КРАТКАЯ ШПАРГАЛКА

**Развёртывание:**
```bash
cd /Users/VadimVthv/Your_donor && ./deploy_safe.sh
```

**Проверка на сервере:**
```bash
ssh root@178.172.212.221
supervisorctl status
tail -30 /var/log/tvoydonor-api.err.log
```

**Восстановление .env:**
```bash
ssh root@178.172.212.221
ls -lt /tmp/.env.backup* | head -1
cp /tmp/.env.backup.XXXXXX /opt/tvoydonor/website/backend/.env
supervisorctl restart all
```

---

## 🎉 ГОТОВО!

**НАЧНИТЕ С АВТОМАТИЧЕСКОГО РАЗВЁРТЫВАНИЯ:**

```bash
cd /Users/VadimVthv/Your_donor
./deploy_safe.sh
```

Скрипт всё сделает за вас, включая сохранение .env! 🚀
