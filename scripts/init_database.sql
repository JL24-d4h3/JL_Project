-- ============================================
-- Script de Inicialización - CDN Offline
-- Ejecutar como usuario postgres primero, luego como cdn_user
-- ============================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Para búsqueda difusa
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- Para búsqueda sin acentos

-- ============================================
-- 1. TABLA: users
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'admin', 'superadmin')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================
-- 2. TABLA: categories
-- ============================================
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

-- ============================================
-- 3. TABLA: tags
-- ============================================
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);

-- ============================================
-- 4. TABLA: content
-- ============================================
CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('video', 'pdf', 'audio', 'interactive', 'image', 'document')),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    mime_type VARCHAR(100),
    
    duration_seconds INT,
    resolution VARCHAR(20),
    bitrate INT,
    
    thumbnail_path VARCHAR(1000),
    preview_path VARCHAR(1000),
    quality_versions JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    access_count INT DEFAULT 0,
    download_count INT DEFAULT 0,
    average_rating DECIMAL(3,2),
    rating_count INT DEFAULT 0,
    
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing', 'failed')),
    priority INT DEFAULT 5,
    is_featured BOOLEAN DEFAULT false,
    
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    
    deleted_at TIMESTAMP,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_content_category ON content(category_id);
CREATE INDEX idx_content_type ON content(type);
CREATE INDEX idx_content_status ON content(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_hash ON content(file_hash);
CREATE INDEX idx_content_priority ON content(priority);
CREATE INDEX idx_content_created ON content(created_at DESC);
CREATE INDEX idx_content_last_accessed ON content(last_accessed) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_search ON content 
    USING GIN(to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(description, '')));
CREATE INDEX idx_content_title_trgm ON content USING GIN(title gin_trgm_ops);

-- ============================================
-- 5. TABLA: content_tags
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
-- 6. TABLA: permissions
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
    expires_at TIMESTAMP,
    UNIQUE(user_id, content_id)
);

CREATE INDEX idx_permissions_user ON permissions(user_id);
CREATE INDEX idx_permissions_content ON permissions(content_id);

-- ============================================
-- 7. TABLA: access_log
-- ============================================
CREATE TABLE access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    duration_watched INT,
    completed BOOLEAN DEFAULT false,
    quality_requested VARCHAR(20),
    bytes_transferred BIGINT
);

CREATE INDEX idx_access_log_content ON access_log(content_id);
CREATE INDEX idx_access_log_user ON access_log(user_id);
CREATE INDEX idx_access_log_time ON access_log(accessed_at DESC);

-- ============================================
-- 8. TABLA: storage_stats
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
-- 9. TABLA: eviction_log
-- ============================================
CREATE TABLE eviction_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID,
    content_title VARCHAR(500),
    reason VARCHAR(100),
    file_size BIGINT,
    last_accessed TIMESTAMP,
    access_count INT,
    evicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evicted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    archived_path VARCHAR(1000)
);

CREATE INDEX idx_eviction_log_date ON eviction_log(evicted_at DESC);

-- ============================================
-- 10. TABLA: sync_status
-- ============================================
CREATE TABLE sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL,
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

-- ============================================
-- TRIGGERS Y FUNCIONES
-- ============================================

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para incrementar contador de accesos
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

-- Función para actualizar uso de tags
CREATE OR REPLACE FUNCTION update_tag_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tag_usage_insert AFTER INSERT ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

CREATE TRIGGER update_tag_usage_delete AFTER DELETE ON content_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage();

-- ============================================
-- DATOS INICIALES
-- ============================================

-- Categorías de ejemplo
INSERT INTO categories (name, slug, description, color, display_order) VALUES
    ('Matemáticas', 'matematicas', 'Contenido de matemáticas', '#3B82F6', 1),
    ('Ciencias', 'ciencias', 'Contenido de ciencias naturales', '#10B981', 2),
    ('Lenguaje', 'lenguaje', 'Literatura y comunicación', '#F59E0B', 3),
    ('Historia', 'historia', 'Historia y geografía', '#8B5CF6', 4),
    ('Inglés', 'ingles', 'Idioma inglés', '#EC4899', 5);

-- Usuario administrador inicial (contraseña configurada en .env)
-- Hash generado con bcrypt (ver .env para la contraseña default)
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
    ('admin', 'admin@cdn.local', '$2b$10$rBV2kHf14.6kJ5mLHV9Que2V5q9J0qJ8qV5q9J0qJ8qV5q9J0qJ8q', 'Administrador Sistema', 'superadmin');

-- Tags comunes
INSERT INTO tags (name, slug) VALUES
    ('Tutorial', 'tutorial'),
    ('Ejercicios', 'ejercicios'),
    ('Teórico', 'teorico'),
    ('Práctico', 'practico'),
    ('Avanzado', 'avanzado'),
    ('Básico', 'basico');

-- Verificación
\echo '============================================'
\echo 'Tablas creadas exitosamente:'
\echo '============================================'
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

\echo ''
\echo '============================================'
\echo 'Conteo de registros iniciales:'
\echo '============================================'
SELECT 'categories' as tabla, COUNT(*) as registros FROM categories
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'tags', COUNT(*) FROM tags;
