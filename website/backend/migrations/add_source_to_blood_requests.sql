-- ============================================
-- Добавление поля source в blood_requests
-- Для отслеживания источника создания запроса
-- ============================================

-- Добавить колонку source (источник создания)
ALTER TABLE blood_requests 
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual';

-- Комментарий для ясности
COMMENT ON COLUMN blood_requests.source IS 'Источник создания: manual (вручную), traffic_light (из светофора)';

-- Обновить существующие записи, которые были созданы из светофора
-- (определяем по описанию)
UPDATE blood_requests 
SET source = 'traffic_light' 
WHERE description LIKE '%Автоматический запрос из светофора%' 
  AND source = 'manual';

-- Создать индекс для быстрой фильтрации
CREATE INDEX IF NOT EXISTS idx_blood_requests_source ON blood_requests(source);

-- Вывести статистику
SELECT 
    source,
    COUNT(*) as count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed
FROM blood_requests
GROUP BY source;
