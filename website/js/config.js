/**
 * Конфигурация API для разных окружений
 * Твой Донор - система донорства крови
 */

// Определяем окружение
const IS_PRODUCTION = window.location.hostname !== 'localhost' && 
                       window.location.hostname !== '127.0.0.1';

// Конфигурация API
const CONFIG = {
    // Для локальной разработки (прямое подключение к Flask на порту 5001)
    development: {
        API_URL: 'http://localhost:5001/api'
    },
    
    // Для продакшена - Nginx проксирует /api/ на Flask
    // БЕЗ ПОРТА! Nginx сам перенаправит на 5001
    production: {
        API_URL: `${window.location.protocol}//${window.location.hostname}/api`
    }
};

// Экспортируем API URL
window.API_URL = IS_PRODUCTION ? CONFIG.production.API_URL : CONFIG.development.API_URL;

// Версия для cache busting
window.VERSION = Date.now();

console.log(`🌐 API URL: ${window.API_URL} (${IS_PRODUCTION ? 'production' : 'development'})`);
