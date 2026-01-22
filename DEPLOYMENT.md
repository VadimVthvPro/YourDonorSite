# 🚀 Руководство по развертыванию BloodDonorBot

## 📋 Предварительные требования

### Системные требования:
- **ОС**: Linux (Ubuntu 20.04+), macOS, Windows 10+
- **Python**: 3.8 или выше
- **PostgreSQL**: 12 или выше
- **RAM**: минимум 512 MB
- **Дисковое пространство**: минимум 100 MB

### Необходимые инструменты:
- Git
- pip (менеджер пакетов Python)
- psql (клиент PostgreSQL)

## 🛠️ Пошаговая установка

### Шаг 1: Подготовка системы

#### Ubuntu/Debian:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и pip
sudo apt install python3 python3-pip python3-venv -y

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка Git
sudo apt install git -y
```

#### macOS:
```bash
# Установка Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка Python
brew install python

# Установка PostgreSQL
brew install postgresql

# Установка Git
brew install git
```

#### Windows:
1. Скачайте и установите Python с [python.org](https://python.org)
2. Скачайте и установите PostgreSQL с [postgresql.org](https://postgresql.org)
3. Скачайте и установите Git с [git-scm.com](https://git-scm.com)

### Шаг 2: Клонирование проекта

```bash
# Клонирование репозитория
git clone <repository-url>
cd blood_donor_bot

# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Шаг 3: Установка зависимостей

```bash
# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 4: Настройка базы данных PostgreSQL

#### Создание пользователя и базы данных:

```bash
# Подключение к PostgreSQL
sudo -u postgres psql

# Создание пользователя (замените 'your_password' на свой пароль)
CREATE USER blood_donor_user WITH PASSWORD 'your_password';

# Создание базы данных
CREATE DATABASE blood_donor_bot OWNER blood_donor_user;

# Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE blood_donor_bot TO blood_donor_user;

# Выход из psql
\q
```

#### Выполнение SQL скрипта:

```bash
# Выполнение скрипта создания таблиц
psql -U blood_donor_user -d blood_donor_bot -f create_database.sql
```

### Шаг 5: Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: "BloodDonorBot")
   - Введите username бота (например: "blood_donor_bot")
4. Скопируйте полученный токен

### Шаг 6: Настройка переменных окружения

```bash
# Создание файла .env
cp env_example.txt .env

# Редактирование файла .env
nano .env
```

Содержимое файла `.env`:
```env
# Telegram Bot Token
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Database Configuration
DB_HOST=localhost
DB_NAME=blood_donor_bot
DB_USER=blood_donor_user
DB_PASSWORD=your_password
DB_PORT=5432
```

### Шаг 7: Тестирование установки

```bash
# Запуск тестов
python test_bot.py

# Запуск бота в тестовом режиме
python bot.py
```

## 🔧 Конфигурация для продакшена

### Настройка systemd (Linux):

Создайте файл службы `/etc/systemd/system/blood-donor-bot.service`:

```ini
[Unit]
Description=BloodDonorBot Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=blood_donor_user
WorkingDirectory=/path/to/blood_donor_bot
Environment=PATH=/path/to/blood_donor_bot/venv/bin
ExecStart=/path/to/blood_donor_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация службы:
```bash
sudo systemctl daemon-reload
sudo systemctl enable blood-donor-bot
sudo systemctl start blood-donor-bot
```

### Настройка supervisor (альтернатива):

Создайте файл `/etc/supervisor/conf.d/blood-donor-bot.conf`:

```ini
[program:blood-donor-bot]
command=/path/to/blood_donor_bot/venv/bin/python /path/to/blood_donor_bot/bot.py
directory=/path/to/blood_donor_bot
user=blood_donor_user
autostart=true
autorestart=true
stderr_logfile=/var/log/blood-donor-bot.err.log
stdout_logfile=/var/log/blood-donor-bot.out.log
```

### Настройка nginx (опционально):

Создайте файл `/etc/nginx/sites-available/blood-donor-bot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Мониторинг и логирование

### Настройка логирования:

Создайте файл `logging.conf`:

```ini
[loggers]
keys=root,blood_donor_bot

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=normalFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_blood_donor_bot]
level=INFO
handlers=consoleHandler,fileHandler
qualname=blood_donor_bot
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=normalFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=normalFormatter
args=('logs/blood_donor_bot.log', 'a')

[formatter_normalFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Создание директории для логов:

```bash
mkdir -p logs
chmod 755 logs
```

## 🔒 Безопасность

### Рекомендации по безопасности:

1. **Измените мастер-пароль для врачей** в файле `bot.py`:
   ```python
   MASTER_PASSWORD = "your_secure_password_here"
   ```

2. **Ограничьте доступ к базе данных**:
   ```bash
   # В файле pg_hba.conf
   host blood_donor_bot blood_donor_user 127.0.0.1/32 md5
   ```

3. **Настройте файрвол**:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 5432/tcp
   sudo ufw enable
   ```

4. **Регулярные резервные копии**:
   ```bash
   # Создание скрипта резервного копирования
   #!/bin/bash
   pg_dump -U blood_donor_user blood_donor_bot > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

## 🚨 Устранение неполадок

### Частые проблемы:

1. **Ошибка подключения к базе данных**:
   ```bash
   # Проверка статуса PostgreSQL
   sudo systemctl status postgresql
   
   # Проверка подключения
   psql -U blood_donor_user -d blood_donor_bot -h localhost
   ```

2. **Бот не отвечает**:
   ```bash
   # Проверка токена
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   
   # Проверка логов
   tail -f logs/blood_donor_bot.log
   ```

3. **Ошибки при регистрации**:
   - Проверьте формат даты (ДД.ММ.ГГГГ)
   - Убедитесь, что группа крови указана правильно
   - Проверьте подключение к базе данных

### Команды для диагностики:

```bash
# Проверка статуса службы
sudo systemctl status blood-donor-bot

# Просмотр логов
sudo journalctl -u blood-donor-bot -f

# Проверка подключения к базе данных
python -c "import psycopg2; psycopg2.connect(host='localhost', database='blood_donor_bot', user='blood_donor_user', password='your_password')"

# Тестирование бота
python test_bot.py
```

## 📈 Масштабирование

### Для высоких нагрузок:

1. **Настройка пула соединений**:
   ```python
   # В bot.py добавьте:
   from psycopg2.pool import SimpleConnectionPool
   
   # Создание пула соединений
   pool = SimpleConnectionPool(1, 20, **self.db_config)
   ```

2. **Кэширование**:
   ```bash
   # Установка Redis
   sudo apt install redis-server
   
   # Установка Python Redis
   pip install redis
   ```

3. **Балансировка нагрузки**:
   - Используйте несколько экземпляров бота
   - Настройте nginx для балансировки
   - Используйте Docker для контейнеризации

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `tail -f logs/blood_donor_bot.log`
2. Запустите тесты: `python test_bot.py`
3. Проверьте подключение к базе данных
4. Убедитесь, что все зависимости установлены

---

**Важно**: Этот бот предназначен для образовательных целей. В продакшене обязательно добавьте дополнительные меры безопасности и мониторинга. 