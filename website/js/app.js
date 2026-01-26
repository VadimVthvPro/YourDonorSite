/**
 * Твой Донор - Главный JavaScript файл
 * Интерактивность, анимации и динамический функционал
 */

console.log('==== app.js ЗАГРУЖЕН ====');

// Глобальный URL для API
// Используем API URL из config.js если доступен, иначе fallback
if (!window.API_URL) {
    window.API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:5001/api'
        : `${window.location.protocol}//${window.location.hostname}:5001/api`;
}
const API_URL = window.API_URL;

/**
 * 🔥 АВТОМАТИЧЕСКИЙ ВХОД ПРИ ОТКРЫТИИ ГЛАВНОЙ СТРАНИЦЫ
 * Проверяет сохранённую сессию и перенаправляет на dashboard
 */
async function autoRedirectIfAuthenticated() {
    // Проверяем, что AuthStorage доступен
    if (typeof AuthStorage === 'undefined') {
        console.warn('⚠️ AuthStorage не загружен, пропускаем авто-вход');
        return false;
    }
    
    // Проверяем наличие сохранённой сессии
    if (!AuthStorage.hasSession()) {
        console.log('📋 Нет сохранённой сессии');
        return false;
    }
    
    console.log('🔍 Найдена сохранённая сессия, проверяем валидность...');
    
    // Валидируем токен на backend
    const validation = await AuthStorage.validate();
    
    if (validation.valid) {
        console.log('✅ Сессия валидна! Автоматический редирект на dashboard...');
        
        const userType = AuthStorage.getUserType();
        const dashboardUrl = userType === 'donor' 
            ? 'pages/donor-dashboard.html' 
            : 'pages/medcenter-dashboard.html';
        
        // Перенаправляем на dashboard
        window.location.href = dashboardUrl;
        return true; // Редирект выполнен
    } else {
        console.log('❌ Сессия невалидна');
        return false;
    }
}

document.addEventListener('DOMContentLoaded', async function() {
    // 🔥 СНАЧАЛА проверяем сессию и делаем редирект при необходимости
    const redirected = await autoRedirectIfAuthenticated();
    
    // Если редирект выполнен, не инициализируем страницу
    if (redirected) return;
    
    // Проверяем авторизацию и обновляем кнопки (если сессия есть, но редиректа не было)
    checkAuthAndUpdateNav();
    
    // Инициализация всех компонентов
    initScrollAnimations();
    initHeader();
    initFAQ();
    initMobileMenu();
    initStatCounters();
    initCentersSelector();
    initSmoothScroll();
});

/**
 * Проверка авторизации и обновление навигации
 */
function checkAuthAndUpdateNav() {
    const authToken = localStorage.getItem('auth_token');
    const userType = localStorage.getItem('user_type');
    const navButtons = document.getElementById('nav-buttons');
    
    if (!navButtons) return;
    
    if (authToken && userType) {
        // Пользователь авторизован
        let dashboardUrl = '';
        let dashboardLabel = '';
        let userName = '';
        
        if (userType === 'donor') {
            dashboardUrl = 'pages/donor-dashboard.html';
            dashboardLabel = 'Личный кабинет';
            const donorData = JSON.parse(localStorage.getItem('donor_user') || '{}');
            userName = donorData.full_name || 'Донор';
        } else if (userType === 'medcenter') {
            dashboardUrl = 'pages/medcenter-dashboard.html';
            dashboardLabel = 'Панель медцентра';
            const mcData = JSON.parse(localStorage.getItem('medcenter_user') || '{}');
            userName = mcData.name || 'Медцентр';
        }
        
        navButtons.innerHTML = `
            <span class="nav-user-name">${userName}</span>
            <a href="${dashboardUrl}" class="btn btn-primary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 18px; height: 18px; margin-right: 6px;">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
                ${dashboardLabel}
            </a>
        `;
    }
}

/**
 * Загрузка статуса крови для главной страницы
 */
async function loadBloodStatus() {
    const container = document.getElementById('blood-status-container');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_URL}/blood-needs/public`);
        const data = await response.json();
        
        if (data.length === 0) {
            container.innerHTML = '<p class="no-data">Данные о потребности в крови пока недоступны</p>';
            return;
        }
        
        // Группируем по медцентрам
        const grouped = {};
        data.forEach(item => {
            if (!grouped[item.medical_center_id]) {
                grouped[item.medical_center_id] = {
                    name: item.medical_center_name,
                    needs: []
                };
            }
            grouped[item.medical_center_id].needs.push(item);
        });
        
        let html = '';
        for (const mcId in grouped) {
            const mc = grouped[mcId];
            html += `
                <div class="blood-status-card">
                    <h3>${mc.name}</h3>
                    <div class="blood-types-grid">
                        ${mc.needs.map(need => `
                            <div class="blood-type-item status-${need.status}">
                                <span class="blood-type">${need.blood_type}</span>
                                <span class="blood-status">${getStatusText(need.status)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Ошибка загрузки статуса крови:', error);
        container.innerHTML = '<p class="loading-error">Не удалось загрузить данные</p>';
    }
}

function getStatusText(status) {
    const texts = {
        'normal': 'Норма',
        'low': 'Мало',
        'critical': 'Срочно!'
    };
    return texts[status] || status;
}

/**
 * Анимации при скролле
 */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.card-animate');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Добавляем задержку для каскадной анимации
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(el => observer.observe(el));
}

/**
 * Поведение шапки при скролле
 */
function initHeader() {
    const header = document.querySelector('.header');
    if (!header) return; // Проверка: элемент может отсутствовать на дашбордах
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        // Добавляем тень при скролле
        if (currentScroll > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });
}

/**
 * FAQ аккордеон
 */
function initFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            // Закрываем все остальные
            faqItems.forEach(otherItem => {
                if (otherItem !== item) {
                    otherItem.classList.remove('active');
                }
            });
            
            // Переключаем текущий
            item.classList.toggle('active');
        });
    });
}

/**
 * Мобильное меню
 */
function initMobileMenu() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');
    const navButtons = document.querySelector('.nav-buttons');
    
    if (!menuBtn) return;
    
    menuBtn.addEventListener('click', () => {
        menuBtn.classList.toggle('active');
        
        // Создаём мобильное меню если его нет
        let mobileNav = document.querySelector('.mobile-nav');
        
        if (!mobileNav) {
            mobileNav = document.createElement('div');
            mobileNav.className = 'mobile-nav';
            mobileNav.innerHTML = `
                <div class="mobile-nav-content">
                    ${navMenu.innerHTML}
                    <div class="mobile-nav-buttons">
                        <a href="pages/auth.html" class="btn btn-outline btn-lg">Войти</a>
                        <a href="pages/auth.html?register=true" class="btn btn-primary btn-lg">Стать донором</a>
                    </div>
                </div>
            `;
            document.body.appendChild(mobileNav);
            
            // Добавляем стили для мобильного меню
            const style = document.createElement('style');
            style.textContent = `
                .mobile-nav {
                    position: fixed;
                    top: 80px;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--color-white);
                    z-index: 999;
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.3s ease;
                }
                .mobile-nav.active {
                    opacity: 1;
                    visibility: visible;
                }
                .mobile-nav-content {
                    padding: 2rem;
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }
                .mobile-nav .nav-menu {
                    display: flex;
                    flex-direction: column;
                    gap: 0;
                }
                .mobile-nav .nav-link {
                    display: block;
                    padding: 1rem 0;
                    font-size: 1.125rem;
                    border-bottom: 1px solid var(--color-gray-100);
                }
                .mobile-nav-buttons {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                    margin-top: 1rem;
                }
                .mobile-nav-buttons .btn {
                    width: 100%;
                }
                .mobile-menu-btn.active span:nth-child(1) {
                    transform: rotate(45deg) translate(5px, 5px);
                }
                .mobile-menu-btn.active span:nth-child(2) {
                    opacity: 0;
                }
                .mobile-menu-btn.active span:nth-child(3) {
                    transform: rotate(-45deg) translate(7px, -6px);
                }
            `;
            document.head.appendChild(style);
            
            // Закрытие при клике на ссылку
            mobileNav.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', () => {
                    menuBtn.classList.remove('active');
                    mobileNav.classList.remove('active');
                });
            });
        }
        
        mobileNav.classList.toggle('active');
    });
}

/**
 * Счётчики статистики с анимацией
 */
function initStatCounters() {
    const counters = document.querySelectorAll('.stat-number[data-count]');
    
    const observerOptions = {
        threshold: 0.5
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    counters.forEach(counter => observer.observe(counter));
}

function animateCounter(element) {
    const target = parseInt(element.dataset.count);
    const duration = 2000; // 2 секунды
    const steps = 60;
    const increment = target / steps;
    let current = 0;
    
    // Функция форматирования числа с триадами
    const formatNumber = (num) => {
        return Math.floor(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    };
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = formatNumber(target);
            clearInterval(timer);
        } else {
            element.textContent = formatNumber(current);
        }
    }, duration / steps);
}

/**
 * Селектор центров донорства
 */
function initCentersSelector() {
    const regionSelect = document.getElementById('region-select');
    const districtSelect = document.getElementById('district-select');
    const centersList = document.getElementById('centers-list');
    
    if (!regionSelect) return;
    
    // База данных центров (будет загружаться из JSON)
    const medicalCentersData = {
        "minsk": {
            "name": "Минск",
            "districts": {
                "central": {
                    "name": "Центральный район",
                    "centers": [
                        {
                            "name": "Республиканский научно-практический центр трансфузиологии и медицинских биотехнологий",
                            "address": "ул. Долгиновский тракт, 160",
                            "type": "hospital"
                        },
                        {
                            "name": "Городская клиническая больница скорой медицинской помощи",
                            "address": "ул. Кижеватова, 58",
                            "type": "hospital"
                        }
                    ]
                },
                "sovetsky": {
                    "name": "Советский район",
                    "centers": [
                        {
                            "name": "6-я городская клиническая больница",
                            "address": "ул. Уральская, 5",
                            "type": "hospital"
                        }
                    ]
                },
                "frunzensky": {
                    "name": "Фрунзенский район",
                    "centers": [
                        {
                            "name": "Минская областная клиническая больница",
                            "address": "ул. Семашко, 8",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "minsk-region": {
            "name": "Минская область",
            "districts": {
                "borisov": {
                    "name": "Борисовский район",
                    "centers": [
                        {
                            "name": "Борисовская центральная районная больница",
                            "address": "г. Борисов, ул. Чапаева, 34",
                            "type": "hospital"
                        }
                    ]
                },
                "molodechno": {
                    "name": "Молодечненский район",
                    "centers": [
                        {
                            "name": "Молодечненская ЦРБ",
                            "address": "г. Молодечно, ул. Космонавтов, 1",
                            "type": "hospital"
                        }
                    ]
                },
                "soligorsk": {
                    "name": "Солигорский район",
                    "centers": [
                        {
                            "name": "Солигорская ЦРБ",
                            "address": "г. Солигорск, ул. Ленина, 35",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "brest": {
            "name": "Брестская область",
            "districts": {
                "brest-city": {
                    "name": "г. Брест",
                    "centers": [
                        {
                            "name": "Брестская областная станция переливания крови",
                            "address": "г. Брест, ул. Медицинская, 6",
                            "type": "hospital"
                        },
                        {
                            "name": "Брестская областная больница",
                            "address": "г. Брест, ул. Медицинская, 7",
                            "type": "hospital"
                        }
                    ]
                },
                "baranovichi": {
                    "name": "Барановичский район",
                    "centers": [
                        {
                            "name": "Барановичская ЦГБ",
                            "address": "г. Барановичи, ул. Советская, 80",
                            "type": "hospital"
                        }
                    ]
                },
                "pinsk": {
                    "name": "Пинский район",
                    "centers": [
                        {
                            "name": "Пинская центральная больница",
                            "address": "г. Пинск, ул. Рокоссовского, 8",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "vitebsk": {
            "name": "Витебская область",
            "districts": {
                "vitebsk-city": {
                    "name": "г. Витебск",
                    "centers": [
                        {
                            "name": "Витебская областная станция переливания крови",
                            "address": "г. Витебск, ул. Чкалова, 18",
                            "type": "hospital"
                        },
                        {
                            "name": "Витебская областная клиническая больница",
                            "address": "г. Витебск, пр. Фрунзе, 43",
                            "type": "hospital"
                        }
                    ]
                },
                "orsha": {
                    "name": "Оршанский район",
                    "centers": [
                        {
                            "name": "Оршанская ЦГБ",
                            "address": "г. Орша, ул. Мира, 20",
                            "type": "hospital"
                        }
                    ]
                },
                "polotsk": {
                    "name": "Полоцкий район",
                    "centers": [
                        {
                            "name": "Полоцкая центральная больница",
                            "address": "г. Полоцк, ул. Гагарина, 6",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "gomel": {
            "name": "Гомельская область",
            "districts": {
                "gomel-city": {
                    "name": "г. Гомель",
                    "centers": [
                        {
                            "name": "Гомельская областная станция переливания крови",
                            "address": "г. Гомель, ул. Братьев Лизюковых, 5",
                            "type": "hospital"
                        },
                        {
                            "name": "Гомельская областная клиническая больница",
                            "address": "г. Гомель, ул. Братьев Лизюковых, 5",
                            "type": "hospital"
                        }
                    ]
                },
                "mozyr": {
                    "name": "Мозырский район",
                    "centers": [
                        {
                            "name": "Мозырская ЦГБ",
                            "address": "г. Мозырь, ул. Котловца, 14",
                            "type": "hospital"
                        }
                    ]
                },
                "zhlobin": {
                    "name": "Жлобинский район",
                    "centers": [
                        {
                            "name": "Жлобинская ЦРБ",
                            "address": "г. Жлобин, ул. Воровского, 1",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "grodno": {
            "name": "Гродненская область",
            "districts": {
                "grodno-city": {
                    "name": "г. Гродно",
                    "centers": [
                        {
                            "name": "Гродненская областная станция переливания крови",
                            "address": "г. Гродно, ул. Обухова, 15",
                            "type": "hospital"
                        },
                        {
                            "name": "Гродненская областная клиническая больница",
                            "address": "г. Гродно, бул. Ленинского Комсомола, 52",
                            "type": "hospital"
                        }
                    ]
                },
                "lida": {
                    "name": "Лидский район",
                    "centers": [
                        {
                            "name": "Лидская ЦРБ",
                            "address": "г. Лида, ул. Мицкевича, 1",
                            "type": "hospital"
                        }
                    ]
                },
                "slonim": {
                    "name": "Слонимский район",
                    "centers": [
                        {
                            "name": "Слонимская ЦРБ",
                            "address": "г. Слоним, ул. Советская, 50",
                            "type": "hospital"
                        }
                    ]
                }
            }
        },
        "mogilev": {
            "name": "Могилёвская область",
            "districts": {
                "mogilev-city": {
                    "name": "г. Могилёв",
                    "centers": [
                        {
                            "name": "Могилёвская областная станция переливания крови",
                            "address": "г. Могилёв, ул. Б.Бирули, 12",
                            "type": "hospital"
                        },
                        {
                            "name": "Могилёвская областная больница",
                            "address": "г. Могилёв, ул. Белыницкого-Бирули, 12",
                            "type": "hospital"
                        }
                    ]
                },
                "bobruisk": {
                    "name": "Бобруйский район",
                    "centers": [
                        {
                            "name": "Бобруйская городская больница скорой медицинской помощи",
                            "address": "г. Бобруйск, ул. Советская, 116",
                            "type": "hospital"
                        }
                    ]
                },
                "osipovichi": {
                    "name": "Осиповичский район",
                    "centers": [
                        {
                            "name": "Осиповичская ЦРБ",
                            "address": "г. Осиповичи, ул. Сумченко, 101",
                            "type": "hospital"
                        }
                    ]
                }
            }
        }
    };
    
    // Обработчик выбора области
    regionSelect.addEventListener('change', function() {
        const region = this.value;
        
        // Сбрасываем район
        districtSelect.innerHTML = '<option value="">Выберите район</option>';
        districtSelect.disabled = !region;
        
        // Очищаем список центров
        showPlaceholder();
        
        if (region && medicalCentersData[region]) {
            const districts = medicalCentersData[region].districts;
            
            for (const [key, value] of Object.entries(districts)) {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = value.name;
                districtSelect.appendChild(option);
            }
        }
    });
    
    // Обработчик выбора района
    districtSelect.addEventListener('change', function() {
        const region = regionSelect.value;
        const district = this.value;
        
        if (region && district && medicalCentersData[region]) {
            const centers = medicalCentersData[region].districts[district]?.centers || [];
            displayCenters(centers);
        } else {
            showPlaceholder();
        }
    });
    
    function displayCenters(centers) {
        if (centers.length === 0) {
            centersList.innerHTML = `
                <div class="centers-placeholder">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p>В выбранном районе нет зарегистрированных центров донорства</p>
                </div>
            `;
            return;
        }
        
        centersList.innerHTML = centers.map(center => `
            <div class="center-item">
                <div class="center-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                    </svg>
                </div>
                <div class="center-info">
                    <h4>${center.name}</h4>
                    <p>${center.address}</p>
                </div>
            </div>
        `).join('');
    }
    
    function showPlaceholder() {
        centersList.innerHTML = `
            <div class="centers-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                    <path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                <p>Выберите область и район, чтобы увидеть ближайшие центры донорства</p>
            </div>
        `;
    }
}

/**
 * Плавный скролл к якорям
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Игнорируем пустые хеши или просто "#"
            if (!href || href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                const header = document.querySelector('.header');
                const headerHeight = header ? header.offsetHeight : 0; // Проверка существования
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/**
 * Утилиты
 */

// Debounce функция
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Форматирование даты
function formatDate(date) {
    const options = { day: 'numeric', month: 'long', year: 'numeric' };
    return new Date(date).toLocaleDateString('ru-RU', options);
}

// Проверка мобильного устройства
function isMobile() {
    return window.innerWidth < 768;
}

// Экспорт для использования в других модулях
window.DonorApp = {
    debounce,
    formatDate,
    isMobile
};
