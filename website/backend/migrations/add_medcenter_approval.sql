-- ============================================
-- Миграция: Добавление системы подтверждения медцентров
-- ============================================

-- Добавляем поле статуса подтверждения
ALTER TABLE medical_centers 
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'approved';

-- Комментарий к полю
COMMENT ON COLUMN medical_centers.approval_status IS 
'Статус подтверждения: pending (ожидает), approved (подтверждён), rejected (отклонён)';

-- Добавляем индекс для быстрого поиска по статусу
CREATE INDEX IF NOT EXISTS idx_mc_approval_status ON medical_centers(approval_status);

-- Все существующие медцентры считаем подтверждёнными
UPDATE medical_centers SET approval_status = 'approved' WHERE approval_status IS NULL;

-- Готово!
SELECT 'Миграция выполнена: добавлено поле approval_status' as message;
