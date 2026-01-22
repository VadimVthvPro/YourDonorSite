/**
 * Твой Донор - Личный кабинет медцентра
 * Управление донорством, светофор, отклики
 */

console.log('==== medcenter-dashboard.js ЗАГРУЖЕН ====');

// Используем API_URL из app.js или определяем свой
const MC_API_URL = window.API_URL || 'http://localhost:5001/api';

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
        initLogout();
        console.log('✓ Выход инициализирован');
    } catch (e) { console.error('✗ Ошибка initLogout:', e); }
    
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
        { blood_type: 'O-', status: 'low' },
        { blood_type: 'A+', status: 'normal' },
        { blood_type: 'A-', status: 'critical' },
        { blood_type: 'B+', status: 'normal' },
        { blood_type: 'B-', status: 'low' },
        { blood_type: 'AB+', status: 'normal' },
        { blood_type: 'AB-', status: 'normal' }
    ];
    renderMiniTrafficLight();
    renderFullTrafficLight();
}

function getStatusClass(status) {
    const map = { 'normal': 'ok', 'low': 'need', 'critical': 'urgent' };
    return map[status] || 'ok';
}

function getStatusText(status) {
    const map = { 'normal': 'Достаточно', 'low': 'Нужно пополнить', 'critical': 'Срочно нужна' };
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
        'low': '#f59e0b', 
        'critical': '#ef4444'
    };
    
    const statusLabels = {
        'normal': 'Достаточно',
        'low': 'Нужно пополнить',
        'critical': 'Срочно нужна'
    };
    
    container.innerHTML = bloodNeedsData.map(item => `
        <div class="blood-panel ${item.status}" 
             data-type="${item.blood_type}" 
             data-status="${item.status}"
             style="background: ${statusColors[item.status]};">
            <div class="blood-panel-type">${item.blood_type}</div>
            <div class="blood-panel-status">${statusLabels[item.status]}</div>
            <div class="blood-panel-buttons">
                <button class="panel-btn ${item.status === 'normal' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'normal')"
                        title="Достаточно">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 13l4 4L19 7"/>
                    </svg>
                </button>
                <button class="panel-btn ${item.status === 'low' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'low')"
                        title="Нужно пополнить">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 8v4"/>
                    </svg>
                </button>
                <button class="panel-btn ${item.status === 'critical' ? 'active' : ''}" 
                        onclick="setBloodStatus('${item.blood_type}', 'critical')"
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
            
            if (status === 'critical') {
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
        renderResponses(responses);
    } catch (error) {
        console.error('Ошибка загрузки откликов:', error);
        // Fallback данные
        const responses = [
            { id: 1, donor_name: 'Нет откликов', donor_blood_type: '-', donor_phone: '-', status: 'pending', created_at: new Date().toISOString() }
        ];
        renderResponses(responses);
    }
}

function renderResponses(responses) {
    if (!responses) responses = [];
    
    const pendingCount = responses.filter(r => r.status === 'pending').length;
    const badge = document.getElementById('responses-badge');
    const statPending = document.getElementById('stat-pending');
    if (badge) badge.textContent = pendingCount;
    if (statPending) statPending.textContent = pendingCount;
    
    // Последние отклики на главной
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
    
    // Полный список
    const listContainer = document.getElementById('responses-list');
    if (listContainer) {
        if (responses.length === 0) {
            listContainer.innerHTML = '<p class="no-data">Нет откликов от доноров</p>';
        } else {
            listContainer.innerHTML = responses.map(r => `
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
                        ` : `
                            <span class="donor-status-badge ${r.status === 'confirmed' ? 'available' : ''}">${getResponseStatusText(r.status)}</span>
                        `}
                    </div>
                </div>
            `).join('');
            
            // Обработчики кнопок
            listContainer.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const action = btn.dataset.action;
                    const id = btn.dataset.id;
                    const newStatus = action === 'approve' ? 'confirmed' : 'cancelled';
                    
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
            showNotification(status === 'confirmed' ? 'Донор подтверждён!' : 'Заявка отклонена', 'success');
            loadResponsesFromAPI();
        } else {
            const result = await response.json();
            showNotification(result.error || 'Ошибка', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
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
        renderStatistics(stats);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        renderStatistics({});
    }
}

function renderStatistics(apiStats) {
    // Обновляем счётчики на главной
    const totalDonors = document.getElementById('stat-donors');
    const activeRequests = document.getElementById('stat-requests');
    
    if (totalDonors) totalDonors.textContent = apiStats.total_donors || 0;
    if (activeRequests) activeRequests.textContent = apiStats.active_requests || 0;
    
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
                <span class="blood-stat-value">${s.count}</span>
            </div>
        `).join('');
    }
    
    // График донаций (пока статический, можно расширить)
    const chartContainer = document.getElementById('donations-chart');
    if (chartContainer) {
        const months = ['Авг', 'Сен', 'Окт', 'Ноя', 'Дек', 'Янв'];
        const values = [0, 0, 0, 0, 0, apiStats.month_donations || 0];
        const max = Math.max(...values, 1);
        
        chartContainer.innerHTML = months.map((m, i) => `
            <div class="chart-bar">
                <span class="bar-value">${values[i]}</span>
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
    
    if (!requests || requests.length === 0) {
        container.innerHTML = '<p class="no-data">Нет активных запросов на донацию</p>';
        return;
    }
    
    container.innerHTML = requests.map(req => {
        const urgencyLabels = {
            'normal': 'Обычная',
            'urgent': 'Срочная',
            'critical': 'Критическая'
        };
        
        const statusLabels = {
            'active': 'Активный',
            'fulfilled': 'Выполнен',
            'cancelled': 'Отменён'
        };
        
        const createdDate = new Date(req.created_at).toLocaleDateString('ru-RU');
        const expiresDate = req.expires_at ? new Date(req.expires_at).toLocaleDateString('ru-RU') : '—';
        
        return `
            <div class="request-card ${req.status}">
                <div class="request-header">
                    <div class="request-blood">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 4C12 4 6 10 6 14a6 6 0 1012 0c0-4-6-10-6-10z"/>
                        </svg>
                        ${req.blood_type}
                    </div>
                    <div class="request-urgency ${req.urgency}">
                        ${urgencyLabels[req.urgency]}
                    </div>
                </div>
                
                <div class="request-body">
                    ${req.description ? `<p class="request-description">${req.description}</p>` : ''}
                    
                    <div class="request-meta">
                        <div class="request-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <polyline points="12 6 12 12 16 14"/>
                            </svg>
                            Создан: ${createdDate}
                        </div>
                        <div class="request-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                                <line x1="16" y1="2" x2="16" y2="6"/>
                                <line x1="8" y1="2" x2="8" y2="6"/>
                                <line x1="3" y1="10" x2="21" y2="10"/>
                            </svg>
                            Истекает: ${expiresDate}
                        </div>
                        <div class="request-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                            </svg>
                            Статус: ${statusLabels[req.status]}
                        </div>
                    </div>
                </div>
                
                <div class="request-footer">
                    <div class="request-stats">
                        <div class="request-stat">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                                <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
                            </svg>
                            <strong>${req.responses_count || 0}</strong> откликов
                        </div>
                        <div class="request-stat">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"/>
                            </svg>
                            <strong>${req.approved_count || 0}</strong> подтверждено
                        </div>
                    </div>
                    
                    <div class="request-actions">
                        ${req.status === 'active' ? `
                            <button class="btn btn-sm btn-success" onclick="fulfillRequest(${req.id})">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="20 6 9 17 4 12"/>
                                </svg>
                                Выполнен
                            </button>
                            <button class="btn btn-sm btn-outline" onclick="cancelRequest(${req.id})">Отменить</button>
                        ` : ''}
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteRequest(${req.id})">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
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
    if (!confirm('Отметить запрос как выполненный?')) return;
    
    try {
        const response = await fetch(`${MC_API_URL}/blood-requests/${requestId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status: 'fulfilled' })
        });
        
        if (response.ok) {
            showNotification('Запрос отмечен как выполненный', 'success');
            await loadBloodRequestsFromAPI();
        } else {
            showNotification('Ошибка обновления статуса', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения', 'error');
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

/**
 * Модальные окна
 */
function initModals() {
    // Срочный запрос
    document.getElementById('urgent-request-btn')?.addEventListener('click', openUrgentModal);
    
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
            
            const data = {
                blood_type: bloodType,
                urgency: formData.get('urgency'),
                description: formData.get('description'),
                expires_days: parseInt(formData.get('expires_days')) || 7
            };
            
            createRequestBtn.classList.add('loading');
            await createBloodRequest(data);
            createRequestBtn.classList.remove('loading');
            form.reset();
        });
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
    document.querySelector('[data-action="send"]')?.addEventListener('click', () => {
        const bloodType = document.querySelector('input[name="urgent_blood"]:checked');
        if (!bloodType) {
            showNotification('Выберите группу крови', 'error');
            return;
        }
        
        const count = donorCounts[bloodType.value] || 0;
        showNotification(`Срочный запрос отправлен ${count} донорам с группой ${bloodType.value}!`, 'success');
        closeModal(document.getElementById('urgent-modal'));
    });
}

function openUrgentModal() {
    document.getElementById('urgent-modal').classList.add('active');
}

function openDonorModal(donor) {
    const modal = document.getElementById('donor-modal');
    const content = document.getElementById('donor-modal-content');
    
    content.innerHTML = `
        <div class="donor-details">
            <div class="donor-detail-row">
                <span class="label">ФИО:</span>
                <span class="value">${donor.name}</span>
            </div>
            <div class="donor-detail-row">
                <span class="label">Группа крови:</span>
                <span class="value blood">${donor.blood}</span>
            </div>
            <div class="donor-detail-row">
                <span class="label">Последняя донация:</span>
                <span class="value">${donor.lastDonation}</span>
            </div>
            <div class="donor-detail-row">
                <span class="label">Статус:</span>
                <span class="value ${donor.status}">${donor.status === 'available' ? 'Доступен' : 'Восстановление'}</span>
            </div>
        </div>
    `;
    
    // Добавляем стили
    const style = document.createElement('style');
    style.textContent = `
        .donor-details {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
        }
        .donor-detail-row {
            display: flex;
            justify-content: space-between;
            padding-bottom: var(--spacing-md);
            border-bottom: 1px solid var(--color-gray-100);
        }
        .donor-detail-row .label {
            color: var(--color-gray-500);
        }
        .donor-detail-row .value {
            font-weight: 600;
        }
        .donor-detail-row .value.blood {
            padding: 0.25rem 0.75rem;
            background: var(--color-primary-lighter);
            color: var(--color-primary);
            border-radius: var(--radius-full);
        }
        .donor-detail-row .value.available {
            color: var(--color-success);
        }
        .donor-detail-row .value.recovery {
            color: var(--color-warning);
        }
    `;
    document.head.appendChild(style);
    
    modal.classList.add('active');
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
    notification.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' 
                ? '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/>' 
                : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
        </svg>
        <span>${message}</span>
    `;
    
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 100px;
            right: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 24px;
            background: var(--color-white);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-xl);
            z-index: 1001;
            animation: slideIn 0.3s ease;
        }
        .notification.success { border-left: 4px solid var(--color-success); }
        .notification.success svg { color: var(--color-success); }
        .notification.error { border-left: 4px solid var(--color-danger); }
        .notification.error svg { color: var(--color-danger); }
        .notification.info { border-left: 4px solid var(--color-accent); }
        .notification.info svg { color: var(--color-accent); }
        .notification svg { width: 20px; height: 20px; }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(100%); }
            to { opacity: 1; transform: translateX(0); }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
}
