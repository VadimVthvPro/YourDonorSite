# Конфигурация Nginx для tvoydonor.by

## Необходимые настройки для location /api/

Убедитесь, что в вашем `/etc/nginx/sites-available/tvoydonor` есть следующий блок:

```nginx
server {
    listen 443 ssl;
    server_name tvoydonor.by www.tvoydonor.by;
    
    # SSL сертификаты
    ssl_certificate /path/to/certificate.pem;
    ssl_certificate_key /path/to/private.key;
    
    # Статические файлы
    root /var/www/tvoydonor/website;
    index index.html;
    
    # Проксирование API запросов на Flask
    location /api/ {
        # ВАЖНО: передаём запросы на Flask
        proxy_pass http://127.0.0.1:5001/api/;
        
        # Необходимые заголовки для корректной работы
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS заголовки (на случай если Flask не отдаёт)
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        
        # Обработка preflight OPTIONS запросов
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With";
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # HTML файлы (SPA routing)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## После изменения конфигурации:

```bash
# Проверить синтаксис
sudo nginx -t

# Перезагрузить nginx
sudo systemctl reload nginx
```

## Проверка работоспособности:

```bash
# Должен вернуть JSON с регионами
curl -v https://tvoydonor.by/api/regions
```

## Важно!

1. **Не используйте порт 5001 в браузере** - Nginx проксирует запросы
2. **Flask должен быть запущен** на порту 5001 локально
3. **CORS настроен в Flask** - не дублируйте слишком много заголовков в Nginx
