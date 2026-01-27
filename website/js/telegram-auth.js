/**
 * ============================================
 * Твой Донор - Telegram Mini App Auth
 * ============================================
 * 
 * Авторизация для Telegram Mini App
 * Использует CloudStorage для сохранения сессии
 * 
 * @version 1.0.0
 * @date 2026-01-27
 */

console.log('🔐 telegram-auth.js ЗАГРУЖЕН');

/**
 * Проверка, что приложение запущено в Telegram Mini App
 */
function isTelegramMiniApp() {
    const hasTelegram = !!window.Telegram;
    const hasWebApp = hasTelegram && !!window.Telegram.WebApp;
    const hasInitData = hasWebApp && !!window.Telegram.WebApp.initData;
    
    console.log(`📱 Проверка Telegram Mini App:`);
    console.log(`   - window.Telegram: ${hasTelegram ? '✅' : '❌'}`);
    console.log(`   - Telegram.WebApp: ${hasWebApp ? '✅' : '❌'}`);
    console.log(`   - initData: ${hasInitData ? '✅ (длина: ' + (window.Telegram?.WebApp?.initData?.length || 0) + ')' : '❌'}`);
    
    if (hasWebApp) {
        console.log(`   - version: ${window.Telegram.WebApp.version || 'неизвестна'}`);
        console.log(`   - platform: ${window.Telegram.WebApp.platform || 'неизвестна'}`);
        console.log(`   - CloudStorage: ${window.Telegram.WebApp.CloudStorage ? '✅' : '❌'}`);
    }
    
    return hasInitData;
}

/**
 * Класс для работы с авторизацией в Telegram Mini App
 */
class TelegramAuth {
    static STORAGE_KEY_TOKEN = 'tvoydonor_access_token';
    static STORAGE_KEY_REFRESH = 'tvoydonor_refresh_token';
    static STORAGE_KEY_USER_TYPE = 'tvoydonor_user_type';
    static STORAGE_KEY_USER_DATA = 'tvoydonor_user_data';
    
    /**
     * Проверка доступности CloudStorage
     */
    static isCloudStorageAvailable() {
        return isTelegramMiniApp() && 
               window.Telegram.WebApp.CloudStorage && 
               typeof window.Telegram.WebApp.CloudStorage.getItem === 'function';
    }
    
    /**
     * Сохранить данные в CloudStorage
     */
    static async saveToCloud(key, value) {
        return new Promise((resolve, reject) => {
            if (!this.isCloudStorageAvailable()) {
                console.warn('⚠️ CloudStorage недоступен');
                resolve(false);
                return;
            }
            
            window.Telegram.WebApp.CloudStorage.setItem(key, value, (error, result) => {
                if (error) {
                    console.error('❌ Ошибка сохранения в CloudStorage:', error);
                    reject(error);
                } else {
                    console.log(`✅ Сохранено в CloudStorage: ${key}`);
                    resolve(true);
                }
            });
        });
    }
    
    /**
     * Получить данные из CloudStorage
     */
    static async getFromCloud(key) {
        return new Promise((resolve, reject) => {
            if (!this.isCloudStorageAvailable()) {
                console.warn('⚠️ CloudStorage недоступен');
                resolve(null);
                return;
            }
            
            window.Telegram.WebApp.CloudStorage.getItem(key, (error, value) => {
                if (error) {
                    console.error('❌ Ошибка чтения из CloudStorage:', error);
                    reject(error);
                } else {
                    resolve(value || null);
                }
            });
        });
    }
    
    /**
     * Удалить данные из CloudStorage
     */
    static async removeFromCloud(key) {
        return new Promise((resolve, reject) => {
            if (!this.isCloudStorageAvailable()) {
                resolve(false);
                return;
            }
            
            window.Telegram.WebApp.CloudStorage.removeItem(key, (error) => {
                if (error) {
                    console.error('❌ Ошибка удаления из CloudStorage:', error);
                    reject(error);
                } else {
                    console.log(`🗑️ Удалено из CloudStorage: ${key}`);
                    resolve(true);
                }
            });
        });
    }
    
    /**
     * 🔥 ГЛАВНОЕ: Сохранить сессию после успешного входа
     * Вызывается из auth.js после login
     */
    static async saveSession(accessToken, refreshToken, userType, userData) {
        if (!isTelegramMiniApp()) {
            console.log('ℹ️ Не Telegram Mini App - используем стандартное хранилище');
            return false;
        }
        
        console.log('📱 Telegram Mini App: Сохранение сессии в CloudStorage...');
        
        try {
            await Promise.all([
                this.saveToCloud(this.STORAGE_KEY_TOKEN, accessToken),
                this.saveToCloud(this.STORAGE_KEY_REFRESH, refreshToken),
                this.saveToCloud(this.STORAGE_KEY_USER_TYPE, userType),
                this.saveToCloud(this.STORAGE_KEY_USER_DATA, JSON.stringify(userData))
            ]);
            
            console.log('✅ Сессия сохранена в Telegram CloudStorage');
            return true;
        } catch (error) {
            console.error('❌ Ошибка сохранения сессии в CloudStorage:', error);
            return false;
        }
    }
    
    /**
     * 🔥 ГЛАВНОЕ: Восстановить сессию при загрузке
     * Вызывается при инициализации приложения
     */
    static async restoreSession() {
        if (!isTelegramMiniApp()) {
            console.log('ℹ️ Не Telegram Mini App - пропускаем CloudStorage');
            return null;
        }
        
        console.log('📱 Telegram Mini App: Попытка восстановления сессии из CloudStorage...');
        
        try {
            const [accessToken, refreshToken, userType, userDataStr] = await Promise.all([
                this.getFromCloud(this.STORAGE_KEY_TOKEN),
                this.getFromCloud(this.STORAGE_KEY_REFRESH),
                this.getFromCloud(this.STORAGE_KEY_USER_TYPE),
                this.getFromCloud(this.STORAGE_KEY_USER_DATA)
            ]);
            
            if (!refreshToken) {
                console.log('ℹ️ Нет сохранённой сессии в CloudStorage');
                return null;
            }
            
            console.log(`✅ Найдена сессия в CloudStorage (${userType})`);
            
            let userData = null;
            try {
                userData = userDataStr ? JSON.parse(userDataStr) : null;
            } catch (e) {
                console.warn('⚠️ Ошибка парсинга userData:', e);
            }
            
            return {
                accessToken,
                refreshToken,
                userType,
                userData
            };
        } catch (error) {
            console.error('❌ Ошибка восстановления сессии из CloudStorage:', error);
            return null;
        }
    }
    
    /**
     * Очистить сессию в CloudStorage
     */
    static async clearSession() {
        if (!isTelegramMiniApp()) return;
        
        console.log('📱 Telegram Mini App: Очистка сессии в CloudStorage...');
        
        try {
            await Promise.all([
                this.removeFromCloud(this.STORAGE_KEY_TOKEN),
                this.removeFromCloud(this.STORAGE_KEY_REFRESH),
                this.removeFromCloud(this.STORAGE_KEY_USER_TYPE),
                this.removeFromCloud(this.STORAGE_KEY_USER_DATA)
            ]);
            
            console.log('✅ Сессия очищена в CloudStorage');
        } catch (error) {
            console.error('❌ Ошибка очистки сессии:', error);
        }
    }
    
    /**
     * 🔥 Авторизация через initData (автоматический вход для привязанных аккаунтов)
     * Если пользователь уже привязал Telegram, можно войти автоматически
     */
    static async loginWithInitData() {
        if (!isTelegramMiniApp()) {
            console.log('   ℹ️ Не Telegram Mini App');
            return null;
        }
        
        const initData = window.Telegram.WebApp.initData;
        if (!initData) {
            console.log('   ℹ️ Нет initData');
            return null;
        }
        
        console.log('   📤 Отправка initData на сервер...');
        console.log('   📦 initData (первые 100 символов):', initData.substring(0, 100) + '...');
        
        const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}/api`;
        const url = `${API_URL}/auth/telegram`;
        
        console.log('   🌐 URL:', url);
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ init_data: initData })
            });
            
            console.log('   📥 Ответ сервера:', response.status, response.statusText);
            
            if (response.ok) {
                const data = await response.json();
                console.log('   ✅ Сервер вернул данные:', JSON.stringify(data).substring(0, 200));
                
                // Сохраняем сессию в CloudStorage
                if (data.refresh_token && this.isCloudStorageAvailable()) {
                    console.log('   💾 Сохраняем в CloudStorage...');
                    await this.saveSession(
                        data.access_token,
                        data.refresh_token,
                        data.user_type,
                        data.user
                    );
                    console.log('   ✅ Сохранено в CloudStorage');
                } else if (data.refresh_token) {
                    console.log('   ⚠️ CloudStorage недоступен, сохраняем в localStorage');
                    localStorage.setItem('tg_refresh_token', data.refresh_token);
                }
                
                return data;
            } else {
                const error = await response.json().catch(() => ({ error: 'Неизвестная ошибка' }));
                console.log('   ❌ Ответ сервера (ошибка):', JSON.stringify(error));
                console.log('   ℹ️ Причина:', error.message || error.error);
                return null;
            }
        } catch (error) {
            console.error('   ❌ Сетевая ошибка:', error.message);
            console.error('   Детали:', error);
            return null;
        }
    }
    
    /**
     * Обновить access token используя refresh token из CloudStorage
     */
    static async refreshAccessToken() {
        const session = await this.restoreSession();
        if (!session || !session.refreshToken) {
            return null;
        }
        
        console.log('📱 Обновление токена через CloudStorage refresh...');
        
        const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}/api`;
        
        try {
            const response = await fetch(`${API_URL}/auth/refresh-telegram`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: session.refreshToken })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Обновляем токены в CloudStorage
                await this.saveSession(
                    data.access_token,
                    data.refresh_token || session.refreshToken,
                    session.userType,
                    data.user || session.userData
                );
                
                console.log('✅ Токен обновлён через CloudStorage');
                return data.access_token;
            } else {
                console.warn('⚠️ Refresh не удался - очищаем сессию');
                await this.clearSession();
                return null;
            }
        } catch (error) {
            console.error('❌ Ошибка refresh:', error);
            return null;
        }
    }
}

/**
 * Интеграция с основным AuthStorage
 * Автоматически определяет контекст (веб или Telegram) и использует нужное хранилище
 */
async function initTelegramAuth() {
    console.log('═══════════════════════════════════════');
    console.log('📱 ИНИЦИАЛИЗАЦИЯ TELEGRAM MINI APP AUTH');
    console.log('═══════════════════════════════════════');
    
    if (!isTelegramMiniApp()) {
        console.log('ℹ️ Обычный веб-браузер - используем стандартную авторизацию');
        return false;
    }
    
    const tg = window.Telegram.WebApp;
    
    console.log('📱 Telegram Mini App обнаружен!');
    console.log('   - initData длина:', tg.initData?.length || 0);
    console.log('   - initDataUnsafe:', JSON.stringify(tg.initDataUnsafe || {}).substring(0, 200));
    console.log('   - CloudStorage доступен:', TelegramAuth.isCloudStorageAvailable());
    console.log('   - User ID:', tg.initDataUnsafe?.user?.id || 'нет');
    console.log('   - Username:', tg.initDataUnsafe?.user?.username || 'нет');
    
    // ШАГ 1: Проверяем CloudStorage
    console.log('');
    console.log('🔍 ШАГ 1: Проверка CloudStorage...');
    
    if (TelegramAuth.isCloudStorageAvailable()) {
        const session = await TelegramAuth.restoreSession();
        
        if (session && session.refreshToken) {
            console.log('   ✅ Найден refresh_token в CloudStorage');
            console.log('   📤 Пробуем обновить токен...');
            
            // Пробуем refresh
            const newToken = await TelegramAuth.refreshAccessToken();
            if (newToken) {
                console.log('   ✅ Токен обновлён успешно!');
                
                // Сохраняем в AuthStorage для совместимости
                if (window.AuthStorage) {
                    AuthStorage._accessToken = newToken;
                    AuthStorage._userType = session.userType;
                    AuthStorage._userData = session.userData;
                    
                    localStorage.setItem('user_type', session.userType);
                    localStorage.setItem('auth_token', newToken);
                    if (session.userData) {
                        localStorage.setItem(`${session.userType}_user`, JSON.stringify(session.userData));
                    }
                }
                
                console.log('═══════════════════════════════════════');
                console.log('✅ АВТОВХОД ЧЕРЕЗ CLOUDSTORAGE УСПЕШЕН!');
                console.log('═══════════════════════════════════════');
                return true;
            } else {
                console.log('   ❌ Refresh не удался, очищаем CloudStorage');
                await TelegramAuth.clearSession();
            }
        } else {
            console.log('   ℹ️ Нет сохранённой сессии в CloudStorage');
        }
    } else {
        console.log('   ⚠️ CloudStorage НЕДОСТУПЕН!');
        console.log('   Возможные причины:');
        console.log('   - Старая версия Telegram');
        console.log('   - Mini App не запущен из бота');
    }
    
    // ШАГ 2: Автовход через initData
    console.log('');
    console.log('🔍 ШАГ 2: Автовход через initData...');
    
    if (!tg.initData) {
        console.log('   ❌ initData пуст!');
        return false;
    }
    
    const autoLoginResult = await TelegramAuth.loginWithInitData();
    
    if (autoLoginResult) {
        console.log('   ✅ Автовход через initData успешен!');
        
        // Сохраняем в AuthStorage
        if (window.AuthStorage) {
            AuthStorage.save(
                autoLoginResult.access_token,
                autoLoginResult.user_type,
                autoLoginResult.user,
                autoLoginResult.refresh_token
            );
        }
        
        console.log('═══════════════════════════════════════');
        console.log('✅ АВТОВХОД ЧЕРЕЗ INITDATA УСПЕШЕН!');
        console.log('═══════════════════════════════════════');
        return true;
    }
    
    console.log('');
    console.log('═══════════════════════════════════════');
    console.log('ℹ️ Автовход не удался - требуется ручной вход');
    console.log('   Причина: Telegram не привязан к аккаунту');
    console.log('═══════════════════════════════════════');
    return false;
}

// Экспортируем в глобальную область
window.TelegramAuth = TelegramAuth;
window.isTelegramMiniApp = isTelegramMiniApp;
window.initTelegramAuth = initTelegramAuth;

console.log('✅ telegram-auth.js инициализирован');

// 🔥 Автоматическая инициализация при загрузке страницы
// Проверяем Telegram Mini App сразу при загрузке скрипта
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('📱 DOMContentLoaded - проверяем Telegram...');
        if (isTelegramMiniApp()) {
            console.log('📱 Запускаем initTelegramAuth...');
            initTelegramAuth().then(success => {
                if (success) {
                    console.log('🎉 Telegram автовход успешен - перезагружаем данные...');
                    // Триггерим событие для dashboard
                    window.dispatchEvent(new Event('telegram-auth-success'));
                }
            });
        }
    });
} else {
    // DOM уже загружен
    console.log('📱 DOM уже загружен - проверяем Telegram...');
    if (isTelegramMiniApp()) {
        console.log('📱 Запускаем initTelegramAuth...');
        initTelegramAuth().then(success => {
            if (success) {
                console.log('🎉 Telegram автовход успешен!');
                window.dispatchEvent(new Event('telegram-auth-success'));
            }
        });
    }
}
