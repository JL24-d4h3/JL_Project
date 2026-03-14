-- init_ai_engine.sql
-- Schema para la integración del AI Engine con el CDN existente.
-- Ejecutar DESPUÉS de init_database.sql (requiere tabla `content`).
--
-- Laptop local:   psql -U cdn_user -d cdn_dev -f scripts/init_ai_engine.sql
-- Jetson producción: psql -U cdn_user -d cdn_prod -f scripts/init_ai_engine.sql

-- ─── Cola de ingesta ────────────────────────────────────────────────────────
-- Registra cada pieza de contenido pendiente de indexación por el AI Engine.
-- El CDN inserta una fila cuando sube un archivo;
-- el AI Engine la consume y actualiza el status.

CREATE TABLE IF NOT EXISTS ai_ingestion_queue (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id    UUID         NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'processing', 'done', 'error')),
    attempts      INT          NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    processed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_queue_status    ON ai_ingestion_queue(status);
CREATE INDEX IF NOT EXISTS idx_ai_queue_content   ON ai_ingestion_queue(content_id);
CREATE INDEX IF NOT EXISTS idx_ai_queue_created   ON ai_ingestion_queue(created_at);

COMMENT ON TABLE  ai_ingestion_queue               IS 'Cola de indexación asíncrona para el AI Engine';
COMMENT ON COLUMN ai_ingestion_queue.status        IS 'pending→processing→done|error';
COMMENT ON COLUMN ai_ingestion_queue.attempts      IS 'Número de intentos de procesamiento (máx 3)';
COMMENT ON COLUMN ai_ingestion_queue.last_error    IS 'Mensaje del último error si status=error';
COMMENT ON COLUMN ai_ingestion_queue.processed_at  IS 'Timestamp cuando se completó o falló definitivamente';


-- ─── Vista de monitoreo ──────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_ingestion_status AS
SELECT
    q.status,
    COUNT(*)           AS total,
    MIN(q.created_at)  AS oldest,
    MAX(q.created_at)  AS newest
FROM   ai_ingestion_queue q
GROUP  BY q.status
ORDER  BY q.status;

COMMENT ON VIEW ai_ingestion_status IS 'Resumen rápido del estado de la cola de indexación';


-- ─── Trigger: marcar processed_at automáticamente ───────────────────────────
CREATE OR REPLACE FUNCTION ai_queue_set_processed_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('done', 'error') AND OLD.status NOT IN ('done', 'error') THEN
        NEW.processed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ai_queue_processed_at ON ai_ingestion_queue;
CREATE TRIGGER trg_ai_queue_processed_at
    BEFORE UPDATE ON ai_ingestion_queue
    FOR EACH ROW EXECUTE FUNCTION ai_queue_set_processed_at();


-- ─── Verificación ────────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE '✓ ai_ingestion_queue creada correctamente';
    RAISE NOTICE '  Ejecutar: SELECT * FROM ai_ingestion_status; para ver estado';
END;
$$;
