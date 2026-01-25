# 🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ ОСТАВШИХСЯ ОШИБОК

## ❌ ПРОБЛЕМЫ

1. **500 ошибка** на `/api/medcenter/10/blood-requests`
2. **Telegram рассылка** не работает при изменении светофора

---

## 🔍 ШАГ 1: ДИАГНОСТИКА

**На вашем Mac выполните:**

```bash
cd /Users/VadimVthv/Your_donor
ssh root@178.172.212.221 "bash -s" < check_errors.sh
```

Пароль: `Vadamahjkl1!`

**Пришлите мне вывод!** Я увижу:
- ✅ Существует ли таблица `blood_requests`
- ✅ Есть ли колонки `source`, `donor_count`, `expires_at`
- ✅ Какие конкретные ошибки в логах
- ✅ Что возвращает API

---

## 🛠️ ШАГ 2: БЫСТРОЕ ИСПРАВЛЕНИЕ

Пока выполняется диагностика, попробуйте это на сервере:

```bash
ssh root@178.172.212.221
```

Затем выполните:

```bash
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

# Проверяем существование таблицы
psql -U donor_user -h localhost your_donor << 'SQL'

-- Если donation_requests всё ещё существует, переименовываем
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'donation_requests' AND table_type = 'BASE TABLE') THEN
        DROP VIEW IF EXISTS blood_requests CASCADE;
        ALTER TABLE donation_requests RENAME TO blood_requests;
        RAISE NOTICE 'Таблица переименована';
    END IF;
END $$;

-- Проверяем наличие колонок
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'web';
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS donor_count INTEGER DEFAULT 0;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

-- Создаём VIEW для совместимости
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

-- Проверяем результат
\d blood_requests

SQL

# Перезапуск
supervisorctl restart all
sleep 2
supervisorctl status
```

---

## 📋 ПРОВЕРКА TELEGRAM БОТА

```bash
# На сервере проверьте логи бота
tail -50 /var/log/tvoydonor-bot.err.log

# Статус бота
supervisorctl status tvoydonor-bot

# Если бот не запущен
supervisorctl restart tvoydonor-bot
```

---

## 🔧 ЕСЛИ ПРОБЛЕМА С TELEGRAM РАССЫЛКОЙ

Проверьте что в `.env` правильный токен бота:

```bash
# На сервере
cat /opt/tvoydonor/website/backend/.env | grep TELEGRAM

# Должен быть:
# TELEGRAM_BOT_TOKEN=8212814214:AAG29mEQN2EWS1wFvKbDqC8nr6SgN3_VeZ8
```

---

## ✅ ПОСЛЕ ИСПРАВЛЕНИЙ

1. Обновите браузер (Ctrl+R)
2. Попробуйте изменить статус светофора
3. Проверьте:
   - ✅ Запросы крови загружаются
   - ✅ Telegram уведомления отправляются
   - ✅ Нет ошибок 500

---

**НАЧНИТЕ С ДИАГНОСТИКИ И ПРИШЛИТЕ МНЕ РЕЗУЛЬТАТ!** 🔍
