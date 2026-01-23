/**
 * Твой Донор - Авторизация и регистрация
 * Логика работы форм входа и регистрации
 */

const API_URL = 'http://localhost:5001/api';

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 auth.js ЗАГРУЖЕН');
    initTypeSwitcher();
    initModeTabs();
    initFormSteps();
    initPasswordToggle();
    loadRegionsFromAPI();
    initFormValidation();
    checkUrlParams();
    
    // Показываем форму входа по умолчанию
    showDefaultForms();
    console.log('✅ auth.js инициализация завершена');
});

/**
 * Показать формы по умолчанию
 */
function showDefaultForms() {
    // Показываем форму донора по умолчанию
    const donorForm = document.getElementById('donor-form');
    const medcenterForm = document.getElementById('medcenter-form');
    
    if (donorForm) donorForm.style.display = 'block';
    if (medcenterForm) medcenterForm.style.display = 'none';
    
    // Показываем форму входа по умолчанию для каждого контейнера
    document.querySelectorAll('.auth-form-container').forEach(container => {
        const loginForm = container.querySelector('[id$="-login-form"]');
        const registerForm = container.querySelector('[id$="-register-form"]');
        const loginTab = container.querySelector('.mode-tab[data-mode="login"]');
        const registerTab = container.querySelector('.mode-tab[data-mode="register"]');
        
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
        if (loginTab) loginTab.classList.add('active');
        if (registerTab) registerTab.classList.remove('active');
    });
}

// Загрузка регионов из API
async function loadRegionsFromAPI() {
    try {
        const response = await fetch(`${API_URL}/regions`);
        const regions = await response.json();
        
        // Заполняем все селекторы регионов
        const regionSelects = document.querySelectorAll('select[name="region_id"], #donor-region, #reg-donor-region, #mc-region, #reg-mc-region');
        regionSelects.forEach(select => {
            if (select) {
                select.innerHTML = '<option value="">Выберите область</option>';
                regions.forEach(region => {
                    const option = document.createElement('option');
                    option.value = region.id;
                    option.textContent = region.name;
                    select.appendChild(option);
                });
                
                // Добавляем обработчик изменения
                select.addEventListener('change', () => loadDistricts(select));
            }
        });
    } catch (error) {
        console.error('Ошибка загрузки регионов:', error);
        // Fallback - используем локальные данные
        initRegionSelectors();
    }
}

// Загрузка районов
async function loadDistricts(regionSelect) {
    const regionId = regionSelect.value;
    const form = regionSelect.closest('form');
    const districtSelect = form.querySelector('select[name="district_id"], [id$="-district"]');
    const medcenterSelect = form.querySelector('select[name="medical_center_id"], [id$="-medcenter"]');
    
    if (!districtSelect) return;
    
    districtSelect.innerHTML = '<option value="">Загрузка...</option>';
    districtSelect.disabled = true;
    
    if (medcenterSelect) {
        medcenterSelect.innerHTML = '<option value="">Сначала выберите район</option>';
        medcenterSelect.disabled = true;
    }
    
    if (!regionId) {
        districtSelect.innerHTML = '<option value="">Сначала выберите область</option>';
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/regions/${regionId}/districts`);
        const districts = await response.json();
        
        districtSelect.innerHTML = '<option value="">Выберите район</option>';
        districts.forEach(district => {
            const option = document.createElement('option');
            option.value = district.id;
            option.textContent = district.name;
            districtSelect.appendChild(option);
        });
        districtSelect.disabled = false;
        
        districtSelect.addEventListener('change', () => loadMedcenters(districtSelect), { once: true });
    } catch (error) {
        console.error('Ошибка загрузки районов:', error);
        districtSelect.innerHTML = '<option value="">Ошибка загрузки</option>';
    }
}

// Загрузка медцентров
async function loadMedcenters(districtSelect) {
    const districtId = districtSelect.value;
    const form = districtSelect.closest('form');
    const medcenterSelect = form.querySelector('select[name="medical_center_id"], [id$="-medcenter"]');
    
    if (!medcenterSelect) return;
    
    medcenterSelect.innerHTML = '<option value="">Загрузка...</option>';
    medcenterSelect.disabled = true;
    
    if (!districtId) {
        medcenterSelect.innerHTML = '<option value="">Сначала выберите район</option>';
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/medcenters?district_id=${districtId}`);
        const medcenters = await response.json();
        
        medcenterSelect.innerHTML = '<option value="">Выберите медцентр</option>';
        medcenters.forEach(mc => {
            const option = document.createElement('option');
            option.value = mc.id;
            option.textContent = mc.name;
            medcenterSelect.appendChild(option);
        });
        medcenterSelect.disabled = false;
    } catch (error) {
        console.error('Ошибка загрузки медцентров:', error);
        medcenterSelect.innerHTML = '<option value="">Ошибка загрузки</option>';
    }
}

// Переключатель режима (вход/регистрация)
function initModeTabs() {
    document.querySelectorAll('.mode-tabs').forEach(tabs => {
        const buttons = tabs.querySelectorAll('.mode-tab');
        const container = tabs.closest('.auth-form-container');
        
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const mode = btn.dataset.mode;
                const loginForm = container.querySelector('[id$="-login-form"]');
                const registerForm = container.querySelector('[id$="-register-form"]');
                
                if (mode === 'login') {
                    if (loginForm) loginForm.style.display = 'block';
                    if (registerForm) registerForm.style.display = 'none';
                } else {
                    if (loginForm) loginForm.style.display = 'none';
                    if (registerForm) registerForm.style.display = 'block';
                }
            });
        });
    });
    
    // Ссылки для переключения
    document.querySelectorAll('.switch-to-register, .switch-to-register-mc').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const container = link.closest('.auth-form-container');
            const registerTab = container.querySelector('.mode-tab[data-mode="register"]');
            if (registerTab) registerTab.click();
        });
    });
    
    document.querySelectorAll('.switch-to-login, .switch-to-login-mc').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const container = link.closest('.auth-form-container');
            const loginTab = container.querySelector('.mode-tab[data-mode="login"]');
            if (loginTab) loginTab.click();
        });
    });
}

// База данных медцентров (синхронизирована с app.js)
const medicalCentersData = {
    "minsk": {
        "name": "Минск",
        "districts": {
            "central": {
                "name": "Центральный район",
                "centers": [
                    { "id": 1, "name": "Республиканский научно-практический центр трансфузиологии", "address": "ул. Долгиновский тракт, 160" },
                    { "id": 2, "name": "Городская клиническая больница скорой медицинской помощи", "address": "ул. Кижеватова, 58" }
                ]
            },
            "sovetsky": {
                "name": "Советский район",
                "centers": [
                    { "id": 3, "name": "6-я городская клиническая больница", "address": "ул. Уральская, 5" }
                ]
            },
            "frunzensky": {
                "name": "Фрунзенский район",
                "centers": [
                    { "id": 4, "name": "Минская областная клиническая больница", "address": "ул. Семашко, 8" }
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
                    { "id": 5, "name": "Борисовская ЦРБ", "address": "г. Борисов, ул. Чапаева, 34" }
                ]
            },
            "molodechno": {
                "name": "Молодечненский район",
                "centers": [
                    { "id": 6, "name": "Молодечненская ЦРБ", "address": "г. Молодечно, ул. Космонавтов, 1" }
                ]
            },
            "soligorsk": {
                "name": "Солигорский район",
                "centers": [
                    { "id": 7, "name": "Солигорская ЦРБ", "address": "г. Солигорск, ул. Ленина, 35" }
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
                    { "id": 8, "name": "Брестская областная станция переливания крови", "address": "г. Брест, ул. Медицинская, 6" },
                    { "id": 9, "name": "Брестская областная больница", "address": "г. Брест, ул. Медицинская, 7" }
                ]
            },
            "baranovichi": {
                "name": "Барановичский район",
                "centers": [
                    { "id": 10, "name": "Барановичская ЦГБ", "address": "г. Барановичи, ул. Советская, 80" }
                ]
            },
            "pinsk": {
                "name": "Пинский район",
                "centers": [
                    { "id": 11, "name": "Пинская центральная больница", "address": "г. Пинск, ул. Рокоссовского, 8" }
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
                    { "id": 12, "name": "Витебская областная станция переливания крови", "address": "г. Витебск, ул. Чкалова, 18" },
                    { "id": 13, "name": "Витебская областная клиническая больница", "address": "г. Витебск, пр. Фрунзе, 43" }
                ]
            },
            "orsha": {
                "name": "Оршанский район",
                "centers": [
                    { "id": 14, "name": "Оршанская ЦГБ", "address": "г. Орша, ул. Мира, 20" }
                ]
            },
            "polotsk": {
                "name": "Полоцкий район",
                "centers": [
                    { "id": 15, "name": "Полоцкая центральная больница", "address": "г. Полоцк, ул. Гагарина, 6" }
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
                    { "id": 16, "name": "Гомельская областная станция переливания крови", "address": "г. Гомель, ул. Братьев Лизюковых, 5" },
                    { "id": 17, "name": "Гомельская областная клиническая больница", "address": "г. Гомель, ул. Братьев Лизюковых, 5" }
                ]
            },
            "mozyr": {
                "name": "Мозырский район",
                "centers": [
                    { "id": 18, "name": "Мозырская ЦГБ", "address": "г. Мозырь, ул. Котловца, 14" }
                ]
            },
            "zhlobin": {
                "name": "Жлобинский район",
                "centers": [
                    { "id": 19, "name": "Жлобинская ЦРБ", "address": "г. Жлобин, ул. Воровского, 1" }
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
                    { "id": 20, "name": "Гродненская областная станция переливания крови", "address": "г. Гродно, ул. Обухова, 15" },
                    { "id": 21, "name": "Гродненская областная клиническая больница", "address": "г. Гродно, бул. Ленинского Комсомола, 52" }
                ]
            },
            "lida": {
                "name": "Лидский район",
                "centers": [
                    { "id": 22, "name": "Лидская ЦРБ", "address": "г. Лида, ул. Мицкевича, 1" }
                ]
            },
            "slonim": {
                "name": "Слонимский район",
                "centers": [
                    { "id": 23, "name": "Слонимская ЦРБ", "address": "г. Слоним, ул. Советская, 50" }
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
                    { "id": 24, "name": "Могилёвская областная станция переливания крови", "address": "г. Могилёв, ул. Б.Бирули, 12" },
                    { "id": 25, "name": "Могилёвская областная больница", "address": "г. Могилёв, ул. Белыницкого-Бирули, 12" }
                ]
            },
            "bobruisk": {
                "name": "Бобруйский район",
                "centers": [
                    { "id": 26, "name": "Бобруйская городская больница СМП", "address": "г. Бобруйск, ул. Советская, 116" }
                ]
            },
            "osipovichi": {
                "name": "Осиповичский район",
                "centers": [
                    { "id": 27, "name": "Осиповичская ЦРБ", "address": "г. Осиповичи, ул. Сумченко, 101" }
                ]
            }
        }
    }
};

/**
 * Переключатель типа пользователя (донор/медцентр)
 */
function initTypeSwitcher() {
    const typeButtons = document.querySelectorAll('.type-btn');
    const donorForm = document.getElementById('donor-form');
    const medcenterForm = document.getElementById('medcenter-form');
    
    if (!donorForm || !medcenterForm) return;
    
    typeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            typeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const type = btn.dataset.type;
            
            if (type === 'donor') {
                donorForm.style.display = 'block';
                medcenterForm.style.display = 'none';
            } else {
                donorForm.style.display = 'none';
                medcenterForm.style.display = 'block';
            }
        });
    });
}

/**
 * Переключатель табов вход/регистрация
 */
function initAuthTabs() {
    document.querySelectorAll('.auth-form-container').forEach(container => {
        const tabs = container.querySelectorAll('.auth-tab');
        const loginForm = container.querySelector('[id$="-login-form"]');
        const registerForm = container.querySelector('[id$="-register-form"]');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                if (tab.dataset.tab === 'login') {
                    loginForm.classList.add('active');
                    registerForm.classList.remove('active');
                } else {
                    registerForm.classList.add('active');
                    loginForm.classList.remove('active');
                }
            });
        });
        
        // Кнопки переключения внутри форм
        container.querySelectorAll('.link-btn[data-switch]').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.dataset.switch;
                tabs.forEach(t => {
                    t.classList.toggle('active', t.dataset.tab === targetTab);
                });
                
                if (targetTab === 'login') {
                    loginForm.classList.add('active');
                    registerForm.classList.remove('active');
                } else {
                    registerForm.classList.add('active');
                    loginForm.classList.remove('active');
                }
            });
        });
    });
}

/**
 * Многошаговая форма регистрации
 */
function initFormSteps() {
    const registerForm = document.getElementById('donor-register-form');
    if (!registerForm) return;
    
    const steps = registerForm.querySelectorAll('.form-step');
    let currentStep = 1;
    
    // Кнопки "Далее"
    registerForm.querySelectorAll('.next-step').forEach(btn => {
        btn.addEventListener('click', () => {
            if (validateStep(currentStep)) {
                if (currentStep < steps.length) {
                    currentStep++;
                    showStep(currentStep);
                }
            }
        });
    });
    
    // Кнопки "Назад"
    registerForm.querySelectorAll('.prev-step').forEach(btn => {
        btn.addEventListener('click', () => {
            if (currentStep > 1) {
                currentStep--;
                showStep(currentStep);
            }
        });
    });
    
    function showStep(step) {
        steps.forEach(s => {
            s.classList.remove('active');
            if (parseInt(s.dataset.step) === step) {
                s.classList.add('active');
            }
        });
    }
    
    function validateStep(step) {
        const currentStepEl = registerForm.querySelector(`.form-step[data-step="${step}"]`);
        const requiredFields = currentStepEl.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.closest('.form-group').classList.add('error');
            } else {
                field.closest('.form-group').classList.remove('error');
            }
        });
        
        // Для шага 2 - проверка выбора группы крови
        if (step === 2) {
            const bloodTypeSelected = currentStepEl.querySelector('input[name="blood_type"]:checked');
            if (!bloodTypeSelected) {
                isValid = false;
                showNotification('Пожалуйста, выберите группу крови', 'error');
            }
        }
        
        return isValid;
    }
}

/**
 * Переключатель видимости пароля
 */
function initPasswordToggle() {
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.previousElementSibling;
            const type = input.type === 'password' ? 'text' : 'password';
            input.type = type;
            btn.classList.toggle('active');
        });
    });
}

/**
 * Каскадные селекторы регионов
 */
function initRegionSelectors() {
    // Для входа донора
    initCascadeSelector('donor-login-region', null, 'donor-login-medcenter');
    
    // Для регистрации донора
    initCascadeSelector('reg-region', 'reg-district', 'reg-medcenter');
    
    // Для входа медцентра
    initCascadeSelector('mc-login-region', 'mc-login-district', 'mc-login-center');
}

function initCascadeSelector(regionId, districtId, centerId) {
    const regionSelect = document.getElementById(regionId);
    const districtSelect = districtId ? document.getElementById(districtId) : null;
    const centerSelect = document.getElementById(centerId);
    
    if (!regionSelect) return;
    
    regionSelect.addEventListener('change', function() {
        const region = this.value;
        
        // Если есть селектор района
        if (districtSelect) {
            districtSelect.innerHTML = '<option value="">Выберите район</option>';
            districtSelect.disabled = !region;
            centerSelect.innerHTML = '<option value="">Сначала выберите район</option>';
            centerSelect.disabled = true;
            
            if (region && medicalCentersData[region]) {
                const districts = medicalCentersData[region].districts;
                for (const [key, value] of Object.entries(districts)) {
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = value.name;
                    districtSelect.appendChild(option);
                }
            }
        } else {
            // Прямой выбор центра после области (для упрощённого входа)
            centerSelect.innerHTML = '<option value="">Выберите медцентр</option>';
            centerSelect.disabled = !region;
            
            if (region && medicalCentersData[region]) {
                const districts = medicalCentersData[region].districts;
                for (const [distKey, distValue] of Object.entries(districts)) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = distValue.name;
                    
                    distValue.centers.forEach(center => {
                        const option = document.createElement('option');
                        option.value = center.id;
                        option.textContent = center.name;
                        optgroup.appendChild(option);
                    });
                    
                    centerSelect.appendChild(optgroup);
                }
            }
        }
    });
    
    if (districtSelect) {
        districtSelect.addEventListener('change', function() {
            const region = regionSelect.value;
            const district = this.value;
            
            centerSelect.innerHTML = '<option value="">Выберите медцентр</option>';
            centerSelect.disabled = !district;
            
            if (region && district && medicalCentersData[region]) {
                const centers = medicalCentersData[region].districts[district]?.centers || [];
                centers.forEach(center => {
                    const option = document.createElement('option');
                    option.value = center.id;
                    option.textContent = center.name;
                    centerSelect.appendChild(option);
                });
            }
        });
    }
}

/**
 * Валидация и отправка форм
 */
function initFormValidation() {
    console.log('🔍 Инициализация валидации форм...');
    
    // Вход донора
    const donorLoginForm = document.getElementById('donor-login-form');
    console.log('Форма входа донора:', donorLoginForm ? 'найдена' : 'НЕ найдена');
    if (donorLoginForm) {
        donorLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('📝 Отправка формы входа донора...');
            
            const formData = new FormData(donorLoginForm);
            const data = Object.fromEntries(formData.entries());
            console.log('Данные формы:', data);
            
            const btn = donorLoginForm.querySelector('button[type="submit"]');
            btn.classList.add('loading');
            btn.textContent = 'Вход...';
            
            try {
                const response = await fetch(`${API_URL}/donor/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        full_name: data.full_name,
                        birth_year: parseInt(data.birth_year),
                        medical_center_id: parseInt(data.medical_center_id),
                        password: data.password
                    })
                });
                
                const result = await response.json();
                console.log('Ответ сервера:', result);
                
                if (response.ok) {
                    // Успех - показываем анимацию
                    btn.classList.remove('loading');
                    btn.classList.add('success');
                    btn.textContent = '';
                    
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_type', 'donor');
                    localStorage.setItem('donor_user', JSON.stringify(result.user));
                    
                    setTimeout(() => {
                        window.location.href = 'donor-dashboard.html';
                    }, 800);
                } else {
                    // Ошибка - показываем анимацию тряски
                    showFormError(donorLoginForm, result.error || 'Неверные данные для входа');
                }
                
            } catch (error) {
                console.error('❌ Ошибка входа:', error);
                showFormError(donorLoginForm, 'Ошибка соединения с сервером');
            } finally {
                if (!btn.classList.contains('success')) {
                    btn.classList.remove('loading');
                    btn.textContent = 'Войти';
                }
            }
        });
    }
    
    // Регистрация донора
    const donorRegisterForm = document.getElementById('donor-register-form');
    if (donorRegisterForm) {
        donorRegisterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(donorRegisterForm);
            const data = Object.fromEntries(formData.entries());
            
            // Проверка группы крови
            if (!data.blood_type) {
                showNotification('Пожалуйста, выберите группу крови', 'error');
                return;
            }
            
            // Проверка Telegram
            if (!data.telegram_username || data.telegram_username.trim() === '') {
                showNotification('Укажите Telegram username для получения уведомлений', 'error');
                return;
            }
            
            // Проверка пароля
            if (!data.password || data.password.length < 6) {
                showNotification('Пароль должен быть не менее 6 символов', 'error');
                return;
            }
            
            if (data.password !== data.password_confirm) {
                showNotification('Пароли не совпадают', 'error');
                return;
            }
            
            const btn = donorRegisterForm.querySelector('button[type="submit"]');
            btn.classList.add('loading');
            
            const payload = {
                full_name: data.full_name,
                birth_year: parseInt(data.birth_year),
                blood_type: data.blood_type,
                medical_center_id: parseInt(data.medical_center_id),
                phone: data.phone || null,
                email: data.email || null,
                telegram_username: data.telegram_username || null,
                password: data.password
            };
            
            console.log('[DONOR REGISTER] Отправка данных:', payload);
            
            try {
                const response = await fetch(`${API_URL}/donor/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_type', 'donor');
                    localStorage.setItem('donor_user', JSON.stringify(result.user));
                    
                    // Проверяем, требуется ли верификация Telegram
                    if (result.telegram_verification_required && result.telegram_code) {
                        showTelegramVerificationModal(result.telegram_code, result.telegram_username);
                    } else {
                        showNotification('Регистрация успешна!', 'success');
                        setTimeout(() => {
                            window.location.href = 'donor-dashboard.html';
                        }, 1000);
                    }
                } else {
                    showNotification(result.error || 'Ошибка регистрации', 'error');
                }
                
            } catch (error) {
                showNotification('Ошибка соединения с сервером', 'error');
            } finally {
                btn.classList.remove('loading');
            }
        });
    }
    
    // Вход медцентра
    const mcLoginForm = document.getElementById('medcenter-login-form');
    console.log('Форма входа медцентра:', mcLoginForm ? 'найдена' : 'НЕ найдена');
    if (mcLoginForm) {
        mcLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('🏥 Отправка формы входа медцентра...');
            
            const formData = new FormData(mcLoginForm);
            const data = Object.fromEntries(formData.entries());
            console.log('Данные формы:', data);
            
            const btn = mcLoginForm.querySelector('button[type="submit"]');
            btn.classList.add('loading');
            
            try {
                const response = await fetch(`${API_URL}/medcenter/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        medical_center_id: parseInt(data.medical_center_id),
                        password: data.password
                    })
                });
                
                const result = await response.json();
                console.log('Ответ сервера:', result);
                
                if (response.ok) {
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_type', 'medcenter');
                    localStorage.setItem('medcenter_user', JSON.stringify(result.medical_center));
                    window.location.href = 'medcenter-dashboard.html';
                } else {
                    showNotification(result.error || 'Неверный пароль', 'error');
                }
                
            } catch (error) {
                console.error('❌ Ошибка входа медцентра:', error);
                showNotification('Ошибка соединения с сервером', 'error');
            } finally {
                btn.classList.remove('loading');
            }
        });
    }
    
    // Регистрация медцентра
    const mcRegisterForm = document.getElementById('medcenter-register-form');
    if (mcRegisterForm) {
        mcRegisterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(mcRegisterForm);
            const data = Object.fromEntries(formData.entries());
            
            // Проверка email
            if (!data.email) {
                showNotification('Укажите рабочий email медцентра', 'error');
                return;
            }
            
            // Проверка пароля
            if (!data.password || data.password.length < 6) {
                showNotification('Пароль должен быть не менее 6 символов', 'error');
                return;
            }
            
            if (data.password !== data.password_confirm) {
                showNotification('Пароли не совпадают', 'error');
                return;
            }
            
            const btn = mcRegisterForm.querySelector('button[type="submit"]');
            btn.classList.add('loading');
            btn.disabled = true;
            
            try {
                const response = await fetch(`${API_URL}/medcenter/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: data.name,
                        district_id: parseInt(data.district_id) || null,
                        region_id: parseInt(data.region_id) || null,
                        address: data.address || null,
                        email: data.email,
                        phone: data.phone || null,
                        password: data.password,
                        is_blood_center: data.is_blood_center === 'on'
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_type', 'medcenter');
                    localStorage.setItem('medcenter_user', JSON.stringify(result.medical_center));
                    showNotification('Медцентр зарегистрирован!', 'success');
                    setTimeout(() => {
                        window.location.href = 'medcenter-dashboard.html';
                    }, 1000);
                } else {
                    showNotification(result.error || 'Ошибка регистрации', 'error');
                }
                
            } catch (error) {
                console.error('Ошибка:', error);
                showNotification('Ошибка соединения с сервером', 'error');
            } finally {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        });
    }
}

/**
 * Проверка URL параметров
 */
function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    
    // Определяем тип пользователя
    const type = params.get('type') || 'donor';
    const mode = params.get('mode') || 'login';
    
    // Активируем нужную кнопку типа
    const typeBtn = document.querySelector(`.type-btn[data-type="${type}"]`);
    if (typeBtn) {
        typeBtn.click();
    }
    
    // Ждём переключения формы и активируем нужный таб
    setTimeout(() => {
        const activeContainer = document.querySelector('.auth-form-container:not([style*="display: none"])');
        if (activeContainer) {
            const modeTab = activeContainer.querySelector(`.mode-tab[data-mode="${mode}"]`);
            if (modeTab) {
                modeTab.click();
            }
        }
    }, 100);
}

/**
 * Показать модальное окно верификации Telegram
 */
function showTelegramVerificationModal(code, telegram_username) {
    // Создаём модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(4px);';
    
    modal.innerHTML = `
        <div class="telegram-verification-modal" style="background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); padding: 48px; border-radius: 24px; max-width: 540px; width: 90%; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: modalFadeIn 0.3s ease-out;">
            <div style="font-size: 64px; margin-bottom: 16px; animation: bounce 0.6s ease-out;">🎉</div>
            <h2 style="margin-bottom: 12px; color: #2c3e50; font-size: 28px; font-weight: 700;">Регистрация успешна!</h2>
            <p style="margin-bottom: 32px; color: #7f8c8d; font-size: 16px;">
                Подтвердите аккаунт в Telegram для получения уведомлений
            </p>
            
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);">
                <p style="margin-bottom: 12px; font-weight: 600; color: white; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Ваш код:</p>
                <div id="code-display" style="font-size: 48px; font-weight: 900; color: white; letter-spacing: 8px; font-family: 'Courier New', monospace; margin: 20px 0; text-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                    ${code}
                </div>
                <button id="copy-code-btn" style="padding: 12px 28px; background: rgba(255,255,255,0.2); color: white; border: 2px solid rgba(255,255,255,0.3); border-radius: 10px; cursor: pointer; font-weight: 700; transition: all 0.2s; backdrop-filter: blur(10px);">
                    📋 Скопировать код
                </button>
            </div>
            
            <div style="text-align: left; background: #e8f4fd; padding: 20px; border-radius: 12px; margin-bottom: 24px; border-left: 4px solid #3498db;">
                <p style="font-weight: 700; margin-bottom: 12px; color: #2c3e50; font-size: 15px;">📱 Всего 2 шага:</p>
                <ol style="margin: 0; padding-left: 20px; line-height: 2; color: #34495e; font-size: 15px;">
                    <li>Откройте бота в Telegram (кнопка ниже)</li>
                    <li>Отправьте боту этот 6-значный код</li>
                </ol>
                <p style="margin-top: 12px; font-size: 13px; color: #7f8c8d; font-style: italic;">
                    💡 Код автоматически подставится при переходе в бота
                </p>
            </div>
            
            <div style="display: flex; gap: 12px; flex-direction: column;">
                <button id="telegram-open-btn" style="padding: 16px; background: linear-gradient(135deg, #0088cc 0%, #005f99 100%); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: 700; font-size: 16px; box-shadow: 0 4px 15px rgba(0,136,204,0.4); transition: all 0.2s;">
                    🚀 Открыть бота в Telegram
                </button>
                <button id="telegram-skip-btn" style="padding: 14px; background: transparent; color: #7f8c8d; border: 2px solid #e0e0e0; border-radius: 12px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s;">
                    Привяжу позже
                </button>
            </div>
            
            <p style="margin-top: 20px; font-size: 13px; color: #95a5a6;">
                ⏱️ Код действителен <strong>10 минут</strong>
            </p>
        </div>
    `;
    
    // Добавляем стили анимации
    const style = document.createElement('style');
    style.textContent = `
        @keyframes modalFadeIn {
            from {
                opacity: 0;
                transform: scale(0.9) translateY(20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        @keyframes bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        #copy-code-btn:hover {
            background: rgba(255,255,255,0.3) !important;
            transform: translateY(-2px);
        }
        #telegram-open-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,136,204,0.5);
        }
        #telegram-skip-btn:hover {
            background: #f8f9fa;
            border-color: #bdc3c7;
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(modal);
    
    // Обработчик кнопки "Скопировать код"
    modal.querySelector('#copy-code-btn').addEventListener('click', (e) => {
        navigator.clipboard.writeText(code).then(() => {
            const btn = e.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Скопировано!';
            btn.style.background = 'rgba(46, 204, 113, 0.3)';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = 'rgba(255,255,255,0.2)';
            }, 2000);
        });
    });
    
    // Обработчик кнопки "Открыть бота"
    modal.querySelector('#telegram-open-btn').addEventListener('click', () => {
        // Deep link с кодом - бот автоматически его проверит
        window.open(`https://t.me/your_donor_bot?start=${code}`, '_blank');
        showNotification('Откройте Telegram и отправьте боту код (он уже скопирован)', 'info');
        
        // Начинаем проверять статус верификации каждые 3 секунды
        startVerificationCheck(modal);
    });
    
    // Обработчик кнопки "Пропустить"
    modal.querySelector('#telegram-skip-btn').addEventListener('click', () => {
        modal.remove();
        style.remove();
        showNotification('Вы можете привязать Telegram позже в профиле', 'info');
        setTimeout(() => {
            window.location.href = 'donor-dashboard.html';
        }, 1500);
    });
}

/**
 * Периодическая проверка статуса верификации
 */
function startVerificationCheck(modal) {
    let attempts = 0;
    const maxAttempts = 40; // 40 * 3 сек = 2 минуты
    
    const checkInterval = setInterval(async () => {
        attempts++;
        
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                clearInterval(checkInterval);
                return;
            }
            
            const response = await fetch(`${API_URL}/donor/profile`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Проверяем, привязан ли Telegram
                if (data.telegram_id) {
                    clearInterval(checkInterval);
                    modal.remove();
                    
                    // Показываем анимацию успеха
                    showSuccessAnimation(() => {
                        window.location.href = 'donor-dashboard.html';
                    });
                }
            }
        } catch (error) {
            console.error('Ошибка проверки верификации:', error);
        }
        
        // Прекращаем проверку через 2 минуты
        if (attempts >= maxAttempts) {
            clearInterval(checkInterval);
        }
    }, 3000);
}

/**
 * Показать анимацию успеха
 */
function showSuccessAnimation(callback) {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.95); display: flex; align-items: center; justify-content: center; z-index: 10000; animation: fadeIn 0.3s ease-out;';
    
    overlay.innerHTML = `
        <div style="text-align: center; animation: zoomIn 0.5s ease-out;">
            <div style="width: 120px; height: 120px; margin: 0 auto 24px; background: linear-gradient(135deg, #2ecc71, #27ae60); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 40px rgba(46, 204, 113, 0.4); animation: pulse 1s infinite;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="animation: checkDraw 0.5s ease-out 0.3s both;">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
            <h2 style="font-size: 32px; font-weight: 700; color: #2c3e50; margin-bottom: 12px;">Аккаунт подтверждён!</h2>
            <p style="font-size: 18px; color: #7f8c8d;">Добро пожаловать в Твой Донор</p>
        </div>
    `;
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes zoomIn {
            from { transform: scale(0.5); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        @keyframes checkDraw {
            from { stroke-dasharray: 100; stroke-dashoffset: 100; }
            to { stroke-dasharray: 100; stroke-dashoffset: 0; }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(overlay);
    
    setTimeout(() => {
        overlay.remove();
        style.remove();
        if (callback) callback();
    }, 2500);
}

/**
 * Показать уведомление
 */
function showNotification(message, type = 'info') {
    // Удаляем предыдущее уведомление
    const existing = document.querySelector('.auth-notification');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `auth-notification ${type}`;
    notification.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' 
                ? '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/>' 
                : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
        </svg>
        <span>${message}</span>
    `;
    
    const form = document.querySelector('.auth-form.active');
    if (form) {
        form.insertBefore(notification, form.firstChild);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

/**
 * Показать ошибку формы с анимацией
 */
function showFormError(form, message) {
    // Анимация тряски
    form.classList.add('error-shake');
    setTimeout(() => {
        form.classList.remove('error-shake');
    }, 500);
    
    // Показываем уведомление
    showNotification(message, 'error');
}

/**
 * Подсветить поле с ошибкой
 */
function highlightFieldError(input, message) {
    const formGroup = input.closest('.form-group');
    if (!formGroup) return;
    
    // Добавляем класс ошибки
    formGroup.classList.add('error');
    
    // Удаляем предыдущее сообщение об ошибке
    const existingError = formGroup.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Добавляем сообщение об ошибке
    if (message) {
        const errorMsg = document.createElement('span');
        errorMsg.className = 'field-error';
        errorMsg.textContent = message;
        formGroup.appendChild(errorMsg);
    }
    
    // Убираем ошибку при фокусе
    input.addEventListener('focus', () => {
        formGroup.classList.remove('error');
        const errorMsg = formGroup.querySelector('.field-error');
        if (errorMsg) {
            errorMsg.remove();
        }
    }, { once: true });
}
