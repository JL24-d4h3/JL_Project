-- ============================================================
-- Migración: Review workflow (pending / rejected)
-- Fecha: 2026-03-09
-- Aplicar con: psql -U postgres cdn_dev -f scripts/migrate_review_workflow.sql
-- ============================================================

BEGIN;

-- 1. Eliminar el CHECK constraint antiguo del status
ALTER TABLE content DROP CONSTRAINT IF EXISTS content_status_check;

-- 2. Cambiar el default a 'pending' (los uploads nuevos esperan revisión)
ALTER TABLE content ALTER COLUMN status SET DEFAULT 'pending';

-- 3. Añadir columna para el motivo de rechazo
ALTER TABLE content ADD COLUMN IF NOT EXISTS rejected_reason TEXT;

-- 4. Agregar el nuevo CHECK constraint con todos los valores válidos
ALTER TABLE content
  ADD CONSTRAINT content_status_check
    CHECK (status IN ('pending', 'active', 'rejected', 'archived', 'processing', 'failed'));

-- Verificar resultado
SELECT column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'content'
  AND column_name IN ('status', 'rejected_reason')
ORDER BY column_name;

COMMIT;
