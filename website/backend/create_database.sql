-- ============================================
-- Твой Донор - База данных веб-платформы
-- PostgreSQL
-- ============================================

-- ============================================
-- Справочник областей
-- ============================================
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Заполняем области Беларуси
INSERT INTO regions (name) VALUES
    ('город Минск'),
    ('Минская область'),
    ('Брестская область'),
    ('Гомельская область'),
    ('Гродненская область'),
    ('Витебская область'),
    ('Могилёвская область')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- Справочник районов
-- ============================================
CREATE TABLE IF NOT EXISTS districts (
    id SERIAL PRIMARY KEY,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_id, name)
);

-- город Минск (region_id = 1)
INSERT INTO districts (region_id, name) VALUES
    (1, 'Центральный район'),
    (1, 'Советский район'),
    (1, 'Московский район'),
    (1, 'Октябрьский район'),
    (1, 'Фрунзенский район'),
    (1, 'Первомайский район'),
    (1, 'Партизанский район'),
    (1, 'Заводской район'),
    (1, 'Ленинский район')
ON CONFLICT DO NOTHING;

-- Минская область (region_id = 2)
INSERT INTO districts (region_id, name) VALUES
    (2, 'Борисовский район'),
    (2, 'Солигорский район'),
    (2, 'Молодечненский район'),
    (2, 'Слуцкий район'),
    (2, 'Жодинский район'),
    (2, 'Минский район')
ON CONFLICT DO NOTHING;

-- Брестская область (region_id = 3)
INSERT INTO districts (region_id, name) VALUES
    (3, 'город Брест'),
    (3, 'Барановичский район'),
    (3, 'Пинский район'),
    (3, 'Кобринский район')
ON CONFLICT DO NOTHING;

-- Гомельская область (region_id = 4)
INSERT INTO districts (region_id, name) VALUES
    (4, 'город Гомель'),
    (4, 'Мозырский район'),
    (4, 'Жлобинский район'),
    (4, 'Речицкий район'),
    (4, 'Светлогорский район')
ON CONFLICT DO NOTHING;

-- Гродненская область (region_id = 5)
INSERT INTO districts (region_id, name) VALUES
    (5, 'город Гродно'),
    (5, 'Лидский район'),
    (5, 'Волковысский район'),
    (5, 'Слонимский район')
ON CONFLICT DO NOTHING;

-- Витебская область (region_id = 6)
INSERT INTO districts (region_id, name) VALUES
    (6, 'город Витебск'),
    (6, 'Оршанский район'),
    (6, 'Полоцкий район'),
    (6, 'Новополоцкий район')
ON CONFLICT DO NOTHING;

-- Могилёвская область (region_id = 7)
INSERT INTO districts (region_id, name) VALUES
    (7, 'город Могилёв'),
    (7, 'Бобруйский район'),
    (7, 'Горецкий район'),
    (7, 'Кричевский район')
ON CONFLICT DO NOTHING;

-- ============================================
-- Медицинские центры
-- ============================================
CREATE TABLE IF NOT EXISTS medical_centers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    district_id INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    address VARCHAR(300),
    phone VARCHAR(50),
    email VARCHAR(100),
    is_blood_center BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    master_password VARCHAR(100) DEFAULT 'doctor2024',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mc_district ON medical_centers(district_id);
CREATE INDEX IF NOT EXISTS idx_mc_active ON medical_centers(is_active);

-- ============================================
-- Потребность в крови (Донорский светофор)
-- ============================================
CREATE TABLE IF NOT EXISTS blood_needs (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    blood_type VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'normal',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(medical_center_id, blood_type)
);

CREATE INDEX IF NOT EXISTS idx_bn_mc ON blood_needs(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_bn_status ON blood_needs(status);

-- ============================================
-- Пользователи (Доноры)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    birth_year INTEGER NOT NULL,
    blood_type VARCHAR(10) NOT NULL,
    
    region_id INTEGER REFERENCES regions(id),
    district_id INTEGER REFERENCES districts(id),
    city VARCHAR(100),
    medical_center_id INTEGER REFERENCES medical_centers(id),
    
    phone VARCHAR(50),
    email VARCHAR(100),
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    
    last_donation_date DATE,
    total_donations INTEGER DEFAULT 0,
    is_honorary_donor BOOLEAN DEFAULT FALSE,
    
    notify_urgent BOOLEAN DEFAULT TRUE,
    notify_low BOOLEAN DEFAULT TRUE,
    
    is_active BOOLEAN DEFAULT TRUE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(full_name, birth_year, medical_center_id)
);

CREATE INDEX IF NOT EXISTS idx_users_blood_type ON users(blood_type);
CREATE INDEX IF NOT EXISTS idx_users_mc ON users(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_users_district ON users(district_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);

-- ============================================
-- Запросы на донацию
-- ============================================
CREATE TABLE IF NOT EXISTS donation_requests (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    blood_type VARCHAR(10) NOT NULL,
    urgency VARCHAR(20) NOT NULL DEFAULT 'normal',
    needed_amount INTEGER DEFAULT 1,
    description TEXT,
    contact_info VARCHAR(300),
    target_district_id INTEGER REFERENCES districts(id),
    
    valid_until TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    responses_count INTEGER DEFAULT 0,
    
    telegram_sent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dr_mc ON donation_requests(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_dr_status ON donation_requests(status);
CREATE INDEX IF NOT EXISTS idx_dr_blood_type ON donation_requests(blood_type);

-- ============================================
-- Отклики доноров
-- ============================================
CREATE TABLE IF NOT EXISTS donation_responses (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES donation_requests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id),
    
    status VARCHAR(20) DEFAULT 'pending',
    planned_date DATE,
    planned_time TIME,
    
    actual_donation_date TIMESTAMP,
    donation_completed BOOLEAN DEFAULT FALSE,
    
    donor_comment TEXT,
    medcenter_comment TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(request_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_resp_request ON donation_responses(request_id);
CREATE INDEX IF NOT EXISTS idx_resp_user ON donation_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_resp_status ON donation_responses(status);

-- ============================================
-- Сообщения/консультации
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    from_medcenter_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    to_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    to_medcenter_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    
    subject VARCHAR(200),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_msg_to_user ON messages(to_user_id);
CREATE INDEX IF NOT EXISTS idx_msg_to_mc ON messages(to_medcenter_id);

-- ============================================
-- Сессии
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    
    session_token VARCHAR(256) NOT NULL UNIQUE,
    user_type VARCHAR(20) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sess_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sess_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sess_mc ON user_sessions(medical_center_id);

-- ============================================
-- Тестовые медцентры
-- ============================================
INSERT INTO medical_centers (name, district_id, address, email, is_blood_center) VALUES
    ('Республиканский центр трансфузиологии', 1, 'ул. Долгиновский тракт, 160', 'rcpt@mail.by', TRUE),
    ('Городская станция переливания крови', 1, 'ул. Уральская, 5', 'gspc@mail.by', TRUE),
    ('1-я городская клиническая больница', 1, 'пр. Независимости, 64', 'gkb1@mail.by', FALSE),
    ('Минская областная клиническая больница', 3, 'ул. Жуковского, 1', 'mokb@mail.by', FALSE),
    ('Брестская областная станция переливания крови', 15, 'г. Брест, ул. Мицкевича, 21', 'brest-blood@mail.by', TRUE),
    ('Гомельская областная станция переливания крови', 19, 'г. Гомель, ул. Пролетарская, 11', 'gomel-blood@mail.by', TRUE),
    ('Гродненская областная станция переливания крови', 24, 'г. Гродно, ул. Ожешко, 9', 'grodno-blood@mail.by', TRUE),
    ('Витебская областная станция переливания крови', 28, 'г. Витебск, ул. Чкалова, 14В', 'vitebsk-blood@mail.by', TRUE),
    ('Могилёвская областная станция переливания крови', 32, 'г. Могилёв, ул. Чехова, 2', 'mogilev-blood@mail.by', TRUE)
ON CONFLICT DO NOTHING;

-- Инициализируем светофор для первого медцентра
INSERT INTO blood_needs (medical_center_id, blood_type, status) VALUES
    (1, 'O+', 'normal'),
    (1, 'O-', 'low'),
    (1, 'A+', 'normal'),
    (1, 'A-', 'critical'),
    (1, 'B+', 'normal'),
    (1, 'B-', 'low'),
    (1, 'AB+', 'normal'),
    (1, 'AB-', 'normal')
ON CONFLICT DO NOTHING;

SELECT 'База данных Твой Донор создана!' as message;
