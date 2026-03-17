-- Migración: convierte la UNIQUE constraint de file_hash a índice único parcial.
-- Un índice parcial (WHERE deleted_at IS NULL) ignora los registros soft-deleted,
-- permitiendo re-subir archivos que fueron eliminados o rechazados.

-- Eliminar la constraint absoluta (bloquea incluso rows con deleted_at IS NOT NULL)
ALTER TABLE content DROP CONSTRAINT IF EXISTS content_file_hash_key;

-- Crear índice único parcial: solo filas "vivas" compiten por el hash
CREATE UNIQUE INDEX IF NOT EXISTS content_file_hash_unique
    ON content(file_hash)
    WHERE deleted_at IS NULL;

SELECT 'Índice único parcial aplicado correctamente.' AS resultado;
