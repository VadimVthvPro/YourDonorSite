# ⚡ БЫСТРАЯ ШПАРГАЛКА

## 🔥 ПРЯМО СЕЙЧАС: ИСПРАВИТЬ СЕРВЕР

```bash
cd /Users/VadimVthv/Your_donor
ssh root@178.172.212.221 "bash -s" < server_fix.sh
```

Введите пароль: `Vadamahjkl1!`

---

## 🚀 ЗАГРУЗИТЬ ОБНОВЛЕНИЯ НА СЕРВЕР

```bash
cd /Users/VadimVthv/Your_donor
./deploy_to_server.sh
```

---

## 🔐 ВОССТАНОВИТЬ .ENV НА СЕРВЕРЕ

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

## 🧪 ПРОВЕРКА РАБОТЫ

```bash
ssh root@178.172.212.221
supervisorctl status
curl http://localhost:5001/api/regions
```

---

## 💾 BACKUP БД

```bash
ssh root@178.172.212.221
cd /opt/tvoydonor/backups
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
pg_dump -U donor_user -h localhost your_donor > backup-$(date +%Y%m%d-%H%M%S).sql
```

---

## 🔄 ПЕРЕЗАПУСК СЕРВИСОВ

```bash
ssh root@178.172.212.221
supervisorctl restart all
```

---

## 🔑 ПАРОЛИ

- **SSH**: Vadamahjkl1!
- **БД сервер**: u1oFnZALhyfpbtir08nH
- **БД локал**: yourdonorishere
- **IP**: 178.172.212.221
- **Домен**: tvoydonor.by

---

## 📄 ПОДРОБНЫЕ ИНСТРУКЦИИ

Смотрите: `FIX_INSTRUCTIONS.md`
