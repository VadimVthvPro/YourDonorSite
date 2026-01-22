-- Скрипт для создания базы данных BloodDonorBot
-- Выполните этот скрипт в PostgreSQL для создания базы данных и таблиц

-- Создание базы данных
CREATE DATABASE blood_donor_bot;

-- Подключение к созданной базе данных
\c blood_donor_bot;

-- Создание таблицы медицинских центров
CREATE TABLE medical_centers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    login VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    contact_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы потребностей крови (Светофор)
CREATE TABLE blood_needs (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id),
    blood_type VARCHAR(10) NOT NULL, -- A+, A-, B+, etc.
    status VARCHAR(20) DEFAULT 'ok' CHECK (status IN ('ok', 'need', 'urgent')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(medical_center_id, blood_type)
);

-- Создание таблицы пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'doctor')),
    blood_type VARCHAR(10),
    city VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    last_donation_date DATE,
    medical_certificate_file_id VARCHAR(255),
    medical_certificate_date DATE,
    is_registered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы запросов на сдачу крови (Старый функционал, можно оставить или мигрировать)
CREATE TABLE donation_requests (
    id SERIAL PRIMARY KEY,
    doctor_id BIGINT NOT NULL, -- Ссылка на telegram_id врача (если врач привязан к user)
    medical_center_id INTEGER REFERENCES medical_centers(id), -- Ссылка на медцентр
    blood_type VARCHAR(10) NOT NULL,
    location VARCHAR(255) NOT NULL,
    request_date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- FOREIGN KEY (doctor_id) REFERENCES users(telegram_id) -- Опционально
);

-- Таблица для отслеживания откликов доноров
CREATE TABLE donation_responses (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    medical_center_id INTEGER REFERENCES medical_centers(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_blood_type ON users(blood_type);
CREATE INDEX idx_users_city ON users(city);
CREATE INDEX idx_medical_centers_city ON medical_centers(city);
CREATE INDEX idx_blood_needs_status ON blood_needs(status);

-- Комментарии
COMMENT ON TABLE medical_centers IS 'Медицинские центры';
COMMENT ON TABLE blood_needs IS 'Потребности в крови по центрам';
COMMENT ON TABLE users IS 'Пользователи (доноры и врачи)';
