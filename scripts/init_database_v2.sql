-- ================================================
-- CDN OFFLINE - DATABASE SCHEMA v2.0
-- Sistema de distribución de contenido educativo
-- Con soporte para edge servers y replicación
-- ================================================

-- ================================================
-- EXTENSIONES
-- ================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Búsqueda difusa
CREATE EXTENSION IF NOT EXISTS "unaccent";     -- Búsqueda sin acentos
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- Para encriptación

-- ================================================
-- MÓDULO 1: GESTIÓN DE USUARIOS Y AUTENTICACIÓN
-- ================================================

-- Tabla: users
-- Usuarios del sistema con roles RBAC
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'admin', 'superadmin')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

COMMENT ON TABLE users IS 'Usuarios del sistema con roles RBAC';
COMMENT ON COLUMN users.role IS 'student: solo lectura, teacher: lectura+subida, admin: gestión completa, superadmin: todo';
COMMENT ON COLUMN users.locked_until IS 'Bloqueo temporal tras múltiples intentos fallidos';

-- Tabla: sessions
-- Sesiones activas con JWT tokens
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token_hash);
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE is_active = true;

COMMENT ON TABLE sessions IS 'Tokens JWT activos para gestión de sesiones';

-- ================================================
-- MÓDULO 2: ORGANIZACIÓN DE CONTENIDO
-- ================================================

-- Tabla: categories
-- Categorías jerárquicas (árbol)
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    icon VARCHAR(100),
    color VARCHAR(7),
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_slug ON categories(slug);
CREATE INDEX idx_categories_active ON categories(is_active) WHERE is_active = true;

COMMENT ON TABLE categories IS 'Categorías jerárquicas tipo Matemáticas > Álgebra > Ecuaciones';

-- Tabla: tags
-- Etiquetas para clasificación transversal
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_usage ON tags(usage_count DESC);

COMMENT ON TABLE tags IS 'Tags como "básico", "tutorial", "ejercicios"';

-- ================================================
-- MÓDULO 3: CONTENIDO PRINCIPAL
-- ================================================

-- Tabla: content
-- Archivos educativos (videos, PDFs, etc.)
CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('video', 'pdf', 'audio', 'interactive', 'image', 'document')),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    
    -- Archivo físico
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    mime_type VARCHAR(100),
    
    -- Metadatos multimedia
    duration_seconds INT,
    resolution VARCHAR(20),
    bitrate INT,
    
    -- Previews
    thumbnail_path VARCHAR(1000),
    preview_path VARCHAR(1000),
    quality_versions JSONB DEFAULT '{}',
    
    -- Cache control (NUEVO)
    cache_control VARCHAR(200) DEFAULT 'public, max-age=31536000',
    etag VARCHAR(64),
    ttl INT DEFAULT 31536000, -- 1 año en segundos
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata flexible
    metadata JSONB DEFAULT '{}',
    
    -- Estadísticas
    access_count INT DEFAULT 0,
    download_count INT DEFAULT 0,
    average_rating DECIMAL(3,2),
    rating_count INT DEFAULT 0,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'rejected', 'archived', 'processing', 'failed')),
    rejected_reason TEXT,
    priority INT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    is_featured BOOLEAN DEFAULT false,
    
    -- Auditoría
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    
    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_content_category ON content(category_id);
CREATE INDEX idx_content_type ON content(type);
CREATE INDEX idx_content_status ON content(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_hash ON content(file_hash);
CREATE INDEX idx_content_etag ON content(etag) WHERE etag IS NOT NULL;
CREATE INDEX idx_content_priority ON content(priority);
CREATE INDEX idx_content_created ON content(created_at DESC);
CREATE INDEX idx_content_last_accessed ON content(last_accessed) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_featured ON content(is_featured) WHERE is_featured = true AND deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_content_search ON content 
    USING GIN(to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(description, '')));
CREATE INDEX idx_content_title_trgm ON content USING GIN(title gin_trgm_ops);

COMMENT ON TABLE content IS 'Contenido educativo con soporte para cache HTTP';
COMMENT ON COLUMN content.cache_control IS 'Directiva Cache-Control para HTTP responses';
COMMENT ON COLUMN content.etag IS 'Entity tag para validación de cache';
COMMENT ON COLUMN content.ttl IS 'Time to live en segundos para invalidación de cache';

-- Tabla: content_tags
-- Relación many-to-many
CREATE TABLE content_tags (
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (content_id, tag_id)
);

CREATE INDEX idx_content_tags_content ON content_tags(content_id);
CREATE INDEX idx_content_tags_tag ON content_tags(tag_id);

-- ================================================
-- MÓDULO 4: INFRAESTRUCTURA DISTRIBUIDA (NUEVO)
-- ================================================

-- Tabla: availability_zones
-- Zonas geográficas para replicación
CREATE TABLE availability_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    region VARCHAR(50) NOT NULL CHECK (region IN ('costa', 'sierra', 'selva')),
    country_code VARCHAR(2) DEFAULT 'PE',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    priority INT DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_zones_region ON availability_zones(region);
CREATE INDEX idx_zones_active ON availability_zones(is_active) WHERE is_active = true;

COMMENT ON TABLE availability_zones IS 'Zonas geográficas: Lima (costa), Cusco (sierra), Iquitos (selva)';
COMMENT ON COLUMN availability_zones.priority IS 'Prioridad de replicación: 10=crítico, 5=normal, 1=bajo';

-- Tabla: storage_nodes
-- Servidores edge para distribución
CREATE TABLE storage_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    hostname VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET NOT NULL,
    port INT DEFAULT 3000,
    zone_id UUID REFERENCES availability_zones(id) ON DELETE SET NULL,
    
    -- Capacidad
    total_capacity_bytes BIGINT NOT NULL,
    used_capacity_bytes BIGINT DEFAULT 0,
    available_capacity_bytes BIGINT,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'online' CHECK (status IN ('online', 'offline', 'maintenance', 'degraded')),
    health_score INT DEFAULT 100 CHECK (health_score BETWEEN 0 AND 100),
    
    -- Conectividad
    latency_ms INT,
    bandwidth_mbps INT,
    
    -- Metadata
    node_type VARCHAR(50) DEFAULT 'edge' CHECK (node_type IN ('origin', 'edge', 'backup')),
    version VARCHAR(50),
    last_heartbeat TIMESTAMP,
    
    -- Auditoría
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_nodes_zone ON storage_nodes(zone_id);
CREATE INDEX idx_nodes_status ON storage_nodes(status);
CREATE INDEX idx_nodes_health ON storage_nodes(health_score DESC);
CREATE INDEX idx_nodes_heartbeat ON storage_nodes(last_heartbeat DESC);
CREATE INDEX idx_nodes_type ON storage_nodes(node_type);

COMMENT ON TABLE storage_nodes IS 'Servidores edge para replicar contenido cerca de los usuarios';
COMMENT ON COLUMN storage_nodes.node_type IS 'origin=servidor principal, edge=cache periférico, backup=respaldo';
COMMENT ON COLUMN storage_nodes.health_score IS '100=perfecto, 0=caído. Basado en latencia, errores, carga';

-- Tabla: content_availability
-- Qué contenido está en qué zona/nodo
CREATE TABLE content_availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    node_id UUID REFERENCES storage_nodes(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES availability_zones(id) ON DELETE CASCADE,
    
    -- Estado de replicación
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'syncing', 'synced', 'failed', 'deleted')),
    replica_path VARCHAR(1000),
    
    -- Validación
    checksum_verified BOOLEAN DEFAULT false,
    last_verification TIMESTAMP,
    
    -- Sincronización
    sync_priority INT DEFAULT 5,
    sync_started_at TIMESTAMP,
    sync_completed_at TIMESTAMP,
    sync_error TEXT,
    retry_count INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(content_id, node_id)
);

CREATE INDEX idx_availability_content ON content_availability(content_id);
CREATE INDEX idx_availability_node ON content_availability(node_id);
CREATE INDEX idx_availability_zone ON content_availability(zone_id);
CREATE INDEX idx_availability_status ON content_availability(status);
CREATE INDEX idx_availability_priority ON content_availability(sync_priority DESC);

COMMENT ON TABLE content_availability IS 'Mapea qué contenido está disponible en qué servidores';

-- Tabla: health_checks
-- Registro de salud de nodos
CREATE TABLE health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID REFERENCES storage_nodes(id) ON DELETE CASCADE,
    
    -- Métricas
    status VARCHAR(50) NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy', 'unreachable')),
    response_time_ms INT,
    cpu_usage_percent DECIMAL(5,2),
    memory_usage_percent DECIMAL(5,2),
    disk_usage_percent DECIMAL(5,2),
    
    -- Conectividad
    http_status_code INT,
    error_message TEXT,
    
    -- Metadata
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checked_by VARCHAR(100) DEFAULT 'system',
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_health_node ON health_checks(node_id);
CREATE INDEX idx_health_time ON health_checks(checked_at DESC);
CREATE INDEX idx_health_status ON health_checks(status);

COMMENT ON TABLE health_checks IS 'Historial de health checks cada 30 segundos';
COMMENT ON COLUMN health_checks.status IS 'healthy: OK, degraded: lento, unhealthy: errores, unreachable: offline';

-- ================================================
-- MÓDULO 5: PERMISOS Y SEGURIDAD
-- ================================================

-- Tabla: permissions
-- Permisos granulares por usuario-contenido
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    can_read BOOLEAN DEFAULT true,
    can_update BOOLEAN DEFAULT false,
    can_delete BOOLEAN DEFAULT false,
    can_share BOOLEAN DEFAULT false,
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(user_id, content_id)
);

CREATE INDEX idx_permissions_user ON permissions(user_id);
CREATE INDEX idx_permissions_content ON permissions(content_id);
CREATE INDEX idx_permissions_expires ON permissions(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE permissions IS 'Permisos individuales que sobrescriben el RBAC general';

-- ================================================
-- MÓDULO 6: ANALYTICS Y LOGS
-- ================================================

-- Tabla: access_log
-- Registro de accesos para analytics
CREATE TABLE access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    node_id UUID REFERENCES storage_nodes(id) ON DELETE SET NULL,
    
    -- Request info
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    
    -- Video metrics
    duration_watched INT,
    completed BOOLEAN DEFAULT false,
    quality_requested VARCHAR(20),
    
    -- Transfer metrics
    bytes_transferred BIGINT,
    cache_hit BOOLEAN DEFAULT false,
    response_time_ms INT,
    http_status INT
);

CREATE INDEX idx_access_content ON access_log(content_id);
CREATE INDEX idx_access_user ON access_log(user_id);
CREATE INDEX idx_access_node ON access_log(node_id);
CREATE INDEX idx_access_time ON access_log(accessed_at DESC);
CREATE INDEX idx_access_cache ON access_log(cache_hit);

COMMENT ON TABLE access_log IS 'Logs de acceso para analytics y troubleshooting';
COMMENT ON COLUMN access_log.cache_hit IS 'true: servido desde cache, false: desde origen';

-- Tabla: storage_stats
-- Snapshots diarios de capacidad
CREATE TABLE storage_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID REFERENCES storage_nodes(id) ON DELETE CASCADE,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    
    -- Capacidad
    total_bytes BIGINT,
    used_bytes BIGINT,
    available_bytes BIGINT,
    
    -- Contadores
    file_count INT,
    video_count INT,
    document_count INT,
    
    -- Referencias
    largest_file_id UUID REFERENCES content(id),
    oldest_access_date TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, snapshot_date)
);

CREATE INDEX idx_storage_stats_node ON storage_stats(node_id);
CREATE INDEX idx_storage_stats_date ON storage_stats(snapshot_date DESC);

COMMENT ON TABLE storage_stats IS 'Estadísticas diarias de almacenamiento por nodo';

-- Tabla: eviction_log
-- Registro de contenido eliminado
CREATE TABLE eviction_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID,
    node_id UUID REFERENCES storage_nodes(id) ON DELETE SET NULL,
    content_title VARCHAR(500),
    reason VARCHAR(100) CHECK (reason IN ('lru', 'lfu', 'manual', 'expired', 'corrupted')),
    file_size BIGINT,
    last_accessed TIMESTAMP,
    access_count INT,
    evicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evicted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    archived_path VARCHAR(1000)
);

CREATE INDEX idx_eviction_date ON eviction_log(evicted_at DESC);
CREATE INDEX idx_eviction_node ON eviction_log(node_id);
CREATE INDEX idx_eviction_reason ON eviction_log(reason);

COMMENT ON TABLE eviction_log IS 'Auditoría de contenido eliminado por políticas LRU';

-- ================================================
-- MÓDULO 7: FUNCIONES Y TRIGGERS
-- ================================================

-- Función: Actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_nodes_updated_at BEFORE UPDATE ON storage_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_availability_updated_at BEFORE UPDATE ON content_availability
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función: Generar ETag automáticamente
CREATE OR REPLACE FUNCTION generate_etag()
RETURNS TRIGGER AS $$
BEGIN
    NEW.etag = encode(digest(NEW.file_hash || NEW.updated_at::text, 'sha256'), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_content_etag BEFORE INSERT OR UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION generate_etag();

-- Función: Incrementar contador de accesos
CREATE OR REPLACE FUNCTION increment_access_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE content 
    SET 
        access_count = access_count + 1,
        last_accessed = CURRENT_TIMESTAMP
    WHERE id = NEW.content_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_increment_access AFTER INSERT ON access_log
    FOR EACH ROW EXECUTE FUNCTION increment_access_count();

-- Función: Actualizar uso de tags
CREATE OR REPLACE FUNCTION update_tag_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tag_insert AFTER INSERT ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

CREATE TRIGGER trg_tag_delete AFTER DELETE ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

-- Función: Actualizar capacidad disponible en nodo
CREATE OR REPLACE FUNCTION update_node_capacity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE storage_nodes
    SET 
        available_capacity_bytes = total_capacity_bytes - used_capacity_bytes,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_node_capacity AFTER INSERT OR UPDATE OF used_capacity_bytes ON storage_nodes
    FOR EACH ROW EXECUTE FUNCTION update_node_capacity();

-- Función: Actualizar health score basado en checks
CREATE OR REPLACE FUNCTION update_node_health_score()
RETURNS TRIGGER AS $$
DECLARE
    avg_response_time INT;
    recent_failures INT;
    new_score INT;
BEGIN
    -- Calcular promedio de response time en últimos 10 checks
    SELECT AVG(response_time_ms)::INT INTO avg_response_time
    FROM (
        SELECT response_time_ms 
        FROM health_checks 
        WHERE node_id = NEW.node_id 
        ORDER BY checked_at DESC 
        LIMIT 10
    ) recent;
    
    -- Contar fallos recientes
    SELECT COUNT(*) INTO recent_failures
    FROM health_checks
    WHERE node_id = NEW.node_id 
      AND status IN ('unhealthy', 'unreachable')
      AND checked_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes';
    
    -- Calcular score
    new_score := 100;
    
    -- Penalizar por latencia
    IF avg_response_time > 1000 THEN
        new_score := new_score - 30;
    ELSIF avg_response_time > 500 THEN
        new_score := new_score - 15;
    ELSIF avg_response_time > 200 THEN
        new_score := new_score - 5;
    END IF;
    
    -- Penalizar por fallos
    new_score := new_score - (recent_failures * 20);
    
    -- Garantizar rango [0, 100]
    new_score := GREATEST(0, LEAST(100, new_score));
    
    -- Actualizar nodo
    UPDATE storage_nodes
    SET 
        health_score = new_score,
        status = CASE
            WHEN new_score >= 80 THEN 'online'
            WHEN new_score >= 50 THEN 'degraded'
            ELSE 'offline'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.node_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_health AFTER INSERT ON health_checks
    FOR EACH ROW EXECUTE FUNCTION update_node_health_score();

-- ================================================
-- MÓDULO 8: VISTAS ÚTILES
-- ================================================

-- Vista: Contenido popular
CREATE VIEW v_popular_content AS
SELECT 
    c.id,
    c.title,
    c.type,
    cat.name as category,
    c.access_count,
    c.average_rating,
    c.file_size,
    u.full_name as created_by_name,
    COUNT(DISTINCT ca.node_id) as replicas_count
FROM content c
LEFT JOIN categories cat ON c.category_id = cat.id
LEFT JOIN users u ON c.created_by = u.id
LEFT JOIN content_availability ca ON c.id = ca.content_id AND ca.status = 'synced'
WHERE c.deleted_at IS NULL AND c.status = 'active'
GROUP BY c.id, cat.name, u.full_name
ORDER BY c.access_count DESC;

-- Vista: Estado de nodos
CREATE VIEW v_nodes_status AS
SELECT 
    sn.id,
    sn.name,
    sn.hostname,
    az.name as zone,
    az.region,
    sn.status,
    sn.health_score,
    sn.total_capacity_bytes,
    sn.used_capacity_bytes,
    sn.available_capacity_bytes,
    ROUND((sn.used_capacity_bytes::float / sn.total_capacity_bytes * 100)::numeric, 2) as usage_percent,
    COUNT(ca.id) as content_count,
    sn.last_heartbeat,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - sn.last_heartbeat))::INT as seconds_since_heartbeat
FROM storage_nodes sn
LEFT JOIN availability_zones az ON sn.zone_id = az.id
LEFT JOIN content_availability ca ON sn.id = ca.node_id AND ca.status = 'synced'
GROUP BY sn.id, sn.name, sn.hostname, az.name, az.region;

-- Vista: Candidatos para eviction
CREATE VIEW v_eviction_candidates AS
SELECT 
    c.id,
    c.title,
    c.file_size,
    c.access_count,
    c.last_accessed,
    c.priority,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - c.last_accessed)) / 86400.0 as days_since_access,
    (c.access_count::float / GREATEST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - c.last_accessed)) / 86400.0, 1.0)) * c.priority as retention_score,
    COUNT(ca.node_id) as replica_count
FROM content c
LEFT JOIN content_availability ca ON c.id = ca.content_id AND ca.status = 'synced'
WHERE c.deleted_at IS NULL 
  AND c.status = 'active'
  AND c.priority < 10
GROUP BY c.id
ORDER BY retention_score ASC;

-- Vista: Dashboard del sistema
CREATE VIEW v_system_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM content WHERE deleted_at IS NULL) as total_content,
    (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
    (SELECT COUNT(*) FROM storage_nodes WHERE status = 'online') as healthy_nodes,
    (SELECT SUM(file_size) FROM content WHERE deleted_at IS NULL) as total_storage_bytes,
    (SELECT COUNT(*) FROM access_log WHERE accessed_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as accesses_today,
    (SELECT AVG(response_time_ms)::INT FROM health_checks WHERE checked_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') as avg_response_time_ms;

-- ================================================
-- MÓDULO 9: DATOS INICIALES
-- ================================================

-- Zona de disponibilidad por defecto (local)
INSERT INTO availability_zones (name, slug, region, latitude, longitude, priority, metadata) VALUES
    ('Lima Centro', 'lima-centro', 'costa', -12.046374, -77.042793, 10, '{"city": "Lima", "datacenter": "primary"}'),
    ('Cusco', 'cusco', 'sierra', -13.531950, -71.967463, 8, '{"city": "Cusco", "datacenter": "secondary"}'),
    ('Iquitos', 'iquitos', 'selva', -3.749220, -73.253140, 7, '{"city": "Iquitos", "datacenter": "edge"}');

-- Nodo principal de almacenamiento
INSERT INTO storage_nodes (
    name, hostname, ip_address, port, zone_id,
    total_capacity_bytes, used_capacity_bytes,
    status, node_type, version
)
SELECT 
    'Servidor Principal', 'localhost', '127.0.0.1'::inet, 3000, id,
    1099511627776, 0, -- 1TB total
    'online', 'origin', '0.1.0'
FROM availability_zones WHERE slug = 'lima-centro';

-- Categorías educativas
INSERT INTO categories (name, slug, description, color, display_order) VALUES
    ('Matemáticas', 'matematicas', 'Contenido de matemáticas', '#3B82F6', 1),
    ('Ciencias', 'ciencias', 'Ciencias naturales y física', '#10B981', 2),
    ('Lenguaje', 'lenguaje', 'Literatura y comunicación', '#F59E0B', 3),
    ('Historia', 'historia', 'Historia y geografía', '#8B5CF6', 4),
    ('Inglés', 'ingles', 'Idioma inglés', '#EC4899', 5);

-- Usuario administrador (password: admin123)
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
    ('admin', 'admin@cdn.local', '$2b$10$UrkYl65IuqZQhVosNm3FT.kJGJMgjDG/NTf9Dvty.p/MY72C6zunu', 'Administrador Sistema', 'superadmin');

-- Tags comunes
INSERT INTO tags (name, slug) VALUES
    ('Tutorial', 'tutorial'),
    ('Ejercicios', 'ejercicios'),
    ('Teórico', 'teorico'),
    ('Práctico', 'practico'),
    ('Avanzado', 'avanzado'),
    ('Básico', 'basico');

-- ================================================
-- VERIFICACIÓN FINAL
-- ================================================

\echo '================================================'
\echo 'DATABASE INITIALIZATION COMPLETED'
\echo '================================================'
\echo ''

\echo 'Tables created:'
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

\echo ''
\echo 'Initial data:'
SELECT 'availability_zones' as tabla, COUNT(*)::text as registros FROM availability_zones
UNION ALL SELECT 'storage_nodes', COUNT(*)::text FROM storage_nodes
UNION ALL SELECT 'categories', COUNT(*)::text FROM categories
UNION ALL SELECT 'users', COUNT(*)::text FROM users
UNION ALL SELECT 'tags', COUNT(*)::text FROM tags;

\echo ''
\echo '================================================'
\echo 'Ready for development!'
\echo 'Default admin user: admin / admin123'
\echo '================================================'
