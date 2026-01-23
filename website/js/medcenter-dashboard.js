/**
 * Твой Донор - Личный кабинет медцентра
 * Управление донорством, светофор, отклики
 */

console.log('==== medcenter-dashboard.js ЗАГРУЖЕН ====');

// Используем API_URL из app.js или определяем свой
const MC_API_URL = window.API_URL || 'http://localhost:5001/api';

/**
 * Форматирование чисел с разделением на триады (пробелами)
 * Пример: 1000000 → "1 000 000"
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

/**
 * Форматирование объёма (мл → литры с триадами)
 * Пример: 450000 → "450 л"
 */
function formatVolume(ml) {
    if (!ml || ml === 0) return '0 л';
    const liters = (ml / 1000).toFixed(1);
    // Убираем .0 если целое число
    const cleanLiters = liters.replace(/\.0$/, '');
    return formatNumber(cleanLiters) + ' л';
}

// Кэш для запросов крови
let bloodRequestsCache = [];
// Кэш для откликов доноров
let responsesCache = [];

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Инициализация dashboard медцентра ===');
    
    if (!checkAuth()) {
        console.warn('Авторизация не пройдена, перенаправление...');
        window.location.href = 'auth.html?type=medcenter';
        return;
    }
    
    console.log('✓ Авторизация OK');
    
    // Синхронные функции - критически важные
    try {
        initNavigation();
        console.log('✓ Навигация инициализирована');
    } catch (e) { console.error('✗ Ошибка initNavigation:', e); }
    
    try {
        initMobileSidebar();
        console.log('✓ Мобильный sidebar инициализирован');
    } catch (e) { console.error('✗ Ошибка initMobileSidebar:', e); }
    
    try {
        initModals();
        console.log('✓ Модальные окна инициализированы');
    } catch (e) { console.error('✗ Ошибка initModals:', e); }
    
    try {
        initForms();
        console.log('✓ Формы инициализированы');
    } catch (e) { console.error('✗ Ошибка initForms:', e); }
    
    try {
        initRequestFilters();
        console.log('✓ Фильтры запросов инициализированы');
    } catch (e) { console.error('✗ Ошибка initRequestFilters:', e); }
    
    try {
        initLogout();
        console.log('✓ Выход инициализирован');
    } catch (e) { console.error('✗ Ошибка initLogout:', e); }
    
    // Инициализация мессенджера
    try {
        initMessenger();
        console.log('✓ Мессенджер инициализирован');
    } catch (e) { console.error('✗ Ошибка initMessenger:', e); }
    
    // Асинхронные функции - загрузка данных (последовательно, чтобы данные загрузились)
    (async () => {
        try {
            await loadMedcenterData();
            console.log('✓ Данные медцентра загружены');
            
            // После загрузки данных медцентра загружаем остальное
            await Promise.all([
                loadTrafficLightFromAPI().then(() => console.log('✓ Светофор загружен')).catch(e => console.error('✗ Ошибка светофора:', e)),
                loadBloodRequestsFromAPI().then(() => console.log('✓ Запросы крови загружены')).catch(e => console.error('✗ Ошибка запросов:', e)),
                loadResponsesFromAPI().then(() => console.log('✓ Отклики загружены')).catch(e => console.error('✗ Ошибка откликов:', e)),
                loadDonorsFromAPI().then(() => console.log('✓ Доноры загружены')).catch(e => console.error('✗ Ошибка доноров:', e)),
                loadStatisticsFromAPI().then(() => console.log('✓ Статистика загружена')).catch(e => console.error('✗ Ошибка статистики:', e))
            ]);
        } catch (e) {
            console.error('✗ Критическая ошибка загрузки:', e);
        }
    })();
    
    console.log('=== Инициализация завершена ===');
});

/**
 * Проверка авторизации
 */
function checkAuth() {
    return localStorage.getItem('auth_token') !== null && localStorage.getItem('user_type') === 'medcenter';
}

function getAuthHeaders() {
    return {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json'
    };
}

function getMedcenterId() {
    const mc = JSON.parse(localStorage.getItem('medcenter_user') || '{}');
    return mc.id;
}

/**
 * Навигация
 */
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-section]');
    const sections = document.querySelectorAll('.dashboard-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = item.dataset.section;
            
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === sectionId) {
                    section.classList.add('active');
                }
            });
            
            updatePageTitle(sectionId);
            document.querySelector('.sidebar')?.classList.remove('active');
        });
    });
    
    // Быстрые действия
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            if (action === 'traffic-light') {
                document.querySelector('[data-section="traffic-light"]').click();
            } else if (action === 'urgent') {
                openUrgentModal();
            }
        });
    });
}

function updatePageTitle(sectionId) {
    const titles = {
        'dashboard': 'Меню медцентра',
        'traffic-light': 'Донорский светофор',
        'responses': 'Отклики доноров',
        'donors': 'База доноров',
        'statistics': 'Статистика',
        'settings': 'Настройки'
    };
    document.querySelector('.page-title').textContent = titles[sectionId] || 'Меню медцентра';
}

/**
 * Мобильное меню
 */
function initMobileSidebar() {
    const toggle = document.querySelector('.mobile-sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => sidebar.classList.toggle('active'));
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }
}

/**
 * Загрузка данных медцентра
 */
async function loadMedcenterData() {
    try {
        const mcId = getMedcenterId();
        console.log('Загрузка данных медцентра ID:', mcId);
        
        if (!mcId) {
            console.error('ID медцентра не найден');
            return;
        }
        
        // Загружаем полные данные из API
        const response = await fetch(`${MC_API_URL}/medcenter/profile`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            console.error('Ошибка загрузки профиля медцентра:', response.status);
            return;
        }
        
        const mcData = await response.json();
        console.log('Данные медцентра с сервера:', mcData);
        
        // Сохраняем в localStorage
        localStorage.setItem('medcenter_user', JSON.stringify(mcData));
        
        // Отображаем в интерфейсе
        const mcNameEl = document.getElementById('mc-name');
        if (mcNameEl) mcNameEl.textContent = mcData.name || 'Медцентр';
        
        // Заполнение формы настроек
        const settingName = document.getElementById('setting-name');
        const settingAddress = document.getElementById('setting-address');
        const settingPhone = document.getElementById('setting-phone');
        const settingEmail = document.getElementById('setting-email');
        
        if (settingName) settingName.value = mcData.name || '';
        if (settingAddress) settingAddress.value = mcData.address || '';
        if (settingPhone) settingPhone.value = mcData.phone || '';
        if (settingEmail) settingEmail.value = mcData.email || '';
        
        console.log('✓ Данные медцентра загружены и отображены');
    } catch (error) {
        console.error('Ошибка загрузки данных медцентра:', error);
    }
}

/**
 * Светофор крови - данные из API
 */
let bloodNeedsData = [];
let donorCountsData = {};

async function loadTrafficLightFromAPI() {
    const mcId = getMedcenterId();
    console.log('Загрузка светофора для медцентра ID:', mcId);
    
    if (!mcId) {
        console.warn('ID медцентра не найден, используем fallback');
        initTrafficLightFallback();
        return;
    }
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-needs/${mcId}`, {
            headers: getAuthHeaders()
        });
        bloodNeedsData = await response.json();
        console.log('Данные светофора загружены:', bloodNeedsData);
        
        renderMiniTrafficLight();
        renderFullTrafficLight();
    } catch (error) {
        console.error('Ошибка загрузки светофора:', error);
        initTrafficLightFallback();
    }
}

function initTrafficLightFallback() {
    bloodNeedsData = [
        { blood_type: 'O+', status: 'normal' },
        { blood_type: 'O-', status: 'needed' },
        { blood_type: 'A+', status: 'normal' },
        { blood_type: 'A-', status: 'urgent' },
        { blood_type: 'B+', status: 'normal' },
        { blood_type: 'B-', status: 'needed' },
        { blood_type: 'AB+', status: 'normal' },
        { blood_type: 'AB-', status: 'normal' }
    ];
    renderMiniTrafficLight();
    renderFullTrafficLight();
}

function getStatusClass(status) {
    const map = { 'normal': 'ok', 'needed': 'need', 'urgent': 'urgent' };
    return map[status] || 'ok';
}

function getStatusText(status) {
    const map = { 'normal': 'Достаточно', 'needed': 'Нужно пополнить', 'urgent': 'Срочно нужна' };
    return map[status] || status;
}

function renderMiniTrafficLight() {
    const container = document.getElementById('mini-traffic-light');
    if (!container) return;
    
    container.innerHTML = bloodNeedsData.map(item => `
        <div class="blood-status-item">
            <span class="blood-status-type">${item.blood_type}</span>
            <span class="status-dot ${getStatusClass(item.status)}"></span>
        </div>
    `).join('');
}

function renderFullTrafficLight() {
    const container = document.getElementById('traffic-light-full');
    if (!container) return;
    
    const statusColors = {
        'normal': '#10b981',
        'needed': '#f59e0b', 
        'urgent': '#ef4444'
    };
    
    const statusLabels = {
        'normal': 'Достаточно',
        'needed': 'Нужно пополнить',
        'urgent': 'Срочно нужна'
    };
    
    container.innerHTML = bloodNeedsData.map(item => `
        <div class="blood-panel ${item.status}" 
             data-type="${item.blood_type}" 
             data-status="${item.status}"
             style="background: ${statusColors[item.status] || '#10b981'};">
            <div class="blood-panel-type">${item.blood_type}</div>
            <div class="blood-panel-status">${statusLabels[item.status] || item.status}</div>
            <div class="blood-panel-buttons">
                <button class="panel-btn ${item.status === 'normal' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'normal')"
                        title="Достаточно">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 13l4 4L19 7"/>
                    </svg>
                </button>
                <button class="panel-btn ${item.status === 'needed' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'needed')"
                        title="Нужно пополнить">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 8v4"/>
                    </svg>
                </button>
                <button class="panel-btn ${item.status === 'urgent' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'urgent')"
                        title="Срочно (рассылка в Telegram)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

async function setBloodStatus(bloodType, status) {
    const mcId = getMedcenterId();
    if (!mcId) {
        showNotification('Ошибка: медцентр не определён', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-needs/${mcId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ blood_type: bloodType, status: status })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Обновляем локальные данные
            const item = bloodNeedsData.find(i => i.blood_type === bloodType);
            if (item) item.status = status;
            
            renderMiniTrafficLight();
            renderFullTrafficLight();
            
            if (status === 'urgent') {
                showNotification(`Срочный запрос на ${bloodType} отправлен донорам!`, 'success');
            } else {
                showNotification(`Статус ${bloodType} обновлён`, 'success');
            }
        } else {
            showNotification(result.error || 'Ошибка обновления', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

/**
 * Отклики доноров - из API
 */
async function loadResponsesFromAPI() {
    const mcId = getMedcenterId();
    
    try {
        const response = await fetch(`${MC_API_URL}/responses?medical_center_id=${mcId}`, {
            headers: getAuthHeaders()
        });
        const responses = await response.json();
        
        // Сохраняем в кэш
        responsesCache = responses;
        
        // Заполняем фильтр запросов
        populateRequestFilter(responses);
        
        renderResponses(responses);
    } catch (error) {
        console.error('Ошибка загрузки откликов:', error);
        renderResponses([]);
    }
}

function populateRequestFilter(responses) {
    const filterSelect = document.getElementById('filter-request');
    if (!filterSelect) return;
    
    // Получаем уникальные запросы
    const requestIds = [...new Set(responses.map(r => r.request_id).filter(id => id))];
    
    // Очищаем и заполняем select
    filterSelect.innerHTML = '<option value="all">Все запросы</option>';
    
    requestIds.forEach(reqId => {
        const request = bloodRequestsCache.find(r => r.id === reqId);
        if (request) {
            const option = document.createElement('option');
            option.value = reqId;
            option.textContent = `Запрос #${reqId} (${request.blood_type})`;
            filterSelect.appendChild(option);
        }
    });
}

function renderResponses(responses) {
    if (!responses) responses = [];
    
    // Применяем фильтры
    const filterStatus = document.getElementById('filter-status')?.value || 'all';
    const filterBlood = document.getElementById('filter-blood')?.value || 'all';
    const filterRequest = document.getElementById('filter-request')?.value || 'all';
    
    let filtered = responses;
    
    if (filterStatus !== 'all') {
        filtered = filtered.filter(r => r.status === filterStatus);
    }
    
    if (filterBlood !== 'all') {
        filtered = filtered.filter(r => r.donor_blood_type === filterBlood);
    }
    
    if (filterRequest !== 'all') {
        filtered = filtered.filter(r => r.request_id == filterRequest);
    }
    
    const pendingCount = responses.filter(r => r.status === 'pending').length;
    const badge = document.getElementById('responses-badge');
    const statPending = document.getElementById('stat-pending');
    if (badge) badge.textContent = pendingCount;
    if (statPending) statPending.textContent = pendingCount;
    
    // Последние отклики на главной (всегда показываем все, без фильтра)
    const recentContainer = document.getElementById('recent-responses-list');
    if (recentContainer) {
        if (responses.length === 0) {
            recentContainer.innerHTML = '<p class="no-data">Нет откликов</p>';
        } else {
            recentContainer.innerHTML = responses.slice(0, 3).map(r => `
                <div class="request-item" data-id="${r.id}">
                    <div class="response-avatar">${getInitials(r.donor_name || 'НД')}</div>
                    <div class="request-info">
                        <div class="request-name">${r.donor_name || 'Донор'}</div>
                        <div class="request-location">${formatDate(r.created_at)}</div>
                    </div>
                    <span class="request-blood">${r.donor_blood_type || '-'}</span>
                </div>
            `).join('');
        }
    }
    
    // Полный список (с применением фильтров) - КАРТОЧКИ С КРЕСТИКАМИ
    const listContainer = document.getElementById('responses-list');
    if (listContainer) {
        if (filtered.length === 0) {
            listContainer.innerHTML = '<p class="no-data">Нет откликов по выбранным фильтрам</p>';
        } else {
            listContainer.innerHTML = filtered.map(r => `
                <div class="response-card ${r.status}" data-id="${r.id}">
                    <div class="response-avatar">${getInitials(r.donor_name || 'НД')}</div>
                    <div class="response-info">
                        <div class="response-name">${r.donor_name || 'Донор'}</div>
                        <div class="response-meta">
                            <span>${r.donor_phone || r.donor_email || '-'}</span>
                            <span>${formatDate(r.created_at)}</span>
                        </div>
                    </div>
                    <span class="response-blood">${r.donor_blood_type || '-'}</span>
                    <div class="response-actions">
                        ${r.status === 'pending' ? `
                            <button class="btn btn-outline btn-sm" data-action="reject" data-id="${r.id}">Отклонить</button>
                            <button class="btn btn-primary btn-sm" data-action="approve" data-id="${r.id}">Подтвердить</button>
                        ` : r.status === 'confirmed' ? `
                            <span class="donor-status-badge available">${getResponseStatusText(r.status)}</span>
                            <button class="btn btn-outline btn-sm" data-action="cancel" data-id="${r.id}" title="Отменить подтверждение">Отменить</button>
                        ` : r.status === 'completed' ? `
                            <span class="donor-status-badge completed">${getResponseStatusText(r.status)}</span>
                        ` : `
                            <span class="donor-status-badge">${getResponseStatusText(r.status)}</span>
                            ${r.status === 'cancelled' ? `
                                <button class="btn btn-ghost btn-sm" data-action="restore" data-id="${r.id}" title="Восстановить отклик">Восстановить</button>
                            ` : ''}
                        `}
                        <button 
                            class="btn btn-sm hide-response-btn" 
                            onclick="hideResponse(${r.id}); event.stopPropagation();" 
                            title="Скрыть отклик"
                            style="
                                opacity: 0.5 !important; 
                                margin-left: 12px !important; 
                                padding: 6px 10px !important; 
                                font-size: 20px !important; 
                                line-height: 1 !important; 
                                background: transparent !important;
                                border: 2px solid transparent !important;
                                color: #6c757d !important;
                                cursor: pointer !important;
                                display: inline-flex !important;
                                align-items: center !important;
                                justify-content: center !important;
                                transition: all 0.2s !important;
                                position: absolute !important;
                                right: 16px !important;
                                top: 50% !important;
                                transform: translateY(-50%) !important;
                            "
                            onmouseover="this.style.opacity='1'; this.style.color='#dc3545'; this.style.borderColor='#dc3545'; this.style.background='rgba(220,53,69,0.05)';"
                            onmouseout="this.style.opacity='0.5'; this.style.color='#6c757d'; this.style.borderColor='transparent'; this.style.background='transparent';"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            `).join('');
            
            // Обработчики кнопок
            listContainer.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const action = btn.dataset.action;
                    const id = btn.dataset.id;
                    
                    let newStatus;
                    let confirmMessage;
                    
                    switch(action) {
                        case 'approve':
                            newStatus = 'confirmed';
                            confirmMessage = 'Подтвердить донора?';
                            break;
                        case 'reject':
                            newStatus = 'cancelled';
                            confirmMessage = 'Отклонить донора?';
                            break;
                        case 'cancel':
                            newStatus = 'pending';
                            confirmMessage = 'Отменить подтверждение? Донор вернётся в статус "Ожидает".';
                            break;
                        case 'restore':
                            newStatus = 'pending';
                            confirmMessage = 'Восстановить отклик донора?';
                            break;
                        default:
                            return;
                    }
                    
                    // Запрашиваем подтверждение
                    if (!confirm(confirmMessage)) return;
                    
                    await updateResponseStatus(id, newStatus);
                });
            });
        }
    }
}

function getResponseStatusText(status) {
    const map = {
        'pending': 'Ожидает',
        'confirmed': 'Подтверждён',
        'completed': 'Завершён',
        'cancelled': 'Отменён'
    };
    return map[status] || status;
}

async function updateResponseStatus(responseId, status) {
    try {
        const response = await fetch(`${MC_API_URL}/responses/${responseId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status: status })
        });
        
        if (response.ok) {
            // Сообщения в зависимости от статуса
            const messages = {
                'confirmed': '✅ Донор подтверждён!',
                'cancelled': '❌ Отклик отменён',
                'pending': '🔄 Статус изменён на "Ожидает"',
                'completed': '✅ Донация завершена'
            };
            showNotification(messages[status] || 'Статус обновлён', 'success');
            
            // Перезагружаем список
            await loadResponsesFromAPI();
            
            // Также обновляем запросы (для счётчика доноров)
            await loadBloodRequestsFromAPI();
        } else {
            const result = await response.json();
            showNotification(result.error || 'Ошибка обновления статуса', 'error');
        }
    } catch (error) {
        console.error('Ошибка updateResponseStatus:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU');
}

/**
 * База доноров - из API
 */
async function loadDonorsFromAPI() {
    try {
        const response = await fetch(`${MC_API_URL}/medcenter/donors`, {
            headers: getAuthHeaders()
        });
        const donors = await response.json();
        renderDonors(donors);
    } catch (error) {
        console.error('Ошибка загрузки доноров:', error);
        renderDonors([]);
    }
}

function renderDonors(donors) {
    const container = document.getElementById('donors-list');
    if (!container) return;
    
    if (!donors || donors.length === 0) {
        container.innerHTML = '<p class="no-data">Нет зарегистрированных доноров</p>';
        return;
    }
    
    // Определяем статус донора по дате последней донации
    function getDonorStatus(lastDonation) {
        if (!lastDonation) return 'available';
        const last = new Date(lastDonation);
        const now = new Date();
        const daysDiff = Math.floor((now - last) / (1000 * 60 * 60 * 24));
        return daysDiff >= 60 ? 'available' : 'recovery';
    }
    
    container.innerHTML = `
        <table class="donors-table">
            <thead>
                <tr>
                    <th>Донор</th>
                    <th>Группа</th>
                    <th>Последняя донация</th>
                    <th>Статус</th>
                    <th>Контакт</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${donors.map(d => {
                    const status = getDonorStatus(d.last_donation_date);
                    return `
                    <tr>
                        <td>
                            <div class="donor-row-name">
                                <div class="donor-avatar-mini">${getInitials(d.full_name || 'НД')}</div>
                                <span>${d.full_name || 'Донор'}</span>
                            </div>
                        </td>
                        <td><span class="response-blood">${d.blood_type || '-'}</span></td>
                        <td>${d.last_donation_date ? formatDate(d.last_donation_date) : 'Нет данных'}</td>
                        <td>
                            <span class="donor-status-badge ${status}">
                                ${status === 'available' ? 'Доступен' : 'Восстановление'}
                            </span>
                        </td>
                        <td>
                            ${d.phone || d.email || d.telegram_username || '-'}
                        </td>
                        <td>
                            <button class="btn btn-outline btn-sm contact-donor" data-id="${d.id}" data-name="${d.full_name}">Написать</button>
                        </td>
                    </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    // Обработчики для связи с донором
    container.querySelectorAll('.contact-donor').forEach(btn => {
        btn.addEventListener('click', () => {
            openContactModal(btn.dataset.id, btn.dataset.name);
        });
    });
    
    // Поиск
    document.getElementById('donor-search')?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        container.querySelectorAll('tbody tr').forEach(row => {
            const name = row.querySelector('.donor-row-name span').textContent.toLowerCase();
            row.style.display = name.includes(query) ? '' : 'none';
        });
    });
}

// Модальное окно для связи с донором
function openContactModal(donorId, donorName) {
    const modal = document.getElementById('donor-modal');
    const content = document.getElementById('donor-modal-content');
    
    if (!modal || !content) {
        showNotification('Функция сообщений в разработке', 'info');
        return;
    }
    
    content.innerHTML = `
        <h3>Написать донору: ${donorName}</h3>
        <form id="contact-donor-form">
            <div class="form-group">
                <label>Тема</label>
                <input type="text" id="msg-subject" placeholder="Тема сообщения">
            </div>
            <div class="form-group">
                <label>Сообщение</label>
                <textarea id="msg-content" rows="4" placeholder="Ваше сообщение..." required></textarea>
            </div>
            <div class="form-buttons">
                <button type="button" class="btn btn-outline" onclick="closeModal(document.getElementById('donor-modal'))">Отмена</button>
                <button type="submit" class="btn btn-primary">Отправить</button>
            </div>
        </form>
    `;
    
    document.getElementById('contact-donor-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await sendMessageToDonor(donorId);
    });
    
    modal.classList.add('active');
}

async function sendMessageToDonor(donorId) {
    const subject = document.getElementById('msg-subject').value;
    const message = document.getElementById('msg-content').value;
    
    try {
        const response = await fetch(`${MC_API_URL}/messages`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                to_user_id: parseInt(donorId),
                subject: subject,
                message: message
            })
        });
        
        if (response.ok) {
            showNotification('Сообщение отправлено!', 'success');
            closeModal(document.getElementById('donor-modal'));
        } else {
            const result = await response.json();
            showNotification(result.error || 'Ошибка отправки', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

/**
 * Статистика - из API
 */
async function loadStatisticsFromAPI() {
    try {
        const response = await fetch(`${MC_API_URL}/stats/medcenter`, {
            headers: getAuthHeaders()
        });
        const stats = await response.json();
        renderDashboardStatistics(stats);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        renderDashboardStatistics({});
    }
}

function renderDashboardStatistics(apiStats) {
    console.log('📊 Обновление статистики на главной:', apiStats);
    
    // Обновляем счётчики на главной С ФОРМАТИРОВАНИЕМ
    const totalDonors = document.getElementById('stat-donors');
    const activeRequests = document.getElementById('stat-requests');
    const pendingResponses = document.getElementById('stat-pending');
    const monthDonations = document.getElementById('stat-donations-month');
    
    if (totalDonors) {
        totalDonors.textContent = formatNumber(apiStats.total_donors || 0);
        console.log('✓ Доноры обновлены:', apiStats.total_donors);
    }
    if (activeRequests) {
        activeRequests.textContent = formatNumber(apiStats.active_requests || 0);
        console.log('✓ Запросы обновлены:', apiStats.active_requests);
    }
    if (pendingResponses) {
        pendingResponses.textContent = formatNumber(apiStats.pending_responses || 0);
        console.log('✓ Ожидают обновлены:', apiStats.pending_responses);
    }
    if (monthDonations) {
        monthDonations.textContent = formatNumber(apiStats.month_donations || 0);
        console.log('✓ Донации за месяц обновлены:', apiStats.month_donations);
    }
    
    // Статистика по группам крови
    const bloodStatsContainer = document.getElementById('blood-stats');
    if (bloodStatsContainer) {
        const donorsByBlood = apiStats.donors_by_blood_type || {};
        const bloodTypes = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'];
        const bloodStats = bloodTypes.map(type => ({
            type: type,
            count: donorsByBlood[type] || 0
        })).sort((a, b) => b.count - a.count);
        
        const max = Math.max(...bloodStats.map(s => s.count), 1);
        
        bloodStatsContainer.innerHTML = bloodStats.map(s => `
            <div class="blood-stat-row">
                <span class="blood-stat-type">${s.type}</span>
                <div class="blood-stat-bar">
                    <div class="blood-stat-fill" style="width: ${(s.count / max) * 100}%"></div>
                </div>
                <span class="blood-stat-value">${formatNumber(s.count)}</span>
            </div>
        `).join('');
    }
    
    // График донаций (с форматированием)
    const chartContainer = document.getElementById('donations-chart');
    if (chartContainer) {
        const months = ['Авг', 'Сен', 'Окт', 'Ноя', 'Дек', 'Янв'];
        const values = [0, 0, 0, 0, 0, apiStats.month_donations || 0];
        const max = Math.max(...values, 1);
        
        chartContainer.innerHTML = months.map((m, i) => `
            <div class="chart-bar">
                <span class="bar-value">${formatNumber(values[i])}</span>
                <div class="bar-fill" style="height: ${(values[i] / max) * 150}px"></div>
                <span class="bar-label">${m}</span>
            </div>
        `).join('');
    }
}

/**
 * Запросы крови
 */
async function loadBloodRequestsFromAPI() {
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests`, {
            headers: getAuthHeaders()
        });
        const requests = await response.json();
        
        // Загружаем отклики для каждого запроса
        const mcId = getMedcenterId();
        const responsesResp = await fetch(`${MC_API_URL}/responses?medical_center_id=${mcId}`, {
            headers: getAuthHeaders()
        });
        const allResponses = await responsesResp.json();
        
        // Группируем отклики по запросам
        const responsesByRequest = {};
        allResponses.forEach(r => {
            if (!responsesByRequest[r.request_id]) {
                responsesByRequest[r.request_id] = [];
            }
            responsesByRequest[r.request_id].push(r);
        });
        
        // Добавляем отклики к запросам
        requests.forEach(req => {
            req.donor_responses = responsesByRequest[req.id] || [];
            req.responses_count = req.donor_responses.length;
            req.approved_count = req.donor_responses.filter(r => r.status === 'confirmed' || r.status === 'completed').length;
        });
        
        // Сохраняем в кэш
        bloodRequestsCache = requests;
        
        renderBloodRequests(requests);
        updateRequestsBadge(requests);
    } catch (error) {
        console.error('Ошибка загрузки запросов крови:', error);
        renderBloodRequests([]);
    }
}

function renderBloodRequests(requests) {
    const container = document.getElementById('requests-list');
    if (!container) return;
    
    // Фильтрация по статусу
    const filterStatus = document.getElementById('requests-filter-status')?.value || 'active';
    const filterBlood = document.getElementById('requests-filter-blood')?.value || 'all';
    
    let filteredRequests = requests;
    
    if (filterStatus !== 'all') {
        filteredRequests = filteredRequests.filter(r => r.status === filterStatus);
    }
    
    if (filterBlood !== 'all') {
        filteredRequests = filteredRequests.filter(r => r.blood_type === filterBlood);
    }
    
    if (!filteredRequests || filteredRequests.length === 0) {
        container.innerHTML = '<p class="no-data">Нет запросов по выбранным фильтрам</p>';
        return;
    }
    
    container.innerHTML = filteredRequests.map(req => {
        const urgencyLabels = {
            'normal': 'Обычный',
            'needed': 'Нужна кровь',
            'urgent': 'Срочный',
            'critical': 'Критичный'
        };
        
        // Время создания
        const timeAgo = formatTimeAgo(req.created_at);
        const expiresDate = req.expires_at ? formatDateShort(req.expires_at) : null;
        
        // Отклики доноров
        const responses = req.donor_responses || [];
        const neededDonors = req.needed_donors;
        const currentDonors = req.current_donors || responses.length;
        const progress = neededDonors > 0 ? Math.round((currentDonors / neededDonors) * 100) : 0;
        
        // Группы крови (может быть несколько)
        const bloodTypes = req.blood_types || [req.blood_type];
        
        return `
            <article class="blood-request-card blood-request-card--${req.urgency}" data-id="${req.id}">
                <!-- Шапка -->
                <header class="card-header">
                    <div class="urgency-badge urgency-badge--${req.urgency}">
                        <span class="urgency-dot"></span>
                        <span class="urgency-text">${urgencyLabels[req.urgency]}</span>
                    </div>
                    <time class="card-time">${timeAgo}</time>
                </header>
                
                <!-- Контент -->
                <div class="card-body">
                    <!-- Группы крови -->
                    <div class="blood-types">
                        ${bloodTypes.map(bt => `<span class="blood-type-tag">${bt}</span>`).join('')}
                    </div>
                    
                    <!-- Мета-информация -->
                    ${expiresDate ? `
                        <div class="card-meta">
                            <span class="meta-item">
                                <span class="meta-label">Истекает:</span>
                                <span class="meta-value">${expiresDate}</span>
                            </span>
                </div>
                    ` : ''}
                    
                    <!-- Прогресс откликов -->
                    <div class="respondents-progress">
                        <div class="progress-header">
                            <span class="progress-label">Откликнулось</span>
                            <span class="progress-value">${currentDonors}${neededDonors ? ` из ${neededDonors}` : ''}</span>
                        </div>
                        ${neededDonors ? `
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${progress}%"></div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                
                <!-- Футер с кнопками -->
                <footer class="card-footer">
                    <button class="btn btn-secondary btn-sm" onclick="showRespondents(${req.id})">
                        👥 Доноры
                        ${currentDonors > 0 ? `<span class="btn-badge">${currentDonors}</span>` : ''}
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="editRequest(${req.id})">
                        Редактировать
                    </button>
                        ${req.status === 'active' ? `
                        <button class="btn btn-primary btn-sm" onclick="markRequestFulfilled(${req.id})">
                                Выполнен
                            </button>
                        <button class="btn btn-icon-only btn-ghost btn-sm" onclick="cancelRequest(${req.id})" title="Отменить">
                            ✕
                        </button>
                    ` : `
                        <span class="request-status-badge ${req.status}">
                            ${req.status === 'fulfilled' ? 'Выполнен' : 'Отменён'}
                        </span>
                    `}
                </footer>
            </article>
        `;
    }).join('');
    
    // Добавляем обработчики фильтров
    const statusFilter = document.getElementById('requests-filter-status');
    const bloodFilter = document.getElementById('requests-filter-blood');
    
    if (statusFilter) {
        statusFilter.onchange = () => renderBloodRequests(requests);
    }
    if (bloodFilter) {
        bloodFilter.onchange = () => renderBloodRequests(requests);
    }
}

function updateRequestsBadge(requests) {
    const badge = document.getElementById('requests-badge');
    if (badge) {
        const activeCount = requests.filter(r => r.status === 'active').length;
        badge.textContent = activeCount;
        badge.style.display = activeCount > 0 ? 'inline-block' : 'none';
    }
}

function openCreateRequestModal() {
    document.getElementById('create-request-modal')?.classList.add('active');
}

async function createBloodRequest(formData) {
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Запрос на донацию создан!', 'success');
            closeModal(document.getElementById('create-request-modal'));
            await loadBloodRequestsFromAPI();
            if (formData.urgency === 'critical') {
                showNotification('Уведомления отправлены донорам!', 'info');
            }
        } else {
            showNotification(result.error || 'Ошибка создания запроса', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

async function fulfillRequest(requestId) {
    if (!confirm('Отметить запрос как выполненный?\n\nДонорам с подтверждённым откликом будет засчитана донация.')) return;
    
    try {
        // Получаем запрос и его отклики
        const request = bloodRequestsCache.find(r => r.id === requestId);
        if (!request) {
            showNotification('Запрос не найден', 'error');
            return;
        }
        
        // Получаем подтверждённые отклики
        const responsesReq = await fetch(`${MC_API_URL}/responses?request_id=${requestId}`, {
            headers: getAuthHeaders()
        });
        
        if (!responsesReq.ok) {
            throw new Error('Ошибка загрузки откликов');
        }
        
        const responses = await responsesReq.json();
        const confirmedResponses = responses.filter(r => r.status === 'confirmed');
        
        // Записываем донации для всех подтверждённых
        for (const resp of confirmedResponses) {
            try {
                await fetch(`${MC_API_URL}/medical-center/donations`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        donor_id: resp.user_id,
                        blood_type: resp.donor_blood_type || request.blood_type,
                        volume_ml: 450,
                        donation_date: new Date().toISOString().split('T')[0],
                        response_id: resp.id,
                        notes: `Донация по запросу #${requestId}`
                    })
                });
            } catch (err) {
                console.error(`Ошибка записи донации для донора ${resp.user_id}:`, err);
            }
        }
        
        // Обновляем статус запроса
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status: 'fulfilled' })
        });
        
        if (response.ok) {
            showNotification(
                `✅ Запрос выполнен! Донаций записано: ${confirmedResponses.length}`, 
                'success'
            );
            await loadBloodRequestsFromAPI();
            await loadResponsesFromAPI();
        } else {
            showNotification('Ошибка обновления статуса', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка выполнения запроса', 'error');
    }
}

async function cancelRequest(requestId) {
    if (!confirm('Отменить этот запрос?')) return;
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status: 'cancelled' })
        });
        
        if (response.ok) {
            showNotification('Запрос отменён', 'success');
            await loadBloodRequestsFromAPI();
        } else {
            showNotification('Ошибка обновления статуса', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения', 'error');
    }
}

async function deleteRequest(requestId) {
    if (!confirm('Удалить этот запрос? Это действие необратимо.')) return;
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showNotification('Запрос удалён', 'success');
            await loadBloodRequestsFromAPI();
        } else {
            showNotification('Ошибка удаления', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения', 'error');
    }
}

// Алиасы для новых имён функций
window.markRequestFulfilled = fulfillRequest;
window.editRequest = function(requestId) {
    openEditRequestModal(requestId);
};
window.archiveRequest = async function(requestId) {
    // В будущем можно добавить отдельный статус "archived"
    showNotification('Запрос перемещён в архив', 'success');
};
window.showAllResponses = function(requestId) {
    // Можно открыть модальное окно со всеми откликами
    const card = document.querySelector(`[data-request-id="${requestId}"]`);
    if (card) {
        card.scrollIntoView({ behavior: 'smooth' });
        showNotification(`Все отклики для запроса #${requestId}`, 'info');
    }
};

/**
 * Открыть модальное окно редактирования запроса
 */
async function openEditRequestModal(requestId) {
    try {
        // Загружаем данные запроса
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки запроса');
        }
        
        const request = await response.json();
        
        // Заполняем форму
        document.getElementById('edit-request-id').value = request.id;
        
        // Выбираем группу крови
        const bloodTypeRadio = document.querySelector(`input[name="edit_blood_type"][value="${request.blood_type}"]`);
        if (bloodTypeRadio) bloodTypeRadio.checked = true;
        
        // Заполняем остальные поля
        document.getElementById('edit-urgency').value = request.urgency;
        document.getElementById('edit-description').value = request.description || '';
        
        // Форматируем дату для input type="date" (YYYY-MM-DD)
        if (request.expires_at) {
            const expiresDate = new Date(request.expires_at);
            const formattedDate = expiresDate.toISOString().split('T')[0];
            document.getElementById('edit-expires-at').value = formattedDate;
        }
        
        // Открываем модальное окно
        document.getElementById('edit-request-modal').classList.add('active');
        
    } catch (error) {
        console.error('Ошибка открытия модального окна редактирования:', error);
        showNotification('Ошибка загрузки данных запроса', 'error');
    }
}

/**
 * Сохранить изменения запроса
 */
async function saveEditedRequest() {
    const requestId = document.getElementById('edit-request-id').value;
    const bloodType = document.querySelector('input[name="edit_blood_type"]:checked');
    
    if (!bloodType) {
        showNotification('Выберите группу крови', 'error');
        return;
    }
    
    const data = {
        blood_type: bloodType.value,
        urgency: document.getElementById('edit-urgency').value,
        description: document.getElementById('edit-description').value,
        expires_at: document.getElementById('edit-expires-at').value
    };
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('✅ Запрос успешно обновлён', 'success');
            closeModal(document.getElementById('edit-request-modal'));
            await loadBloodRequestsFromAPI(); // Обновляем список
        } else {
            showNotification('❌ ' + (result.error || 'Ошибка обновления'), 'error');
        }
    } catch (error) {
        console.error('Ошибка сохранения запроса:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Модальные окна
 */
function initModals() {
    // Срочный запрос
    document.getElementById('urgent-request-btn')?.addEventListener('click', openUrgentModal);
    
    // Переключение учёта доноров
    const donorLimitRadios = document.querySelectorAll('input[name="donor_limit"]');
    const donorCountInput = document.getElementById('donor-count-input');
    
    donorLimitRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'limited') {
                donorCountInput.style.display = 'block';
                document.getElementById('needed-donors').required = true;
            } else {
                donorCountInput.style.display = 'none';
                document.getElementById('needed-donors').required = false;
            }
        });
    });
    
    // Создание запроса крови
    const createRequestBtn = document.querySelector('[data-action="create-request"]');
    if (createRequestBtn) {
        createRequestBtn.addEventListener('click', async () => {
            const form = document.getElementById('create-request-form');
            const formData = new FormData(form);
            
            const bloodType = formData.get('request_blood');
            if (!bloodType) {
                showNotification('Выберите группу крови', 'error');
                return;
            }
            
            const donorLimit = formData.get('donor_limit');
            const neededDonors = donorLimit === 'limited' ? parseInt(formData.get('needed_donors')) : null;
            
            if (donorLimit === 'limited' && (!neededDonors || neededDonors < 1)) {
                showNotification('Укажите количество доноров', 'error');
                return;
            }
            
            const data = {
                blood_type: bloodType,
                urgency: formData.get('urgency'),
                description: formData.get('description'),
                expires_days: parseInt(formData.get('expires_days')) || 7,
                needed_donors: neededDonors,
                auto_close: donorLimit === 'limited'
            };
            
            createRequestBtn.classList.add('loading');
            await createBloodRequest(data);
            createRequestBtn.classList.remove('loading');
            form.reset();
        });
    }
    
    // Сохранение отредактированного запроса
    const saveRequestBtn = document.querySelector('[data-action="save-request"]');
    if (saveRequestBtn) {
        saveRequestBtn.addEventListener('click', saveEditedRequest);
    }
    
    // Отправка сообщения донору
    const sendMessageBtn = document.querySelector('[data-action="send-message"]');
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', sendMessageToDonor);
    }
    
    // Закрытие модалок
    document.querySelectorAll('.modal').forEach(modal => {
        modal.querySelector('.modal-close')?.addEventListener('click', () => closeModal(modal));
        modal.querySelector('[data-action="cancel"]')?.addEventListener('click', () => closeModal(modal));
        modal.querySelector('[data-action="close"]')?.addEventListener('click', () => closeModal(modal));
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal(modal);
        });
    });
    
    // Отправка срочного запроса
    document.querySelector('[data-action="send"]')?.addEventListener('click', async () => {
        const bloodType = document.querySelector('input[name="urgent_blood"]:checked');
        if (!bloodType) {
            showNotification('Выберите группу крови', 'error');
            return;
        }
        
        // Создаём срочный запрос через API
        try {
            const response = await fetch(`${MC_API_URL}/blood-requests`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    blood_type: bloodType.value,
                    urgency: 'urgent',
                    description: 'Срочный запрос крови',
                    expires_days: 2
                })
            });
            
            if (response.ok) {
                showNotification(`Срочный запрос отправлен донорам с группой ${bloodType.value}!`, 'success');
        closeModal(document.getElementById('urgent-modal'));
                await loadBloodRequestsFromAPI(); // Обновляем список запросов
            } else {
                const error = await response.json();
                showNotification('Ошибка отправки запроса: ' + (error.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            console.error('Ошибка отправки срочного запроса:', error);
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

function openUrgentModal() {
    document.getElementById('urgent-modal').classList.add('active');
}

function openDonorModal(donor) {
    const modal = document.getElementById('donor-modal');
    const donorInfo = document.getElementById('donor-info');
    const donorId = document.getElementById('donor-id');
    
    // Заполняем информацию о доноре
    donorInfo.innerHTML = `
        <div style="display: grid; gap: 10px;">
            <div><strong>Донор:</strong> ${donor.donor_name || donor.name || 'Неизвестно'}</div>
            <div><strong>Группа крови:</strong> <span class="blood-type-badge">${donor.blood_type || donor.blood || '—'}</span></div>
            <div><strong>Телефон:</strong> ${donor.donor_phone || donor.phone || '—'}</div>
            <div><strong>Email:</strong> ${donor.donor_email || donor.email || '—'}</div>
        </div>
    `;
    
    donorId.value = donor.donor_id || donor.user_id || donor.id;
    
    // Очищаем форму
    document.getElementById('message-type').value = 'invitation';
    document.getElementById('message-text').value = '';
    document.getElementById('send-telegram').checked = true;
    
    modal.classList.add('active');
}

/**
 * Отправить сообщение донору
 */
async function sendMessageToDonor() {
    const donorId = document.getElementById('donor-id').value;
    const messageType = document.getElementById('message-type').value;
    const messageText = document.getElementById('message-text').value;
    const sendTelegram = document.getElementById('send-telegram').checked;
    
    if (!messageText.trim()) {
        showNotification('❌ Введите текст сообщения', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${MC_API_URL}/messages`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                user_id: donorId,
                message_type: messageType,
                message: messageText,
                send_telegram: sendTelegram
            })
        });
        
        if (response.ok) {
            showNotification('✅ Сообщение отправлено', 'success');
            closeModal(document.getElementById('donor-modal'));
        } else {
            const error = await response.json();
            showNotification('❌ ' + (error.error || 'Ошибка отправки'), 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки сообщения:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

function closeModal(modal) {
    modal.classList.remove('active');
}

/**
 * Формы настроек
 */
function initForms() {
    const settingsForm = document.getElementById('mc-settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const mcId = getMedcenterId();
            if (!mcId) {
                showNotification('Ошибка: медцентр не определён', 'error');
                return;
            }
            
            const formData = {
                address: document.getElementById('setting-address')?.value || '',
                phone: document.getElementById('setting-phone')?.value || '',
                email: document.getElementById('setting-email')?.value || ''
            };
            
            console.log('Сохранение настроек медцентра:', formData);
            
            try {
                const response = await fetch(`${MC_API_URL}/medcenter/profile`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✓ Настройки сохранены', 'success');
                    // Перезагружаем данные
                    await loadMedcenterData();
                } else {
                    showNotification('✗ ' + (result.error || 'Ошибка сохранения'), 'error');
                }
            } catch (error) {
                console.error('Ошибка сохранения настроек:', error);
                showNotification('✗ Ошибка соединения', 'error');
            }
        });
    }
    
    const passwordForm = document.getElementById('password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const newPass = document.getElementById('new-password')?.value;
            const confirm = document.getElementById('confirm-password')?.value;
            
            if (newPass !== confirm) {
                showNotification('Пароли не совпадают', 'error');
                return;
            }
            
            showNotification('Пароль изменён', 'success');
            e.target.reset();
        });
    }
}

/**
 * Инициализация фильтров запросов крови
 */
function initRequestFilters() {
    // Фильтры запросов крови
    const statusFilter = document.getElementById('requests-filter-status');
    const bloodFilter = document.getElementById('requests-filter-blood');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            renderBloodRequests(bloodRequestsCache);
        });
    }
    
    if (bloodFilter) {
        bloodFilter.addEventListener('change', () => {
            renderBloodRequests(bloodRequestsCache);
        });
    }
    
    // Фильтры откликов доноров
    const responseStatusFilter = document.getElementById('filter-status');
    const responseBloodFilter = document.getElementById('filter-blood');
    const responseRequestFilter = document.getElementById('filter-request');
    
    if (responseStatusFilter) {
        responseStatusFilter.addEventListener('change', () => {
            renderResponses(responsesCache);
        });
    }
    
    if (responseBloodFilter) {
        responseBloodFilter.addEventListener('change', () => {
            renderResponses(responsesCache);
        });
    }
    
    if (responseRequestFilter) {
        responseRequestFilter.addEventListener('change', () => {
            renderResponses(responsesCache);
        });
    }
}

/**
 * Выход
 */
function initLogout() {
    document.getElementById('logout-btn')?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        try {
            await fetch(`${MC_API_URL}/logout`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
        } catch (error) {
            console.log('Logout error:', error);
        }
        
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('medcenter_user');
        window.location.href = 'auth.html';
    });
}

/**
 * Утилиты
 */
function getInitials(name) {
    const parts = name.split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
}

function showNotification(message, type = 'info') {
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // SVG иконки в зависимости от типа
    let svgIcon = '';
    if (type === 'success') {
        svgIcon = '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/>';
    } else if (type === 'error') {
        svgIcon = '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>';
    } else {
        svgIcon = '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>';
    }
    
    notification.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${svgIcon}
        </svg>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
}

/**
 * Показать все отклики на запрос (модальное окно с пагинацией)
 */
async function showAllResponses(requestId, filterBloodType = null) {
    try {
        // Загружаем все отклики для запроса
        const response = await fetch(`${API_URL}/responses?request_id=${requestId}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (!response.ok) throw new Error('Ошибка загрузки откликов');
        
        let responses = await response.json();
        
        // Фильтруем по группе крови, если указана
        if (filterBloodType) {
            responses = responses.filter(r => r.donor_blood_type === filterBloodType);
        }
        
        // Создаём модальное окно
        const modal = document.createElement('div');
        modal.id = 'all-responses-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content all-responses-modal">
                <div class="modal-header">
                    <h3>Отклики на запрос ${filterBloodType ? `(группа ${filterBloodType})` : ''} — ${responses.length} шт.</h3>
                    <button class="modal-close" onclick="closeAllResponsesModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="responses-filters">
                        <input type="text" id="response-search" placeholder="Поиск по имени или телефону..." class="form-input">
                        <select id="response-status-filter" class="form-select">
                            <option value="all">Все статусы</option>
                            <option value="pending">Ожидает</option>
                            <option value="confirmed">Подтверждён</option>
                            <option value="completed">Завершён</option>
                            <option value="rejected">Отклонён</option>
                        </select>
                        ${!filterBloodType ? `
                        <select id="response-blood-filter" class="form-select">
                            <option value="all">Все группы крови</option>
                            <option value="O+">O+</option>
                            <option value="O-">O-</option>
                            <option value="A+">A+</option>
                            <option value="A-">A-</option>
                            <option value="B+">B+</option>
                            <option value="B-">B-</option>
                            <option value="AB+">AB+</option>
                            <option value="AB-">AB-</option>
                        </select>
                        ` : ''}
                    </div>
                    <div id="responses-table-container"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Рендерим отклики с пагинацией
        renderResponsesTable(responses);
        
        // Обработчики фильтров
        const applyFilters = () => {
            const search = document.getElementById('response-search').value.toLowerCase();
            const status = document.getElementById('response-status-filter').value;
            const bloodFilter = document.getElementById('response-blood-filter');
            const blood = bloodFilter ? bloodFilter.value : 'all';
            
            const filtered = responses.filter(r => {
                const matchSearch = !search || 
                    r.donor_name?.toLowerCase().includes(search) ||
                    r.donor_phone?.toLowerCase().includes(search) ||
                    r.donor_email?.toLowerCase().includes(search);
                const matchStatus = status === 'all' || r.status === status;
                const matchBlood = blood === 'all' || r.donor_blood_type === blood;
                return matchSearch && matchStatus && matchBlood;
            });
            renderResponsesTable(filtered);
        };
        
        document.getElementById('response-search').addEventListener('input', applyFilters);
        document.getElementById('response-status-filter').addEventListener('change', applyFilters);
        if (document.getElementById('response-blood-filter')) {
            document.getElementById('response-blood-filter').addEventListener('change', applyFilters);
        }
        
    } catch (error) {
        console.error('Ошибка загрузки откликов:', error);
        showNotification('Ошибка загрузки откликов', 'error');
    }
}

/**
 * Рендер таблицы откликов с пагинацией
 */
let currentResponsesPage = 1;
let currentResponsesData = [];

function renderResponsesTable(responses, page = 1) {
    currentResponsesData = responses;
    currentResponsesPage = page;
    
    const container = document.getElementById('responses-table-container');
    if (!container) return;
    
    const pageSize = 20;
    const totalPages = Math.ceil(responses.length / pageSize);
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const pageResponses = responses.slice(startIndex, endIndex);
    
    const statusLabels = {
        'pending': 'Ожидает',
        'confirmed': 'Подтверждён',
        'completed': 'Завершён',
        'rejected': 'Отклонён'
    };
    
    const statusColors = {
        'pending': '#ffc107',
        'confirmed': '#28a745',
        'completed': '#17a2b8',
        'rejected': '#dc3545'
    };
    
    container.innerHTML = `
        <div class="responses-table">
            <table class="table">
                <thead>
                    <tr>
                        <th>№</th>
                        <th>Донор</th>
                        <th>Группа крови</th>
                        <th>Статистика</th>
                        <th>Контакты</th>
                        <th>Статус</th>
                        <th>Дата отклика</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    ${pageResponses.map((r, idx) => {
                        // Вычисляем дни с последней донации
                        let daysSinceLastDonation = null;
                        let canDonate = true;
                        let validationWarning = '';
                        
                        if (r.donor_last_donation_date) {
                            const lastDate = new Date(r.donor_last_donation_date);
                            const today = new Date();
                            daysSinceLastDonation = Math.floor((today - lastDate) / (1000 * 60 * 60 * 24));
                            
                            if (daysSinceLastDonation < 60) {
                                canDonate = false;
                                validationWarning = `⚠️ Прошло только ${daysSinceLastDonation} дней (нужно 60)`;
                            }
                        }
                        
                        // Проверка группы крови
                        const bloodTypeMatch = r.donor_blood_type === r.request_blood_type;
                        if (!bloodTypeMatch) {
                            canDonate = false;
                            validationWarning = `⚠️ Группа крови не совпадает`;
                        }
                        
                        return `
                        <tr ${!canDonate && r.status === 'pending' ? 'style="background-color: #fff3cd;"' : ''}>
                            <td>${startIndex + idx + 1}</td>
                            <td>
                                <div class="donor-cell">
                                    <div class="response-avatar-small">${getInitials(r.donor_name || 'НД')}</div>
                                    <div>
                                        <div class="donor-name">${r.donor_name || 'Донор'}</div>
                                        ${r.donor_comment ? `<div class="donor-comment-small">"${r.donor_comment}"</div>` : ''}
                                        ${validationWarning ? `<div style="color: #856404; font-size: 11px; margin-top: 4px;">${validationWarning}</div>` : ''}
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="blood-badge" style="${!bloodTypeMatch ? 'border: 2px solid #dc3545;' : ''}">${r.donor_blood_type || '-'}</span>
                            </td>
                            <td>
                                <div style="font-size: 12px; white-space: nowrap;">
                                    <div><strong>Донаций:</strong> ${r.donor_total_donations || 0}</div>
                                    ${r.donor_last_donation_date ? `
                                        <div><strong>Последняя:</strong> ${formatDateShort(r.donor_last_donation_date)}</div>
                                        <div style="color: ${canDonate ? '#28a745' : '#dc3545'};">
                                            <strong>${daysSinceLastDonation}</strong> дней назад
                                        </div>
                                    ` : '<div style="color: #28a745;">✓ Не сдавал ранее</div>'}
                                </div>
                            </td>
                            <td>
                                ${r.donor_phone ? `<div>📞 ${r.donor_phone}</div>` : ''}
                                ${r.donor_email ? `<div>📧 ${r.donor_email}</div>` : ''}
                            </td>
                            <td>
                                <span class="status-badge" style="background-color: ${statusColors[r.status]}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                    ${statusLabels[r.status] || r.status}
                                </span>
                            </td>
                            <td>${new Date(r.created_at).toLocaleString('ru-RU')}</td>
                            <td>
                                <div class="action-buttons" style="display: flex; gap: 6px; align-items: center;">
                                    <button class="btn btn-sm btn-primary" onclick="openDonorModal({donor_id: ${r.user_id}, donor_name: '${(r.donor_name || '').replace(/'/g, "\\'")}', blood_type: '${r.donor_blood_type}', donor_phone: '${r.donor_phone || ''}', donor_email: '${r.donor_email || ''}'})">
                                        ✉️
                                    </button>
                                    ${r.status === 'pending' ? `
                                        <button class="btn btn-sm btn-success" onclick="confirmResponse(${r.id})" title="Подтвердить${!canDonate ? ' (есть предупреждения!)' : ''}">
                                            ✓
                                        </button>
                                        <button class="btn btn-sm btn-ghost" onclick="rejectResponse(${r.id})" title="Отклонить">
                                            ✕
                                        </button>
                                    ` : ''}
                                    ${r.status === 'confirmed' ? `
                                        <button class="btn btn-sm btn-success" onclick="recordDonation(${r.user_id}, ${r.id})" title="Записать донацию">
                                            🩸
                                        </button>
                                        <button class="btn btn-sm" onclick="unconfirmResponse(${r.id})" title="Отменить подтверждение">
                                            ↶
                                        </button>
                                    ` : ''}
                                    <button 
                                        class="btn btn-sm hide-response-btn" 
                                        onclick="hideResponse(${r.id})" 
                                        title="Скрыть отклик"
                                        style="
                                            opacity: 0.5 !important; 
                                            margin-left: auto !important; 
                                            padding: 6px 10px !important; 
                                            font-size: 20px !important; 
                                            line-height: 1 !important; 
                                            background: transparent !important;
                                            border: 2px solid transparent !important;
                                            color: #6c757d !important;
                                            cursor: pointer !important;
                                            display: inline-flex !important;
                                            align-items: center !important;
                                            justify-content: center !important;
                                            transition: all 0.2s !important;
                                        "
                                        onmouseover="this.style.opacity='1'; this.style.color='#dc3545'; this.style.borderColor='#dc3545'; this.style.background='rgba(220,53,69,0.05)';"
                                        onmouseout="this.style.opacity='0.5'; this.style.color='#6c757d'; this.style.borderColor='transparent'; this.style.background='transparent';"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                    }).join('')}
                </tbody>
            </table>
        </div>
        
        ${totalPages > 1 ? `
            <div class="pagination">
                <button class="btn btn-sm" ${page === 1 ? 'disabled' : ''} onclick="changePage(${page - 1})">
                    ← Назад
                </button>
                <span class="pagination-info">
                    Страница ${page} из ${totalPages} (${responses.length} откликов)
                </span>
                <button class="btn btn-sm" ${page === totalPages ? 'disabled' : ''} onclick="changePage(${page + 1})">
                    Вперёд →
                </button>
            </div>
        ` : ''}
    `;
}

function changePage(page) {
    renderResponsesTable(currentResponsesData, page);
}

/**
 * Закрыть модал всех откликов
 */
function closeAllResponsesModal() {
    const modal = document.getElementById('all-responses-modal');
    if (modal) modal.remove();
}

/**
 * Форматировать время "X назад"
 */
function formatTimeAgo(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Только что';
    if (diffMins < 60) return `${diffMins} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays === 1) return 'Вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;
    return formatDateShort(dateString);
}

/**
 * Форматировать дату компактно
 */
function formatDateShort(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const months = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ];
    
    return `${date.getDate()} ${months[date.getMonth()]}`;
}

/**
 * Показать всех откликнувшихся доноров для запроса
 */
function showRespondents(requestId) {
    // Найти запрос
    const request = bloodRequestsCache.find(r => r.id === requestId);
    if (!request) {
        showNotification('Запрос не найден', 'error');
        return;
    }
    
    // Переключаемся на секцию "Отклики доноров"
    const responsesLink = document.querySelector('a[data-section="responses"]');
    if (responsesLink) {
        responsesLink.click();
    }
    
    // Ждём отрисовки секции, затем применяем фильтр
    setTimeout(() => {
        // Устанавливаем фильтр по группе крови
        const bloodFilterSelect = document.getElementById('filter-blood');
        if (bloodFilterSelect) {
            bloodFilterSelect.value = request.blood_type;
            // Триггерим событие change для применения фильтра
            bloodFilterSelect.dispatchEvent(new Event('change'));
        }
        
        // Устанавливаем фильтр по запросу
        const requestFilterSelect = document.getElementById('filter-request');
        if (requestFilterSelect) {
            requestFilterSelect.value = requestId;
            requestFilterSelect.dispatchEvent(new Event('change'));
        }
        
        // Прокручиваем к секции
        const responsesSection = document.getElementById('responses');
        if (responsesSection) {
            responsesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        showNotification(`Фильтр: ${request.blood_type} для запроса #${requestId}`, 'info');
    }, 300);
}

/**
 * Записать успешную донацию
 */
async function recordDonation(donorId, responseId = null) {
    // Запросить подтверждение
    const confirmed = confirm('Подтвердить, что донор сдал кровь?');
    if (!confirmed) return;
    
    // Получить информацию о доноре
    const donorResponse = await fetch(`${MC_API_URL}/donors?donor_id=${donorId}`, {
        headers: getAuthHeaders()
    });
    
    if (!donorResponse.ok) {
        showNotification('Ошибка загрузки данных донора', 'error');
        return;
    }
    
    const donors = await donorResponse.json();
    const donor = donors.find(d => d.id === donorId);
    
    if (!donor) {
        showNotification('Донор не найден', 'error');
        return;
    }
    
    // Запросить объём крови
    const volume = prompt('Объём сданной крови (мл):', '450');
    if (!volume) return;
    
    const volumeInt = parseInt(volume);
    if (isNaN(volumeInt) || volumeInt < 100 || volumeInt > 600) {
        showNotification('Некорректный объём крови', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${MC_API_URL}/medical-center/donations`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                donor_id: donorId,
                blood_type: donor.blood_type,
                volume_ml: volumeInt,
                donation_date: new Date().toISOString().split('T')[0],
                response_id: responseId,
                notes: ''
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('✅ Донация успешно записана!', 'success');
            // Обновляем списки
            await loadResponsesFromAPI();
            await loadDonorsFromAPI();
        } else {
            showNotification('❌ ' + (result.error || 'Ошибка записи донации'), 'error');
        }
    } catch (error) {
        console.error('Ошибка записи донации:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Подтвердить отклик донора
 */
async function confirmResponse(responseId) {
    if (!confirm('Подтвердить отклик донора?\n\nБудет выполнена валидация группы крови и времени с последней донации.')) return;
    
    try {
        const response = await fetch(`${MC_API_URL}/responses/${responseId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ 
                status: 'confirmed',
                comment: 'Подтверждён медцентром'
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('✅ Отклик подтверждён', 'success');
            
            // Перезагрузить запросы, чтобы увидеть автозакрытие
            await loadBloodRequestsFromAPI();
            await showAllResponses(currentResponsesData[0]?.request_id);
        } else {
            // Показываем ошибку валидации
            const error = await response.json();
            const errorMsg = error.error || 'Ошибка подтверждения';
            
            // Если это ошибка валидации - показываем подробно
            if (response.status === 400) {
                alert(`❌ ВАЛИДАЦИЯ НЕ ПРОЙДЕНА\n\n${errorMsg}`);
            } else {
                showNotification(`❌ ${errorMsg}`, 'error');
            }
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Отменить подтверждение отклика (вернуть в pending)
 */
async function unconfirmResponse(responseId) {
    if (!confirm('Отменить подтверждение?\n\nОтклик вернётся в статус "Ожидает".')) return;
    
    try {
        const response = await fetch(`${MC_API_URL}/responses/${responseId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ 
                status: 'pending',
                comment: 'Подтверждение отменено'
            })
        });
        
        if (response.ok) {
            showNotification('✅ Подтверждение отменено', 'success');
            await showAllResponses(currentResponsesData[0]?.request_id);
        } else {
            showNotification('❌ Ошибка отмены', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Отклонить отклик донора
 */
async function rejectResponse(responseId) {
    const reason = prompt('Причина отклонения (необязательно):');
    if (reason === null) return; // Пользователь отменил
    
    try {
        const response = await fetch(`${MC_API_URL}/responses/${responseId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ 
                status: 'rejected',
                comment: reason || 'Отклонён медцентром'
            })
        });
        
        if (response.ok) {
            showNotification('✅ Отклик отклонён', 'success');
            await showAllResponses(currentResponsesData[0]?.request_id);
        } else {
            showNotification('❌ Ошибка отклонения', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}


// ============================================
// СТАТИСТИКА
// ============================================

let currentStatsperiod = 'month';
let statsData = null;

async function initStatistics() {
    // Устанавливаем текущую дату как макс. для date inputs
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('stats-date-to').value = today;
    
    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    document.getElementById('stats-date-from').value = monthAgo.toISOString().split('T')[0];
    
    // Обработчики кнопок периода
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentStatsperiod = btn.dataset.period;
            loadStatistics();
        });
    });
    
    // Применить кастомный период
    document.getElementById('apply-custom-period').addEventListener('click', () => {
        loadStatistics(true);
    });
    
    // Экспорт
    document.getElementById('export-stats-btn').addEventListener('click', exportStatistics);
    
    // Загрузить при открытии секции
    loadStatistics();
}

async function loadStatistics(useCustomDates = false) {
    try {
        let url = `${API_URL}/medical-center/statistics?`;
        
        if (useCustomDates) {
            const from = document.getElementById('stats-date-from').value;
            const to = document.getElementById('stats-date-to').value;
            url += `from=${from}&to=${to}`;
        } else {
            url += `period=${currentStatsperiod}`;
        }
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки статистики');
        }
        
        statsData = await response.json();
        renderStatistics(statsData);
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        showNotification('Ошибка загрузки статистики', 'error');
    }
}

function renderStatistics(stats) {
    console.log('Рендеринг статистики:', stats);
    
    // Проверка данных
    if (!stats) {
        console.error('Нет данных статистики');
        showNotification('Нет данных статистики', 'error');
        return;
    }
    
    // Проверяем, есть ли полная структура
    if (!stats.blood_requests || !stats.responses || !stats.donations) {
        console.error('Неполные данные статистики:', stats);
        showNotification('Ошибка: неполные данные статистики', 'error');
        return;
    }
    
    // Основные метрики (с форматированием)
    document.getElementById('stat-requests').textContent = formatNumber(stats.blood_requests.total || 0);
    document.getElementById('stat-donors').textContent = formatNumber(stats.responses.unique_donors || 0);
    document.getElementById('stat-donations').textContent = formatNumber(stats.donations.total || 0);
    document.getElementById('stat-volume').textContent = formatVolume(stats.donations.total_volume_ml || 0);
    
    // Изменения
    renderStatChange('stat-requests-change', stats.blood_requests.change_percent || 0);
    renderStatChange('stat-donors-change', stats.responses.change_percent || 0);
    renderStatChange('stat-donations-change', stats.donations.change_percent || 0);
    renderStatChange('stat-volume-change', stats.donations.change_percent || 0);
    
    // Диаграмма по срочности
    renderUrgencyChart(stats.blood_requests.by_urgency);
    
    // Диаграмма по группам крови
    renderBloodTypeChart(stats.donations.by_blood_type);
    
    // Детальная статистика ЗАПРОСОВ (с форматированием)
    document.getElementById('detail-total-requests').textContent = formatNumber(stats.blood_requests.total);
    document.getElementById('detail-active-requests').textContent = formatNumber(stats.blood_requests.active);
    document.getElementById('detail-closed-requests').textContent = formatNumber(stats.blood_requests.closed);
    document.getElementById('detail-cancelled-requests').textContent = formatNumber(stats.blood_requests.cancelled);
    document.getElementById('detail-expired-requests').textContent = formatNumber(stats.blood_requests.expired || 0);
    document.getElementById('detail-critical-requests').textContent = formatNumber(stats.blood_requests.by_urgency?.critical || 0);
    document.getElementById('detail-urgent-requests').textContent = formatNumber(stats.blood_requests.by_urgency?.urgent || 0);
    
    // Детальная статистика ОТКЛИКОВ (с форматированием)
    document.getElementById('detail-total-responses').textContent = formatNumber(stats.responses.total_responses);
    document.getElementById('detail-confirmed-responses').textContent = formatNumber(stats.responses.confirmed);
    document.getElementById('detail-pending-responses').textContent = formatNumber(stats.responses.pending || 0);
    document.getElementById('detail-declined-responses').textContent = formatNumber(stats.responses.declined || 0);
    document.getElementById('detail-conversion-rate').textContent = stats.responses.conversion_rate + '%';
    document.getElementById('detail-unique-donors').textContent = formatNumber(stats.responses.unique_donors);
    
    // Детальная статистика ДОНАЦИЙ (с форматированием)
    document.getElementById('detail-total-donations').textContent = formatNumber(stats.donations.total);
    document.getElementById('detail-total-volume-ml').textContent = formatNumber(stats.donations.total_volume_ml) + ' мл';
    document.getElementById('detail-total-volume-liters').textContent = formatVolume(stats.donations.total_volume_ml);
    
    // Средние показатели (с форматированием)
    const avgResponsesPerRequest = stats.blood_requests.total > 0 
        ? (stats.responses.total_responses / stats.blood_requests.total).toFixed(1) 
        : 0;
    document.getElementById('detail-avg-responses').textContent = avgResponsesPerRequest;
    
    const avgVolume = stats.donations.total > 0 
        ? (stats.donations.total_volume_ml / stats.donations.total).toFixed(0) 
        : 0;
    document.getElementById('detail-avg-volume').textContent = formatNumber(avgVolume) + ' мл';
}

function renderStatChange(elementId, change) {
    const el = document.getElementById(elementId);
    el.textContent = (change > 0 ? '+' : '') + change + '%';
    el.className = 'stat-change';
    if (change > 0) el.classList.add('positive');
    if (change < 0) el.classList.add('negative');
}

function renderUrgencyChart(urgencyData) {
    const container = document.getElementById('urgency-chart');
    const total = urgencyData.normal + urgencyData.needed + urgencyData.urgent + urgencyData.critical;
    
    if (total === 0) {
        container.innerHTML = '<div class="chart-empty">Нет данных</div>';
        return;
    }
    
    const colors = {
        'normal': '#95a5a6',
        'needed': '#f39c12',
        'urgent': '#e67e22',
        'critical': '#e74c3c'
    };
    
    const labels = {
        'normal': 'Обычные',
        'needed': 'Нужно пополнить',
        'urgent': 'Срочные',
        'critical': 'Критичные'
    };
    
    const data = [
        { key: 'normal', value: urgencyData.normal },
        { key: 'needed', value: urgencyData.needed },
        { key: 'urgent', value: urgencyData.urgent },
        { key: 'critical', value: urgencyData.critical }
    ].filter(d => d.value > 0);
    
    container.innerHTML = `
        <div class="chart-pie-list">
            ${data.map(d => `
                <div class="chart-pie-item">
                    <div class="chart-pie-color" style="background: ${colors[d.key]}"></div>
                    <div class="chart-pie-label">${labels[d.key]}</div>
                    <div class="chart-pie-value">${d.value}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderBloodTypeChart(bloodTypeData) {
    const container = document.getElementById('blood-type-chart');
    
    if (!bloodTypeData || bloodTypeData.length === 0) {
        container.innerHTML = '<div class="chart-empty">Нет данных о донациях</div>';
        return;
    }
    
    const maxCount = Math.max(...bloodTypeData.map(d => d.count), 1);
    const maxVolume = Math.max(...bloodTypeData.map(d => d.total_volume || 0), 1);
    
    // Цвета для разных групп крови
    const bloodColors = {
        'O+': '#e74c3c', 'O-': '#c0392b',
        'A+': '#3498db', 'A-': '#2980b9',
        'B+': '#2ecc71', 'B-': '#27ae60',
        'AB+': '#9b59b6', 'AB-': '#8e44ad'
    };
    
    container.innerHTML = `
        <div class="blood-type-chart-grid">
            ${bloodTypeData.map(d => {
                const volumeLiters = ((d.total_volume || 0) / 1000).toFixed(2);
                const color = bloodColors[d.blood_type] || '#95a5a6';
                
                return `
                    <div class="blood-type-card" style="border-left: 4px solid ${color}">
                        <div class="blood-type-header">
                            <div class="blood-type-icon" style="background: linear-gradient(135deg, ${color}, ${color}dd)">
                                🩸
                            </div>
                            <div class="blood-type-name">${d.blood_type}</div>
                        </div>
                        <div class="blood-type-stats">
                            <div class="blood-type-stat">
                                <div class="stat-label">Донаций</div>
                                <div class="stat-value">${d.count}</div>
                            </div>
                            <div class="blood-type-stat">
                                <div class="stat-label">Объём</div>
                                <div class="stat-value">${volumeLiters} л</div>
                            </div>
                        </div>
                        <div class="blood-type-bar-container">
                            <div class="blood-type-bar" style="width: ${(d.count / maxCount) * 100}%; background: ${color}"></div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function exportStatistics() {
    try {
        console.log('🔄 Начало экспорта статистики...');
        
        let url = `${API_URL}/medical-center/statistics/export?`;
        
        // Используем те же параметры, что и для текущей статистики
        const from = document.getElementById('stats-date-from').value;
        const to = document.getElementById('stats-date-to').value;
        
        if (from && to) {
            url += `from=${from}&to=${to}`;
        } else {
            url += `period=${currentStatsperiod}`;
        }
        
        console.log('📡 URL экспорта:', url);
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        console.log('📥 Ответ сервера:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Ошибка от сервера:', errorText);
            throw new Error(`Ошибка экспорта: ${response.status} ${response.statusText}`);
        }
        
        // Скачиваем файл
        const blob = await response.blob();
        console.log('📦 Blob получен, размер:', blob.size, 'байт');
        
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        // Получаем имя файла из заголовка
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `statistics_${new Date().toISOString().split('T')[0]}.txt`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }
        
        console.log('💾 Имя файла:', filename);
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
        console.log('✅ Файл успешно скачан!');
        showNotification('Статистика успешно скачана', 'success');
        
    } catch (error) {
        console.error('❌ Ошибка экспорта:', error);
        showNotification(`Ошибка экспорта статистики: ${error.message}`, 'error');
    }
}

// Инициализация статистики при открытии секции
document.addEventListener('DOMContentLoaded', () => {
    // Добавляем в обработчик навигации
    const existingNavHandler = document.querySelector('[data-section="statistics"]');
    if (existingNavHandler) {
        existingNavHandler.addEventListener('click', () => {
            setTimeout(initStatistics, 100);
        });
    }
});

// ============================================
// ОЧИСТКА УСТАРЕВШИХ ОТКЛИКОВ
// ============================================

async function cleanupOutdatedResponses() {
    const confirmed = confirm(
        '⚠️ Удалить все устаревшие отклики?\n\n' +
        'Будут удалены отклики со статусом "Ожидает", "Отклонён" и "Отменён" ' +
        'на закрытые, отменённые или истёкшие запросы.\n\n' +
        'Подтверждённые и завершённые отклики НЕ будут удалены.'
    );
    
    if (!confirmed) return;
    
    try {
        const response = await fetch(`${API_URL}/medical-center/responses/cleanup`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Ошибка очистки');
        }
        
        const result = await response.json();
        
        showNotification(
            `✅ ${result.message}`,
            'success'
        );
        
        // Перезагружаем список откликов
        await loadResponsesFromAPI();
        
    } catch (error) {
        console.error('Ошибка очистки откликов:', error);
        showNotification('❌ Ошибка при очистке откликов', 'error');
    }
}

// Инициализация кнопки очистки
document.addEventListener('DOMContentLoaded', () => {
    const cleanupBtn = document.getElementById('cleanup-responses-btn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', cleanupOutdatedResponses);
    }
});

// ============================================
// СКРЫТИЕ ОТКЛИКОВ
// ============================================

async function hideResponse(responseId) {
    const confirmed = confirm('Скрыть этот отклик?\n\nОтклик не будет удалён из базы данных, но исчезнет из списка.');
    
    if (!confirmed) return;
    
    try {
        const response = await fetch(`${API_URL}/responses/${responseId}/hide`, {
            method: 'PUT',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Ошибка скрытия');
        }
        
        showNotification('✅ Отклик скрыт', 'success');
        
        // Перезагружаем список
        await loadResponsesFromAPI();
        
    } catch (error) {
        console.error('Ошибка скрытия отклика:', error);
        showNotification('❌ Ошибка при скрытии отклика', 'error');
    }
}

/**
 * Инициализация мессенджера
 */
function initMessenger() {
    // Используем функцию из messenger.js, если она доступна
    if (typeof initMessengerUI === 'function') {
        initMessengerUI();
    }
}
