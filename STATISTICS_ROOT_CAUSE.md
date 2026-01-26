# 🔬 НАЙДЕНА КОРНЕВАЯ ПРОБЛЕМА!

## 🔴 КРИТИЧЕСКАЯ ОШИБКА

### Проблема: Две функции загрузки статистики

**Есть ДВЕ функции:**

1. **`loadUserData()`** (строка 917) - загружает из `localStorage`
   - Вызывается ВСЕГДА при загрузке страницы
   - Обновляет элементы: `stat-donations`, `total-volume`, `lives-saved`
   - Источник данных: `localStorage.getItem('donor_donations')`
   - **ПРОБЛЕМА:** `localStorage` НЕ обновляется автоматически!

2. **`loadDonationStatistics()`** (строка 2080) - загружает из API
   - Вызывается только при инициализации
   - Обновляет элементы: `hero-donations`, `drop-donations`, `stat-total-donations`
   - Источник данных: `GET /api/donor/statistics`
   - **ПРОБЛЕМА:** Не обновляет главную статистику на sidebar!

---

## 📊 ТЕКУЩИЙ ПОТОК ДАННЫХ

```
1. Страница загружается
   ↓
2. checkAuthAndRestore() ✅
   ↓
3. loadUserDataFromAPI() ✅
   ↓  (Загружает profile, сохраняет в localStorage)
   ↓
4. loadDonationStatistics() ✅ (добавили мы)
   ↓  (Загружает статистику из API)
   ↓
5. НО! loadUserData() НЕ вызывается после loadDonationStatistics()!
   ↓
6. Элементы stat-donations, total-volume ПУСТЫЕ! ❌
```

---

## ✅ РЕШЕНИЕ

### Вариант 1: Обновить `loadUserData()` чтобы брать из API

```javascript
async function loadUserData() {
    const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
    
    // Имя пользователя
    const fio = userData.full_name || userData.fio || 'Пользователь';
    document.getElementById('user-name').textContent = fio;
    document.getElementById('user-initials').textContent = getInitials(fio);
    
    // ✅ ИСПРАВЛЕНИЕ: Загружаем статистику из API, а не из localStorage
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/statistics`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const stats = await response.json();
            
            // Обновляем главную статистику (sidebar)
            document.getElementById('stat-donations').textContent = stats.total_donations || 0;
            document.getElementById('total-volume').textContent = ((stats.total_volume_ml || 0) / 1000).toFixed(1) + ' л';
            document.getElementById('lives-saved').textContent = stats.lives_saved_estimate || 0;
            
            // Обновляем информацию о последней донации
            if (stats.last_donation_date) {
                const lastDate = new Date(stats.last_donation_date);
                document.getElementById('info-last-donation').textContent = formatDate(lastDate);
                
                // Расчёт дней до следующей донации
                if (stats.days_until_next !== null) {
                    if (stats.can_donate) {
                        document.getElementById('stat-next').textContent = 'Готов';
                        document.getElementById('stat-status').textContent = 'Готов';
                    } else {
                        document.getElementById('stat-next').textContent = `${stats.days_until_next} дн.`;
                        document.getElementById('stat-status').textContent = 'Восст.';
                    }
                }
            } else {
                document.getElementById('info-last-donation').textContent = 'Ещё не сдавали';
                document.getElementById('stat-next').textContent = 'Готов';
                document.getElementById('stat-status').textContent = 'Готов';
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        // Fallback к localStorage если API недоступен
        const donations = parseInt(userData.total_donations || localStorage.getItem('donor_donations') || '0');
        document.getElementById('stat-donations').textContent = donations;
        document.getElementById('total-volume').textContent = donations * 450 + ' мл';
        document.getElementById('lives-saved').textContent = donations * 3;
    }
    
    // Информация о профиле
    const bloodType = userData.blood_type || '—';
    document.getElementById('info-blood-type').textContent = bloodType;
    
    // ... остальной код ...
}
```

### Вариант 2: Вызывать `renderDonationStatistics()` после `loadDonationStatistics()`

```javascript
async function loadDonationStatistics() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/statistics`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            console.error('Ошибка загрузки статистики:', response.status);
            return;
        }
        
        const stats = await response.json();
        console.log('Статистика загружена:', stats);
        
        // ✅ ДОБАВИТЬ: Обновляем главную статистику (sidebar)
        updateMainStatistics(stats);
        
        // Рендерим детальную статистику
        renderDonationStatistics(stats);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// ✅ НОВАЯ ФУНКЦИЯ
function updateMainStatistics(stats) {
    // Обновляем sidebar статистику
    document.getElementById('stat-donations').textContent = stats.total_donations || 0;
    
    const volumeLiters = ((stats.total_volume_ml || 0) / 1000).toFixed(1);
    document.getElementById('total-volume').textContent = volumeLiters + ' л';
    document.getElementById('lives-saved').textContent = stats.lives_saved_estimate || 0;
    
    // Обновляем последнюю донацию
    if (stats.last_donation_date) {
        document.getElementById('info-last-donation').textContent = formatDateShort(stats.last_donation_date);
        
        if (stats.days_until_next !== null) {
            if (stats.can_donate) {
                document.getElementById('stat-next').textContent = 'Готов';
                document.getElementById('stat-status').textContent = 'Готов';
            } else {
                document.getElementById('stat-next').textContent = `${stats.days_until_next} дн.`;
                document.getElementById('stat-status').textContent = 'Восст.';
            }
        }
    }
}
```

---

## 🎯 РЕКОМЕНДУЕМОЕ РЕШЕНИЕ

**Используем Вариант 2** - он проще и безопаснее:

1. Добавляем функцию `updateMainStatistics(stats)`
2. Вызываем её в `loadDonationStatistics()` перед `renderDonationStatistics()`
3. Оставляем `loadUserData()` без изменений (fallback)

---

## 📝 ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| Файл | Что делать |
|------|-----------|
| `donor-dashboard.js` | Добавить `updateMainStatistics()` и вызвать в `loadDonationStatistics()` |

---

## 🧪 ТЕСТ ПОСЛЕ ИСПРАВЛЕНИЯ

1. Открыть donor dashboard
2. ✅ В sidebar должна отображаться статистика:
   - Количество донаций
   - Объём крови (в литрах)
   - Спасённые жизни
3. ✅ Открыть консоль браузера:
   - Должно быть: "Статистика загружена: {total_donations: X, ...}"

---

**Готов создать исправленный файл!** 🚀
