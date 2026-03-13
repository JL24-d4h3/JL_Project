# Diseño de Base de Datos - CDN Offline

## 1. Esquema Completo

### 1.1 Diagrama ER (Entidad-Relación)

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    Users    │         │   Content   │         │   Categories│
├─────────────┤         ├─────────────┤         ├─────────────┤
│ id (PK)     │────┐    │ id (PK)     │    ┌────│ id (PK)     │
│ username    │    │    │ title       │    │    │ name        │
│ email       │    │    │ description │────┘    │ slug        │
│ password    │    │    │ category_id │         │ parent_id   │
│ role        │    │    │ file_path   │         │ order       │
│ created_at  │    │    │ file_size   │         └─────────────┘
└─────────────┘    │    │ file_hash   │
       │           │    │ type        │
       │           │    │ created_by  │───┐
       │           │    │ created_at  │   │
       │           │    └─────────────┘   │
       │           │            │         │
       │           │            │         │
       │           │    ┌───────┴──────┐  │
       │           └────│ Permissions  │  │
       │                ├──────────────┤  │
       │                │ id (PK)      │  │
       │           ┌────│ user_id (FK) │  │
       │           │    │ content_id   │  │
       │           │    │ can_read     │  │
       │           │    │ can_update   │  │
       │           │    │ can_delete   │  │
       │           │    └──────────────┘  │
       │           │                      │
       │           │    ┌──────────────┐  │
       │           └────│ Access_Log   │  │
       │                ├──────────────┤  │
       └────────────────│ id (PK)      │  │
                        │ user_id (FK) │  │
                   ┌────│ content_id   │  │
                   │    │ accessed_at  │  │
                   │    │ duration     │  │
                   │    │ device_info  │  │
                   │    └──────────────┘  │
                   │                      │
                   │    ┌──────────────┐  │
                   └────│   Tags       │  │
                        ├──────────────┤  │
                        │ id (PK)      │  │
                        │ name         │  │
                        └──────────────┘  │
                                          │
                        ┌──────────────┐  │
                        │Content_Tags  │  │
                        ├──────────────┤  │
                        │ content_id   │──┘
                        │ tag_id       │
                        └──────────────┘
```

---

## 2. Scripts SQL

### 2.1 Creación de Base de Datos

```sql
-- Crear la base de datos
CREATE DATABASE cdn_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'es_PE.UTF-8'
    LC_CTYPE = 'es_PE.UTF-8'
    TEMPLATE = template0;

-- Conectar a la base
\c cdn_db

-- Habilitar extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Para búsqueda difusa
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- Para búsqueda sin acentos
```

### 2.2 Tablas Principales

```sql
-- ============================================
-- Tabla: users
-- Almacena usuarios del sistema
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt hash
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'admin', 'superadmin')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb -- Datos adicionales flexibles
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================
-- Tabla: categories
-- Categorías jerárquicas de contenido
-- ============================================
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    icon VARCHAR(100), -- Nombre de icono (opcional)
    color VARCHAR(7), -- Color hex (ej: #3B82F6)
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_slug ON categories(slug);

-- Ejemplo de datos:
-- Matemáticas (parent)
--   └─ Álgebra (child)
--   └─ Geometría (child)
-- Ciencias (parent)
--   └─ Física (child)

-- ============================================
-- Tabla: tags
-- Etiquetas para clasificación adicional
-- ============================================
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    usage_count INT DEFAULT 0, -- Cuántos contenidos usan este tag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);

-- ============================================
-- Tabla: content
-- Contenido educativo (videos, PDFs, etc.)
-- ============================================
CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE, -- Para URLs amigables
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('video', 'pdf', 'audio', 'interactive', 'image', 'document')),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    
    -- Información del archivo
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL, -- Bytes
    file_hash VARCHAR(64) NOT NULL, -- SHA-256 para integridad y deduplicación
    mime_type VARCHAR(100),
    
    -- Específico para video/audio
    duration_seconds INT, -- Duración del contenido
    resolution VARCHAR(20), -- ej: 1920x1080 para video original
    bitrate INT, -- kbps
    
    -- Thumbnails y previews
    thumbnail_path VARCHAR(1000),
    preview_path VARCHAR(1000), -- Video corto de preview
    
    -- Versiones de calidad (para videos)
    quality_versions JSONB DEFAULT '{}', 
    -- Ejemplo: {"720p": "/storage/videos/abc/720p.mp4", "480p": "..."}
    
    -- Metadata adicional flexible
    metadata JSONB DEFAULT '{}',
    -- Ejemplo: {"author": "Prof. García", "language": "es", "level": "intermedio"}
    
    -- Estadísticas
    access_count INT DEFAULT 0,
    download_count INT DEFAULT 0,
    average_rating DECIMAL(3,2), -- 0.00 a 5.00
    rating_count INT DEFAULT 0,
    
    -- Estado y prioridad
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing', 'failed')),
    priority INT DEFAULT 5, -- 1=muy baja, 5=normal, 10=muy alta (afecta eviction)
    is_featured BOOLEAN DEFAULT false,
    
    -- Auditoría
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP, -- Para LRU eviction
    
    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Índices para performance
CREATE INDEX idx_content_category ON content(category_id);
CREATE INDEX idx_content_type ON content(type);
CREATE INDEX idx_content_status ON content(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_hash ON content(file_hash); -- Para deduplicación
CREATE INDEX idx_content_priority ON content(priority);
CREATE INDEX idx_content_created ON content(created_at DESC);
CREATE INDEX idx_content_last_accessed ON content(last_accessed) WHERE deleted_at IS NULL;

-- Full-text search index
CREATE INDEX idx_content_search ON content 
    USING GIN(to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(description, '')));

-- Trigger search con similitud (búsqueda difusa)
CREATE INDEX idx_content_title_trgm ON content USING GIN(title gin_trgm_ops);

-- ============================================
-- Tabla: content_tags
-- Relación many-to-many entre content y tags
-- ============================================
CREATE TABLE content_tags (
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (content_id, tag_id)
);

CREATE INDEX idx_content_tags_content ON content_tags(content_id);
CREATE INDEX idx_content_tags_tag ON content_tags(tag_id);

-- ============================================
-- Tabla: permissions
-- Permisos granulares por usuario y contenido
-- ============================================
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
    expires_at TIMESTAMP, -- Opcional: permisos temporales
    UNIQUE(user_id, content_id)
);

CREATE INDEX idx_permissions_user ON permissions(user_id);
CREATE INDEX idx_permissions_content ON permissions(content_id);

-- ============================================
-- Tabla: access_log
-- Registro de accesos y visualizaciones
-- ============================================
CREATE TABLE access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB, -- {device: "laptop", os: "linux", browser: "chrome"}
    duration_watched INT, -- Segundos vistos (para videos)
    completed BOOLEAN DEFAULT false, -- Si completó el video/documento
    quality_requested VARCHAR(20), -- 720p, 480p, etc.
    bytes_transferred BIGINT -- Datos transferidos
);

CREATE INDEX idx_access_log_content ON access_log(content_id);
CREATE INDEX idx_access_log_user ON access_log(user_id);
CREATE INDEX idx_access_log_time ON access_log(accessed_at DESC);

-- Particionamiento opcional para logs (cuando crece mucho)
-- CREATE TABLE access_log_2026_02 PARTITION OF access_log
-- FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- ============================================
-- Tabla: storage_stats
-- Estadísticas de almacenamiento (snapshot diario)
-- ============================================
CREATE TABLE storage_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date DATE DEFAULT CURRENT_DATE,
    total_bytes BIGINT,
    used_bytes BIGINT,
    available_bytes BIGINT,
    file_count INT,
    video_count INT,
    document_count INT,
    largest_file_id UUID REFERENCES content(id),
    oldest_access_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_storage_stats_date ON storage_stats(snapshot_date);

-- ============================================
-- Tabla: eviction_log
-- Registro de contenido eliminado por políticas
-- ============================================
CREATE TABLE eviction_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID, -- No FK porque el content se borrará
    content_title VARCHAR(500),
    reason VARCHAR(100), -- 'lru', 'lfu', 'manual', 'expired'
    file_size BIGINT,
    last_accessed TIMESTAMP,
    access_count INT,
    evicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evicted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    archived_path VARCHAR(1000) -- Si se guardó en backup
);

CREATE INDEX idx_eviction_log_date ON eviction_log(evicted_at DESC);

-- ============================================
-- Tabla: sync_status (para replicación futura)
-- Track de sincronización entre nodos
-- ============================================
CREATE TABLE sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL, -- Identificador del nodo
    status VARCHAR(50) CHECK (status IN ('pending', 'syncing', 'synced', 'failed')),
    priority INT DEFAULT 5,
    last_sync_attempt TIMESTAMP,
    last_successful_sync TIMESTAMP,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, node_id)
);

CREATE INDEX idx_sync_status_node ON sync_status(node_id);
CREATE INDEX idx_sync_status_status ON sync_status(status);
```

---

## 3. Triggers y Funciones

```sql
-- ============================================
-- Function: Actualizar updated_at automáticamente
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar a tablas relevantes
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Function: Actualizar contador de accesos
-- ============================================
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

CREATE TRIGGER update_access_count AFTER INSERT ON access_log
    FOR EACH ROW EXECUTE FUNCTION increment_access_count();

-- ============================================
-- Function: Actualizar uso de tags
-- ============================================
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

CREATE TRIGGER update_tag_usage_on_insert AFTER INSERT ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

CREATE TRIGGER update_tag_usage_on_delete AFTER DELETE ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

-- ============================================
-- Function: Verificar duplicados por hash
-- ============================================
CREATE OR REPLACE FUNCTION check_duplicate_content()
RETURNS TRIGGER AS $$
DECLARE
    existing_content UUID;
BEGIN
    SELECT id INTO existing_content 
    FROM content 
    WHERE file_hash = NEW.file_hash 
      AND deleted_at IS NULL 
      AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid)
    LIMIT 1;
    
    IF existing_content IS NOT NULL THEN
        RAISE NOTICE 'Duplicate content detected: %', existing_content;
        -- Opcional: abortar o permitir con warning
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_duplicate_content_trigger BEFORE INSERT OR UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION check_duplicate_content();
```

---

## 4. Vistas Útiles

```sql
-- ============================================
-- Vista: Contenido más popular
-- ============================================
CREATE VIEW v_popular_content AS
SELECT 
    c.id,
    c.title,
    c.type,
    cat.name as category,
    c.access_count,
    c.average_rating,
    c.created_at,
    u.full_name as created_by_name
FROM content c
LEFT JOIN categories cat ON c.category_id = cat.id
LEFT JOIN users u ON c.created_by = u.id
WHERE c.deleted_at IS NULL AND c.status = 'active'
ORDER BY c.access_count DESC;

-- ============================================
-- Vista: Estadísticas por categoría
-- ============================================
CREATE VIEW v_category_stats AS
SELECT 
    cat.id,
    cat.name,
    COUNT(c.id) as content_count,
    SUM(c.file_size) as total_size_bytes,
    AVG(c.access_count) as avg_access_count,
    SUM(c.access_count) as total_accesses
FROM categories cat
LEFT JOIN content c ON cat.id = c.category_id AND c.deleted_at IS NULL
GROUP BY cat.id, cat.name
ORDER BY content_count DESC;

-- ============================================
-- Vista: Contenido candidato para eviction (LRU)
-- ============================================
CREATE VIEW v_eviction_candidates AS
SELECT 
    c.id,
    c.title,
    c.file_size,
    c.access_count,
    c.last_accessed,
    c.priority,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - c.last_accessed)) / 86400.0 as days_since_access,
    -- Score: menor = mejor candidato
    (c.access_count::float / GREATEST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - c.last_accessed)) / 86400.0, 1.0)) * c.priority as retention_score
FROM content c
WHERE c.deleted_at IS NULL 
  AND c.status = 'active'
  AND c.priority < 10 -- No tocar contenido de alta prioridad
ORDER BY retention_score ASC;

-- ============================================
-- Vista: Dashboard de sistema
-- ============================================
CREATE VIEW v_system_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM content WHERE deleted_at IS NULL) as total_content,
    (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
    (SELECT SUM(file_size) FROM content WHERE deleted_at IS NULL) as total_storage_bytes,
    (SELECT COUNT(*) FROM access_log WHERE accessed_at > CURRENT_TIMESTAMP - INTERVAL '7 days') as accesses_last_week,
    (SELECT AVG(access_count) FROM content WHERE deleted_at IS NULL) as avg_content_popularity;
```

---

## 5. Datos de Prueba (Seed)

```sql
-- ============================================
-- Insertar datos de prueba
-- ============================================

-- Usuarios
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
('admin', 'admin@cdn.local', '$2b$10$HASH...', 'Administrador', 'admin'),
('teacher1', 'teacher@cdn.local', '$2b$10$HASH...', 'Prof. García', 'teacher'),
('student1', 'student@cdn.local', '$2b$10$HASH...', 'Juan Pérez', 'student');

-- Categorías
INSERT INTO categories (name, slug, description, color) VALUES
('Matemáticas', 'matematicas', 'Contenido de matemáticas', '#3B82F6'),
('Ciencias', 'ciencias', 'Contenido de ciencias naturales', '#10B981'),
('Literatura', 'literatura', 'Contenido de literatura y lenguaje', '#F59E0B');

-- Subcategorías
INSERT INTO categories (name, slug, parent_id, color) 
SELECT 'Álgebra', 'algebra', id, '#3B82F6' FROM categories WHERE slug = 'matematicas';

INSERT INTO categories (name, slug, parent_id, color)
SELECT 'Geometría', 'geometria', id, '#3B82F6' FROM categories WHERE slug = 'matematicas';

-- Tags
INSERT INTO tags (name, slug) VALUES
('secundaria', 'secundaria'),
('primaria', 'primaria'),
('básico', 'basico'),
('avanzado', 'avanzado'),
('tutorial', 'tutorial');

-- Contenido de ejemplo (deberás ajustar paths reales)
INSERT INTO content (
    title, slug, description, type, category_id, 
    file_path, file_size, file_hash, duration_seconds,
    thumbnail_path, created_by
)
SELECT 
    'Números Reales - Introducción',
    'numeros-reales-introduccion',
    'Video introductorio sobre números reales y sus propiedades',
    'video',
    id,
    '/storage/videos/sample1/original.mp4',
    52428800, -- 50 MB
    'abc123...',
    600, -- 10 minutos
    '/storage/thumbnails/sample1.jpg',
    (SELECT id FROM users WHERE username = 'teacher1')
FROM categories WHERE slug = 'algebra';
```

---

## 6. Queries de Mantenimiento

```sql
-- Vaciar access_log antiguo (>90 días)
DELETE FROM access_log WHERE accessed_at < CURRENT_DATE - INTERVAL '90 days';

-- Limpiar contenido marcado como eliminado (>30 días)
DELETE FROM content WHERE deleted_at < CURRENT_DATE - INTERVAL '30 days';

-- Actualizar estadísticas
ANALYZE content;
ANALYZE access_log;

-- Reindexar (si performance degrada)
REINDEX TABLE content;

-- Vacuum (recuperar espacio)
VACUUM FULL content;
```

---

## 7. Backup y Restore

```bash
# Backup completo
pg_dump -U postgres -Fc cdn_db > cdn_backup_$(date +%Y%m%d).dump

# Backup solo schema
pg_dump -U postgres -s cdn_db > cdn_schema.sql

# Restore
pg_restore -U postgres -d cdn_db cdn_backup_20260216.dump

# Restore desde SQL
psql -U postgres cdn_db < cdn_schema.sql
```

---

Este diseño de base de datos proporciona:
✅ Escalabilidad para miles de contenidos
✅ Performance optimizado con índices apropiados
✅ Flexibilidad con campos JSONB
✅ Auditoría completa (created_at, updated_at, deleted_at)
✅ Soporte para múltiples tipos de contenido
✅ Sistema de permisos granular
✅ Base para analytics y eviction policies
